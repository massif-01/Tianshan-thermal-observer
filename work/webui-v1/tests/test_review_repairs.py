"""Finite R1-R6 regressions; synthetic data, clocks and transports only."""
import asyncio
import copy
import json
import time
from pathlib import Path
import pytest
from producer import Producer,web_config,native_config
from tto_web.state import State
from tto_web.common import utc
from tto_web.source import Publication,follow


@pytest.mark.parametrize('enabled',[False,True])
def test_optional_memory_null_and_display_failures_cannot_abort_native_commit(tmp_path,enabled):
    from tto.engine import engine_for
    from tto.storage import Journal,source_identity
    from tto_field.runtime import Pipeline
    from tto_field.support import Clock,Evidence
    config=native_config();engine=engine_for(config,record_schema=2)
    journal=Journal(config,root=tmp_path/'native',simulated=True,record_schema=2)
    ev=Evidence(tmp_path);packets=[]
    binding=dict(command_id='SYNTHETIC-REVIEW',collector_source_sha256=source_identity()['sha256'],synthetic_loopback_only=True)
    pipeline=Pipeline(tmp_path,config,binding,'diagnose',Clock(),ev,public_sink=packets.append if enabled else None)
    p=Producer();start=time.monotonic()-13
    def process(kind,payload,t):
        raw=journal.observation(dict(kind=kind,payload=payload,mono_s=start+t,received_at_utc=utc(),connection_epoch=1))
        processed=engine.process(raw);pipeline.on_record(raw,processed,engine);return processed
    try:
        for t in range(13):
            process('fan',p.fan(),t)
            if t%5==0:process('temp',p.temp(),t)
            process('orin',p.packet(t),t)
        payload=p.packet(13);payload['memory']=None
        before=pipeline.callbacks
        result=process('orin',payload,13)
        assert result['quality']['accepted'] and pipeline.callbacks==before+1
        if enabled:
            assert next(m for m in packets[-1]['metrics'] if m['id']=='memory.ram')['value'] is None
            original=pipeline.web_adapter.encode
            def fail(*args):raise RuntimeError('SECRET payload must not escape')
            pipeline.web_adapter.encode=fail
            process('fan',p.fan(),13.1)
            assert pipeline.callbacks==before+2 and pipeline.get()['clock']['observer_input_mono_s']==start+13.1
            assert packets[-1]['schema']=='TTO-WEB-DISPLAY-GAP-v1'
            state=State(web_config());state.accept(p.step(0));state.accept(packets[-1])
            assert not state.source_connected and all(m['value'] is None for m in state.snapshot()['metrics'])
            assert pipeline.web_publisher.errors==__import__('collections').deque(['RuntimeError'],maxlen=32)
            assert 'SECRET' not in json.dumps(packets[-1])
            pipeline.web_adapter.encode=original
            process('fan',p.fan(),13.2)
            assert packets[-1]['publication_gap']
        # Original evidence failure remains fatal; the display boundary cannot swallow it.
        def fail_native(*args):raise OSError('native evidence failure')
        ev.append=fail_native
        with pytest.raises(ValueError,match='field_projection_failed:OSError'):process('fan',p.fan(),13.3)
    finally:ev.close();journal.close({})


@pytest.mark.parametrize('outer',[4000,2500])
def test_gpu_native_age_and_same_source_metric_ages(outer):
    p=Producer(time.monotonic()-10);s=State(web_config())
    p.row('fan',0,p.fan());p.row('temp',0,p.temp())
    payload=p.packet(1,gpu_age=2000);payload['telemetry_meta']['sample_age_ms']=outer
    packet=p.row('orin',1,payload,connection_epoch=1);s.accept(packet,now=p.start+1.01)
    metrics={m['id']:m for m in s.snapshot()['metrics']}
    for id in ['power.gpu','power.cpu_soc_mss','usage.cpu.mean','cpu.cores.0.usage','memory.ram']:
        assert metrics[id]['age_lower_bound_ms']==pytest.approx(outer+10)
    gpu=metrics['usage.gpu']
    assert gpu['age_lower_bound_ms']==pytest.approx(outer+2010)
    if outer==4000:assert gpu['value'] is None and gpu['reason_code']=='gpu_effective_stale'
    else:assert gpu['value']==0 and gpu['remaining_valid_ms']==pytest.approx(490)
    s.refresh(p.start+1.6)
    assert next(m for m in s.snapshot()['metrics'] if m['id']=='usage.gpu')['value'] is None


@pytest.mark.asyncio
async def test_legacy_publication_does_not_invent_unrecorded_predictions(publication_dir):
    p=Producer(time.monotonic()-20);s=State(web_config())
    config=web_config();descriptor=publication_dir/'active.json';config['source']['active_descriptor']=str(descriptor)
    stop=asyncio.Event()
    async with Publication(descriptor) as pub:
        task=asyncio.create_task(follow(config,s,stop))
        try:
            pub.put(p.step(20))
            for _ in range(100):
                if s.packet:break
                await asyncio.sleep(.01)
            assert s.packet and s.predictions=={}
            assert s.snapshot()['forecast']['status']=='not_connected'
        finally:task.cancel();await asyncio.gather(task,return_exceptions=True)


def test_events_are_scoped_to_current_run_and_epoch():
    p=Producer(time.monotonic()-40);s=State(web_config());packet=p.step(0);s.accept(packet,now=p.start+.01)
    s.event('runner','old task',20000);old=s.events[-1]
    assert old['run_id']==packet['run_id'] and old['source_epoch']==packet['source_epoch']
    s.event('web','global event')
    for run,epoch in [('new-run',packet['source_epoch']),('new-run',packet['source_epoch']+1)]:
        replacement=copy.deepcopy(packet);replacement.update(run_id=run,source_epoch=epoch,input_mono_s=p.start+30)
        s.accept(replacement,now=p.start+30.01)
        assert all(e['id']!=old['id'] for e in s.current_events())
        assert all(e['run_id'] is None or (e['run_id'],e['source_epoch'])==(run,epoch) for e in s.current_events())
        s.event('runner','old task',20000);old=s.events[-1];assert old['count']==1
    assert next(e for e in s.events if e['source']=='web')['elapsed_ms'] is None


@pytest.mark.asyncio
async def test_observe_terminal_reasons_and_stop_during_backoff_do_not_revive(tmp_path,monkeypatch):
    import tto_web.source as source
    from tto_web.common import atomic_json
    path=tmp_path/'native.json';atomic_json(path,native_config())
    config=web_config();config['source'].update(mode='observe',observation_config=str(path))
    for reason in ('authorization_failed','external_stop','ValueError:observation_processing_failed','reconnect_attempt_budget'):
        calls=[]
        async def collect(*args,**kwargs):
            calls.append(kwargs['stop_event']);return None,dict(stop_reason=reason)
        monkeypatch.setattr(source,'collect',collect)
        state=State(config);stop=asyncio.Event();task=asyncio.create_task(source.observe(config,state,stop))
        if reason=='reconnect_attempt_budget':
            while '退避' not in state.source_status:await asyncio.sleep(.001)
            assert not calls[0] is stop and not stop.is_set()
            stop.set()
        await asyncio.wait_for(task,1)
        await asyncio.sleep(.02)
        assert len(calls)==1 and not state.source_connected
        assert '正在观察' not in state.source_status
