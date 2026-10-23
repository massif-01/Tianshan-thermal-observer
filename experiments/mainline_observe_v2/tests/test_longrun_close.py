"""O1/O2 actual consumer retention and installed CLI against the real session store."""
import copy,gzip,json,subprocess,sys
from pathlib import Path
from tto_field.observe_storage import SessionStore
from tto_field.projection import SavedStream


def test_quality_history_policy_preserves_frames():
    # Small direct policy check; the independent 86400-row probe uses the real native engine.
    from tto.engine import engine_for
    from tto.config import load_config
    from tto_field.g2_model.g2_runtime import Predictor
    config=load_config(environ={})
    manifest={'config':config,'observer_run_id':'synthetic-policy-unit','config_sha256':'synthetic','source_identity':{'sha256':'synthetic'}}
    spec=Predictor().spec
    old=SavedStream(manifest,spec,engine_for(config,record_schema=2))
    live=SavedStream(manifest,spec,engine_for(config,record_schema=2),retain_quality_history=False)
    processed={'quality':{'accepted':False,'reason':'synthetic_test'}}
    for n in range(10):
        raw=dict(mono_s=float(n),kind='boundary',reason='test',ref=str(n),received_at_utc='2026-10-21T00:00:00Z')
        assert old.feed(raw,copy.deepcopy(processed))==live.feed(raw,copy.deepcopy(processed))
    assert old.retain_quality_history and len(old.quality)==old.quality_seen==10
    assert live.quality_seen==10 and live.quality==[] and not live.retain_quality_history


def test_installed_live_history_equals_closed_across_fragments(tmp_path):
    store=SessionStore(tmp_path/'session',budget=1000000,segment_bytes=100000,chunk_bytes=160,min_free=0)
    for name in ('states','predictions','observations'):
        for n in range(20):store.append(store.root,name,dict(n=n,example='synthetic-only'))
    # The former prefix glob must not pull a different logical stream into the query.
    (store.root/'states-extra.jsonl').write_text('{"n":999}\n')
    files_before={p.name:p.read_bytes() for p in store.root.glob('*.jsonl*')}
    def query(name,last):
        p=subprocess.run([str(Path(sys.executable).with_name('tto-observe')),'history','--session',str(store.root),'--stream',name,'--last',str(last)],capture_output=True,text=True,check=True,timeout=10)
        return [x['n'] for x in json.loads(p.stdout)]
    live={(name,last):query(name,last) for name in ('states','predictions','observations') for last in (3,7,25)}
    assert all(rows==list(range(max(0,20-last),20)) for (name,last),rows in live.items())
    assert files_before=={p.name:p.read_bytes() for p in store.root.glob('*.jsonl*')}
    store.close()
    assert live=={(name,last):query(name,last) for name,last in live}
    # Number ordering remains correct beyond four digits, with no full-index dependency.
    numeric=tmp_path/'numeric';numeric.mkdir()
    for filename,n in [('states.jsonl',1),('states-9999.jsonl',9999),('states-10000.jsonl',10000)]:
        (numeric/filename).write_text(json.dumps({'n':n})+'\n')
    p=subprocess.run([str(Path(sys.executable).with_name('tto-observe')),'history','--session',str(numeric),'--stream','states','--last','2'],capture_output=True,text=True,check=True,timeout=10)
    assert [x['n'] for x in json.loads(p.stdout)]==[9999,10000]


def test_thirty_day_history_expires_whole_days_across_restart(tmp_path,monkeypatch):
    from datetime import date, timedelta
    from tto_field.observe_storage import expire_history
    today=date(2026,10,24);active=tmp_path/'active';active.mkdir()
    def session(name,day,device='one',host='host'):
        root=tmp_path/name;root.mkdir()
        (root/'history-retention.json').write_text(json.dumps(dict(device_id=device,host=host,day=day.isoformat(),retention_days=30)))
        for name in ('observations.jsonl.gz','predictions.jsonl.gz','scores.jsonl.gz'):
            (root/name).write_bytes(gzip.compress(b'{}\n'))
        return root
    days=[session(f'day-{n}',today-timedelta(days=n)) for n in range(32)]
    same_day=session('same-day',today-timedelta(days=30))
    other=session('other-device',today-timedelta(days=60),device='other')
    other_host=session('other-host',today-timedelta(days=60),host='another-host')
    archive=tmp_path/'archived-test';archive.mkdir();(archive/'summary.json').write_text('{}')
    # Even a wall-clock jump cannot make the currently open session delete itself.
    (active/'history-retention.json').write_text(json.dumps(dict(device_id='one',host='host',day='2000-01-01')))
    assert expire_history(active,'one','host',today)==[str(today-timedelta(days=n)) for n in (31,30)]
    assert all(p.exists() for p in days[:30]) and all(not p.exists() for p in days[30:])
    assert not same_day.exists() and other.exists() and other_host.exists() and archive.exists() and active.exists()
    # No in-memory cursor: the next invocation after restart expires the next day.
    assert expire_history(active,'one','host',today+timedelta(days=1))==[str(today-timedelta(days=29))]
    assert not days[29].exists() and all(p.exists() for p in days[:29])

    # Actual startup must reclaim expired data under the native lock before
    # metadata/free-space checks can reject the new session.
    import asyncio,socket,time,uuid
    from fake_source import FakeSource
    from tto.config import load_config
    from tto_field.observe_runtime import run_observe
    import tto_field.observe_storage as storage
    import tto_field.observe_runtime as runtime
    from tto.recordio import read_records
    blocked=session('space-to-reclaim',date(2000,1,1),device='fixture',host=socket.gethostname())
    finished=[]
    def reclaim(*args):
        time.sleep(1.1)  # Longer than the monitor tick: no writes may race initialization.
        expired=expire_history(*args);finished.append(time.monotonic());return expired
    monkeypatch.setattr(runtime,'expire_history',reclaim)
    disk_usage=storage.shutil.disk_usage
    monkeypatch.setattr(storage.shutil,'disk_usage',lambda path:type('Disk',(),{'free':0})() if blocked.exists() else disk_usage(path))
    async def start():
        async with FakeSource() as source:
            config=load_config(environ={});config['orin'].update(base_url=source.url,source_sample_interval_ms=1000,source_interval_evidence='owned fixture');config['tianshan']['base_url']=source.url
            registration=dict(device_id='fixture',thermal_config_id='fixture',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
            result=await run_observe(config,registration,tmp_path/'restarted',2,local_loopback=True)
            assert result['reason']=='duration' and result['native_callbacks']>0 and not blocked.exists()
            assert all(row['interval_origin_mono_s']>=finished[0] for row in read_records(tmp_path/'restarted/resources.jsonl.gz'))
    asyncio.run(start())
