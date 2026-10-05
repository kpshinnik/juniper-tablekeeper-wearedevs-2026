"""Reservation rules. All writes operate on unpublished, private candidate state."""
import hashlib
import hmac
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import unquote

import exactjson as j
from exactjson import Number

UTC = timezone.utc
SECOND_US = 1_000_000
MINUTE_US = 60 * SECOND_US
DAY_US = 1440 * MINUTE_US
WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
LOCAL = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}\Z')
DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')
CLOCK = re.compile(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z')
REFERENCE = re.compile(r'[A-Z0-9]{6,12}\Z')


class Fault(Exception):
    def __init__(self, status=422, code='validation_failed', message=None):
        self.status, self.code = status, code
        self.message = message or code.replace('_', ' ')
        super().__init__(self.message)


def require(condition, code='validation_failed', status=422):
    if not condition:
        raise Fault(status, code)


def obj(value):
    require(type(value) is dict, 'malformed_request', 400)
    return value


def field(body, key, kind, optional=False):
    if key not in body:
        if optional:
            return None
        raise Fault()
    value = body[key]
    require(type(value) is kind, 'malformed_request', 400)
    return value


def ident(value):
    require(type(value) is str, 'malformed_request', 400)
    require(0 < len(value) <= 64)
    return value


def integer(value, minimum=1, maximum=None, party=False):
    numeric = isinstance(value, Number) or type(value) is int
    require(numeric, 'validation_failed' if party else 'malformed_request', 422 if party else 400)
    value = value if isinstance(value, Number) else Number.parse(value)
    require(value.integral and value >= minimum and (maximum is None or value <= maximum))
    return value


def calendar(value):
    require(type(value) is str, 'malformed_request', 400)
    require(DATE.fullmatch(value))
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Fault() from None


def minute(value):
    require(type(value) is str, 'malformed_request', 400)
    require(CLOCK.fullmatch(value))
    return int(value[:2]) * 60 + int(value[3:])


def opening(value):
    require(type(value) is list, 'malformed_request', 400)
    result, seen = [], set()
    for entry in value:
        obj(entry)
        day = field(entry, 'weekday', str)
        require(day in WEEKDAYS and day not in seen)
        start, end = field(entry, 'opens', str), field(entry, 'closes', str)
        require(minute(start) < minute(end))
        seen.add(day)
        result.append({'weekday': day, 'opens': start, 'closes': end})
    return result


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8', 'surrogatepass'), salt, 120000)
    return 'pbkdf2-sha256$120000$' + salt.hex() + '$' + digest.hex()


def password_matches(password, encoded):
    algorithm, iterations, salt, expected = encoded.split('$')
    if algorithm != 'pbkdf2-sha256' or iterations != '120000':
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8', 'surrogatepass'), bytes.fromhex(salt), 120000)
    return hmac.compare_digest(actual.hex(), expected)


def credentials(body, signup=False):
    email, password = field(body, 'email', str), field(body, 'password', str)
    require(re.fullmatch(r'[^@\s]+@[^@\s]+', email))
    require(len(password) >= 8)
    name = field(body, 'display_name', str) if signup else None
    return email, password, name


def empty_state():
    return {'schema': 1, 'users': {}, 'restaurants': {}, 'reservations': {}, 'tokens': {}, 'receipts': []}


def now():
    return datetime.now(UTC).isoformat()


def delta_us(value):
    return (value.days * 86400 + value.seconds) * SECOND_US + value.microseconds


def wall_us(value):
    return ((value.toordinal() - 1) * DAY_US + value.hour * 60 * MINUTE_US
            + value.minute * MINUTE_US + value.second * SECOND_US + value.microsecond)


def instant(value):
    """Exact UTC microseconds; unlike datetime, the integer can cross year limits."""
    offset = value.utcoffset()
    require(offset is not None)
    return wall_us(value) - delta_us(offset)


def timestamp(value):
    """RFC3339 spelling of an exact instant, including old second offsets.

    Minute-aligned IANA offsets retain their local representation. Historical
    offsets with seconds use UTC when its calendar date is representable. At
    a calendar edge, an adjacent whole-minute offset moves the clock by the
    compensating seconds; the instant is never rounded or clamped.
    """
    local_offset = value.utcoffset()
    require(local_offset is not None)
    offset = delta_us(local_offset)
    if offset % MINUTE_US == 0:
        return value.isoformat()
    point = instant(value)
    lower = offset // MINUTE_US
    for minutes in (0, lower, lower + 1):
        wall = point + minutes * MINUTE_US
        if -1440 < minutes < 1440 and 0 <= wall <= wall_us(datetime.max):
            local = datetime.min + timedelta(microseconds=wall)
            return local.replace(tzinfo=timezone(timedelta(minutes=minutes))).isoformat()
    raise Fault()  # No representable RFC3339 coordinate for the supplied instant.


def local_instant(value, zone, *anchors):
    """Convert an instant back to a representable local datetime.

    ZoneInfo handles normal instants directly. When the intermediate UTC date is
    out of range, invert its local offsets and verify the exact instant instead.
    Offsets from the interval boundaries seed this inversion; discovered offsets
    are also checked, including both folds, without inventing any timezone rule.
    """
    maximum = wall_us(datetime.max)
    if 0 <= value <= maximum:
        try:
            naive_utc = datetime.min + timedelta(microseconds=value)
            return zone.fromutc(naive_utc.replace(tzinfo=zone))
        except OverflowError:
            pass
    offsets = [a.replace(fold=fold).utcoffset() for a in anchors for fold in (0, 1)]
    visited = set()
    while offsets:
        offset = offsets.pop()
        amount = delta_us(offset)
        if amount in visited:
            continue
        visited.add(amount)
        local_value = value + amount
        if not 0 <= local_value <= maximum:
            continue
        naive = datetime.min + timedelta(microseconds=local_value)
        first, second = (naive.replace(tzinfo=zone, fold=fold) for fold in (0, 1))
        offsets.extend([first.utcoffset(), second.utcoffset()])
        if first.utcoffset() < second.utcoffset():
            continue  # The guessed local wall time is in a forward gap.
        for candidate_time in (first, second):
            if instant(candidate_time) == value:
                return candidate_time
    raise Fault(422, 'outside_opening_hours')


def utc(value):
    """Parse an explicit-offset timestamp into its exact, unbounded instant."""
    try:
        dt = datetime.fromisoformat(value)
        require(dt.tzinfo is not None)
        return instant(dt)
    except (TypeError, ValueError, OverflowError):
        raise Fault() from None


def resolve(local, zone):
    require(type(local) is str, 'malformed_request', 400)
    require(LOCAL.fullmatch(local))
    try:
        naive = datetime.fromisoformat(local)
        dt = naive.replace(tzinfo=ZoneInfo(zone), fold=0)
        # ZoneInfo supplies pre/post offsets for a gap and first/second offsets
        # for a fold. Only a forward gap has fold0's offset below fold1's.
        # This does not need an intermediate UTC datetime near calendar limits.
        valid = dt.utcoffset() >= dt.replace(fold=1).utcoffset()
        require(valid, 'invalid_local_time')
        return dt
    except (ValueError, OverflowError):
        raise Fault() from None


def restaurant(state, rid):
    ident(rid)
    require(rid in state['restaurants'], 'not_found', 404)
    return state['restaurants'][rid]


def booking(state, reference, user):
    value = state['reservations'].get(reference)
    require(value is not None and value['user_id'] == user, 'not_found', 404)
    return value


def public(value):
    result = {k: v for k, v in value.items() if k != 'user_id'}
    # Existing snapshots may contain the former ISO offset-second spelling.
    # Read projection fixes current output without editing stored timestamps or
    # original receipt JSON. Idempotent replay bypasses this projection.
    for key in ('starts_at', 'ends_at'):
        result[key] = timestamp(datetime.fromisoformat(result[key]))
    result['table_ids'] = list(tables(value))
    if len(result['table_ids']) == 1:
        result['table_id'] = result['table_ids'][0]
    else:
        result.pop('table_id', None)
    return result


def tables(value):
    return value['table_ids'] if 'table_ids' in value else [value['table_id']]


def combinations(rest):
    value = rest.get('combinable', [])
    require(type(value) is list, 'malformed_request', 400)
    known, seen = {t['id'] for t in rest['tables']}, set()
    for pair in value:
        require(type(pair) is list, 'malformed_request', 400)
        require(len(pair) == 2)
        ids = [ident(t) for t in pair]
        require(len(set(ids)) == 2 and set(ids) <= known and frozenset(ids) not in seen)
        seen.add(frozenset(ids))
    return value


def selection(rest, body, old=None):
    require(not ('table_id' in body and 'table_ids' in body))
    if 'table_ids' in body:
        ids = field(body, 'table_ids', list)
    elif 'table_id' in body:
        ids = [field(body, 'table_id', str)]
    elif old is not None:
        ids = tables(old)
    else:
        raise Fault()
    ids = [ident(value) for value in ids]
    require(bool(ids) and len(set(ids)) == len(ids))
    require(len(ids) <= 2, 'combination_not_allowed')
    require(set(ids) <= {t['id'] for t in rest['tables']}, 'not_found', 404)
    if len(ids) == 2:
        ordered = next((p for p in rest.get('combinable', []) if set(p) == set(ids)), None)
        require(ordered is not None, 'combination_not_allowed')
        ids = ordered
    return list(ids)


def capacity(rest, ids):
    values = [next(t['capacity'] for t in rest['tables'] if t['id'] == ident) for ident in ids]
    return values[0] if len(values) == 1 else j.add_integers(*values)


def record_request(record):
    """An internal dual-alias single record is not a dual-field client request."""
    body = dict(record)
    if 'table_ids' in body:
        require(type(body['table_ids']) is list)
        if 'table_id' in body:
            require(body['table_ids'] == [body['table_id']])
            del body['table_id']
    return body


def bounds(rest, day):
    row = next((x for x in rest['opening_hours'] if x['weekday'] == WEEKDAYS[day.weekday()]), None)
    if row is None:
        return None
    # Opening/closing hours are wall-clock boundaries, not requested starts.
    # A boundary in a DST gap must not invalidate the rest of that open day.
    # fold=0 retains the first-occurrence upper bound when closing is repeated.
    zone = ZoneInfo(rest['timezone'])
    start = datetime.fromisoformat(day.isoformat() + 'T' + row['opens']).replace(tzinfo=zone, fold=0)
    end = datetime.fromisoformat(day.isoformat() + 'T' + row['closes']).replace(tzinfo=zone, fold=0)
    return row, start, end


def interval(rest, local):
    start = resolve(local, rest['timezone'])
    day = start.date()
    limits = bounds(rest, day)
    require(limits is not None, 'outside_opening_hours')
    row, opens, closes = limits
    delta = minute(local[11:]) - minute(row['opens'])
    require(delta >= 0 and start.replace(tzinfo=None) < closes.replace(tzinfo=None)
            and instant(start) < instant(closes), 'outside_opening_hours')
    step = rest['slot_minutes']
    require(delta == 0 or (step <= delta and delta % step.small_int(1440) == 0), 'not_on_slot_grid')
    remaining = (instant(closes) - instant(start)) // MINUTE_US
    duration = rest['reservation_duration_minutes']
    require(duration <= remaining, 'outside_opening_hours')
    end = local_instant(instant(start) + duration.small_int(2880) * MINUTE_US, start.tzinfo, start, closes)
    require(end.replace(tzinfo=None) <= closes.replace(tzinfo=None), 'outside_opening_hours')
    return start, end


def candidate(state, body, old=None):
    obj(body)
    rid = old['restaurant_id'] if old else ident(field(body, 'restaurant_id', str))
    rest = restaurant(state, rid)
    ids = selection(rest, body, old)
    local = body.get('starts_at_local', old['starts_at_local'] if old else None)
    if local is None and 'starts_at_local' not in body:
        raise Fault()
    party = body.get('party_size', old['party_size'] if old else None)
    party = integer(party, party=True)
    start, end = interval(rest, local)
    require(capacity(rest, ids) >= party, 'party_exceeds_capacity')
    result = dict(old) if old else {'reservation_id': 'res_' + secrets.token_hex(12),
                                   'reference': new_reference(state), 'created_at': now(), 'status': 'confirmed'}
    result.update(restaurant_id=rid, table_ids=ids, starts_at_local=local, party_size=party,
                  starts_at=timestamp(start), ends_at=timestamp(end))
    if len(ids) == 1:
        result['table_id'] = ids[0]
    else:
        result.pop('table_id', None)
    return result


def new_reference(state):
    while True:
        value = secrets.token_hex(5).upper()
        if value not in state['reservations']:
            return value


def overlap(a, b):
    return utc(a['starts_at']) < utc(b['ends_at']) and utc(b['starts_at']) < utc(a['ends_at'])


def free(state, reservation, excluded=()):
    return all(not (other['status'] == 'confirmed' and reference not in excluded
                    and other['restaurant_id'] == reservation['restaurant_id']
                    and set(tables(other)).intersection(tables(reservation)) and overlap(other, reservation))
               for reference, other in state['reservations'].items())


def editable(state, reservation):
    require(reservation['status'] != 'cancelled', 'reservation_cancelled', 409)
    cutoff = state['restaurants'][reservation['restaurant_id']]['cancellation_cutoff_minutes']
    whole_minutes, fraction = divmod(utc(reservation['starts_at']) - instant(datetime.now(UTC)), MINUTE_US)
    # Compare exact integer units before materializing any huge compact cutoff.
    require(cutoff < whole_minutes or (cutoff == whole_minutes and fraction > 0), 'cutoff_passed', 409)


def reset(body):
    obj(body)
    reservations = field(body, 'reservations', list) if 'reservations' in body else []
    state = empty_state()
    for u in field(body, 'users', list):
        obj(u)
        uid = ident(field(u, 'id', str))
        email, password, name = credentials(u, True)
        require(uid not in state['users'] and not any(x['email'] == email for x in state['users'].values()))
        state['users'][uid] = {'id': uid, 'email': email, 'display_name': name, 'password_hash': password_hash(password)}
    for r in field(body, 'restaurants', list):
        obj(r)
        rid, zone = ident(field(r, 'id', str)), field(r, 'timezone', str)
        require(rid not in state['restaurants'])
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError):
            raise Fault() from None
        result = {'id': rid, 'name': field(r, 'name', str), 'timezone': zone,
                  'opening_hours': opening(field(r, 'opening_hours', list)), 'tables': []}
        for key in ['slot_minutes', 'reservation_duration_minutes', 'cancellation_cutoff_minutes']:
            require(key in r)
            result[key] = integer(r[key], 0 if key == 'cancellation_cutoff_minutes' else 1)
        seen = set()
        for t in field(r, 'tables', list):
            obj(t)
            tid = ident(field(t, 'id', str))
            require(tid not in seen and 'capacity' in t)
            seen.add(tid)
            result['tables'].append({'id': tid, 'label': field(t, 'label', str), 'capacity': integer(t['capacity'])})
        result['combinable'] = j.clone(r.get('combinable', []))
        combinations(result)
        state['restaurants'][rid] = result
    ids = set()
    for r in reservations:
        obj(r)
        uid = ident(field(r, 'user_id', str))
        require(uid in state['users'])
        result = candidate(state, r)
        result['reservation_id'] = ident(field(r, 'id', str))
        reference = field(r, 'reference', str)
        require(REFERENCE.fullmatch(reference) and reference not in state['reservations'] and result['reservation_id'] not in ids)
        result.update(reference=reference, user_id=uid)
        if 'status' in r:
            result['status'] = field(r, 'status', str)
            require(result['status'] in ('confirmed', 'cancelled'))
        require(result['status'] == 'cancelled' or free(state, result))
        ids.add(result['reservation_id'])
        state['reservations'][reference] = result
    return state


def availability(state, query):
    require(all(k in query for k in ['restaurant_id', 'date', 'party_size']))
    rest = restaurant(state, query['restaurant_id'])
    day = calendar(query['date'])
    require(re.fullmatch('[0-9]+', query['party_size']))
    party = integer(Number.parse(query['party_size'].lstrip('0') or '0'), party=True)
    slots = []
    limits = bounds(rest, day)
    if limits:
        row, opens, closes = limits
        start_min, end_min = minute(row['opens']), minute(row['closes'])
        step = rest['slot_minutes']
        step = step.small_int(1440) if step <= 1440 else 1441
        for m in range(start_min, end_min, step):
            local = day.isoformat() + 'T' + f'{m // 60:02}:{m % 60:02}'
            try:
                start, end = interval(rest, local)
            except Fault as err:
                if err.code in ('invalid_local_time', 'outside_opening_hours'):
                    continue
                raise
            ids, options = [], []
            for t in rest['tables']:
                r = {'restaurant_id': rest['id'], 'table_id': t['id'], 'starts_at': timestamp(start), 'ends_at': timestamp(end)}
                if t['capacity'] >= party and free(state, r):
                    ids.append(t['id'])
                    options.append({'table_ids': [t['id']], 'capacity': t['capacity']})
            for pair in rest.get('combinable', []):
                r = {'restaurant_id': rest['id'], 'table_ids': pair, 'starts_at': timestamp(start), 'ends_at': timestamp(end)}
                # Occupancy excludes the pair before its capacity needs output.
                if free(state, r):
                    seats = capacity(rest, pair)
                    if seats >= party:
                        options.append({'table_ids': list(pair), 'capacity': seats})
            slots.append({'starts_at_local': local, 'starts_at': timestamp(start), 'available_table_ids': ids,
                          'available_options': options})
    return {'restaurant_id': rest['id'], 'date': day.isoformat(), 'timezone': rest['timezone'], 'slots': slots}


def snapshot(state):
    # Opaque state must survive ordinary JSON carriers, including binary-float
    # parsers. JSON text inside a string protects every exact number and nested
    # value while preserving fixture insertion order and avoiding tagged collisions.
    encoded = j.dumps(state)
    payload = encoded.decode('ascii')
    checksum = hashlib.sha256(encoded).hexdigest()
    return {'track': 'tablekeeper', 'format_version': 1, 'state': {'payload': payload, 'sha256': checksum}}


def import_state(body):
    try:
        require(body.get('track') == 'tablekeeper' and j.equal(body.get('format_version'), 1))
        envelope = body['state']
        payload = envelope['payload']
        if type(payload) is str:
            digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            payload = j.loads(payload)
        else:
            # Accept intact snapshots from our earlier Stage 1 representation.
            digest = hashlib.sha256(j.dumps(payload, canonical=True)).hexdigest()
        require(type(envelope['sha256']) is str and hmac.compare_digest(digest, envelope['sha256']))
        validate_state(payload)
        return j.clone(payload)
    except (KeyError, TypeError, ValueError, Fault, OverflowError):
        raise Fault() from None


def validate_state(state):
    """Integrity plus structure: never trust an imported checksum alone."""
    require(type(state) is dict and j.equal(state.get('schema'), 1))
    require(set(state) == {'schema', 'users', 'restaurants', 'reservations', 'tokens', 'receipts'})
    for name in ['users', 'restaurants', 'reservations', 'tokens']:
        require(type(state[name]) is dict)
    require(type(state['receipts']) is list)
    users, emails = state['users'], set()
    for uid, u in users.items():
        ident(uid); require(type(u) is dict and u['id'] == uid)
        require(type(u['email']) is str and re.fullmatch(r'[^@\s]+@[^@\s]+', u['email']) and u['email'] not in emails)
        require(type(u['display_name']) is str)
        require(type(u['password_hash']) is str and re.fullmatch(r'pbkdf2-sha256\$120000\$[a-f0-9]{32}\$[a-f0-9]{64}', u['password_hash']))
        emails.add(u['email'])
    for token, uid in state['tokens'].items():
        require(type(token) is str and bool(token) and uid in users)
    # Reuse fixture validation without exposing or manufacturing a password.
    for rid, r in state['restaurants'].items():
        ident(rid); require(r['id'] == rid and type(r['name']) is str)
        ZoneInfo(r['timezone']); opening(r['opening_hours'])
        for key in ['slot_minutes', 'reservation_duration_minutes', 'cancellation_cutoff_minutes']:
            integer(r[key], 0 if key == 'cancellation_cutoff_minutes' else 1)
        seen = set()
        require(type(r['tables']) is list)
        for t in r['tables']:
            tid = ident(t['id']); require(tid not in seen and type(t['label']) is str)
            integer(t['capacity']); seen.add(tid)
        combinations(r)
    identities = set()
    for reference, r in state['reservations'].items():
        require(type(reference) is str and REFERENCE.fullmatch(reference) and r['reference'] == reference)
        require(r['user_id'] in users and r['status'] in ('confirmed', 'cancelled'))
        rid = ident(r['reservation_id']); require(rid not in identities); identities.add(rid)
        utc(r['created_at'])
        reconstructed = candidate(state, record_request(r), r)
        require(j.equal(public(reconstructed), public(r)))
        if r['status'] == 'confirmed':
            require(free(state, r, (reference,)))
    scopes, creation_references = set(), set()
    response_fields = {'reservation_id', 'reference', 'restaurant_id', 'party_size',
                       'status', 'starts_at_local', 'starts_at', 'ends_at', 'created_at'}
    for receipt in state['receipts']:
        require(type(receipt) is dict and receipt['user_id'] in users and receipt['method'] == 'POST')
        require(receipt['path'] in ('/reservations', '/reservation-moves'))
        require(type(receipt['key']) is str and 1 <= len(receipt['key']) <= 255)
        require(type(receipt['body']) is dict and type(receipt['response']) is dict)
        producer = receipt.get('producer_stage', 1)
        require(j.equal(producer, 1) or j.equal(producer, 2))
        legacy = j.equal(producer, 1)
        scope = (receipt['user_id'], receipt['method'], receipt['path'], receipt['key'])
        require(scope not in scopes); scopes.add(scope)
        creating = receipt['path'] == '/reservations'
        if creating:
            rows, requests = [receipt['response']], [receipt['body']]
            require(all(k in receipt['body'] for k in ('restaurant_id', 'starts_at_local', 'party_size'))
                    and ('table_id' in receipt['body'] if legacy else
                         'table_id' in receipt['body'] or 'table_ids' in receipt['body']))
            reference = receipt['response']['reference']
            require(reference not in creation_references)
            creation_references.add(reference)
        else:
            require(set(receipt['response']) == {'reservations'})
            rows, requests = receipt['response']['reservations'], receipt['body'].get('moves')
            require(type(rows) is list and type(requests) is list and 1 <= len(requests) <= 8 and len(rows) == len(requests))
        references, restaurant_id = set(), None
        for row, request in zip(rows, requests):
            require(type(row) is dict and type(request) is dict)
            ids = tables(row)
            require(type(ids) is list and 1 <= len(ids) <= 2)
            require(('table_ids' not in row) if legacy else ('table_ids' in row))
            aliases = {'table_id'} if legacy else {'table_ids'} if len(ids) == 2 else {'table_id', 'table_ids'}
            require(set(row) == response_fields | aliases)
            reference = row['reference']
            require(type(reference) is str and reference not in references)
            references.add(reference)
            if creating:
                require(request['restaurant_id'] == row['restaurant_id'])
            else:
                require(type(request.get('reference')) is str and request['reference'] == reference)
            current = state['reservations'][row['reference']]
            require(current['user_id'] == receipt['user_id'] and current['reservation_id'] == row['reservation_id'])
            require(current['created_at'] == row['created_at'] and current['restaurant_id'] == row['restaurant_id'])
            require(row['status'] == 'confirmed')
            if restaurant_id is None:
                restaurant_id = row['restaurant_id']
            require(row['restaurant_id'] == restaurant_id)
            historical = dict(row, user_id=receipt['user_id'])
            # Validate the receipt's own timestamps/fields, then its correspondence
            # to the original request. Do not compare historical occupancy with
            # today's assignments: receipts intentionally survive later changes.
            require(j.equal(public(candidate(state, record_request(row), historical)), public(row)))
            original_fields = {k: v for k, v in request.items() if k != 'table_ids'} if legacy else request
            require(j.equal(public(candidate(state, original_fields, historical)), public(row)))
        for index, row in enumerate(rows):
            require(not any(set(tables(row)).intersection(tables(other)) and overlap(row, other) for other in rows[:index]))


def authenticated(state, headers):
    auth = headers.get('authorization', '')
    require(auth.startswith('Bearer ') and len(auth.split()) == 2, 'unauthenticated', 401)
    token = auth[7:]
    require(token in state['tokens'], 'unauthenticated', 401)
    return state['tokens'][token]


def dispatch(state, method, path, query, headers, body):
    """Return (status, response, candidate state or None). No input mutation."""
    if method == 'GET' and path == '/health':
        return 200, {'status': 'ok'}, None
    if method == 'POST' and path == '/_test/reset':
        return 204, None, reset(body)
    if method == 'GET' and path == '/_test/export':
        return 200, snapshot(state), None
    if method == 'POST' and path == '/_test/import':
        return 204, None, import_state(obj(body))
    if method == 'POST' and path in ('/auth/signup', '/auth/login'):
        obj(body)
        signup = path == '/auth/signup'
        email, password, name = credentials(body, signup)
        user = next((u for u in state['users'].values() if u['email'] == email), None)
        if signup:
            require(user is None, 'email_taken', 409)
            user = {'id': 'u_' + secrets.token_hex(12), 'email': email, 'display_name': name, 'password_hash': password_hash(password)}
        else:
            require(user is not None and password_matches(password, user['password_hash']), 'unauthenticated', 401)
        work = j.clone(state)
        work['users'][user['id']] = user
        token = secrets.token_urlsafe(32)
        work['tokens'][token] = user['id']
        return 201 if signup else 200, {'user_id': user['id'], 'display_name': user['display_name'], 'token': token}, work
    if method == 'GET' and path == '/restaurants':
        return 200, {'restaurants': [{k: r[k] for k in ['id', 'name', 'timezone']} for r in state['restaurants'].values()]}, None
    if method == 'GET' and re.fullmatch(r'/restaurants/[^/]+', path):
        return 200, restaurant(state, unquote(path.split('/')[2], errors='strict')), None
    if method == 'GET' and path == '/availability':
        return 200, availability(state, query), None
    user = authenticated(state, headers)
    idempotent = method == 'POST' and path in ('/reservations', '/reservation-moves')
    if method in ('POST', 'PATCH', 'PUT'):
        obj(body)
    key = None
    if idempotent:
        key = headers.get('idempotency-key')
        require(key is not None and len(key) > 0, 'missing_idempotency_key', 400)
        require(len(key) <= 255)
        for receipt in state['receipts']:
            if receipt['user_id'] == user and receipt['method'] == method and receipt['path'] == path and receipt['key'] == key:
                require(j.equal(receipt['body'], body), 'idempotency_key_reuse', 409)
                return 200, receipt['response'], None
    if method == 'GET' and path == '/reservations':
        rows = [public(r) for r in state['reservations'].values() if r['user_id'] == user]
        rows.sort(key=lambda r: utc(r['starts_at']), reverse=True)
        return 200, {'reservations': rows}, None
    match = re.fullmatch(r'/reservations/([^/]+)(/cancel)?', path)
    if match and ((method == 'GET' and not match[2]) or (method == 'PATCH' and not match[2]) or (method == 'POST' and match[2])):
        old = booking(state, match[1], user)
        if method == 'GET':
            return 200, public(old), None
        if method == 'POST' and old['status'] == 'cancelled':
            return 200, public(old), None
        editable(state, old)
        result = dict(old, status='cancelled') if method == 'POST' else candidate(state, body, old)
        if method == 'PATCH':
            require(free(state, result, (old['reference'],)), 'table_unavailable', 409)
        work = j.clone(state)
        work['reservations'][old['reference']] = result
        return 200, public(result), work
    if method == 'POST' and path == '/reservations':
        result = candidate(state, body)
        result['user_id'] = user
        require(free(state, result), 'table_unavailable', 409)
        work = j.clone(state)
        work['reservations'][result['reference']] = result
        response = public(result)
    elif method == 'POST' and path == '/reservation-moves':
        moves = body.get('moves')
        require(type(moves) is list and 1 <= len(moves) <= 8)
        seen, prepared, restaurant_id = set(), [], None
        for move in moves:
            require(type(move) is dict and type(move.get('reference')) is str and move['reference'] not in seen)
            seen.add(move['reference'])
        for move in moves:
            old = booking(state, move['reference'], user)
            if restaurant_id is None:
                restaurant_id = old['restaurant_id']
            require(old['restaurant_id'] == restaurant_id)
            editable(state, old)
            prepared.append(candidate(state, move, old))
        for i, r in enumerate(prepared):
            require(free(state, r, seen), 'table_unavailable', 409)
            require(not any(set(tables(r)).intersection(tables(o)) and overlap(r, o) for o in prepared[:i]), 'table_unavailable', 409)
        work = j.clone(state)
        for r in prepared:
            work['reservations'][r['reference']] = r
        response = {'reservations': [public(r) for r in prepared]}
    else:
        raise Fault(404, 'not_found')
    work['receipts'].append({'user_id': user, 'method': method, 'path': path, 'key': key,
                             'body': j.clone(body), 'response': j.clone(response), 'producer_stage': 2})
    return 201, response, work
