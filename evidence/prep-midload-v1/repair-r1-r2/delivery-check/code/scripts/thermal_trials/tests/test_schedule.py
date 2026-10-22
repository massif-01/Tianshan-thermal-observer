import asyncio
import copy
import heapq
import json
import sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
import pytest
from trial import run_schedule,PHASES
from run_midload import main
from health import TrialHealth
from tto.config import load_config
from tto.engine import engine_for
from tto.demo import fan_packet,temp_packet
sys.path.insert(0,str(Path(__file__).parents[3]/'tests'))
from test_platform_curve import new_packet


class FakeClock:
    def __init__(self):self.t=0.;self.waiters=[];self.counter=0;self.scheduled=False
    def now(self):return self.t
    def utc(self):return (datetime(2026,10,13,tzinfo=timezone.utc)+timedelta(seconds=self.t)).isoformat()
    async def sleep(self,seconds):
        future=asyncio.get_running_loop().create_future();self.counter+=1
        heapq.heappush(self.waiters,(self.t+seconds,self.counter,future))
        if not self.scheduled:self.scheduled=True;asyncio.get_running_loop().call_soon(self.advance)
        await future
    def advance(self):
        self.scheduled=False
        while self.waiters and self.waiters[0][2].done():heapq.heappop(self.waiters)
        if not self.waiters:return
        self.t=max(self.t,self.waiters[0][0])
        while self.waiters and self.waiters[0][0]<=self.t:
            _,_,future=heapq.heappop(self.waiters)
            if not future.done():future.set_result(None)
        if self.waiters and not self.scheduled:
            self.scheduled=True;asyncio.get_running_loop().call_soon(self.advance)


class FakeHealth:
    def __init__(self,ready=True,gap=None,abnormal=None):self.ready=ready;self.gap=gap;self.abnormal_at=abnormal
    def observe(self,*args):pass
    def snapshot(self,t):
        current=self.ready and not (self.gap and self.gap[0]<=t<self.gap[1])
        return dict(current_ready=current,continuous_60s=self.ready,abnormal=self.abnormal_at is not None and t>=self.abnormal_at,gaps_180s=[],latest=None)


class FakeRequester:
    def __init__(self,clock,duration=2.,status='completed'):self.clock=clock;self.duration=duration;self.status=status;self.starts=[];self.ends=[];self.cancelled=0
    async def request(self,ident,timeout_s):
        self.starts.append(dict(id=ident,t=self.clock.now(),timeout=timeout_s))
        try:await self.clock.sleep(self.duration)
        except asyncio.CancelledError:self.cancelled+=1;raise
        self.ends.append(self.clock.now())
        return dict(status=self.status,client_end_mono_s=self.clock.now())


async def scenario(health=None,duration=2.,phases=PHASES,hard=2700,max_requests=256,operator_stop=None):
    clock=FakeClock();stop=asyncio.Event();collector=asyncio.create_task(stop.wait());events=[];req=FakeRequester(clock,duration)
    async def interrupt():await clock.sleep(operator_stop);stop.set()
    timer=asyncio.create_task(interrupt()) if operator_stop is not None else None
    try:
        result=await run_schedule(clock,health or FakeHealth(),req,stop,collector,lambda event,**kw:events.append(dict(event=event,t=clock.now(),**kw)),phases=phases,hard_limit_s=hard,max_requests=max_requests)
    finally:
        stop.set();await collector
        if timer:timer.cancel();await asyncio.gather(timer,return_exceptions=True)
    return result,req,events,clock


@pytest.mark.asyncio
async def test_full_fixed_schedule_single_requests_natural_end_and_real_gaps():
    r,q,events,c=await scenario(duration=3.)
    assert r['status']=='completed' and 2480<=r['elapsed_schedule_s']<2495
    starts={e['phase']:e for e in events if e['event']=='phase_start'};ends={e['phase']:e for e in events if e['event']=='phase_end'}
    assert any(e['event']=='background_check' and 180<=e['t']<181 for e in events)
    for ident in ['M20','M60','M180']:
        window=starts[ident];requests=[x for x in q.starts if x['id'].startswith(ident+'-')]
        assert requests and all(window['actual_start_mono_s']<=x['t']<window['window_deadline_mono_s'] for x in requests)
        assert ends[ident]['actual_end_mono_s']>=max(e for x,e in zip(q.starts,q.ends) if x['id'].startswith(ident+'-'))
    assert len(q.starts)<=256 and q.cancelled==0
    assert starts['cooldown_1']['actual_start_mono_s']>=ends['M20']['actual_end_mono_s']


@pytest.mark.asyncio
async def test_timeout_unknown_stops_following_blocks_without_server_end_claim():
    r,q,events,c=await scenario(duration=31.)
    assert r['stop_reason']=='request_termination_unknown' and q.cancelled==1 and len(q.starts)==1
    assert r['server_request_completion']=='unknown'


@pytest.mark.asyncio
async def test_background_missing_inputs_leaves_records_and_sends_no_requests():
    r,q,_,_=await scenario(health=FakeHealth(ready=False))
    assert r['stop_reason']=='background_inputs_incomplete' and not q.starts


@pytest.mark.asyncio
async def test_current_aux_gap_pauses_only_within_original_window():
    r,q,events,_=await scenario(health=FakeHealth(gap=(605,612)))
    assert r['status']=='completed' and not any(605<=x['t']<612 for x in q.starts)
    assert any(e['event']=='admission_paused' for e in events)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['operator','collector','guard'])
async def test_stop_cleanup_and_no_following_load(kind):
    if kind=='guard':r,q,events,c=await scenario(health=FakeHealth(abnormal=603))
    else:r,q,events,c=await scenario(operator_stop=603)
    assert r['status']=='stopped' and all(x['id'].startswith('M20-') for x in q.starts)
    assert not any(e.get('phase')=='M60' for e in events)


@pytest.mark.asyncio
async def test_hard_deadline_and_request_count_are_finite():
    r,q,events,c=await scenario(phases=[('resident_background','passive',2600),('M20','work',300)],hard=2700)
    assert r['status']=='stopped' and r['elapsed_schedule_s']<=2700
    r,q,events,c=await scenario(max_requests=2)
    assert r['stop_reason']=='request_count_limit' and len(q.starts)==2


def test_default_help_and_preview_do_not_connect_or_read_credentials(tmp_path,monkeypatch,capsys):
    secret=tmp_path/'headers.json';secret.write_text('{"Authorization":"DO_NOT_READ_OR_PRINT"}')
    cfg={'trial_id':'TTO-MIDLOAD-DEV-v1.0','inference':{'base_url':'http://203.0.113.99:58000','model':'RM-01 VLM','messages':[{'role':'user','content':'non-sensitive test'}],'headers_file':str(secret)}}
    p=tmp_path/'plan.json';p.write_text(json.dumps(cfg));original=Path.read_text
    def guarded(self,*args,**kwargs):assert self!=secret;return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',guarded)
    assert main(['--plan','--trial-config',str(p),'--tto-config','/unreachable/private/local.json'])==0
    assert 'DO_NOT_READ_OR_PRINT' not in capsys.readouterr().out
    with pytest.raises(SystemExit) as e:main(['--help'])
    assert e.value.code==0
    assert main(['--dry-run','--trial-config',str(p)])==0
    broken=tmp_path/'broken.json';broken.write_text('{}');assert main(['--trial-config',str(broken)])==2


def test_health_uses_one_original_processed_stream_and_does_not_extend_TTL():
    c=load_config(environ={});c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='owned fixture')
    engine=engine_for(c,record_schema=2);health=TrialHealth()
    for t in range(71):
        for kind,payload in [('fan',fan_packet(19)),('temp',temp_packet()),('orin',new_packet(t+1))]:
            r=dict(kind=kind,payload=payload,mono_s=float(t),ref=f'fixture/{kind}:{t}',connection_epoch=1,observer_run_id='owned-fixture')
            health.observe(r,engine.process(r),engine)
    assert health.snapshot(70)['continuous_60s']
    assert health.snapshot(72.5)['current_ready']  # Existing fan <=2.5s qualification is unchanged.
    assert not health.snapshot(73)['current_ready']
    f=fan_packet(19);f['data']['fans'][0]['guard_active']=True
    r=dict(kind='fan',payload=f,mono_s=74.,ref='fixture/guard',observer_run_id='owned-fixture')
    health.observe(r,engine.process(r),engine);assert health.snapshot(74)['abnormal']


@pytest.mark.parametrize('case',['disabled','invalid_temperature','binding_change'])
def test_explicit_control_change_stays_stopped_after_normal_snapshot(case):
    c=load_config(environ={});engine=engine_for(c,record_schema=2);health=TrialHealth()
    def observe(kind,payload,t):
        r=dict(kind=kind,payload=payload,mono_s=t,ref=f'fixture/{kind}:{t}',observer_run_id='owned-fixture')
        health.observe(r,engine.process(r),engine)
    observe('fan',fan_packet(19),0.);observe('temp',temp_packet(),0.)
    if case=='disabled':
        f=fan_packet(19);f['data']['fans'][0]['enabled']=False;observe('fan',f,1.)
    else:
        d=temp_packet()
        if case=='invalid_temperature':d['data']['valid']=False
        else:d['data']['bound_variable']='changed_temperature_binding'
        observe('temp',d,1.)
    assert health.snapshot(1.)['abnormal']
    observe('fan',fan_packet(19),2.);observe('temp',temp_packet(),2.)
    assert health.snapshot(2.)['abnormal']
