"""D222: direct inherited combination-cell availability obligation.

Derived from Stage2: combination cells are shown when the declared pair is
available for the searched party size. Singles retain explicit false cells.
This reproduces the Stage4 frozen U402/U404 absence failure without new APIs.
"""
import json
import pytest
from playwright.sync_api import expect
from derived.test_stage1 import headers
from derived.test_stage2_browser import (BASE, DAY, browser_world, fixture, seed, login, search)


@pytest.mark.parametrize('width',[375,1360],ids=['mobile','desktop'])
def test_D222_occupied_member_excludes_pair_cell(browser_world,width,record_property):
    """An occupied member excludes its pair cell; a touching free slot still has the available pair in declared order."""
    c,page,errors,out=browser_world; fx=fixture(pair=True); token=seed(c,fx)
    page.set_viewport_size({'width':width,'height':900})
    response=c.post('/reservations',json={'restaurant_id':'r','table_id':'a',
        'starts_at_local':DAY+'T18:00','party_size':2},headers=headers(token,'occupy-a'))
    assert response.status_code==201
    slots=c.get('/availability',params={'restaurant_id':'r','date':DAY,'party_size':4}).json()['slots']
    selected={x['starts_at_local'][-5:]:x['available_options'] for x in slots}
    assert not any(x['table_ids']==['b','a'] for x in selected['18:00'])
    assert any(x['table_ids']==['b','a'] for x in selected['19:00'])
    login(page); search(page)
    expect(page.get_by_test_id('slot-b+a-19:00')).to_have_attribute('data-available','true')
    expect(page.get_by_test_id('slot-a-18:00')).to_have_attribute('data-available','false')
    cell=page.get_by_test_id('slot-b+a-18:00')
    observed={'width':width,'api_pair_available_at_1800':False,'api_pair_available_at_1900':True,
        'pair_cell_1800_count':cell.count(),'pair_cell_available':cell.get_attribute('data-available') if cell.count() else None}
    (out/'pair-visibility.json').write_text(json.dumps(observed,indent=2)+'\n')
    page.screenshot(path=str(out/'occupied-pair-grid.png'),full_page=True)
    record_property('observed',json.dumps(observed))
    assert errors==[]
    expect(cell).to_have_count(0)
