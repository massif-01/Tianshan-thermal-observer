import asyncio,json,socket,time,uuid
from pathlib import Path
from fake_source import FakeSource
from tto.config import load_config
from tto_field.observe_runtime import Consumer,run_observe
from tto_field.g2_model.g2_runtime import Predictor,ThermalObserver

class FaultObserver(ThermalObserver):
    failed=False
    def step(self,frame):
        if frame['new_TJ'] and not self.failed:self.failed=True;raise ArithmeticError('injected owned model failure')
        return super().step(frame)
class BlockOnce(ThermalObserver):
    paused=False
    def step(self,frame):
        if not self.paused:self.paused=True;time.sleep(2)
        return super().step(frame)
class Burst(FakeSource):
    async def tick(self):
        burst=False
        while True:
            if self.connections:
                if not burst:
                    burst=True
                    for _ in range(120):await self.sio.emit('tegrastats_update',self.packet())
                else:await self.sio.emit('tegrastats_update',self.packet())
            await asyncio.sleep(1)

def run_case(tmp_path,monkeypatch,kind):
    def init(self):self.predictor=Predictor();self.observer=kind(self.predictor.spec);self.stateful_observers=1
    monkeypatch.setattr(Consumer,'_model_import',init)
    async def go():
        async with (Burst() if kind is BlockOnce else FakeSource()) as server:
            c=load_config(environ={});c['orin'].update(base_url=server.url,source_sample_interval_ms=1000,source_interval_evidence='own fixture');c['tianshan']['base_url']=server.url
            reg=dict(device_id='synthetic',thermal_config_id='synthetic',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
            s=await run_observe(c,reg,tmp_path/'session',5,local_loopback=True,storage_options=dict(min_free=0))
            assert server.posts==server.model_gets==0
            return s
    return asyncio.run(go())

def test_model_exception_keeps_native_raw_and_later_recovers(tmp_path,monkeypatch):
    s=run_case(tmp_path,monkeypatch,FaultObserver)
    assert s['model_errors']>=1 and s['native_summary']['orin_event_count']>=3 and s['consumer_stopped']
    assert s['native_summary']['stop_reason']=='duration' and s['reason']=='duration'
    states=[json.loads(x) for x in (tmp_path/'session/states.jsonl').read_text().splitlines()]
    assert any(x['model'].get('reasons')==['model_error'] for x in states)
    assert any(x['model']['available'] for x in states)

def test_queue_overrun_and_lag_keep_raw_with_explicit_loss_marker(tmp_path,monkeypatch):
    s=run_case(tmp_path,monkeypatch,BlockOnce)
    assert s['model_dropped_frames']>0 and s['native_summary']['orin_event_count']>=120
    assert s['native_summary']['dropped']==0 and s['consumer_stopped'] and s['reason']=='duration'
    events=[json.loads(x) for x in (tmp_path/'session/events.jsonl').read_text().splitlines()]
    assert any(x['reason']=='model_queue_full_raw_preserved' for x in events)
    assert any(x['reason']=='model_consumer_late_raw_preserved' for x in events)

class WrongDevice(FakeSource):
    def packet(self):
        p=super().packet()
        if self.elapsed()>2:p['gpu']['device_uuid']='SYNTHETIC-OTHER-DEVICE'
        return p

def test_device_identity_change_stops_own_recording(tmp_path):
    async def go():
        async with WrongDevice() as server:
            c=load_config(environ={});c['orin'].update(base_url=server.url,source_sample_interval_ms=1000,source_interval_evidence='owned fixture');c['tianshan']['base_url']=server.url
            reg=dict(device_id='synthetic',thermal_config_id='synthetic',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
            s=await run_observe(c,reg,tmp_path/'session',8,local_loopback=True,storage_options=dict(min_free=0))
            assert s['reason']=='device_gpu_identity_conflict' and s['elapsed_s']<7 and s['consumer_stopped']
    asyncio.run(go())

def test_existing_native_lock_is_a_blocker_not_killed(tmp_path):
    from tto.storage import InstanceLock
    async def go():
        c=load_config(environ={});c['orin'].update(base_url='http://127.0.0.1:9',source_sample_interval_ms=1000,source_interval_evidence='fixture');c['tianshan']['base_url']='http://127.0.0.1:9'
        reg=dict(device_id='fixture',thermal_config_id='fixture',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
        with InstanceLock():
            s=await run_observe(c,reg,tmp_path/'blocked',2,local_loopback=True,storage_options=dict(min_free=0))
            assert s['collector_count']==0 and s['native_run_id'] is None and s['reason']=='observe_software_error'
    asyncio.run(go())

def test_projection_exception_disables_model_not_raw(tmp_path,monkeypatch):
    from tto_field.projection import SavedStream
    def fail(*args):raise ValueError('owned projection injection')
    monkeypatch.setattr(SavedStream,'feed',fail)
    s=run_case(tmp_path,monkeypatch,FaultObserver)
    assert s['projection_disabled'] and s['reason']=='duration' and s['native_summary']['orin_event_count']>=3 and s['valid_TJ_observed']>=3
    index=json.loads((tmp_path/'session/stream-index.json').read_text())
    rows=[json.loads(x) for name in index['streams']['./observations'] for x in (tmp_path/'session'/name).read_text().splitlines()]
    assert any(x['communication']['measurement']['TJ_and_rails']['raw_valid'] for x in rows if x['kind']=='orin')
