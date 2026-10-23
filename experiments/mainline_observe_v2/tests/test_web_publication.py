"""Local sockets + recorded replay; imports Web source, never installs/serves it."""
import asyncio
import copy
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest
from tto_field.web_encoding import WebEncoder, SPEC
from tto_field.web_publication import Publication, CAPACITY

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'work/webui-v1/src'))
from tto_web.state import State
from tto_web.source import follow
import tto_web.common as web_common

BOOT = 'test:observe-publication-local'

@pytest.fixture(autouse=True)
def web_clock(monkeypatch):
    monkeypatch.setattr(web_common, 'boot_id', lambda: BOOT)
    monkeypatch.setattr('tto_web.state.boot_id', lambda: BOOT)
    monkeypatch.setattr('tto_web.source.boot_id', lambda: BOOT)
    monkeypatch.setattr('tto_web.adapter.boot_id', lambda: BOOT)

@pytest.fixture
def pubdir():
    with tempfile.TemporaryDirectory(dir='/tmp', prefix='tp-') as name:
        yield Path(name)


def wait_for(check, timeout=3):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if check():return
        time.sleep(.005)
    raise AssertionError('condition not reached')


def bundle(t=None, run='run-A', kind='boundary'):
    t=time.monotonic() if t is None else t
    raw=dict(mono_s=t,kind=kind,ref='raw:'+str(t),received_at_utc='2026-10-23T00:00:00Z',payload={})
    comm=dict(measurement=dict(TJ_and_rails=dict(raw_valid=False)))
    frame=dict(t=t,identity=dict(run_id=run,config_sha256='config',source_epoch=0),source_reset=False,
               new_TJ=False,safety={},measurement={},_communication=comm)
    state=dict(observer=dict(phase='unavailable',available=False,reasons=['model_error']),generated_clock_domain='process-clock')
    return raw,dict(quality={}),frame,state,t+2.5


def receive(path, count=1):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3);sock.connect(str(path/'publication.sock'))
        with sock.makefile('rb') as stream:
            return [json.loads(stream.readline()) for _ in range(count)]


def test_encoder_unavailable_is_renderable_and_deadline_never_renewed():
    raw,processed,frame,state,deadline=bundle(t=10)
    encoder=WebEncoder('run-A','config',BOOT,test_replay=True)
    packet=encoder.encode(raw,processed,frame,frame['_communication'],state,11)
    assert packet['model']['Tf_C'] is packet['model']['Ts_C'] is packet['model']['E_C'] is None
    assert packet['consumable_until_mono_s']==11
    assert 'Tf_C' not in state['observer']
    web=State({'source':{'mode':'follow'},'advisory':{}})
    packet['metrics']=[dict(id='temperature.tj',label='TJ',kind='observed',unit='°C',reason_code=None,
        source_id='synthetic',source_time_utc=None,time_quality='same_clock',value=40.,status='valid',sample_id='tj',
        as_of_elapsed_ms=0.,_at=10.,_expiry=12.,source_ref='r',received_at_utc='x',
        remaining_valid_ms=2000.,age_lower_bound_ms=0.,last_observation=None)]
    web.accept(packet,now=10.1);web.refresh(10.1)
    assert web._snapshot['model']['Tf_C'] is None
    web.refresh(20)
    assert web._snapshot['model']['remaining_valid_ms']==0
    # Model-failure ledger output must remain valid at the display boundary.
    from tto_field.observe_predictions import Ledger
    from tto_field.prediction_view import PredictionView
    from tto_field.web_encoding import SPEC_ID
    from test_observe_contract import frame as ledger_frame, outputs
    import jsonschema
    rows=[];view=PredictionView(10.)
    def committed(stream,row):
        rows.append(row);view.committed(stream,row)
    ledger=Ledger(committed,dict(run_id='run-A',clock_domain='test',model_id='frozen',model_sha256=SPEC['model_sha256'],spec_sha256=SPEC_ID))
    f=ledger_frame(10.);f['identity']['run_id']='run-A'
    ledger.consume(f,10.01,[],state_status='unavailable',wall_clock=dict(utc='2026-10-23T00:00:00Z',mono_s=10.01))
    page=dict(view.page(now=10.02),boot_id=BOOT,publisher_id='unavailable-test')
    web.begin_publication('unavailable-test');web.accept_predictions(page,now=10.02)
    for name in ('src/tto_web','requirements'):
        schema=json.loads((ROOT/'work/webui-v1'/name/'contracts/dashboard.schema.json').read_text())
        if name=='src/tto_web':jsonschema.validate(web.snapshot(),schema)
        for row in web.snapshot()['predictions']:
            jsonschema.validate(row,{'$defs':schema['$defs'],'$ref':'#/$defs/forecast'})
    assert len(view.rows)==3 and all(r['conditional_assumptions'] is None for r in view.rows.values())
    assert all(r['conditional_assumptions']==[] for r in rows)  # Formal ledger stays unchanged.
    f=ledger_frame(15.);f['identity']['run_id']='run-A'
    ledger.consume(f,15.01,outputs(),state_status='tracking',wall_clock=dict(utc='2026-10-23T00:00:05Z',mono_s=15.01))
    assert all(r['conditional_assumptions']=={'PWM':'conditional'} for r in list(view.rows.values())[-3:])


def orin_bundle(t, *, sample_time=None, epoch=0, gpu_status=None):
    from tto.profiles import uniform_gpu
    raw,processed,frame,state,deadline=bundle(t=t,kind='orin')
    payload=json.loads((Path(__file__).parent/'fixtures/orin.json').read_text())
    if sample_time:payload['gpu']['sampled_at_utc']=sample_time
    if gpu_status in ('error','unavailable'):
        payload['gpu'].update(status=gpu_status,utilization_pct=None,sampled_at_utc=None,age_at_telemetry_receive_ms=None)
        if gpu_status=='unavailable':payload['gpu']['source']='unavailable'
    raw['payload']=payload
    processed['quality']=dict(accepted=True,age_lower_bound_ms=0,
        gpu=uniform_gpu(payload,payload['platform']['family'],t))
    frame.update(new_TJ=True,measurement=dict(tj=dict(raw_valid=True)))
    frame['identity']['source_epoch']=epoch
    frame['_communication']['measurement']['TJ_and_rails']['raw_valid']=True
    return raw,processed,frame,state,deadline


@pytest.mark.parametrize('withdrawn',[False,True])
def test_queue_overrun_is_bounded_and_recovery_clears_cache(pubdir,monkeypatch,withdrawn):
    # Seed real display state before blocking encoding and dropping a fan withdrawal.
    entered=threading.Event();release=threading.Event()
    original=WebEncoder.encode
    def gated(self,raw,*args):
        if raw['ref']=='blocked':
            entered.set();assert release.wait(3)
        return original(self,raw,*args)
    monkeypatch.setattr(WebEncoder,'encode',gated)
    p=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert p.ready.wait(3)
    sock=socket.socket(socket.AF_UNIX);sock.settimeout(3);sock.connect(str(pubdir/'publication.sock'))
    stream=sock.makefile('rb');web=State({'source':{'mode':'follow'},'advisory':{}})
    def read():
        row=json.loads(stream.readline())
        web.accept(row,now=row.get('input_mono_s',200))
        return row
    def metrics(row):return {m['id']:m for m in row['metrics']}
    try:
        raw,processed,frame,state,deadline=bundle(t=100,kind='fan')
        raw['payload']={'data':{'fans':[{'id':0,'target_duty':30}]}}
        frame['measurement']['last_successful_pwm']=dict(raw_valid=True,source_ref=raw['ref'],value_percent=30)
        p.submit(raw,processed,frame,state,deadline)
        assert metrics(read())['fan.pwm.actual']['value']==30
        p.submit(*orin_bundle(100.1));first=metrics(read())['usage.gpu']
        assert first['status']=='valid'
        blocked=list(bundle(t=101));blocked[0]['ref']='blocked'
        blocked[2]['_communication']['measurement']['TJ_and_rails']['raw_valid']=not withdrawn
        p.submit(*blocked);assert entered.wait(3)
        # This invalidating event must be lost, so recovery cannot rely on seeing it.
        p.submit(*bundle(t=101.1,kind='fan'))
        base=102 if withdrawn else 104
        for n in range(30):p.submit(*orin_bundle(base+n*.001))
        assert p.snapshot()['pending']<=CAPACITY and p.snapshot()['dropped']>=24
        release.set();rows=[]
        while True:
            row=read();rows.append(row)
            if row.get('input_mono_s')==base+.029:break
        assert any(r['schema']=='TTO-WEB-DISPLAY-GAP-v1' for r in rows)
        recovered=[r for r in rows if r.get('publication_gap')]
        assert recovered and 'fan.pwm.actual' not in metrics(recovered[0])
        last=metrics(rows[-1])['usage.gpu']
        assert last['sample_id']==first['sample_id'] and last['_expiry']==first['_expiry']
        visible=next(m for m in web.snapshot()['metrics'] if m['id']=='usage.gpu')
        assert visible['value'] is None and visible['status']==('invalid' if withdrawn else 'stale')
        # A model-only reset cannot renew that sample either.
        reset=list(orin_bundle(base+.1));reset[2]['source_reset']=True
        p.submit(*reset);assert metrics(read())['usage.gpu']['_expiry']==first['_expiry']
        # New sample and new source epoch are allowed to recover; no permanent latch.
        p.submit(*orin_bundle(base+.2,sample_time='2026-10-23T00:00:01Z'))
        assert metrics(read())['usage.gpu']['status']=='valid'
        p.submit(*orin_bundle(base+.3,epoch=1));changed=read()
        assert changed['source_epoch']==1 and metrics(changed)['usage.gpu']['status']=='valid'
        assert p.snapshot()['max_pending']==CAPACITY
        if not withdrawn:
            # No-sample/error or untrusted identity cannot replace the last real A.
            for n,bad in enumerate(('error','unavailable','malformed')):
                t=base+1+n;stamp=f'2026-10-23T00:00:{10+n:02d}Z'
                p.submit(*orin_bundle(t,sample_time=stamp,epoch=1));trusted=metrics(read())['usage.gpu']
                assert trusted['status']=='valid'
                rejected=orin_bundle(t+.1,sample_time='invalid-time' if bad=='malformed' else stamp,epoch=1,gpu_status=bad)
                assert rejected[1]['quality']['gpu']['contract_valid']==(bad!='malformed')
                p.submit(*rejected);assert metrics(read())['usage.gpu']['status']=='invalid'
                p.invalidate();p.submit(*orin_bundle(t+.2,sample_time=stamp,epoch=1))
                assert read()['schema']=='TTO-WEB-DISPLAY-GAP-v1'
                restored=metrics(read())['usage.gpu']
                assert restored['sample_id']==trusted['sample_id'] and restored['_expiry']==trusted['_expiry']
                assert restored['status']=='invalid'
    finally:
        release.set();stream.close();sock.close();assert p.close()['worker_stopped']
    assert json.loads((pubdir/'active.json').read_text())['ended'] is True


def test_encode_failure_sends_gap_then_recovers_without_cached_values(pubdir,monkeypatch):
    p=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert p.ready.wait(3)
    original=WebEncoder.encode
    called=[0]
    def fail_once(self,*args):
        called[0]+=1
        if called[0]==1:
            self.metrics['fan.pwm.actual']={'value':99,'status':'valid'}
            self.source_health['fan']={'old':True}
            raise ValueError('INJECTED SECRET MUST NOT BE PUBLISHED')
        return original(self,*args)
    monkeypatch.setattr(WebEncoder,'encode',fail_once)
    try:
        p.submit(*bundle());wait_for(lambda:p.snapshot()['errors']==1)
        gap=receive(pubdir)[0]
        assert gap['schema']=='TTO-WEB-DISPLAY-GAP-v1' and 'SECRET' not in json.dumps(gap)
        p.submit(*bundle());wait_for(lambda:p.snapshot()['published']==1)
        packet=receive(pubdir)[0]
        assert packet['publication_gap'] and packet['metrics']==[] and 'fan' not in packet['source_health']
    finally:p.close()


def test_start_failure_and_conflicting_owner_leave_original_alive(pubdir):
    first=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert first.ready.wait(3)
    try:
        second=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert second.ready.wait(3)
        assert second.close()['errors']==1
        assert not json.loads((pubdir/'active.json').read_text())['ended']
        first.submit(*bundle());wait_for(lambda:first.snapshot()['published']==1)
        assert receive(pubdir)[0]['schema']=='TTO-WEB-PUBLICATION-v1'
    finally:first.close()


def test_slow_socket_disconnects_but_producer_keeps_publishing(pubdir,monkeypatch):
    # Real non-reading Unix peer, large valid packets, no fake socket/drain.
    original=WebEncoder.encode
    def large(self,*args):
        row=original(self,*args);row['padding']='x'*240000;return row
    monkeypatch.setattr(WebEncoder,'encode',large)
    p=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert p.ready.wait(3)
    sock=socket.socket(socket.AF_UNIX);sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024);sock.connect(str(pubdir/'publication.sock'))
    try:
        wait_for(lambda:p.snapshot()['connected']==1)
        for _ in range(50):
            before=p.snapshot()['published'];p.submit(*bundle())
            wait_for(lambda:p.snapshot()['published']>before)
            if p.snapshot()['slow_clients']:break
        wait_for(lambda:p.snapshot()['slow_clients']>0)
        before=p.snapshot()['published'];p.submit(*bundle());wait_for(lambda:p.snapshot()['published']>before)
        assert p.snapshot()['max_pending']<=CAPACITY and p.snapshot()['errors']==0
    finally:
        result=p.close();sock.close();assert result['worker_stopped']


def test_actual_follow_disconnect_subscriber_restart_producer_restart_and_expiry(pubdir,monkeypatch):
    async def go():
        config={'source':{'mode':'follow','active_descriptor':str(pubdir/'active.json')},'advisory':{}}
        p=Publication(pubdir/'active.json',BOOT,test_replay=True).start()
        await asyncio.to_thread(p.ready.wait,3)
        state=State(config);stop=asyncio.Event();task=asyncio.create_task(follow(config,state,stop))
        async def until(check):
            for _ in range(600):
                if check():return
                await asyncio.sleep(.01)
            raise AssertionError('follow did not recover')
        try:
            p.submit(*bundle());await until(lambda:state.source_connected)
            old=state.packet['run_id']
            # Subscriber stops, publisher remains independent.
            stop.set();task.cancel();await asyncio.gather(task,return_exceptions=True)
            before=p.snapshot()['published'];p.submit(*bundle());await until(lambda:p.snapshot()['published']>before)
            # Fresh subscriber (Web restart), no HTTP service.
            state=State(config);stop=asyncio.Event();task=asyncio.create_task(follow(config,state,stop))
            await until(lambda:state.source_connected)
            # Producer restarts; run identity changes, source_epoch truthfully starts at zero.
            await asyncio.to_thread(p.close)
            await until(lambda:not state.source_connected)
            p=Publication(pubdir/'active.json',BOOT,test_replay=True).start();await asyncio.to_thread(p.ready.wait,3)
            p.submit(*bundle(run='run-B'));await until(lambda:state.source_connected and state.packet['run_id']!=old)
            assert state.packet['source_epoch']==0
            state.refresh(state.packet['input_mono_s']+10)
            assert state._snapshot['model']['remaining_valid_ms']==0
            # Programming failures in a receiver must be observed by the owner,
            # which retires siblings and withdraws current values before exiting.
            def broken_accept(*args,**kwargs):raise RuntimeError('owned receiver failure')
            monkeypatch.setattr(state,'accept',broken_accept)
            p.submit(*bundle(run='run-B'))
            await until(task.done)
            assert isinstance(task.exception(),RuntimeError) and not state.source_connected
            assert state.forecast is None
        finally:
            stop.set();task.cancel();await asyncio.gather(task,return_exceptions=True);await asyncio.to_thread(p.close)
    asyncio.run(go())


@pytest.mark.parametrize('fault',['none','encode','submit','close','thread_start','view','boot'])
def test_collector_socket_values_and_publication_faults_do_not_stop_recording(tmp_path,pubdir,monkeypatch,fault):
    from fake_source import FakeSource
    from tto.config import load_config
    import tto_field.observe_runtime as runtime
    from tto_field.web_encoding import short
    boot=BOOT if fault=='boot' else 'owned-local-fixture-boot'
    monkeypatch.setattr(runtime,'boot_identity',lambda:boot)
    if fault=='encode':
        def fail(*args):raise ValueError('owned encoding failure')
        monkeypatch.setattr(WebEncoder,'encode',fail)
    if fault=='submit':
        def fail(*args):raise OSError('owned enqueue failure')
        monkeypatch.setattr(Publication,'submit',fail)
    if fault=='view':
        from tto_field.prediction_view import PredictionView
        def fail(*args):raise ValueError('owned read projection failure')
        monkeypatch.setattr(PredictionView,'apply',fail)
    if fault=='close':
        close=Publication.close
        def fail(self,**kwargs):close(self,**kwargs);raise OSError('owned close failure')
        monkeypatch.setattr(Publication,'close',fail)
    if fault=='thread_start':
        start=threading.Thread.start
        def fail(self):
            if self.name=='web-publication':raise RuntimeError('owned thread start failure')
            return start(self)
        monkeypatch.setattr(threading.Thread,'start',fail)
    if fault=='none':
        # Unused processing outputs must never be copied for publication.
        class Unused:
            def __deepcopy__(self,memo):raise AssertionError('unused output copied')
        original=runtime.Consumer.on_record;submit=Publication.submit;qualities={};checks=[]
        def record(self,raw,processed,engine):
            selected=dict(processed,quality=copy.deepcopy(processed['quality']),unused=Unused())
            qualities[raw['ref']]=selected['quality']
            original(self,raw,selected,engine)
        def selected_submit(self,raw,processed,*args):
            checks.append(set(processed)=={'quality'} and (processed['quality'] is None or processed['quality'] is not qualities[raw['ref']]))
            return submit(self,raw,processed,*args)
        monkeypatch.setattr(runtime.Consumer,'on_record',record)
        monkeypatch.setattr(Publication,'submit',selected_submit)
    states=[];publish=runtime.Consumer.publish
    def capture_state(self,*args):
        states.append(copy.deepcopy(args[1:]));return publish(self,*args)
    monkeypatch.setattr(runtime.Consumer,'publish',capture_state)
    async def go():
        import uuid
        packets=[]
        async with FakeSource() as source:
            config=load_config(environ={})
            config['orin'].update(base_url=source.url,source_sample_interval_ms=1000,source_interval_evidence='owned local fixture')
            config['tianshan']['base_url']=source.url
            reg=dict(device_id='synthetic',thermal_config_id='synthetic',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
            task=asyncio.create_task(runtime.run_observe(config,reg,tmp_path/'session',12 if fault=='none' else 4,local_loopback=True,storage_options={'min_free':0},publication_descriptor=pubdir/'active.json'))
            async def collect_public():
                while not (pubdir/'publication.sock').exists() and not task.done():await asyncio.sleep(.01)
                if task.done():return
                reader,writer=await asyncio.open_unix_connection(str(pubdir/'publication.sock'))
                try:
                    while line:=await reader.readline():packets.append(json.loads(line))
                finally:writer.close();await writer.wait_closed()
            reader_task=asyncio.create_task(collect_public())
            result=await task;await asyncio.wait_for(reader_task,3)
            assert result['reason']=='duration' and result['native_summary']['orin_event_count']>=2
            assert result['stateful_observer_count']==1 and result['consumer_stopped']
            assert source.posts==source.model_gets==0 and result['native_summary']['dropped']==0
        assert not list((tmp_path/'session').glob('states*'))
        assert states
        if fault=='none':
            by_time={f['t']:(f,s,deadline) for f,s,deadline in states}
            data=[x for x in packets if x['schema']=='TTO-WEB-PUBLICATION-v1']
            assert len(data)>3, (result,packets[:1])
            for packet in data:
                native,model,deadline=by_time[packet['input_mono_s']]
                assert packet['boot_id']==boot and packet['run_id']==short(native['identity']['run_id'])
                assert packet['source_epoch']==native['identity']['source_epoch']
                assert packet['process_clock_domain']==result['clock_end']['domain']
                assert packet['model_id']==native['identity']['model_sha256']
                assert packet['spec_id']==native['identity']['spec_sha256']
                assert packet['model']==model['observer']
                assert packet['consumable_until_mono_s']==deadline
                tj=next((m for m in packet['metrics'] if m['id']=='temperature.tj' and m['status']=='valid'),None)
                if tj:assert tj['value']==native['measurement']['tj']['value_C']
            assert result['publication']['errors']==result['publication_callback_errors']==0
            assert checks and all(checks)
            from tto_web.state import State
            from tto_web.source import follow
            import tto_web.state as web_state
            import tto_web.source as web_source
            monkeypatch.setattr(web_state,'boot_id',lambda:boot);monkeypatch.setattr(web_source,'boot_id',lambda:boot)
            state=State({'source':{'active_descriptor':str(pubdir/'active.json')},'advisory':{}})
            stop=asyncio.Event();subscriber=asyncio.create_task(follow(state.config,state,stop))
            try:
                for _ in range(100):
                    if state.prediction_ended and not state.prediction_syncing:break
                    await asyncio.sleep(.01)
                formal=[r for r in state.predictions.values() if r['phase_at_origin'] in ('tracking','degraded')]
                assert formal, result
                scope=state.snapshot()['prediction_history_identity']
                assert scope['source_epoch']<state.snapshot()['source_epoch']
                assert {r['prediction_id'] for h in (15,45,90) for r in state.prediction_view(h)['records']}=={r['prediction_id'] for r in formal}
                assert state.snapshot()['publication_status']=='ended' and not state.snapshot()['forecast']['latest_prediction_ids']
            finally:stop.set();subscriber.cancel();await asyncio.gather(subscriber,return_exceptions=True)

        elif fault=='view':
            assert result['publication']['prediction_view_failure']=='ValueError'
            assert result['model_errors']==0 and not result['error']
            assert (tmp_path/'session/predictions.jsonl.gz').stat().st_size and (tmp_path/'session/scores.jsonl.gz').stat().st_size
            meta=json.loads((pubdir/'active.json').read_text())
            assert meta['publication_failed'] and not meta['ended'] and meta['prediction_final'] is None
        elif fault=='boot':
            assert result['publication']['errors']==1 and result['publication']['worker_stopped']
            assert not packets and not (pubdir/'publication.sock').exists()
        elif fault=='submit':assert result['publication_callback_errors']>0
        elif fault=='thread_start':
            assert result['publication'] is None and result['publication_callback_errors']==0
            assert result['publication_lifecycle_error']==dict(phase='initialization',error_class='RuntimeError')
        elif fault=='close':assert result['publication_lifecycle_error']==dict(phase='close',error_class='OSError')
        else:assert result['publication']['errors']>0
    asyncio.run(go())


def test_shutdown_descriptor_error_is_isolated(pubdir,monkeypatch):
    import tto_field.web_publication as module
    p=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert p.ready.wait(3)
    original=module.atomic_json
    def fail(path,row):
        if row.get('ended'):raise OSError('owned descriptor failure')
        original(path,row)
    monkeypatch.setattr(module,'atomic_json',fail)
    result=p.close()
    assert result['worker_stopped'] and result['errors']==1 and not (pubdir/'publication.sock').exists()


@pytest.mark.parametrize('fault',['serialization','oversized'])
def test_invalid_public_packet_is_gap_and_recovers(pubdir,monkeypatch,fault):
    original=WebEncoder.encode
    count=[0]
    def broken(self,*args):
        row=original(self,*args);count[0]+=1
        if count[0]==1:row['bad']=float('nan') if fault=='serialization' else 'x'*600000
        return row
    monkeypatch.setattr(WebEncoder,'encode',broken)
    p=Publication(pubdir/'active.json',BOOT,test_replay=True).start();assert p.ready.wait(3)
    try:
        p.submit(*bundle());wait_for(lambda:p.snapshot()['errors']==1)
        assert receive(pubdir)[0]['schema']=='TTO-WEB-DISPLAY-GAP-v1'
        p.submit(*bundle());wait_for(lambda:p.snapshot()['published']==1)
        assert receive(pubdir)[0]['publication_gap']
    finally:assert p.close()['worker_stopped']
