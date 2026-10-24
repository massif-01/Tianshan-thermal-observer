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
    def reclaim(*args,**kwargs):
        time.sleep(1.1)  # Longer than the monitor tick: no writes may race initialization.
        expired=expire_history(*args,**kwargs);finished.append(time.monotonic());return expired
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


def test_continuous_days_cross_midnight_prune_and_archive(tmp_path,monkeypatch):
    from datetime import date,timedelta
    from tto_field.observe_storage import DailyStore,expire_history,history_files
    from tto_field.observe_predictions import Ledger
    from tto_field.observe_cli import archive
    from test_observe_contract import frame,outputs
    from tto.util import file_hash
    from tto.recordio import read_records
    day=[date(2026,10,1)];root=tmp_path/'continuous'
    store=DailyStore(root,today=lambda:day[0],min_free=0,chunk_bytes=20000)
    store.metadata(root/'history-retention.json',dict(layout='utc-days',device_id='one',host='host',day=str(day[0])))
    ledger=Ledger(lambda name,row:store.append(root,name,row),dict(run_id='r',clock_domain='d'),daily=True)
    def rows(stream):return [row for p,live in history_files(root,stream) for row in read_records(p,live=live)]
    def consume(t):ledger.consume(frame(t),t+.01,outputs(),state_status='tracking',wall_clock=dict(utc=str(day[0])+'T23:59:30Z',mono_s=t+.01))
    consume(0);day[0]+=timedelta(days=1);consume(35);consume(50);consume(90)
    ledger.advance(90,str(day[0]))
    # A slow seal must release the current writer, not cause model lag at midnight.
    import threading
    started=threading.Event();release=threading.Event();written=threading.Event()
    close=SessionStore.close
    def slow_close(journal):
        started.set();assert release.wait(5);close(journal)
    ready=set(store.days)-{p['origin_day'] for b in ledger.pending for p in b['items']}-{str(day[0])}
    with monkeypatch.context() as patch:
        patch.setattr(SessionStore,'close',slow_close)
        seal=threading.Thread(target=store.seal_days,args=(ready,));seal.start()
        assert started.wait(2)
        writer=threading.Thread(target=lambda:(store.append(root,'events',dict(reason='during_seal')),written.set()))
        writer.start()
        try:assert written.wait(2)
        finally:release.set();seal.join(2);writer.join(2)
        assert not seal.is_alive() and not writer.is_alive()
    assert (root/'days/2026-10-01/files.json').exists()
    scored=[r for r in rows('scores') if r['status']=='scored' and r['horizon_s']==90]
    assert len(scored)==3 and {r['origin_day'] for r in scored}=={'2026-10-01'}
    assert json.loads((root/'days/2026-10-01/scoring.json').read_text())['per_method']['G2-HOLD/90']['n']==1
    # Missing sources still settle their existing targets and release old day statistics.
    ledger.advance(183,str(day[0]));assert not ledger.pending
    assert ledger.last_anchor==90 and ledger.identity['run_id']=='r'
    cli=Path(sys.executable).with_name('tto-observe')
    result=subprocess.run([str(cli),'history','--session',str(root),'--stream','scores','--last','1000'],capture_output=True,text=True,check=True)
    settled=[row['settled_mono_s'] for row in json.loads(result.stdout)]
    assert settled==sorted(settled) and settled[-1]==183
    # Midnight between date reads must not publish an uncommitted day for sealing.
    from types import SimpleNamespace
    from tto_field.observe_runtime import Consumer
    consumer=SimpleNamespace(store=store,ledger=ledger,lag_limit=.25,ready_days=set())
    def midnight():
        previous=day[0];day[0]=date(2026,10,3);return previous
    with monkeypatch.context() as patch:
        patch.setattr(store,'today',midnight)
        Consumer.maintain_days(consumer)
        assert '2026-10-02' not in consumer.ready_days
        store.seal_days(consumer.ready_days)
        Consumer.maintain_days(consumer)
        assert (root/'days/2026-10-02/scoring.json').exists()
        store.seal_days(consumer.ready_days)
    for n in range(2,33):
        day[0]=date(2026,10,1)+timedelta(days=n)
        store.append(root,'observations',dict(n=n))
        store.seal_days(set(store.days)-{str(day[0])});expire_history(root,'one','host',day[0],active_store=store)
    assert len(list((root/'days').iterdir()))==30 and not (root/'days/2026-10-01').exists()
    assert set(store.recorded_days)=={p.name for p in (root/'days').iterdir()}
    # Recent startup failures have metadata but no daily records yet; retain their evidence.
    for name,age in [('recent-failed',0),('expired-failed',31)]:
        failed=tmp_path/name;failed.mkdir()
        (failed/'history-retention.json').write_text(json.dumps(dict(layout='utc-days',device_id='one',host='host',day=str(day[0]-timedelta(days=age)))))
        (failed/'failure.json').write_text('{"reason":"startup_write_failed"}')
    expire_history(root,'one','host',day[0])
    assert (tmp_path/'recent-failed/failure.json').is_file() and not (tmp_path/'expired-failed').exists()
    # Active history remains readable; a small clock correction cannot reopen a sealed day.
    last=store.recording_day();day[0]-=timedelta(days=1)
    store.append(root,'observations',dict(n=33));assert store.recording_day()==last
    assert rows('observations')[-1]['n']==33
    store.metadata(root/'status.json',dict(running=False));store.metadata(root/'summary.json',dict(scope='synthetic retained window'))
    # Closing only seals the open day, never re-reads already sealed raw data.
    old=(root/'days/2026-10-04/observations-0001.jsonl.gz');before=file_hash(old)
    import tto_field.observe_storage as storage
    def hash_open_only(path):
        assert Path(path)!=old, 'sealed raw file re-hashed on shutdown'
        return file_hash(path)
    with monkeypatch.context() as patch:
        patch.setattr(storage,'file_hash',hash_open_only);store.close()
    assert file_hash(old)==before
    inventory=json.loads((root/'files.json').read_text())
    assert {name for name in inventory if name.startswith('days/')}=={
        f'days/{day}/files.json' for day in store.recorded_days}
    assert archive(root,tmp_path/'retained.zip')['files_verified']>30
    import pytest
    for damaged in (old,old.parent/'files.json'):
        before=damaged.read_bytes();damaged.write_bytes(before[:-1]+b' ')
        with pytest.raises(ValueError,match='SHA mismatch'):archive(root,tmp_path/'invalid.zip')
        assert not (tmp_path/'invalid.zip').exists()
        damaged.write_bytes(before)

    # Whole-day loss, including loss of every daily directory, must not become
    # a successful metadata-only archive or be mistaken for normal retention.
    import zipfile
    next_run=tmp_path/'next-run';next_run.mkdir()
    for missing in (old.parent/'files.json',old.parent,root/'days'):
        saved=tmp_path/'missing-history';missing.rename(saved)
        destination=tmp_path/'missing.zip'
        try:
            with pytest.raises(FileNotFoundError):archive(root,destination)
            assert not destination.exists()
            if missing==root/'days':
                expire_history(next_run,'one','host',date(2026,11,3))
                assert (root/'summary.json').exists()
        finally:saved.rename(missing)

    # After restart the persisted inventory, not the old writer's memory, owns
    # retention. Commit expiry before deleting; an interrupted delete may leave
    # old extras, but those unverified extras must not enter the ZIP.
    def failed_delete(path):raise OSError('injected retention deletion failure')
    with monkeypatch.context() as patch:
        patch.setattr(storage.shutil,'rmtree',failed_delete)
        with pytest.raises(OSError,match='retention deletion failure'):
            expire_history(next_run,'one','host',date(2026,11,3))
    assert old.exists() and 'days/2026-10-04/files.json' not in json.loads((root/'files.json').read_text())
    archive(root,tmp_path/'pruned.zip')
    with zipfile.ZipFile(tmp_path/'pruned.zip') as zipped:
        assert not any(name.startswith('days/2026-10-04/') for name in zipped.namelist())
        actual=[json.loads(line) for name in sorted(zipped.namelist()) if Path(name).name.startswith('observations-')
                for line in gzip.decompress(zipped.read(name)).splitlines()]
        assert actual==rows('observations') and all(row['n']!=3 for row in actual)
    assert expire_history(next_run,'one','host',date(2026,11,3))==['2026-10-04']
    assert not old.parent.exists()
    archive(root,tmp_path/'after-pruning.zip')
    # Each atomic replacement owns its temporary file. A dead process's old
    # temporary path cannot block a new startup, nor should it be overwritten.
    inventory_path=root/'files.json';inventory_raw=inventory_path.read_bytes()
    orphan=root/'files.json.next';orphan.write_bytes(b'interrupted previous process')
    def interrupted_replace(source,destination):raise OSError('injected inventory replacement failure')
    with monkeypatch.context() as patch:
        patch.setattr(storage.os,'replace',interrupted_replace)
        with pytest.raises(OSError,match='inventory replacement failure'):
            expire_history(next_run,'one','host',date(2026,11,4))
    assert inventory_path.read_bytes()==inventory_raw and not list(root.glob('files.json.*.next'))
    assert orphan.read_bytes()==b'interrupted previous process'
    assert expire_history(next_run,'one','host',date(2026,11,4))==['2026-10-05']
    archive(root,tmp_path/'after-interrupted-replacement.zip')
    index_path=root/'stream-index.json';index_raw=index_path.read_bytes()
    index=dict(json.loads(index_raw),contract='TTO-OBSERVE-DAYS-v1');index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError,match='requires retained-day inventory'):archive(root,tmp_path/'old-layout.zip')
    index_path.write_bytes(index_raw)
    # Missing retained days remain an error until they leave the 30-day window;
    # once every expected date expires, the closed session can be fully reclaimed.
    (root/'days').rename(tmp_path/'gone-days')
    expire_history(next_run,'one','host',date(2026,12,3))
    assert not root.exists()

    # The seal-time receipt must survive until root finalization: neither a
    # vanished day nor a valid-JSON replacement index can be adopted as truth.
    for missing in (True,False):
        lost=DailyStore(tmp_path/f'lost-before-close-{missing}',today=lambda:date(2026,11,3),min_free=0)
        lost.append(lost.root,'observations',dict(n=1));lost.seal_days({'2026-11-03'})
        if missing:(lost.root/'days/2026-11-03').rename(tmp_path/'lost-day')
        else:
            index=lost.root/'days/2026-11-03/files.json'
            index.write_bytes(b'{}'+b' '*(index.stat().st_size-2))
        with pytest.raises(FileNotFoundError if missing else ValueError):lost.close()
