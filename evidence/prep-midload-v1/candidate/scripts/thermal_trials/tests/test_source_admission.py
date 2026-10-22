"""R1: production source decisions feed real health and real scheduling."""
import asyncio
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[3]/'tests'))
from tto.config import load_config
from tto.engine import engine_for
from tto.demo import fan_packet,temp_packet
from test_platform_curve import new_packet
from health import TrialHealth
from trial import run_schedule
from test_schedule import FakeClock,FakeRequester


def feed(engine,health,t,seq,missing=False,kind='orin'):
    for aux,payload in [('fan',fan_packet(19)),('temp',temp_packet())]:
        record=dict(kind=aux,payload=payload,mono_s=float(t),ref=f'r1/{aux}:{t}',observer_run_id='r1-source-fixture')
        health.observe(record,engine.process(record),engine)
    payload=new_packet(seq)
    if missing:payload['temperature'].pop('tj')
    record=dict(kind=kind,payload=payload,mono_s=float(t),ref=f'r1/{kind}:{seq}:{t}',connection_epoch=1,observer_run_id='r1-source-fixture')
    result=engine.process(record);health.observe(record,result,engine);return result['quality']


def replay(end):
    engine=engine_for(load_config(environ={}),record_schema=2);health=TrialHealth()
    for t in range(end+1):feed(engine,health,t,t+1,missing=71<=t<=131)
    return engine,health


@pytest.mark.asyncio
@pytest.mark.parametrize('at,current,history,requests',[(70,True,True,1),(71,False,False,0),(131,False,False,0),(132,True,False,0),(191,True,False,0),(192,True,True,1)])
async def test_normal_missing_TJ_and_recovery_through_production_schedule(tmp_path,at,current,history,requests):
    engine,health=replay(at);snapshot=health.snapshot(at)
    assert snapshot['current_ready'] is current and snapshot['continuous_60s'] is history
    assert snapshot['abnormal'] is False
    if 71<=at<=131:
        assert snapshot['latest']['source_accepted_t']==70 and snapshot['latest']['source_age_ms']==(at-70)*1000
        assert engine.q.anchor_t==at  # Refused message time must not refresh the stored value.
    clock=FakeClock();clock.t=float(at);stop=asyncio.Event();collector=asyncio.create_task(stop.wait());requester=FakeRequester(clock,.2);events=[]
    try:
        result=await run_schedule(clock,health,requester,stop,collector,lambda event,**kw:events.append(dict(event=event,**kw)),
                                  phases=[('R1-admission','work',.15)],hard_limit_s=10)
    finally:stop.set();await collector
    assert len(requester.starts)==requests
    (tmp_path/'decision.json').write_text(json.dumps(dict(at=at,snapshot=snapshot,requests=requester.starts,result=result,events=events),indent=2)+'\n')


def test_duplicate_never_refreshes_the_accepted_sample_deadline():
    engine,health=replay(70);deadline=health.snapshot(70)['latest']['source_valid_until']
    for t in range(71,77):
        q=feed(engine,health,t,71)
        assert q['reason']=='duplicate' and not q['accepted']
        assert health.snapshot(t)['latest']['source_valid_until']==deadline
    assert not health.snapshot(76)['current_ready']


def test_source_boundary_keeps_current_and_continuous_recovery_separate():
    engine,health=replay(70)
    record=dict(kind='boundary',reason='socketio_disconnected',mono_s=70.5,ref='r1/disconnected',observer_run_id='r1-source-fixture')
    health.observe(record,engine.process(record),engine)
    assert not health.snapshot(70.5)['current_ready']
    feed(engine,health,71,72)
    assert health.snapshot(71)['current_ready'] and not health.snapshot(71)['continuous_60s']
    for t in range(72,132):feed(engine,health,t,t+1)
    assert health.snapshot(131)['continuous_60s']


@pytest.mark.asyncio
async def test_missing_TJ_during_admitted_window_pauses_new_requests():
    engine,health=replay(70);clock=FakeClock();clock.t=70.;stop=asyncio.Event();collector=asyncio.create_task(stop.wait())
    requester=FakeRequester(clock,.3)
    async def lose_source():
        await clock.sleep(.15);feed(engine,health,clock.now(),72,missing=True)
        return clock.now()
    lost=asyncio.create_task(lose_source())
    try:
        result=await run_schedule(clock,health,requester,stop,collector,lambda *args,**kw:None,phases=[('R1-existing-window','work',1.)],hard_limit_s=10)
        missing_at=await lost
    finally:stop.set();await collector
    assert result['status']=='completed' and requester.starts
    assert not any(r['t']>=missing_at for r in requester.starts)
