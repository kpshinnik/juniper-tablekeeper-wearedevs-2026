"""Check serialization boundaries introduced by the lossless JSON repair."""
import httpx
import pytest
from test_boundaries import api, body, book, observe


@pytest.mark.parametrize('depth',[250,350,450],ids=['J001-depth-250','J002-depth-350','J003-depth-450'])
def test_accepted_nested_receipt_remains_exportable(api,record_property,depth):
    """An accepted unknown nested value must have a complete portable JSON export and replay."""
    c,t,_=api
    nested='value'
    for _ in range(depth): nested={'x':nested}
    payload=body(ignored=nested)
    first=book(c,t['alice'],'nested-export',payload)
    assert first.status_code==201, first.text
    try:
        snapshot=c.get('/_test/export')
    except httpx.HTTPError as error:
        observe(record_property,depth=depth,create=first.status_code,export_error=type(error).__name__,health=c.get('/health').status_code)
        pytest.fail('Accepted receipt could not be exported: '+type(error).__name__)
    assert snapshot.status_code==200, snapshot.text
    restored=c.post('/_test/import',content=snapshot.content)
    retry=book(c,t['alice'],'nested-export',payload)
    observe(record_property,depth=depth,create=first.status_code,export=snapshot.status_code,bytes=len(snapshot.content),restore=restored.status_code,retry=retry.status_code)
    assert restored.status_code==204 and retry.status_code==200 and retry.json()==first.json()
