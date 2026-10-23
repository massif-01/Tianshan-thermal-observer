import copy
import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from eligibility import replay_evidence,assess_saved_prediction
from event_metrics import event_metrics
from tto.engine import engine_for
from tto.storage import Journal
from tto.demo import fan_packet,temp_packet
# Original synthetic platform producer, not a permissive new parser.
sys.path.insert(0,str(Path(__file__).parents[3]/'tests'))
from test_platform_curve import new_packet
from tto.config import load_config


def recorded(tmp_path,fan_gap=(),power_gap=(),abnormal=None,conflict=False):
    c=load_config(environ={});c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='owned synthetic fixture')
    engine=engine_for(c,record_schema=2);j=Journal(c,tmp_path,simulated=True,record_schema=2)
    for t in range(121):
        rows=[]
        if t not in fan_gap:
            fan=fan_packet(19)
            if abnormal and t==72:fan['data']['fans'][0][abnormal]=True
            rows.append(dict(kind='fan',payload=fan,mono_s=float(t)))
        if t%5==0:rows.append(dict(kind='temp',payload=temp_packet(),mono_s=float(t)))
        p=new_packet(t+1)
        if t in power_gap:p['power'].pop('vdd_gpu')
        rows.append(dict(kind='orin',payload=p,mono_s=float(t),connection_epoch=1))
        if conflict and t==72:
            changed=copy.deepcopy(rows[-1]);changed['payload']['temperature']['tj']+=1;rows.append(changed)
        for r in rows:
            r['received_at_utc']='2026-10-13T00:00:00+00:00';saved=j.observation(r);out=engine.process(saved);j.processing_output(saved,out)
    j.close({});return replay_evidence(j.path)


def prediction(e,t=60,h=15):
    s=next(s for s in e['samples'] if s['t']==t)
    return dict(ref=s['ref'],t=t,h=h,B={'B0':45.,'B1':46.,'R_TJ':47.,'R_IO':48.,'G2-HOLD':49.},unavailable={})


def test_future_fan_gap_and_power_gap_keep_B_values_and_truth(tmp_path):
    for kind in ['fan','power']:
        e=recorded(tmp_path/kind,fan_gap=range(70,75) if kind=='fan' else (),power_gap=range(70,75) if kind=='power' else ())
        p=prediction(e);r=assess_saved_prediction(e,p)
        assert r['target_valid'] and r['B_values']==p['B'] and not r['A_eligible']
        assert r['control_context']=='aux_observation_gap'
        assert all(r['origin_inputs_valid'].values())


def test_origin_missing_PWM_blocks_IO_but_TJ_methods_keep_own_inputs(tmp_path):
    e=recorded(tmp_path,fan_gap=range(55,66));r=assess_saved_prediction(e,prediction(e,t=60))
    assert r['origin_inputs_valid']['B0'] and r['origin_inputs_valid']['B1'] and r['origin_inputs_valid']['R_TJ']
    assert not r['origin_inputs_valid']['R_IO'] and not r['origin_inputs_valid']['G2-HOLD']


def test_explicit_abnormal_and_original_source_isolation_not_restored(tmp_path):
    for flag in ['temp_stale','guard_active','fault']:
        e=recorded(tmp_path/flag,abnormal=flag);r=assess_saved_prediction(e,prediction(e))
        assert r['target_valid'] and r['control_context']=='observed_abnormal_or_changed'
    e=recorded(tmp_path/'conflict',conflict=True);r=assess_saved_prediction(e,prediction(e))
    assert not r['target_valid'] and e['isolated_segments']


def test_independent_labels_and_future_temperatures_cannot_modify_emitted_B(tmp_path):
    e=recorded(tmp_path);p=prediction(e,t=60,h=45);r=assess_saved_prediction(e,p)
    assert r['target_valid'];assert not assess_saved_prediction(e,prediction(e,t=60,h=90))['target_valid']
    changed=copy.deepcopy(e)
    for s in changed['samples']:
        if s['t']>60:s['values']['tj']+=50
    assert assess_saved_prediction(changed,p)['B_values']==r['B_values']
    assert p['B']=={'B0':45.,'B1':46.,'R_TJ':47.,'R_IO':48.,'G2-HOLD':49.}


def test_peak_comparison_uses_common_times_and_area_is_not_energy():
    samples=[dict(ref=str(t),t=float(t),target_valid=True,source_epoch=1,control_eligible=True,values={'tj':40.+(5 if t==1 else 0),'duty':19}) for t in range(-30,10)]
    nodes=[dict(t=float(t),complete=True,valid_until=t+1) for t in range(-30,10)]
    models=[dict(ref=str(t),A={'G1':41.,'G2':42.}) for t in range(2,6)]
    r=event_metrics(samples,nodes,dict(start=0.,end=2.),models)
    assert r['actual_peak_C']==45 and r['model_peak_comparison']['G2']['actual_peak_C']==40
    assert r['model_peak_comparison']['G2']['peak_window_incomplete']
    assert r['positive_temperature_rise_area_C_s']==5 and r['not_energy_or_heat_capacity']
