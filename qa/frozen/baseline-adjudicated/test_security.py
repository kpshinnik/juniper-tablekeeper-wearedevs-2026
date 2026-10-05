"""Security cases protect state integrity and privacy at the public HTTP boundary."""
import copy
import json
import pytest
from conftest import book, error, headers, reservations
pytestmark = pytest.mark.security

BAD_BOOKINGS = [
 ('S001-party-bool','party_size',True,422,'validation_failed'),
 ('S002-party-string','party_size','3',422,'validation_failed'),
 ('S003-party-zero','party_size',0,422,'validation_failed'),
 ('S004-party-negative','party_size',-1,422,'validation_failed'),
 ('S005-party-fraction','party_size',1.2,422,'validation_failed'),
 ('S006-party-null','party_size',None,422,'validation_failed'),
 ('S007-party-array','party_size',[3],422,'validation_failed'),
 ('S008-party-object','party_size',{'value':3},422,'validation_failed'),
 ('S009-party-large','party_size',10**30,422,'party_exceeds_capacity'),
 ('S010-party-over-capacity','party_size',5,422,'party_exceeds_capacity'),
 ('S011-time-offset','starts_at_local','2030-01-01T18:00+01:00',422,'validation_failed'),
 ('S012-time-zulu','starts_at_local','2030-01-01T18:00Z',422,'validation_failed'),
 ('S013-time-seconds','starts_at_local','2030-01-01T18:00:00',422,'validation_failed'),
 ('S014-time-space','starts_at_local','2030-01-01 18:00',422,'validation_failed'),
 ('S015-time-invalid-date','starts_at_local','2030-02-30T18:00',422,'validation_failed'),
 ('S016-time-invalid-hour','starts_at_local','2030-01-01T24:00',422,'validation_failed'),
 ('S017-time-invalid-minute','starts_at_local','2030-01-01T18:60',422,'validation_failed'),
 ('S018-time-nonpadded','starts_at_local','2030-1-1T8:00',422,'validation_failed'),
 ('S019-time-integer','starts_at_local',123,400,'malformed_request'),
 ('S020-time-object','starts_at_local',{},400,'malformed_request'),
 ('S021-restaurant-integer','restaurant_id',1,400,'malformed_request'),
 ('S022-restaurant-array','restaurant_id',[],400,'malformed_request'),
 ('S023-table-object','table_id',{},400,'malformed_request'),
 ('S024-table-null','table_id',None,400,'malformed_request'),
 ('S025-unknown-restaurant','restaurant_id','does-not-exist',404,'not_found'),
 ('S026-unknown-table','table_id','does-not-exist',404,'not_found'),
 ('S027-table-length-limit','table_id','x'*65,422,'validation_failed'),
 ('S028-restaurant-length-limit','restaurant_id','x'*65,422,'validation_failed'),
]

@pytest.mark.parametrize('case,field,value,status,code',BAD_BOOKINGS,ids=[x[0] for x in BAD_BOOKINGS])
def test_invalid_booking_is_atomic(api,world,case,field,value,status,code):
    """Rejected adversarial input must leave both occupancy and retry key reusable."""
    error(book(api,world,body=dict(world.body,**{field:value}),key=case),status,code)
    assert reservations(api,world)==[]
    assert book(api,world,key=case).status_code==201

@pytest.mark.parametrize('field',['restaurant_id','table_id','starts_at_local','party_size'],ids=['S029-missing-restaurant','S030-missing-table','S031-missing-time','S032-missing-party'])
def test_missing_required_field(api,world,field):
    """Missing fields cannot allocate partial state."""
    body=dict(world.body); del body[field]
    error(book(api,world,body=body),422,'validation_failed')
    assert reservations(api,world)==[]

@pytest.mark.parametrize('raw',['{','[]','null','true','17','"text"','{"a":NaN}','{"a":Infinity}'],ids=['S033-broken-json','S034-array-root','S035-null-root','S036-bool-root','S037-number-root','S038-string-root','S039-nan','S040-infinity'])
def test_invalid_json(api,world,raw):
    """Non-object and non-standard JSON are rejected before mutation."""
    error(api.post('/reservations',content=raw,headers={**headers(world,key='raw'),'Content-Type':'application/json'}),400,'malformed_request')
    assert reservations(api,world)==[]

@pytest.mark.parametrize('value',['1e2','4.0','+4','-1','0','true','NaN','Infinity'],ids=['S041-query-exponent','S042-query-float','S043-query-plus','S044-query-negative','S045-query-zero','S046-query-bool','S047-query-nan','S048-query-infinity'])
def test_query_integer_grammar(api,world,value):
    """Strict decimal query parsing prevents numeric coercion bypass."""
    error(api.get('/availability',params={'restaurant_id':'r_main','date':world.date,'party_size':value}),422,'validation_failed')

@pytest.mark.parametrize('token',['','Basic fake','Bearer','Bearer fake','Bearer null','Bearer x.y.z'],ids=['S049-no-auth','S050-basic-auth','S051-empty-bearer','S052-forged-token','S053-null-token','S054-forged-jwt'])
def test_bad_auth(api,world,token):
    """Private lists cannot be read with absent or forged credentials."""
    error(api.get('/reservations',headers={'Authorization':token}),401,'unauthenticated')

@pytest.mark.parametrize('method,suffix',[('GET',''),('PATCH',''),('POST','/cancel')],ids=['S055-idor-read','S056-idor-amend','S057-idor-cancel'])
def test_cross_user_reference(api,world,method,suffix):
    """A leaked reference grants no access to a different account."""
    a=book(api,world).json(); kw={'headers':headers(world,'bob')}
    if method!='GET': kw['json']={'party_size':1}
    error(api.request(method,'/reservations/'+a['reference']+suffix,**kw),404,'not_found')
    assert reservations(api,world)==[a] and reservations(api,world,'bob')==[]

@pytest.mark.parametrize('key',[None,'','k'*256],ids=['S058-missing-key','S059-empty-key','S060-overlong-key'])
def test_invalid_idempotency_header(api,world,key):
    """Invalid keys cannot allocate bookings."""
    missing=key in (None,'')
    error(api.post('/reservations',json=world.body,headers=headers(world,key=key)),400 if missing else 422,'missing_idempotency_key' if missing else 'validation_failed')
    assert reservations(api,world)==[]

@pytest.mark.parametrize('field,value',[('party_size',True),('restaurant_id','unknown'),('starts_at_local','broken')],ids=['S061-reuse-before-type','S062-reuse-before-resource','S063-reuse-before-date'])
def test_idempotency_precedence(api,world,field,value):
    """Changed payloads cannot reuse a successful key even if invalid for another reason."""
    original=book(api,world,key='captured'); assert original.status_code==201
    error(book(api,world,key='captured',body=dict(world.body,**{field:value})),409,'idempotency_key_reuse')
    assert book(api,world,key='captured').json()==original.json()

@pytest.mark.parametrize('payload',["' OR 1=1 --",'<script>alert(1)</script>','../../etc/passwd','${7*7}'],ids=['S064-sql-login','S065-script-login','S066-path-login','S067-template-login'])
def test_login_injection(api,world,payload):
    """Malformed-email injection strings are rejected before state changes (§6)."""
    before=api.get('/_test/export').json()
    error(api.post('/auth/login',json={'email':payload,'password':payload}),422,'validation_failed')
    assert api.get('/_test/export').json()==before

@pytest.mark.parametrize('mutate',['track','version','missing-state','nonobject-state','empty-state'],ids=['S068-import-track','S069-import-version','S070-import-missing-state','S071-import-state-type','S072-import-empty-state'])
def test_bad_import_preserves_destination(api,world,mutate):
    """Rejected replacement preserves sessions, bookings and completed retry receipts."""
    receipt=book(api,world,key='kept').json(); before=api.get('/_test/export').json(); bad=copy.deepcopy(before)
    if mutate=='track': bad['track']='other'
    elif mutate=='version': bad['format_version']=999
    elif mutate=='missing-state': del bad['state']
    elif mutate=='nonobject-state': bad['state']=[]
    else: bad['state']={}
    error(api.post('/_test/import',json=bad),422,'validation_failed')
    assert api.get('/_test/export').json()==before
    assert book(api,world,key='kept').json()==receipt


def test_S073_import_missing_track(api,world):
    """An incomplete snapshot envelope cannot replace destination state."""
    before=api.get('/_test/export').json(); bad=copy.deepcopy(before); del bad['track']
    error(api.post('/_test/import',json=bad),422,'validation_failed')
    assert api.get('/_test/export').json()==before


def test_S074_passwords_are_hashed(api,world):
    """Portable state never stores the seeded passwords in plaintext."""
    exported=api.get('/_test/export').text
    for user in world.data['users']: assert user['password'] not in exported


def test_S075_mass_assignment(api,world):
    """Client cannot choose owner, status, reference or server identity."""
    r=book(api,world,body=dict(world.body,user_id='bob',status='cancelled',reference='HACKED',reservation_id='HACKED'))
    assert r.status_code==201
    assert r.json()['reference']!='HACKED' and r.json()['reservation_id']!='HACKED'
    assert r.json()['status']=='confirmed' and reservations(api,world,'bob')==[]


def test_S076_reset_revokes_tokens(api,world):
    """Reusing account IDs after reset does not preserve stale bearer tokens."""
    assert api.post('/_test/reset',json=world.data).status_code==204
    error(api.get('/reservations',headers=headers(world)),401,'unauthenticated')


def test_S077_import_revokes_destination_token(api,world):
    """Import restores source sessions and removes destination-only sessions."""
    snapshot=api.get('/_test/export').json()
    extra=api.post('/auth/login',json={'email':'alice@example.test','password':'alice-correct-horse'}).json()['token']
    assert api.post('/_test/import',json=snapshot).status_code==204
    error(api.get('/reservations',headers={'Authorization':'Bearer '+extra}),401,'unauthenticated')
    assert api.get('/reservations',headers=headers(world)).status_code==200


def test_S078_json_canonicalization(api,world):
    """Whitespace and object-key order cannot bypass duplicate-write protection."""
    original=book(api,world,key='canonical')
    raw=json.dumps(dict(reversed(list(world.body.items()))),indent=4)
    replay=api.post('/reservations',content=raw,headers={**headers(world,key='canonical'),'Content-Type':'application/json'})
    assert replay.status_code==200 and replay.json()==original.json() and len(reservations(api,world))==1


def test_S079_unknown_fields_in_retry_identity(api,world):
    """Unknown fields are ignored by business logic but remain part of full JSON identity."""
    assert book(api,world,key='unknown').status_code==201
    error(book(api,world,key='unknown',body=dict(world.body,unused='different')),409,'idempotency_key_reuse')


def test_S080_cancelled_retry_does_not_resurrect(api,world):
    """A successful old receipt can be replayed without resurrecting its cancelled booking."""
    original=book(api,world,key='cancelled'); ref=original.json()['reference']
    assert api.post(f'/reservations/{ref}/cancel',json={},headers=headers(world)).status_code==200
    replay=book(api,world,key='cancelled')
    assert replay.status_code==200 and replay.json()==original.json()
    assert reservations(api,world)[0]['status']=='cancelled'


def test_S081_mixed_owner_batch_atomic(api,world):
    """A mixed-owner batch cannot partially alter the caller's first booking."""
    a=book(api,world).json(); b=book(api,world,user='bob',body=dict(world.body,table_id='t_3')).json()
    error(api.post('/reservation-moves',json={'moves':[{'reference':a['reference'],'party_size':1},{'reference':b['reference'],'party_size':1}]},headers=headers(world,key='mixed')),404,'not_found')
    assert reservations(api,world)==[a]


def test_S082_duplicate_batch_reference(api,world):
    """Duplicate members cannot modify one record multiple times in one batch."""
    a=book(api,world).json(); move={'reference':a['reference'],'party_size':1}
    error(api.post('/reservation-moves',json={'moves':[move,move]},headers=headers(world,key='dup')),422,'validation_failed')
    assert reservations(api,world)==[a]


def test_S083_failed_amend_preserves_occupancy(api,world):
    """A failed capacity check neither alters the original booking nor frees its slot."""
    a=book(api,world).json()
    error(api.patch('/reservations/'+a['reference'],json={'table_id':'t_1','party_size':3},headers=headers(world)),422,'party_exceeds_capacity')
    assert reservations(api,world)==[a]
    error(book(api,world,user='bob'),409,'table_unavailable')


def test_S084_public_responses_no_credentials(api,world):
    """Public browsing cannot expose account credentials or active tokens."""
    for path in ['/restaurants','/restaurants/r_main','/availability?restaurant_id=r_main&date='+world.date+'&party_size=3']:
        r=api.get(path); assert r.status_code==200
        for secret in [*world.tokens.values(),'alice-correct-horse','bob-correct-horse','alice@example.test']: assert secret not in r.text
