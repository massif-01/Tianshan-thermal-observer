"""Finite checks for this research-sidecar behavior, not production/firmware regression."""
from pathlib import Path
import copy
import io
import json
import socket
import sys
import pytest

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT))
from refprep.files import read,write,lines,sha,dump_lines
from refprep.records import register_session,load_session,normalize,commit_record,import_file,latest_records,temperature
from refprep.clocks import align_time,clock_map,utc_seconds,iso
from refprep.cues import CueEngine,DEFAULT_PLAN,replay_events,read_events,watch_file,actual_event
from refprep.compare import compare,asof_interval
from ref import main as cli


@pytest.fixture
def store(tmp_path):
    path=tmp_path/'sidecar'
    register_session(path,read(ROOT/'fixtures/synthetic/fin-session.json'))
    register_session(path,read(ROOT/'fixtures/synthetic/back-session.json'))
    return path


def test_T01_cli_plan_and_zero_compare_no_network(tmp_path,monkeypatch,capsys):
    def forbidden(*args,**kwargs):raise AssertionError('Network action forbidden')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket,'getaddrinfo',forbidden)
    assert cli(['plan'])==0
    result=compare(tmp_path/'empty',ROOT/'fixtures/real/M-frozen.jsonl',tmp_path/'report',draw=False)
    assert result['status']=='not_measured' and result['real_numeric_points']==0
    assert not result['physical_mapping_validated'] and result['coverage']
    assert (tmp_path/'report/中文对照报告.html').exists()


def test_T02_fixed_cues_no_model_selection_or_request_storm():
    events=read_events(ROOT/'fixtures/synthetic/events.jsonl');plan=read(ROOT/'fixtures/synthetic/cue-plan.json')
    a=replay_events(events,plan)
    changed=copy.deepcopy(events)
    for e in changed:e['imaginary_model_prediction']=999
    b=replay_events(changed+changed,plan)
    def signature(s):return [(r['status'],r['checkpoint_ids'],r['prompt_due_at_utc'],r['replay_emitted_at_utc']) for r in s['history']]
    assert signature(a)==signature(b)
    prompts=[r for r in a['history'] if r['status']=='prompt']
    assert len(prompts)==14
    assert all(p['prompt_emitted_at_utc'] is None and p['replay'] for p in prompts)
    times=[utc_seconds(p['replay_emitted_at_utc']) for p in prompts]
    assert all(b-a>=30 for a,b in zip(times,times[1:]))


def test_T02_real_runner_uses_actual_end_and_startup_does_not_catch_up(tmp_path):
    path=ROOT/'fixtures/real/M-runner-events-subset.jsonl'
    plan=read(ROOT/'fixtures/real/M-cue-plan.json')
    events=read_events(path);result=replay_events(events,plan)
    end=next(e for e in events if e['event']=='phase_end' and e['phase']=='M60')
    actual=actual_event(end)
    cue=next(h for h in result['history'] if any(k.startswith('medium-after30') for k in h['checkpoint_ids']))
    assert utc_seconds(cue['prompt_due_at_utc'])==pytest.approx(actual['utc_s']+30,abs=1e-6)
    assert end['actual_end_mono_s']!=end['planned_end_mono_s']
    state=watch_file(path,plan,tmp_path/'watch',follow=False)
    assert state['emitted_count']==0
    again=watch_file(path,plan,tmp_path/'watch',follow=False)
    assert again['emitted_count']==0


def test_T02_late_duplicate_merge_cap_and_early_end():
    plan=copy.deepcopy(DEFAULT_PLAN);plan['bindings']['medium']='M'
    engine=CueEngine(plan,replay=True)
    def event(kind,t,phase):return dict(event=kind,phase=phase,mono_s=t,occurred_at_utc=iso(t))
    engine.ingest(event('phase_end',100,'M'),400)
    engine.advance(400)
    assert engine.state['emitted_count']<=1
    assert sum(h['status']=='missed_late_event_no_catchup' for h in engine.state['history'])>=2
    fresh=CueEngine(plan,replay=True)
    fresh.ingest(event('phase_start',100,'sparse'),100)
    fresh.ingest(event('phase_end',110,'sparse'),110)
    assert any(h['status']=='not_collected_phase_ended' for h in fresh.state['history'])
    merge=CueEngine(plan,replay=True)
    merge.ingest(event('phase_end',100,'sparse'),100)
    merge.ingest(event('phase_end',110,'M'),110)
    assert any(len(c['checkpoint_ids'])==2 for c in merge.state['pending'])
    assert all(c['original_due'] for c in merge.state['pending'])


def test_T03_mark_late_value_and_write_are_distinct(store,capsys):
    assert cli(['mark','--store',str(store),'--session-id','SYNTH-fin','--record-id','late'])==0
    first=lines(store/'records.jsonl')[0]
    assert first['operator_mark_at_utc'] and first['measured_at_raw'] is None and first['temperature_c'] is None
    assert cli(['record','--store',str(store),'--session-id','SYNTH-fin','--record-id','late','--revise',
        '--value','42.1','--unit','C','--measured-at','2026-10-13T17:40:00+00:00','--uncertainty-s','2'])==0
    history=lines(store/'records.jsonl');current=latest_records(store)
    assert len(history)==2 and len(current)==1
    assert history[0]==first and current[0]['supersedes']==first['revision_id']
    assert current[0]['operator_mark_at_utc']==first['operator_mark_at_utc']
    assert current[0]['measured_at_raw']!=current[0]['recorded_at_utc']


def test_T03_timezones_unknown_precision_and_clock_domains(store):
    session=load_session(store,'SYNTH-fin')
    rec=normalize(store,'SYNTH-fin',dict(record_id='t',original_value=42,original_unit='C',
        measured_at_raw='2026-10-14T20:00:00+08:00',time_uncertainty_s=1))
    aligned=align_time(rec,session)
    assert aligned['interval_utc_s']==[utc_seconds('2026-10-14T12:00:00Z')-1,utc_seconds('2026-10-14T12:00:00Z')+1]
    rec['measured_at_raw']='2026-10-14T12:00:00'
    session['time']['timezone']=None
    assert align_time(rec,session)['status']=='timezone_unknown'
    rec['measured_at_raw']='2026-10-14T12:00:00Z';rec['time_uncertainty_s']=None
    assert align_time(rec,session)['interval_utc_s'] is None
    rec['clock_domain']='camera-not-host'
    assert align_time(rec,session)['status']=='measurement_clock_not_session_clock'
    session['time']=dict(clock_domain='camera',sync_anchors=[])
    rec['clock_domain']='camera'
    assert align_time(rec,session)['status']=='unaligned_clock'


def test_T03_independent_offset_drift_and_monotonic_not_temperature():
    profile=dict(clock_domain='camera',sync_anchors=[dict(clock_time=100.,run_utc=iso(1000),uncertainty_s=.2,evidence='clock-photo-1')])
    m=clock_map(profile,'run')
    assert m['scale']==1 and m['offset']==900 and m['anchor_error_s']==.2
    assert 'single_anchor_offset_only_drift_unverified' in m['flags']
    profile['sync_anchors'].append(dict(clock_time=200.,run_utc=iso(1100.1),uncertainty_s=.3,evidence='clock-photo-2'))
    m=clock_map(profile,'run');assert m['scale']==pytest.approx(1.001)
    s=dict(run_id='run',time=profile);r=dict(run_id='run',clock_domain='camera',measured_at_raw=150.,time_uncertainty_s=.1,temperature_c=41)
    a=align_time(r,s);r['temperature_c']=100
    assert align_time(r,s)==a
    mono=dict(clock_domain='run_monotonic',sync_basis='same host clock pair',sync_uncertainty_s=.1)
    assert clock_map(mono,'run',dict(run_id='run',utc_s=1000,mono_s=12))['offset']==988


@pytest.mark.parametrize('value,unit,expected',[(32,'F',0),(108.5,'F',42.5),(0,'C',0),(None,'C',None)])
def test_T04_units_null_and_no_precision_invention(value,unit,expected):
    assert temperature(value,unit)==expected


@pytest.mark.parametrize('value',['NaN','Infinity',float('-inf')])
def test_T04_nonfinite_not_normal_reading(value):
    with pytest.raises(ValueError):temperature(value,'C')


def test_T04_session_and_site_kind_never_silently_merge(store):
    s=load_session(store,'SYNTH-fin');s['settings']['emissivity']=.8
    with pytest.raises(ValueError,match='Immutable'):register_session(store,s)
    with pytest.raises(ValueError,match='measurement_kind mismatch'):
        normalize(store,'SYNTH-fin',dict(record_id='wrong',measurement_kind='outlet_air',original_value=42,original_unit='C'))
    assert load_session(store,'SYNTH-fin')['settings']['emissivity'] is None


def test_T05_generic_csv_json_duplicate_and_artifact_sha(store,tmp_path):
    fixture=ROOT/'fixtures/synthetic'
    image=fixture/'image-evidence.png';before=sha(image)
    a=import_file(store,fixture/'external.csv',read(fixture/'csv-mapping.json'))
    b=import_file(store,fixture/'external.csv',read(fixture/'csv-mapping.json'))
    assert a['added']==3 and b['status']=='duplicate_import' and b['added']==0
    import_file(store,fixture/'external.json',read(fixture/'json-mapping.json'))
    records=latest_records(store);assert len(records)==5
    assert next(r for r in records if r['record_id']=='fin-work')['temperature_c']==42.5
    picture=next(r for r in records if r['record_id']=='fin-image-only')
    assert picture['temperature_c'] is None and picture['artifact']['sha256']==before
    assert sha(store/picture['artifact']['stored_relative_path'])==before==sha(image)
    assert picture['artifact']['numeric_decoding']=='not_performed'
    assert picture['measured_at_raw'] is None and picture['artifact']['mtime_s_diagnostic_only']


def test_T06_image_metadata_not_exposure_and_unknown_brand_allowed(store):
    rec=normalize(store,'SYNTH-fin',dict(record_id='photo',artifact_path=ROOT/'fixtures/synthetic/image-evidence.png',
        image_metadata_time_raw='2026-10-14T12:00:00Z'))
    assert rec['temperature_c'] is None and rec['measured_at_raw'] is None
    assert rec['artifact']['image_metadata_time_raw']
    assert 'unknown_settings_emissivity' in rec['measurement_flags']


def test_T08_interval_range_not_best_match_and_no_gap_interpolation():
    def row(t,end,seg='a'):
        return dict(utc_s=t,valid_until_utc_s=end,segment=seg,source_epoch=1,state_input_cutoff_utc_s=t,ref=str(t),
            **{k:40+t for k in ['measured_TJ_C','Tf_A_long_C','Ts_A_long_C','STATE_G2_C','STATE_LP30_C','STATE_QS_C','STATE_LP120_C','actual_successful_PWM_percent_at_state_origin']})
    rows=[row(10,11.5),row(11,11.4),row(12.5,14)]
    a=asof_interval(rows,10.2,11.2)
    assert a['ranges']['STATE_G2_C']==[50,51]
    assert asof_interval(rows,11.2,12.6)['ranges'] is None
    assert asof_interval(rows,11.6,11.7)['status']=='asof_state_expired'
    contiguous=[row(10,11),row(11,12,'new')]
    assert 'boundary' in asof_interval(contiguous,10.2,11.2)['status']
    real=lines(ROOT/'fixtures/real/M-frozen.jsonl')
    assert asof_interval(real,real[20]['utc_s'],real[24]['utc_s'])['ranges'] is not None
    assert all(r['original_qualification_refs'] and 'sealed original' in r['validity_source'] for r in real)


def test_T07_T09_external_changes_do_not_change_models_or_select_new_reference(store,tmp_path):
    trajectory=ROOT/'fixtures/real/M-frozen.jsonl';before=sha(trajectory)
    times=read(ROOT/'fixtures/synthetic/point-times.json')
    for ident,value,key in [('fin-bg',41,'background'),('second',42,'work')]:
        rec=normalize(store,'SYNTH-fin',dict(record_id=ident,original_value=value,original_unit='C',
            measured_at_raw=times[key],time_uncertainty_s=0))
        commit_record(store,rec)
    first=compare(store,trajectory,tmp_path/'a',draw=False)
    values=dict(record_id='second',original_value=80,original_unit='C',measured_at_raw=times['work'],time_uncertainty_s=0)
    commit_record(store,normalize(store,'SYNTH-fin',values),allow_revision=True)
    second=compare(store,trajectory,tmp_path/'b',draw=False)
    p=lines(tmp_path/'b/paired-points.jsonl')
    assert all(v['delta']['reference_record_id']=='fin-bg' for v in p if v['delta'])
    assert before==sha(trajectory) and first['model_sha256']==second['model_sha256']
    assert second['physical_mapping_validated'] is False and not second['model_refit']


def test_T03_interactive_capture_is_interval_not_exact_camera_exposure(store,monkeypatch,capsys):
    s=read(ROOT/'fixtures/synthetic/fin-session.json');s['session_id']='unknown-camera';s['time']=dict(clock_domain='camera',sync_anchors=[])
    register_session(store,s);monkeypatch.setattr('builtins.input',lambda prompt:'42')
    assert cli(['record','--store',str(store),'--session-id','unknown-camera','--capture-interval'])==0
    rec=latest_records(store)[-1]
    assert rec['measured_interval_raw']['start']<=rec['measured_interval_raw']['end']
    assert rec['measured_at_raw'] is None and rec['clock_domain']=='operator_host_utc'
    assert align_time(rec,s)['interval_utc_s'] is None


def test_T11_maintenance_only_numeric_tolerance_original_hash_strict():
    provenance=read(ROOT/'maintenance/provenance.json')
    original=ROOT/'handoff/references/slowstate-snapshot/tests/test_slowstate.py'
    assert sha(original)==provenance['original_test_file_sha256']
    old=(ROOT/'maintenance/original-target-test.txt').read_text()
    new=(ROOT/'maintenance/tolerance-target-test.py.txt').read_text()
    assert new==old.replace("assert all(r['Tf']==r['sealed_Tf'] for r in long)","assert all(abs(r['Tf']-r['sealed_Tf'])<=1e-10 for r in long)")
    source=ROOT.parent/'thermal_slowstate_v1'
    if source.exists():
        def replay_lines(path):
            value=lines(path)
            if path.name=='states-A-long.jsonl':value[0]['Tf']+=1e-14  # in-memory cross-platform rounding example only
            return value
        ns=dict(ROOT=source,read=read,jsonlines=replay_lines)
        exec(compile(new,'maintained-old-target','exec'),ns)
        ns['test_two_dimensional_export_and_anchor_not_forecast']((None,None,None,lines(source/'results/states-causal60.jsonl')))
    assert sha(original)==provenance['original_test_file_sha256']
