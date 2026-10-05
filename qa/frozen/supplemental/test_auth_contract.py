"""Stage 1 section 6: distinguish invalid email grammar from unknown credentials.

These new cases do not rewrite historical S064-S067 results or their frozen inputs.
"""
import pytest
from test_boundaries import api, observe


@pytest.mark.parametrize('email',[
    "' OR 1=1 --", '<script>alert(1)</script>', '../../etc/passwd', '${7*7}',
],ids=['A001-sql-malformed','A002-script-malformed','A003-path-malformed','A004-template-malformed'])
def test_malformed_email_validation(api,record_property,email):
    """An email outside local@domain is a 422 validation error and grants no session."""
    c,_,_=api;before=c.get('/_test/export').json()
    r=c.post('/auth/login',json={'email':email,'password':'synthetic-password'})
    after=c.get('/_test/export').json()
    observe(record_property,status=r.status_code,error=r.json().get('error'),state_unchanged=before==after)
    assert r.status_code==422 and r.json()['error']['code']=='validation_failed' and before==after


@pytest.mark.parametrize('email',[
    "'OR1=1--@audit.test", '<script>alert(1)</script>@audit.test', '../../etc/passwd@audit.test', '${7*7}@audit.test',
],ids=['A005-sql-unknown','A006-script-unknown','A007-path-unknown','A008-template-unknown'])
def test_valid_format_unknown_credentials(api,record_property,email):
    """Valid-format unknown injection-like identities stay unauthenticated and unchanged."""
    c,_,_=api;before=c.get('/_test/export').json()
    r=c.post('/auth/login',json={'email':email,'password':'synthetic-password'})
    after=c.get('/_test/export').json()
    observe(record_property,status=r.status_code,error=r.json().get('error'),state_unchanged=before==after)
    assert r.status_code==401 and r.json()['error']['code']=='unauthenticated' and before==after
