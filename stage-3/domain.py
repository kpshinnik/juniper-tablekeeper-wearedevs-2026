"""Dated policies and recurring agreements, prepared as one private transaction.

The accepted prior-stage module owns legacy snapshot validation. Native state
also carries its baseline and actual operation journal: import reconstructs the
state to validate historical terms, identities, receipts and every counter.
"""
import legacy
from legacy import *


def policy_zero(rest):
    return dict(policy_version=0, capacities={t['id']: t['capacity'] for t in rest['tables']},
                **{k: j.clone(rest[k]) for k in ('slot_minutes', 'reservation_duration_minutes',
                                               'cancellation_cutoff_minutes', 'opening_hours')})


def selected_terms(state, rest, day):
    choices = [p for p in state['policies'][rest['id']] if p['effective_from'] <= day]
    chosen = max(choices, key=lambda p: (p['effective_from'], p['policy_version'])) if choices else policy_zero(rest)
    return j.clone({k: v for k, v in chosen.items() if k != 'effective_from'})


def configured(rest, terms):
    return dict(rest, **{k: terms[k] for k in ('slot_minutes', 'reservation_duration_minutes',
                                             'cancellation_cutoff_minutes', 'opening_hours')},
                tables=[dict(t, capacity=terms['capacities'][t['id']]) for t in rest['tables']])


def changes(old, result):
    edits = []
    ids = tables(result)
    if old is None or tables(old) != ids:
        pair = len(ids) == 2 or (old is not None and len(tables(old)) == 2)
        edits.append({'field': 'table_ids' if pair else 'table_id',
                      'from': None if old is None else list(tables(old)) if pair else tables(old)[0],
                      'to': list(ids) if pair else ids[0]})
    for name in ('starts_at_local', 'party_size'):
        if old is None or not j.equal(old[name], result[name]):
            edits.append({'field': name, 'from': None if old is None else old[name], 'to': result[name]})
    return edits


def append_history(state, result, event, at, old=None):
    entries = state['histories'].setdefault(result['reference'], [])
    if entries and utc(at) < utc(entries[-1]['at']):
        at = entries[-1]['at']
    entries.append({'seq': len(entries) + 1, 'at': at, 'event': event,
                    'changes': [] if event == 'cancelled' else changes(old, result),
                    'revision': result['revision'], 'accepted_terms': j.clone(result['accepted_terms'])})


def from_base(base, native):
    state = j.clone(base)
    state.update(schema=3, policies={rid: [] for rid in base['restaurants']}, histories={}, series={},
                 restaurant_revisions={rid: 0 for rid in base['restaurants']})
    for rest in state['restaurants'].values():
        rest.setdefault('manager_user_ids', [])
    for value in state['reservations'].values():
        value.update(revision=1, accepted_terms=policy_zero(state['restaurants'][value['restaurant_id']]))
        state['histories'][value['reference']] = []
        if native:
            append_history(state, value, 'created', value['created_at'])
    state['audit'] = {'base': j.clone(base), 'native': native, 'events': []}
    return state


def empty_state():
    return from_base(legacy.empty_state(), True)


def reset(body):
    base = legacy.reset(body)
    for source in body['restaurants']:
        managers = source.get('manager_user_ids', [])
        require(type(managers) is list, 'malformed_request', 400)
        managers = [ident(value) for value in managers]
        require(len(set(managers)) == len(managers))
        base['restaurants'][source['id']]['manager_user_ids'] = managers
    return from_base(base, True)


class Context:
    """Actual operation time and generated identities, replayable without RNG."""
    def __init__(self, at=None, allocations=None):
        self.at = now() if at is None else at
        utc(self.at)
        self.allocations = [] if allocations is None else allocations
        self.replaying = allocations is not None
        self.position = 0

    def allocate(self, kind, occupied):
        if self.replaying:
            require(self.position < len(self.allocations))
            row = self.allocations[self.position]
            require(type(row) is dict and set(row) == {'kind', 'value'} and row['kind'] == kind)
            value = ident(row['value'])
        else:
            while True:
                value = secrets.token_hex(5).upper() if kind == 'reference' else kind + '_' + secrets.token_hex(12)
                if value not in occupied:
                    break
            self.allocations.append({'kind': kind, 'value': value})
        require(value not in occupied)
        if kind == 'reference':
            require(REFERENCE.fullmatch(value))
        self.position += 1
        return value


def candidate(state, body, old=None, context=None):
    obj(body)
    context = Context() if context is None else context
    rid = old['restaurant_id'] if old is not None else ident(field(body, 'restaurant_id', str))
    rest = restaurant(state, rid)
    ids = selection(rest, body, old)
    local = body.get('starts_at_local', old['starts_at_local'] if old else None)
    if local is None and 'starts_at_local' not in body:
        raise Fault()
    # Validate syntax even on a no-op, without selecting a newer policy.
    resolve(local, rest['timezone'])
    party = integer(body.get('party_size', old['party_size'] if old else None), party=True)
    if old is not None and ids == tables(old) and local == old['starts_at_local'] and j.equal(party, old['party_size']):
        return dict(old)
    terms = selected_terms(state, rest, local[:10])
    rules = configured(rest, terms)
    start, end = interval(rules, local)
    require(capacity(rules, ids) >= party, 'party_exceeds_capacity')
    result = dict(old) if old else {
        'reservation_id': context.allocate('res', {r['reservation_id'] for r in state['reservations'].values()}),
        'reference': context.allocate('reference', state['reservations']),
        'created_at': context.at, 'status': 'confirmed'}
    result.update(restaurant_id=rid, table_ids=ids, starts_at_local=local, party_size=party,
                  starts_at=timestamp(start), ends_at=timestamp(end), accepted_terms=terms,
                  revision=old['revision'] + 1 if old else 1)
    if len(ids) == 1:
        result['table_id'] = ids[0]
    else:
        result.pop('table_id', None)
    return result


def editable(state, reservation, at=None):
    require(reservation['status'] != 'cancelled', 'reservation_cancelled', 409)
    cutoff = reservation['accepted_terms']['cancellation_cutoff_minutes']
    whole, fraction = divmod(utc(reservation['starts_at']) - utc(now() if at is None else at), MINUTE_US)
    require(cutoff < whole or (cutoff == whole and fraction > 0), 'cutoff_passed', 409)


def expected_revision(body, value):
    if 'expected_revision' in body:
        revision = integer(body['expected_revision'], party=True)
        require(j.equal(revision, value), 'stale_revision', 409)


def availability(state, query):
    require('explain' not in query or query['explain'] == 'true')
    require(all(k in query for k in ('restaurant_id', 'date', 'party_size')))
    rest = restaurant(state, query['restaurant_id'])
    day = calendar(query['date'])
    terms = selected_terms(state, rest, day.isoformat())
    rules = configured(rest, terms)
    projected = dict(state, restaurants=dict(state['restaurants'], **{rest['id']: rules}))
    result = legacy.availability(projected, query)
    if 'explain' in query:
        party = integer(Number.parse(query['party_size'].lstrip('0') or '0'), party=True)
        for slot in result['slots']:
            start, end = interval(rules, slot['starts_at_local'])
            slot['explain'] = []
            for table in rules['tables']:
                sufficient = table['capacity'] >= party
                unoccupied = free(state, {'restaurant_id': rest['id'], 'table_id': table['id'],
                                          'starts_at': timestamp(start), 'ends_at': timestamp(end)})
                slot['explain'].append({'table_id': table['id'], 'policy_version': terms['policy_version'],
                                        'available': sufficient and unoccupied,
                                        'rules': [{'rule': 'capacity', 'holds': sufficient},
                                                  {'rule': 'no_overlap', 'holds': unoccupied}]})
    return result


def published_policy(rest, body, version):
    try:
        result = {'effective_from': calendar(body['effective_from']).isoformat(), 'policy_version': version}
        for name, lower, upper in [('slot_minutes', 1, 1440), ('reservation_duration_minutes', 1, 1440),
                                    ('cancellation_cutoff_minutes', 0, 10080)]:
            result[name] = integer(body[name], lower, upper, party=True)
        result['opening_hours'] = opening(body['opening_hours'])
        require(type(body['capacities']) is dict and set(body['capacities']) == {t['id'] for t in rest['tables']})
        result['capacities'] = {tid: integer(value, 1, 100, party=True) for tid, value in body['capacities'].items()}
        return result
    except (KeyError, TypeError, ValueError, Fault):
        raise Fault() from None


def member_changes(state, references, exception):
    for agreement in state['series'].values():
        affected = [o for o in agreement['occurrences'] if o['reference'] in references]
        if affected:
            agreement['revision'] += 1
            if exception:
                for occurrence in affected:
                    occurrence['exception'] = True


def series_public(state, agreement):
    return {'series_id': agreement['series_id'], 'revision': agreement['revision'],
            'interval_weeks': agreement['interval_weeks'],
            'occurrences': [{'index': o['index'], 'reference': o['reference'], 'exception': o['exception'],
                             'reservation': public(state['reservations'][o['reference']])}
                            for o in agreement['occurrences']]}


def idempotent_path(method, path):
    return method == 'POST' and (path in ('/reservations', '/reservation-moves', '/series')
                                or re.fullmatch(r'/restaurants/[^/]+/policies', path))


def replay(state, user, method, path, key, body):
    require(type(key) is str and len(key) > 0, 'missing_idempotency_key', 400)
    require(len(key) <= 255)
    for receipt in state['receipts']:
        if (receipt['user_id'], receipt['method'], receipt['path'], receipt['key']) == (user, method, path, key):
            require(j.equal(receipt['body'], body), 'idempotency_key_reuse', 409)
            return receipt
    return None


def operate(state, method, path, body, user, key, context):
    """Mutate only an unpublished candidate. Called identically by journal replay."""
    obj(body)
    require(user in state['users'])
    is_idempotent = idempotent_path(method, path)
    if is_idempotent:
        require(replay(state, user, method, path, key, body) is None)
    match = re.fullmatch(r'/reservations/([^/]+)(/cancel)?', path)
    policy_match = re.fullmatch(r'/restaurants/([^/]+)/policies', path)
    if match and ((method == 'PATCH' and not match[2]) or (method == 'POST' and match[2])):
        old = booking(state, match[1], user)
        if method == 'POST' and old['status'] == 'cancelled':
            return 200, public(old), False
        if method == 'PATCH':
            expected_revision(body, old['revision'])
        editable(state, old, context.at)
        result = dict(old, status='cancelled', revision=old['revision'] + 1) if method == 'POST' else candidate(state, body, old, context)
        if not changes(old, result) and method == 'PATCH':
            return 200, public(old), False
        require(method == 'POST' or free(state, result, (old['reference'],)), 'table_unavailable', 409)
        state['reservations'][old['reference']] = result
        append_history(state, result, 'cancelled' if method == 'POST' else 'changed', context.at, old)
        member_changes(state, {old['reference']}, method == 'PATCH')
        state['restaurant_revisions'][old['restaurant_id']] += 1
        return 200, public(result), True
    if method == 'POST' and path == '/reservations':
        result = candidate(state, body, context=context)
        result['user_id'] = user
        require(free(state, result), 'table_unavailable', 409)
        state['reservations'][result['reference']] = result
        append_history(state, result, 'created', context.at)
        state['restaurant_revisions'][result['restaurant_id']] += 1
        response = public(result)
    elif method == 'POST' and policy_match:
        rest = restaurant(state, unquote(policy_match[1], errors='strict'))
        require(user in rest['manager_user_ids'], 'forbidden', 403)
        response = published_policy(rest, body, len(state['policies'][rest['id']]) + 1)
        state['policies'][rest['id']].append(response)
        state['restaurant_revisions'][rest['id']] += 1
    elif method == 'POST' and path == '/reservation-moves':
        moves = body.get('moves')
        require(type(moves) is list and 1 <= len(moves) <= 8)
        seen, prepared, rid = set(), [], None
        for move in moves:
            require(type(move) is dict and type(move.get('reference')) is str and move['reference'] not in seen)
            seen.add(move['reference'])
        for move in moves:
            old = booking(state, move['reference'], user)
            if rid is None:
                rid = old['restaurant_id']
            require(old['restaurant_id'] == rid)
            expected_revision(move, old['revision'])
            editable(state, old, context.at)
            prepared.append((old, candidate(state, move, old, context)))
        for index, (_, result) in enumerate(prepared):
            require(free(state, result, seen), 'table_unavailable', 409)
            require(not any(set(tables(result)).intersection(tables(other)) and overlap(result, other)
                            for _, other in prepared[:index]), 'table_unavailable', 409)
        changed = set()
        for old, result in prepared:
            if changes(old, result):
                changed.add(result['reference'])
                state['reservations'][result['reference']] = result
                append_history(state, result, 'changed', context.at, old)
        if changed:
            member_changes(state, changed, True)
            state['restaurant_revisions'][rid] += 1
        response = {'reservations': [public(result) for _, result in prepared]}
    elif method == 'POST' and path == '/series':
        count = integer(body.get('count'), 2, 12, party=True).small_int(12)
        weeks = integer(body.get('interval_weeks'), 1, 4, party=True).small_int(4)
        anchor = booking(state, field(body, 'anchor_reference', str), user)
        editable(state, anchor, context.at)
        require(not any(o['reference'] == anchor['reference'] for s in state['series'].values()
                        for o in s['occurrences']), 'already_in_series', 409)
        agreement = {'series_id': context.allocate('series', state['series']), 'user_id': user,
                     'restaurant_id': anchor['restaurant_id'], 'revision': 1, 'interval_weeks': weeks, 'occurrences': []}
        start_day = calendar(anchor['starts_at_local'][:10])
        for index in range(count):
            try:
                scheduled = (start_day + timedelta(days=index * weeks * 7)).isoformat()
            except OverflowError:
                raise Fault() from None
            if index == 0:
                result = anchor
            else:
                result = candidate(state, {'restaurant_id': anchor['restaurant_id'], 'table_ids': tables(anchor),
                                           'starts_at_local': scheduled + anchor['starts_at_local'][10:],
                                           'party_size': anchor['party_size']}, context=context)
                result['user_id'] = user
                require(free(state, result), 'table_unavailable', 409)
                state['reservations'][result['reference']] = result
                append_history(state, result, 'created', context.at)
            agreement['occurrences'].append({'index': index, 'reference': result['reference'],
                                             'exception': False, 'scheduled_date': scheduled})
        state['series'][agreement['series_id']] = agreement
        state['restaurant_revisions'][anchor['restaurant_id']] += 1
        response = series_public(state, agreement)
    else:
        raise Fault(404, 'not_found')
    require(bool(is_idempotent))
    state['receipts'].append({'user_id': user, 'method': method, 'path': path, 'key': key,
                              'body': j.clone(body), 'response': j.clone(response), 'producer_stage': 3})
    return 201, response, True


def validate_state(state):
    """Reconstruct native history instead of accepting checksum-valid inventions."""
    require(type(state) is dict)
    if j.equal(state.get('schema'), 1):
        legacy.validate_state(state)
        return from_base(state, False)
    require(j.equal(state.get('schema'), 3))
    require(set(state) == {'schema', 'users', 'restaurants', 'reservations', 'tokens', 'receipts',
                           'policies', 'histories', 'series', 'restaurant_revisions', 'audit'})
    audit = state['audit']
    require(type(audit) is dict and set(audit) == {'base', 'native', 'events'})
    require(type(audit['native']) is bool and type(audit['events']) is list)
    base = audit['base']
    legacy.validate_state(base)
    if audit['native']:
        require(not base['tokens'] and not base['receipts'])
    for rest in base['restaurants'].values():
        managers = rest.get('manager_user_ids', [])
        require(type(managers) is list)
        require(len({ident(uid) for uid in managers}) == len(managers))
    accounts = legacy.empty_state()
    accounts.update(users=state['users'], tokens=state['tokens'])
    legacy.validate_state(accounts)
    for name in ('users', 'tokens'):
        require(all(key in state[name] and j.equal(value, state[name][key]) for key, value in base[name].items()))
    rebuilt = from_base(base, audit['native'])
    rebuilt.update(users=j.clone(state['users']), tokens=j.clone(state['tokens']))
    for event in audit['events']:
        require(type(event) is dict and set(event) == {'user_id', 'method', 'path', 'body', 'key', 'at', 'allocations'})
        require(type(event['allocations']) is list and type(event['method']) is str and type(event['path']) is str)
        context = Context(event['at'], event['allocations'])
        _, _, published = operate(rebuilt, event['method'], event['path'], event['body'], event['user_id'], event['key'], context)
        require(published and context.position == len(context.allocations))
    require(j.equal({k: v for k, v in rebuilt.items() if k != 'audit'}, {k: v for k, v in state.items() if k != 'audit'}))
    rebuilt['audit'] = j.clone(audit)
    return rebuilt


def import_state(body):
    try:
        require(body.get('track') == 'tablekeeper' and j.equal(body.get('format_version'), 1))
        envelope = body['state']
        payload = envelope['payload']
        if type(payload) is str:
            digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            payload = j.loads(payload)
        else:
            digest = hashlib.sha256(j.dumps(payload, canonical=True)).hexdigest()
        require(type(envelope['sha256']) is str and hmac.compare_digest(digest, envelope['sha256']))
        return validate_state(payload)
    except (KeyError, TypeError, ValueError, Fault, OverflowError, AttributeError):
        raise Fault() from None


def dispatch(state, method, path, query, headers, body):
    if method == 'POST' and path == '/_test/reset':
        return 204, None, reset(body)
    if method == 'POST' and path == '/_test/import':
        return 204, None, import_state(obj(body))
    if method == 'GET' and path == '/availability':
        return 200, availability(state, query), None
    if (method == 'GET' and path in ('/health', '/_test/export', '/restaurants')) or (
            method == 'GET' and re.fullmatch(r'/restaurants/[^/]+', path)) or (
            method == 'POST' and path in ('/auth/signup', '/auth/login')):
        return legacy.dispatch(state, method, path, query, headers, body)
    policy_match = re.fullmatch(r'/restaurants/([^/]+)/policies', path)
    if method == 'GET' and policy_match:
        rest = restaurant(state, unquote(policy_match[1], errors='strict'))
        return 200, {'policies': state['policies'][rest['id']]}, None
    private_read = method == 'GET' and (re.fullmatch(r'/reservations/[^/]+/(?:history|decision)', path)
                                        or re.fullmatch(r'/series/[^/]+', path))
    try:
        user = authenticated(state, headers)
    except Fault:
        if private_read:
            raise Fault(404, 'not_found') from None
        raise
    if method in ('POST', 'PATCH', 'PUT'):
        obj(body)
    key = headers.get('idempotency-key') if idempotent_path(method, path) else None
    if idempotent_path(method, path):
        receipt = replay(state, user, method, path, key, body)
        if receipt is not None:
            return 200, receipt['response'], None
    if method == 'GET' and path == '/reservations':
        rows = [public(r) for r in state['reservations'].values() if r['user_id'] == user]
        rows.sort(key=lambda r: utc(r['starts_at']), reverse=True)
        return 200, {'reservations': rows}, None
    match = re.fullmatch(r'/reservations/([^/]+)(?:/(history|decision))?', path)
    if method == 'GET' and match:
        value = booking(state, match[1], user)
        if match[2] == 'history':
            return 200, {'reference': value['reference'], 'entries': state['histories'][value['reference']]}, None
        if match[2] == 'decision':
            return 200, {k: value[k] for k in ('reference', 'revision', 'accepted_terms')}, None
        return 200, public(value), None
    match = re.fullmatch(r'/series/([^/]+)', path)
    if method == 'GET' and match:
        agreement = state['series'].get(match[1])
        require(agreement is not None and agreement['user_id'] == user, 'not_found', 404)
        return 200, series_public(state, agreement), None
    work = j.clone(state)
    context = Context()
    status, response, published = operate(work, method, path, body, user, key, context)
    if published:
        work['audit']['events'].append({'user_id': user, 'method': method, 'path': path, 'body': j.clone(body),
                                         'key': key, 'at': context.at, 'allocations': context.allocations})
    return status, response, work if published else None
