"""Model history contract counterexamples; synthetic packets, no device or fitting."""
import asyncio
import copy
import json
import math
import time
from pathlib import Path
import aiohttp
import jsonschema
import pytest
from aiohttp import web
from producer import Producer,web_config
from tto_web.state import State,ModelRow,MODEL_GROUP,MODEL_IDS
from tto_web.source import Publication,follow
from tto_web.server import app_for
from tto_web.display import DisplayPublisher
import tto_web.state as state_module


@pytest.fixture(scope='module')
def factory():
    producer=Producer(1000.)
    for t in range(31):template=producer.step(t)
    def make(t,phase='tracking',values=(43.,41.,32.)):
        p=copy.deepcopy(template);p.update(origin_mono_s=1000.,input_mono_s=1000.+t,consumable_until_mono_s=1002.5+t)
        p['model'].update(phase=phase,Tf_C=values[0],Ts_C=values[1],E_C=values[2],conditional_inputs_rails_W_PWM=None)
        for m in p['metrics']:
            m.update(as_of_elapsed_ms=t*1000,_at=1000.+t,_expiry=1005.+t)
            if m['id']=='temperature.tj':m.update(sample_id=str(t),source_ref='synthetic:'+str(t),value=44.)
        p['tj_sample_id']=str(t)
        return p
    return make


def put(s,p,now=None):
    s.accept(p,now=p['input_mono_s']+.01 if now is None else now)


def columns(s,n=2000):return s.series(list(MODEL_GROUP),0,math.inf,n)


def assert_aligned(series):
    assert all([(p['t'],p['sample_id']) for p in r['points']]==[(p['t'],p['sample_id']) for p in series[0]['points']] for r in series)


def test_post_correction_values_and_only_fresh_tj(factory):
    s=State(web_config());p=factory(0);put(s,p)
    assert s.model_history[-1].values==(44.,43.,41.,32.)
    assert s.model_history[-1].values[1]!=s.model_history[-1].values[0]
    put(s,p,1000.02)
    p=factory(.1);p['new_tj']=False;put(s,p)
    assert len(s.model_history)==1
    p=factory(.2);put(s,p)
    series=columns(s);assert_aligned(series)
    assert series[1]['kind']=='estimate' and series[1]['estimate_stage']=='posterior'
    assert series[1]['points'][-1]['source_ref']=='synthetic:0.2'
    assert [r.t for r in s.model_history]==[0,200]


def test_real_observer_history_is_posterior_of_same_tj():
    producer=Producer(time.monotonic()-90.)
    s=State(web_config());checked=0
    for seconds in range(91):
        packet=producer.step(seconds,tj=44.3+3.*math.sin(seconds/8.))
        s.accept(packet,now=producer.start+seconds+.01)
        row=s.model_history[-1]
        if row.reason is not None:continue
        assert row.sample_id==packet['tj_sample_id']
        assert row.t==pytest.approx(seconds*1000.,abs=.001)
        tj,tf,_,_=row.values
        innovation=packet['model']['latest_innovation_C']
        assert tf!=tj
        assert (tj-tf)*innovation>0
        assert 0<=(tj-tf)/innovation<=1
        checked+=1
    assert checked>=60


@pytest.mark.parametrize('case,reason',[
    ('provisional','phase_unavailable'),('unavailable','phase_unavailable'),
    ('invalid_tj','tj_invalid'),('nan','nonfinite_state'),('inf','nonfinite_state'),
    ('expired','model_expired'),('at_deadline','model_expired'),('alignment','alignment_mismatch'),
    ('sample_identity','alignment_mismatch'),
])
def test_invalid_is_null_never_zero_or_hold(factory,case,reason):
    s=State(web_config());put(s,factory(0));p=factory(1);now=1001.01
    if case in ('provisional','unavailable'):p['model']['phase']=case
    if case=='invalid_tj':next(m for m in p['metrics'] if m['id']=='temperature.tj')['status']='invalid'
    if case in ('nan','inf'):p['model']['Ts_C']=float(case)
    if case=='expired':p['consumable_until_mono_s']=1000.9
    if case=='at_deadline':p['consumable_until_mono_s']=now
    if case=='alignment':next(m for m in p['metrics'] if m['id']=='temperature.tj')['as_of_elapsed_ms']=999.
    if case=='sample_identity':p['tj_sample_id']='different'
    put(s,p,now);assert s.model_history[-1].reason==reason
    assert s.model_history[-1].values==(None,)*4
    series=columns(s);assert_aligned(series)
    assert all(r['points'][-1]['value'] is None for r in series)
    json.dumps(series,allow_nan=False)


def test_invalid_duplicate_cannot_recover_without_new_sample(factory):
    s=State(web_config());p=factory(0,'provisional');put(s,p)
    p['model']['phase']='tracking';put(s,p,1000.02)
    assert s.model_history[-1].reason is not None
    put(s,factory(.1));assert s.model_history[-1].reason is None


def test_gap_barrier_delayed_sample_and_expiry_without_request(factory):
    s=State(web_config());put(s,factory(0));s.refresh(1002.6)
    assert s.model_history[-1].t==2500 and s.model_history[-1].reason=='model_expired'
    for t in range(20):s.refresh(1002.6+t*.01)
    assert len(s.model_history)==2
    put(s,factory(2),1003.)
    assert len(s.model_history)==2 and s.model_history[-1].t==2500
    put(s,factory(2.5),1003.01)
    assert len(s.model_history)==2 and s.model_history[-1].values==(None,)*4
    put(s,factory(3),1003.02);assert s.model_history[-1].values[1]==43
    assert [r.t for r in s.model_history]==[0,2500,3000]


def test_expiry_before_replacing_packet_not_lost(factory):
    s=State(web_config());put(s,factory(0));put(s,factory(3),1003.01)
    assert [r.reason for r in s.model_history]==[None,'model_expired',None]


def test_disconnect_advances_barrier_beyond_coalesced_expiry_gap(factory,monkeypatch):
    s=State(web_config());put(s,factory(0));s.refresh(1002.6)
    assert s.model_history[-1].t==2500 and s.model_history[-1].reason=='model_expired'
    monkeypatch.setattr(state_module.time,'monotonic',lambda:1004.)
    s.disconnect()
    assert s.model_gap_t==4000
    before=list(s.model_history)
    assert len(before)==2 and before[-1].t==2500
    delayed=factory(3)
    assert delayed['input_mono_s']<1004.01<delayed['consumable_until_mono_s']
    put(s,delayed,1004.01)
    assert list(s.model_history)==before


def test_gap_same_time_wins_and_disconnect_recovery(factory,monkeypatch):
    s=State(web_config());p=factory(0);put(s,p)
    p['publication_gap']=True;put(s,p,1000.02)
    assert len(s.model_history)==1 and s.model_history[0].reason=='publication_gap'
    p=factory(1);p['new_tj']=False;put(s,p)
    assert len(s.model_history)==1
    put(s,factory(2));assert s.model_history[-1].reason is None
    monkeypatch.setattr(state_module.time,'monotonic',lambda:1002.5)
    s.disconnect();assert s.model_history[-1].reason=='source_disconnected'
    put(s,factory(2.4),1002.6);assert s.model_history[-1].t==2500 and s.model_history[-1].values==(None,)*4
    put(s,factory(3),1003.01);assert s.model_history[-1].reason is None


@pytest.mark.parametrize('identity',['run_id','source_epoch'])
def test_identity_reset_clears_history_and_dedup(factory,identity):
    s=State(web_config());put(s,factory(0));p=factory(1)
    p[identity]=p[identity]+1 if identity=='source_epoch' else 'new-run'
    put(s,p);assert len(s.model_history)==1 and s.model_history[0].t==1000
    assert s.model_gap_t==-math.inf


@pytest.mark.parametrize('key',['model_id','spec_id'])
def test_frozen_mismatch_stays_rejected(factory,key):
    s=State(web_config());put(s,factory(0));p=factory(1);p[key]='test-alternate'
    with pytest.raises(ValueError,match='frozen model/spec'):put(s,p)
    assert len(s.model_history)==1


def test_common_extrema_signed_differences_and_gap_segment_edges():
    s=State(web_config())
    # None of the four columns at 40 is an individual min/max; only residual is.
    for i in range(200):
        values=(float(i),float(i),float(i),float(i))
        if i==40:values=(40.,35.,45.,50.)
        reason='publication_gap' if i in (70,72,100,110,120,130,140,150) else None
        s.model_history.append(ModelRow(i,(None,)*4 if reason else values,str(i),None,'test', 'tracking',reason))
    result=columns(s,16);assert_aligned(result)
    times=[p['t'] for p in result[0]['points']]
    assert {0,40,69,70,71,72,73,100,199}.issubset(times)
    assert result[0]['soft_budget_exceeded']
    assert result[0]['sampling']=='joint_bucket_extrema_and_gaps'
    assert s.model_series(['model.Tf_C'],0,math.inf,16)['model.Tf_C']['points']==result[1]['points']
    a=next(i for i,p in enumerate(result[0]['points']) if p['t']==40)
    assert result[1]['points'][a]['value']-result[2]['points'][a]['value']==-10
    assert result[2]['points'][a]['value']-result[3]['points'][a]['value']==-5


def test_capacity_trim_and_clear(factory):
    s=State(web_config());put(s,factory(0))
    for i in range(20000):s.model_history.append(ModelRow(i*200.,(44.,43.,41.,32.),str(i),'time','ref','tracking',None))
    assert len(s.model_history)==18002
    s.refresh(5000.)
    assert s.model_history[0].t>=400000 and len(s.model_history)<=18002
    p=factory(4001);p['run_id']='next';put(s,p)
    assert len(s.model_history)==1


async def serve(state):
    runner=web.AppRunner(app_for(web_config(),start_source=False,state=state),shutdown_timeout=.1)
    await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    return runner,'http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])


async def test_actual_publication_follow_http_contract_and_silent_expiry(publication_dir):
    p=Producer(time.monotonic()-30);s=State(web_config())
    for t in range(30):s.accept(p.step(t),now=p.start+t+.01)
    c=web_config();c['source']['active_descriptor']=str(publication_dir/'active.json')
    stop=asyncio.Event()
    async with Publication(publication_dir/'active.json') as pub:
        task=asyncio.create_task(follow(c,s,stop));runner,url=await serve(s)
        try:
            packet=p.step(30);pub.put(packet);await asyncio.sleep(.25)
            async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
                result=await(await client.get(url+'/api/v1/series?ids='+','.join(MODEL_GROUP))).json()
                schema=json.loads((Path(state_module.__file__).parent/'contracts/series.schema.json').read_text())
                jsonschema.validate(result,schema);assert_aligned(result['series'])
                assert result['series'][1]['points'][-1]['value']==packet['model']['Tf_C']
                assert result['service_epoch']==s.epoch and result['model_id']==packet['model_id']
                boot=await(await client.get(url+'/api/v1/bootstrap')).json()
                assert boot['series_capabilities']['model_state_history']
                assert {m['id'] for m in boot['available_series']}==set(MODEL_IDS)
                assert not any(m['id'] in MODEL_IDS for m in boot['available_fields'])
                old=s.series(['temperature.tj'],0,math.inf,2000)[0]
                assert old['points'][-1]['value']==44.3 and 'alignment_group' not in old
                default=await(await client.get(url+'/api/v1/series')).json()
                assert not any(r['id'] in MODEL_IDS for r in default['series'])
                assert (await client.get(url+'/api/v1/series?from=2&to=1')).status==400
                await asyncio.sleep(2.6)
                result=await(await client.get(url+'/api/v1/series?ids='+','.join(MODEL_GROUP))).json()
                jsonschema.validate(result,schema)
                assert result['series'][1]['points'][-1]['reason_code']=='model_expired'
                assert result['series'][1]['points'][-2]['value'] is not None
                # Actual optional display boundary converts encode failure to an immediate break.
                DisplayPublisher(pub.put).publish(lambda:(_ for _ in ()).throw(ValueError('SYNTHETIC')))
                await asyncio.sleep(.2);assert not s.source_connected
        finally:
            stop.set();task.cancel();await asyncio.gather(task,return_exceptions=True);await runner.cleanup()


def test_series_examples_validate():
    root=Path(state_module.__file__).parent/'contracts'
    schema=json.loads((root/'series.schema.json').read_text())
    examples=list(root.glob('series-example-*.json'));assert len(examples)==3
    for p in examples:jsonschema.validate(json.loads(p.read_text()),schema)
    example=json.loads((root/'series-example-tracking.json').read_text())
    for case in ('missing_alignment','wrong_kind','wrong_unit','missing_phase'):
        invalid=copy.deepcopy(example);row=invalid['series'][1]
        if case=='missing_alignment':row.pop('alignment_group')
        elif case=='wrong_kind':row['kind']='observed'
        elif case=='wrong_unit':row['unit']='W'
        else:row['points'][-1].pop('phase_at_sample')
        with pytest.raises(jsonschema.ValidationError):jsonschema.validate(invalid,schema)
    # Actual rc5 schema extracted from the sealed wheel, not reconstructed from rc6.
    old_schema=json.loads((Path(__file__).parent/'fixtures/series-rc5.schema.json').read_text())
    for case in ('joint_tj_kind','joint_tj_stage','numeric_sample_id'):
        invalid=copy.deepcopy(example)
        if case=='joint_tj_kind':invalid['series'][0]['kind']='estimate'
        elif case=='joint_tj_stage':invalid['series'][0]['estimate_stage']='posterior'
        else:invalid['series'][1]['points'][-1]['sample_id']=None
        jsonschema.validate(invalid,old_schema)
        with pytest.raises(jsonschema.ValidationError):jsonschema.validate(invalid,schema)


async def test_waiting_series_schema_and_unknown_fields_rejected():
    runner,url=await serve(State(web_config()))
    try:
        async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
            value=await(await client.get(url+'/api/v1/series?ids='+','.join(MODEL_GROUP))).json()
            schema=json.loads((Path(state_module.__file__).parent/'contracts/series.schema.json').read_text())
            jsonschema.validate(value,schema)
            assert value['run_id'] is None and value['model_id'] is None
            assert all(row['points']==[] for row in value['series'])
            wrong=copy.deepcopy(value);wrong['series'][1]['points']=[dict(t=0,value=None,status='unknown',sample_id=None,source_ref=None,received_at_utc=None,reason_code='invented')]
            with pytest.raises(jsonschema.ValidationError):jsonschema.validate(wrong,schema)
            wrong=copy.deepcopy(value);wrong['uncontracted']=True
            with pytest.raises(jsonschema.ValidationError):jsonschema.validate(wrong,schema)
    finally:await runner.cleanup()

