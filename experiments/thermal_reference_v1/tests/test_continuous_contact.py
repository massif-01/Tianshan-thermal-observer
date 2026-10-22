"""ADD1 acceptance using generic synthetic CSV; no claim about actual YET export syntax."""
from pathlib import Path
import copy
import csv
import sys
import pytest

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT))
from refprep.files import read,write,sha,lines
from refprep.records import register_session,import_file,latest_records,session_event
from refprep.clocks import align_time
from refprep.compare import compare


@pytest.fixture
def contact(tmp_path):
    store=tmp_path/'normalized';fixture=ROOT/'fixtures/contact-synthetic'
    for site in ['fin','back']:register_session(store,read(fixture/(site+'-session.json')))
    return store,fixture


def test_ADD1_original_rows_equal_values_channel_mapping_and_cadence(contact):
    store,fixture=contact;path=fixture/'generic-continuous.csv';digest=sha(path)
    receipt=import_file(store,path,read(fixture/'mapping.json'))
    assert receipt['rows']==240 and receipt['added']==239 and receipt['rejected_rows']==1
    records=latest_records(store)
    assert len(records)==239
    assert len([r for r in records if r['temperature_c']==41])>1
    assert {r['site_id'] for r in records}=={'SYNTH-contact-fin-site','SYNTH-contact-back-site'}
    assert sha(store/receipt['raw_stored_relative_path'])==digest==sha(path)
    ledger=lines(store/receipt['row_ledger_relative_path'])
    err=next(r for r in ledger if r['status']=='rejected')
    assert err['provenance']['original_row']['temperature']=='ERR' and err['reason']
    assert err['provenance']['csv_line_span'][0]==err['provenance']['input_row']+1
    missing=next(r for r in records if r['record_id']=='contact-A-52')
    assert missing['temperature_c'] is None and missing['original_value']==''
    assert not any(r['record_id']=='contact-A-75' for r in records)
    bg=next(r for r in records if r['record_id']=='contact-bg')
    assert bg['measured_at_raw']==0 and bg['instrument_sample_time_raw']=='0'
    assert bg['provenance']['exported_at_raw']!=bg['recorded_at_utc']
    for cadence in receipt['cadence'].values():
        assert cadence['positive_interval_median_s']==1 and cadence['positive_interval_max_s']>=2
        assert cadence['equal_adjacent_temperature_pairs']>50
    again=import_file(store,path,read(fixture/'mapping.json'))
    assert again['added']==0 and again['status']=='duplicate_import'
    assert len(latest_records(store))==239


def test_ADD1_relative_time_needs_anchor_and_interval_basis(contact,tmp_path):
    store,fixture=contact;mapping=read(fixture/'mapping.json')
    mapping['time_axis']['mode']='relative_seconds'
    mapping['time_axis']['interval_basis']=None
    with pytest.raises(ValueError,match='independent'):import_file(store,fixture/'generic-continuous.csv',mapping)
    mapping['time_axis']['interval_basis']='synthetic setting'
    session=read(fixture/'fin-session.json');session['time']['sync_anchors']=[]
    other=tmp_path/'no-anchor';register_session(other,session)
    mapping['channels']={'A':dict(session_id=session['session_id'],site_id=session['site_id'])}
    result=import_file(other,fixture/'generic-continuous.csv',mapping)
    assert result['added']==0 and result['rejected_rows']==240
    ledger=lines(other/result['row_ledger_relative_path'])
    assert any('independent start anchor' in r['reason'] for r in ledger)
    assert not (other/'records.jsonl').exists()


def test_ADD1_timestamp_and_wide_column_selection_no_value_dedup(contact,tmp_path):
    store,fixture=contact;mapping=read(fixture/'mapping.json')
    # Selecting a named wide temperature column needs no vendor-specific parser.
    path=tmp_path/'wide.csv'
    path.write_text('time,probe_A,probe_B\n1,42,43\n2,42,43\n3,42,43\n')
    mapping['columns']=dict(measured_at_raw='time',original_value='probe_A')
    mapping['constants'].update(session_id='SYNTH-contact-fin',original_unit='C',original_channel='A')
    mapping.pop('channels');mapping['time_axis']['mode']='relative_seconds'
    receipt=import_file(store,path,mapping)
    assert receipt['added']==3 and all(r['temperature_c']==42 for r in latest_records(store))
    assert len({r['record_id'] for r in latest_records(store)})==3
    # Timestamp route retains actual instrument strings; independent anchors still govern alignment.
    stamp=tmp_path/'stamps.json';write(stamp,[dict(t='2026-10-14T10:00:00+08:00',v=108.5)])
    mapping['columns']=dict(measured_at_raw='t',original_value='v');mapping['constants']['original_unit']='F'
    mapping['time_axis']=dict(mode='timestamp')
    assert import_file(store,stamp,mapping)['added']==1
    assert latest_records(store)[-1]['temperature_c']==42.5
    session=read(store/'sessions/SYNTH-contact-fin.json')
    assert align_time(latest_records(store)[-1],session)['status']=='sample_clock_coordinate_not_anchor_clock'


def test_ADD1_contact_no_IR_requirements_unknown_response_and_independent_time(contact,tmp_path):
    store,fixture=contact;mapping=read(fixture/'mapping.json')
    import_file(store,fixture/'generic-continuous.csv',mapping)
    session=read(store/'sessions/SYNTH-contact-fin.json')
    assert not any('emissivity' in f or 'roi' in f or 'reflected' in f for f in session['quality_limitations'])
    assert any('response_not_calibrated' in f for f in session['quality_limitations'])
    record=next(r for r in latest_records(store) if r['record_id']=='contact-A-60')
    timing=align_time(record,session)
    assert timing['interval_utc_s'] and timing['mapping']['drift_ppm']==pytest.approx(100,abs=.01)
    changed=copy.deepcopy(record);changed['temperature_c']=999
    assert align_time(changed,session)==timing
    session['time']['sync_anchors'][1]['uncertainty_s']=None
    assert align_time(record,session)['interval_utc_s'] is None


def test_ADD1_probe_integrity_events_require_new_session_and_leave_model_frozen(contact,tmp_path):
    store,fixture=contact;mapping=read(fixture/'mapping.json');trajectory=ROOT/'fixtures/real/M-frozen.jsonl'
    before=sha(trajectory);import_file(store,fixture/'generic-continuous.csv',mapping)
    event=session_event(store,'SYNTH-contact-fin','probe_loose','90',.5,'SYNTHETIC deliberate event')
    assert event['new_session_required']
    result=compare(store,trajectory,tmp_path/'report',draw=False)
    paired=lines(tmp_path/'report/paired-points.jsonl')
    post=[r for r in paired if r['record']['session_id']=='SYNTH-contact-fin' and r['record']['measured_at_raw']>=90]
    assert post and all(r['model_match']['ranges'] is None for r in post)
    assert any(r['model_match']['ranges'] is not None for r in paired if r['record']['session_id']=='SYNTH-contact-back')
    assert before==sha(trajectory) and result['status']=='synthetic_demo_only'
    assert not result['physical_mapping_validated'] and not result['real_YET_CSV_mapping_accepted']
    assert not result['model_refit'] and result['session_events'][0]['event_id']==event['event_id']
