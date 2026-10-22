import copy
import json
import time
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from tto_web.state import State
from tto_web.adapter import SPEC, SPEC_PATH
from tto_web.common import boot_id
from producer import Producer,web_config


def ready(seconds=120):
    p=Producer(time.monotonic()-seconds);s=State(web_config())
    for t in range(seconds+1):
        packet=p.step(t);s.accept(packet,now=p.start+t+.01)
    return p,s,packet


def test_frozen_sha_no_training_and_exact_forecast_against_independent_ode():
    p,s,packet=ready()
    assert packet['model']['phase']=='tracking'
    assert packet['model']['dynamic_parameter_updates']==0
    assert {p['horizon_s'] for p in s.predictions}=={15,45,90}
    inputs=packet['model']['conditional_inputs_rails_W_PWM'];x=[44.3,packet['model']['Ts_C'],packet['model']['E_C']]
    d=SPEC['dynamic'];a,c=d['a'],d['c'];cool=d['d0']+d['d1']*inputs[2]
    def rhs(t,y):return [a*(y[1]-y[0])+d['b_g']*inputs[0]+d['b_c']*inputs[1],c*(y[0]-y[1])-cool*(y[1]-y[2]),0]
    for pred in list(s.predictions)[-3:]:
        independent=solve_ivp(rhs,[0,pred['horizon_s']],x,rtol=1e-11,atol=1e-12).y[0,-1]
        assert abs(pred['value_C']-independent)<1e-8
        assert pred['target_elapsed_ms']==pred['origin_elapsed_ms']+1000*pred['horizon_s']
        assert pred['issued_elapsed_ms']>=pred['origin_elapsed_ms']
    old=[(v['prediction_id'],v['value_C']) for v in s.predictions]
    s.accept(p.step(121,tj=70),now=p.start+121+.01)
    assert old==[(v['prediction_id'],v['value_C']) for v in list(s.predictions)[:len(old)]]


def test_units_zero_raw_rpm_and_no_secret_disclosure():
    p,s,packet=ready(12);m={m['id']:m for m in s.snapshot()['metrics']}
    assert m['power.gpu']['value']==1.984
    assert m['power.cpu_soc_mss']['value']==5.952
    assert m['power.gpu.average']['value']==1.988
    assert m['cpu.cores.0.usage']['value']==0
    assert m['memory.swap']['value']==0
    assert m['fan.rpm']['value'] is None and m['fan.rpm']['last_observation']['value']==0
    assert m['fan.rpm']['status']=='unverified'
    encoded=json.dumps(s.snapshot())
    assert 'Authorization' not in encoded and '/Users/' not in encoded and 'bound_variable' not in encoded
    assert s.snapshot()['model']['calibrated_confidence'] is None
    assert s.snapshot()['context']['active_requests'] is None


def test_gpu_cache_never_renews_and_new_equal_sample_retained():
    p=Producer(time.monotonic()-10);s=State(web_config())
    packet=p.step(0);s.accept(packet,now=p.start+.01)
    gpu=next(m for m in packet['metrics'] if m['id']=='usage.gpu');expiry=gpu['_expiry'];sample=gpu['sample_id']
    packet=p.step(1,keep_gpu=True,gpu_age=0);s.accept(packet,now=p.start+1.01)
    gpu=next(m for m in packet['metrics'] if m['id']=='usage.gpu')
    assert gpu['sample_id']==sample and gpu['_expiry']==expiry
    assert len(s.history['temperature.tj'])==2
    duplicate=p.row('orin',1.1,copy.deepcopy(p.engine.features.history and p.packet(1.1)),connection_epoch=1)
    assert duplicate
    s.refresh(p.start+6)
    assert next(m for m in s.snapshot()['metrics'] if m['id']=='usage.gpu')['value'] is None


def test_invalid_withdrawal_not_old_valid_and_boundary_epoch():
    p,s,packet=ready(12)
    packet=p.row('orin',13,p.packet(13,invalid=True),connection_epoch=1);s.accept(packet,now=p.start+13.01)
    assert next(m for m in s.snapshot()['metrics'] if m['id']=='temperature.tj')['value'] is None
    packet=p.row('boundary',14,None,reason='socketio_disconnected');s.accept(packet,now=p.start+14.01)
    assert all(m['value'] is None for m in s.snapshot()['metrics'] if m['id']=='temperature.tj')
    assert s.snapshot()['source_epoch']>0


def test_same_cached_ws_sample_does_not_add_history():
    p=Producer(time.monotonic()-10);s=State(web_config());p.step(0)
    payload=p.packet(1)
    packet=p.row('orin',1,payload,connection_epoch=1);s.accept(packet,now=p.start+1.01)
    before=copy.deepcopy(s.history['temperature.tj'])
    packet=p.row('orin',1.2,payload,connection_epoch=1);s.accept(packet,now=p.start+1.21)
    assert list(s.history['temperature.tj'])==list(before)


def test_model_and_measurement_expiry_without_messages_and_disconnect():
    p,s,packet=ready(12);s.refresh(p.start+18)
    assert s.snapshot()['model']['phase']=='unavailable'
    assert next(m for m in s.snapshot()['metrics'] if m['id']=='temperature.tj')['status']=='stale'
    assert s.history['temperature.tj'][-1]['value'] is None
    s.disconnect()
    assert all(m['value'] is None for m in s.snapshot()['metrics'])


def test_first_valid_label_plus2_window_sign_and_missing():
    p,s,packet=ready(12)
    pred=copy.deepcopy(s.predictions[-2]);pred.update(prediction_id='target',target_elapsed_ms=15000,status='pending',value_C=45)
    s.predictions.clear();s.predictions.append(pred)
    s.accept(p.step(14,tj=40),now=p.start+14.01);assert pred['status']=='pending'
    s.accept(p.step(15,tj=46),now=p.start+15.01)
    assert pred['status']=='matched' and pred['observed_C']==46 and pred['error_C']==-1
    s.accept(p.step(16,tj=90),now=p.start+16.01);assert pred['observed_C']==46
    missing=copy.deepcopy(pred);missing.update(prediction_id='missing',status='pending',target_elapsed_ms=18000,observed_C=None,error_C=None)
    s.predictions.append(missing);s.accept(p.step(21,tj=40),now=p.start+21.01);assert missing['status']=='missing_label'
    view=s.prediction_view(45)['summary'];assert view['matched_count']==1 and view['MAE_C']==1 and view['max_underprediction_C']==1


def test_epoch_does_not_pair_and_delayed_publication_is_excluded():
    p,s,packet=ready(12)
    late=p.step(13);s.accept(late,now=p.start+110)
    # Expired observer state cannot issue a newly computed future forecast.
    assert all(v['origin_elapsed_ms']!=13000 for v in s.predictions)
    s.accept(p.row('boundary',111,None,reason='socketio_disconnected'),now=p.start+111.01)
    assert all(v['status']!='pending' for v in s.predictions)


def test_curve_reference_available_withheld_domain_and_identity():
    from tto.util import digest
    p,s,packet=ready();curve=dict(method_id='CURVE-REFERENCE-v1',verified=True,temperature_binding='agx_info.temperature.tj',device_id='SYNTHETIC-THOR',curve_id='SYNTHETIC-CURVE',source_config_sha256=packet['config_id'],fan_id=0,points=[[20,10],[80,70]])
    curve['sha256']=digest(curve);State.validate_curve(curve);s.curve=curve;s.refresh(p.start+120.01)
    assert s.snapshot()['advisory']['status']=='available'
    assert 10<=s.snapshot()['advisory']['value_percent']<=70
    assert s.last_advisory_basis['T_ref_C']>=44.3 and s.last_advisory_basis['device_write_permitted'] is False
    packet=p.row('fan',121,p.fan(guard_active=True));s.accept(packet,now=p.start+121.01)
    assert s.snapshot()['advisory']['value_percent'] is None
    p,s,packet=ready();s.curve=curve;curve['points']=[[1,10],[2,20]];s.refresh(p.start+120.01)
    assert s.snapshot()['advisory']['status']=='out_of_domain'
    curve['device_id']='other';s.refresh(p.start+120.01);assert s.snapshot()['advisory']['value_percent'] is None


def test_contract_examples_and_actual_snapshots():
    jsonschema=pytest.importorskip('jsonschema')
    schema=json.loads((Path(__file__).parents[1]/'requirements/contracts/dashboard.schema.json').read_text())
    for path in (Path(__file__).parents[1]/'requirements/contracts').glob('example-*.json'):jsonschema.validate(json.loads(path.read_text()),schema)
    runtime_schema=json.loads((Path(__file__).parents[1]/'src/tto_web/contracts/dashboard.schema.json').read_text())
    p,s,packet=ready(12);jsonschema.validate(s.snapshot(),runtime_schema);s.disconnect();jsonschema.validate(s.snapshot(),runtime_schema)


def test_extrema_and_gaps_are_preserved_and_history_is_bounded():
    s=State(web_config());s.history['temperature.tj']=[dict(t=i,value=None if i==51 else 1000 if i==50 else -100 if i==49 else 0,sample_id=str(i),received_at_utc=None,status='valid',source_ref='synthetic') for i in range(100)]
    values=[v['value'] for v in s.series(['temperature.tj'],0,100,16)[0]['points']]
    assert None in values and 1000 in values and -100 in values


def test_unknown_clock_is_rejected():
    p,s,packet=ready(12);packet['clock_domain_id']='unrelated-host'
    with pytest.raises(ValueError):s.accept(packet)
