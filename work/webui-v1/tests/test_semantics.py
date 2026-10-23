import copy
import json
import time
from pathlib import Path
import pytest
from tto_web.state import State
from producer import Producer,web_config,seed_predictions


def ready(seconds=120):
    p=Producer(time.monotonic()-seconds);s=State(web_config())
    for t in range(seconds+1):
        packet=p.step(t);s.accept(packet,now=p.start+t+.01)
    seed_predictions(s,packet)
    return p,s,packet


def test_forecast_uses_committed_values_and_is_not_recomputed_on_new_measurement():
    p,s,packet=ready()
    old=copy.deepcopy(s.predictions)
    assert [v['value_C'] for v in old.values()]==[46.,48.,50.]
    s.accept(p.step(121,tj=70),now=p.start+121.01)
    assert s.predictions==old
    assert s.snapshot()['forecast']['latest_prediction_ids']==list(old)


def test_units_zero_raw_rpm_and_no_secret_disclosure():
    p,s,packet=ready(12);m={m['id']:m for m in s.snapshot()['metrics']}
    assert m['power.gpu']['value']==1.984
    assert m['power.cpu_soc_mss']['value']==5.952
    assert m['power.gpu.average']['value']==1.988
    assert m['cpu.cores.0.usage']['value']==0
    assert m['memory.swap']['value']==0
    assert m['fan.rpm']['value'] is None and m['fan.rpm']['last_observation']['value']==0
    assert m['fan.rpm']['status']=='unverified'
    assert m['fan.pwm.target']['label']=='TianshanOS 目标 PWM'
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


def test_web_waits_for_backend_score_and_does_not_match_measurement_itself():
    p,s,packet=ready(12)
    page=seed_predictions(s,packet,[0])
    pred_id=page['records'][0]['prediction_id']
    s.accept(p.step(15,tj=47),now=p.start+15.01)
    assert s.predictions[pred_id]['status']=='pending'
    revised=copy.deepcopy(page);revised['cursor']+=1
    revised['records'][0].update(status='matched',observed_C=47.,error_C=-1.,settled_elapsed_ms=15000,revision=revised['cursor'])
    s.accept_predictions(revised,now=p.start+15.01)
    s.accept(p.step(16,tj=90),now=p.start+16.01)
    assert s.predictions[pred_id]['observed_C']==47 and s.predictions[pred_id]['error_C']==-1
    view=s.prediction_view(15)['summary'];assert view['matched_count']==1 and view['MAE_C']==1


def test_epoch_does_not_pair_and_delayed_publication_is_excluded():
    p,s,packet=ready(12)
    late=p.step(13);s.accept(late,now=p.start+110)
    # Expired observer state cannot issue a newly computed future forecast.
    assert all(v['origin_elapsed_ms']!=13000 for v in s.predictions.values())
    s.accept(p.row('boundary',111,None,reason='socketio_disconnected'),now=p.start+111.01)
    assert s.snapshot()['forecast']['latest_prediction_ids']==[]
    assert not s.prediction_view(45)['records']
    assert s.snapshot()['prediction_history_identity']['source_epoch']==s.snapshot()['source_epoch']
    # Only the publisher's terminal contract may select the earlier issued group.
    old={k:packet[k] for k in ('run_id','source_epoch','model_id','spec_id')}
    identity=dict(old,source_epoch=s.snapshot()['source_epoch'])
    terminal=dict(schema='TTO-PREDICTION-PAGE-v1',boot_id=packet['boot_id'],publisher_id=s.publisher_id,
        origin_mono_s=p.start,sync_status='synced',identity=identity,history_identity=old,ended=True,
        ended_at_mono_s=p.start+111,cursor=s.prediction_cursor,watermark=s.prediction_cursor,
        has_more=False,retained_from_mono_s=p.start-3600,records=[],forecast={})
    with pytest.raises(ValueError,match='history identity'):
        s.accept_predictions(dict(terminal,ended=False),now=p.start+111.01)
    with pytest.raises(ValueError,match='history identity'):
        s.accept_predictions(dict(terminal,history_identity=dict(old,run_id='other-run')),now=p.start+111.01)
    s.accept_predictions(terminal,now=p.start+111.01)
    assert s.snapshot()['source_epoch']==identity['source_epoch']
    assert s.snapshot()['prediction_history_identity']==old
    assert s.prediction_view(45)['records'] and s.snapshot()['publication_status']=='ended'
    s.begin_publication('next-publisher');s.refresh(p.start+112)
    assert s.snapshot()['prediction_history_identity'] is None and not s.prediction_view(45)['records']


def test_curve_reference_available_withheld_domain_and_identity():
    from tto.util import digest
    p,s,packet=ready();curve=dict(method_id='CURVE-REFERENCE-v1',verified=True,temperature_binding='agx_info.temperature.tj',device_id='SYNTHETIC-THOR',curve_id='SYNTHETIC-CURVE',source_config_sha256=packet['config_id'],fan_id=0,points=[[20,10],[80,70]])
    curve['sha256']=digest(curve);State.validate_curve(curve);s.curve=curve;s.refresh(p.start+120.01)
    assert s.snapshot()['advisory']['status']=='available'
    assert 10<=s.snapshot()['advisory']['value_percent']<=70
    assert s.last_advisory_basis['T_ref_C']>=44.3 and s.last_advisory_basis['device_write_permitted'] is False
    s.forecast['consumable_until_mono_s']=p.start+120.5
    s.refresh(p.start+120.01)
    assert s.snapshot()['advisory']['remaining_valid_ms']==pytest.approx(490)
    s.refresh(p.start+120.6)
    assert s.snapshot()['advisory']['value_percent'] is None
    packet=p.row('fan',121,p.fan(guard_active=True));s.accept(packet,now=p.start+121.01)
    assert s.snapshot()['advisory']['value_percent'] is None
    assert s.snapshot()['advisory']['reason']=='数据/模式/保护上下文不满足'
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
