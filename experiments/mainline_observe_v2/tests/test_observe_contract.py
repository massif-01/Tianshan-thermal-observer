from tto.recordio import read_records
import copy, json, socket, uuid
from pathlib import Path
import pytest
from tto_field.observe_predictions import Ledger
from tto_field.observe_storage import SessionStore
from tto.storage import LimitReached,InstanceLock
from tto.config import load_config,require_live

def frame(t,value=40,epoch=0,valid=True,new=True):
    return dict(t=t,ref=f'r/{t}',utc='2026-10-21T00:00:00Z',new_TJ=new,source_reset=False,
        identity=dict(run_id='r',source_epoch=epoch),measurement=dict(tj=dict(value_C=value,raw_valid=valid,
        valid_until_mono_s=t+5,source_ref=f'r/{t}',observed_mono_s=t,observed_utc='2026-10-21T00:00:00Z')))
def make():
    rows=[];l=Ledger(lambda k,x:rows.append((k,x)),dict(run_id='r',clock_domain='d'));return l,rows
def outputs():return [dict(method=m,horizon_s=h,value_C=40,assumptions={'PWM':'conditional'}) for m in ['G2-HOLD','B0','B1'] for h in [15,45,90]]
def consume(l,t,**kw):l.consume(frame(t,**kw),t+.01,outputs(),state_status='degraded',wall_clock=dict(utc='2026-10-21T00:00:00Z',mono_s=t+.01))

def test_maturity_first_qualified_and_missing_not_zero():
    l,rows=make();consume(l,0);consume(l,14,value=99);assert not [x for k,x in rows if k=='scores']
    consume(l,15,value=45,valid=False)
    l.advance(17.1,'2026-10-21',receive_lag=.25)
    l.consume(frame(17,value=42),17.2,outputs(),state_status='degraded',wall_clock=dict(utc='2026-10-21T00:00:17Z',mono_s=17.2))
    scored=[x for k,x in rows if k=='scores' and x['status']=='scored'];assert len(scored)==3 and all(x['label_ref']=='r/17' and x['error_C']==-2 for x in scored)
    l.finish(20);assert any(x.get('reason')=='target_not_mature_at_end' for k,x in rows if k=='scores')

def test_late_publication_all_methods_same_real_issue():
    l,rows=make();l.consume(frame(0),16,outputs(),state_status='tracking',wall_clock=dict(utc='x',mono_s=16))
    ps=[x for k,x in rows if k=='predictions'];assert len(ps)==9 and len({x['issued_at']['mono_s'] for x in ps})==1
    assert all(x['value_C'] is None and x['late'] for x in ps if x['horizon_s']==15)

def test_epoch_clock_identity_and_expiry():
    l,rows=make();consume(l,0);consume(l,16,epoch=1)
    assert not [x for k,x in rows if k=='scores' and x['status']=='scored']
    with pytest.raises(ValueError):consume(l,15)
    bad=frame(17);bad['identity']['run_id']='other'
    with pytest.raises(ValueError):l.consume(bad,17.01,[],state_status='x',wall_clock=dict(utc='x',mono_s=17.01))

def test_no_interpolation_or_early_label_and_common_sets():
    l,rows=make();consume(l,0);consume(l,18,value=41)
    assert any(x.get('reason')=='missing_qualified_label_within_2s' for k,x in rows if k=='scores')
    assert not l.stats

def test_rotation_keeps_unique_stream_identity_and_budget(tmp_path):
    now=[0.];store=SessionStore(tmp_path/'s',budget=200000,segment_bytes=1000,chunk_bytes=500,segment_seconds=4,min_free=0,clock=lambda:now[0])
    for n in range(20):
        store.append(store.root,'observations',dict(native_run_id='one',n=n))
        for stream in ('predictions','scores'):store.append(store.root,stream,dict(n=n))
        now[0]+=.5
    store.close();index=json.loads((store.root/'stream-index.json').read_text());assert index['rotations']>=2 and index['heat_state_reset_by_rotation'] is False
    records=[]
    for p in index['streams']['./observations']:records += list(read_records(store.root/p))
    assert [x['n'] for x in records]==list(range(20))
    assert {x['native_run_id'] for x in records}=={'one'}
    from tto.util import file_hash
    for name,info in json.loads((store.root/'files.json').read_text()).items():
        assert (store.root/name).stat().st_size==info['bytes'] and file_hash(store.root/name)==info['sha256']
    assert store.total==sum(p.stat().st_size for p in store.root.rglob('*') if p.is_file())
    assert all(s['byte_count']<=store.segment_bytes for s in store.segments)
    assert all(p.stat().st_size<=store.chunk_bytes for p in store.root.glob('*.gz'))
    small=SessionStore(tmp_path/'small',budget=1000,chunk_bytes=500,min_free=0)
    with pytest.raises(LimitReached):
        for n in range(100):small.append(small.root,'raw',{'v':'a'*100,'n':n})
    # The rejected record must not change the gzip dictionary/CRC of committed rows.
    committed=[p for p in small.root.glob('*.gz')]
    before=[list(read_records(p,live=True)) for p in committed]
    small.close_prefix(small.root)
    assert before==[list(read_records(p)) for p in committed]

def test_disk_and_storage_error_not_silent(tmp_path,monkeypatch):
    import tto_field.observe_storage as module
    s=SessionStore(tmp_path/'x',min_free=1)
    monkeypatch.setattr(module.shutil,'disk_usage',lambda p:type('D',(),{'free':0})())
    with pytest.raises(LimitReached,match='min_free'):s.append(s.root,'raw',{})

def test_legacy_four_hour_guard_unchanged():
    c=load_config(environ={});c['orin']['base_url']='http://127.0.0.1:1';c['tianshan']['base_url']='http://127.0.0.1:2'
    with pytest.raises(ValueError):require_live(c,86400)
    require_live(c,86400,observe=True)
    require_live(c,None,observe=True)
    with pytest.raises(ValueError):require_live(c,None)
    with pytest.raises(ValueError):require_live(c,86401,observe=True)

def test_native_single_instance_lock_not_deleted(tmp_path):
    path=tmp_path/'lock'
    with InstanceLock(path):
        with pytest.raises(ValueError):
            with InstanceLock(path):pass
    assert path.exists()

def test_stat_buffer_bounded_total_not_faked():
    from tto_field.observe_limits import Samples
    b=Samples()
    for n in range(20000):b.append(n)
    assert len(b)==4096 and b.total==20000 and b[0]==15904 and b[1:3]==[15905,15906]

def test_event_tail_missing_gap_not_zero(tmp_path):
    from tto_field.observe_workload import EventTail
    p=tmp_path/'protocol';rows=[];t=EventTail(p,dict(session_id='r',clock_domain='s'), 'd',lambda k,x:rows.append(x))
    t.tick();assert t.current['client_inflight'] is None
    p.write_text('');t.tick()
    with p.open('a') as f:f.write(json.dumps(dict(event='request_submit',request_id='q',native_run_id='r',mono_s=1))+'\n')
    t.tick();assert t.current['client_inflight'] is None
    p.write_text('');t.tick();assert t.current['event']=='source_unknown'

def test_resource_policy_sustained_and_unknown_not_single_peak():
    from tto_field.observe_limits import ReceiverBudget
    b=ReceiverBudget();row=lambda c,r=70*1024**2:dict(cpu_pct_single_core=c,rss_bytes=r)
    for n in range(37):assert b.sample(row(9),n) is None
    assert b.sample(row(9),37)=='receiver_sustained_CPU_budget'
    b=ReceiverBudget()
    assert b.sample(row(99),1) is None
    for n in range(2,50):assert b.sample(row(1),n) is None
    assert b.sample(row(1,129*1024**2),50)=='receiver_RSS_budget'
    assert b.sample(row(99,129*1024**2),51,enforce=False) is None and b.mean is not None
    b=ReceiverBudget()
    for n in range(3,13):assert b.sample(row(None),n) is None
    assert b.sample(row(None),13)=='resource_unavailable'

def test_foreground_requires_current_window_and_no_old_cpu_permission():
    from tto_field.observe_cli import validate_start
    from tto.util import digest
    from tto.config import public_config
    from datetime import datetime,timedelta,timezone
    c=load_config(environ={});c['orin']['base_url']='http://127.0.0.1:1';c['tianshan']['base_url']='http://127.0.0.1:2'
    reg=dict(device_id='D',thermal_config_id='C',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
    now=datetime.now(timezone.utc);g=dict(action='readonly-observe',explicit_user_start=True,evidence='LOCAL TEST',candidate_version=__import__('tto_field').__version__,config_sha256=digest(public_config(c)),max_duration_s=60,session_max_bytes=8*1024**3,self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=90)).isoformat(),**{k:reg[k] for k in ['device_id','thermal_config_id','session_id']})
    import tto_field,hashlib
    package=Path(tto_field.__file__).parent
    g.update(candidate_manifest_sha256=hashlib.sha256((package/'candidate-files.json').read_bytes()).hexdigest(),model_manifest_sha256=hashlib.sha256((package/'g2_model/frozen-model-manifest.json').read_bytes()).hexdigest())
    validate_start(c,reg,g,60,True)
    with pytest.raises(ValueError,match='continuous'):validate_start(c,reg,g,None,True)
    continuous=dict(g,continuous=True,expires_at_utc=None,max_duration_s=None)
    validate_start(c,reg,continuous,None,True)
    with pytest.raises(ValueError,match='window does not cover'):validate_start(c,reg,continuous,60,True)
    for key,value in [('candidate_version','0.2.4+cpu.3'),('action','cpu-sidecar-readonly'),('expires_at_utc',(now-timedelta(seconds=1)).isoformat())]:
        bad=dict(g,**{key:value})
        with pytest.raises(ValueError):validate_start(c,reg,bad,60,True)

def test_repeated_status_is_atomic_but_identity_metadata_immutable(tmp_path):
    s=SessionStore(tmp_path/'s',min_free=0)
    s.metadata(s.root/'status.json',dict(running=True,n=1));s.metadata(s.root/'status.json',dict(running=True,n=2))
    assert json.loads((s.root/'status.json').read_text())['n']==2 and not list(s.root.glob('*.next'))
    s.metadata(s.root/'launch.json',dict(pid=1))
    with pytest.raises(FileExistsError):s.metadata(s.root/'launch.json',dict(pid=2))

def test_ninety_second_target_and_origin_coverage():
    l,rows=make();consume(l,0)
    for t in range(1,90):
        f=frame(t,valid=False,new=False);l.consume(f,t+.01,[],state_status='unavailable',wall_clock=dict(utc='x',mono_s=t+.01))
    consume(l,90,value=41)
    assert len([x for k,x in rows if k=='scores' and x.get('status')=='scored' and x['horizon_s']==90])==3
    s=l.summary();assert s['valid_TJ_denominator']==2 and s['same_set_G2_B0']['G2-HOLD/90']['n']==1

def test_model_line_golden_shared_api_byte_exact_values():
    from tto_field.g2_model.g2_runtime import Predictor
    root=Path(__file__).resolve().parents[3]/'evidence/mainline-observe-20261021/integration/model-golden/cases.json'
    api=Predictor();cases=json.loads(root.read_text())['cases']
    for case in cases:
        args=dict(case['input']);state=args.pop('state');records=api.predict(state,**args)
        for actual,expected in zip(records,case['expected']):
            assert actual['method']==expected['method'] and actual['horizon_s']==expected['horizon_s']
            assert actual['unavailable_reasons']==expected['unavailable_reasons']
            if expected['value_C'] is None:assert actual['value_C'] is None
            else:assert abs(actual['value_C']-expected['value_C'])<=1e-8

def test_future_TJ_cannot_change_frozen_prediction():
    from tto_field.g2_model.g2_runtime import Predictor
    root=Path(__file__).resolve().parents[3]/'evidence/mainline-observe-20261021/integration/model-golden/cases.json'
    case=copy.deepcopy(json.loads(root.read_text())['cases'][0]['input']);state=case.pop('state');api=Predictor()
    before=api.predict(state,**case);later=copy.deepcopy(case['origin']);later.update(ref='FUTURE-NOT-AVAILABLE',received_at_mono_s=case['origin']['received_at_mono_s']+100,value_C=999)
    case['history']=list(case.get('history',[]))+[later];after=api.predict(state,**case)
    assert [(x['value_C'],x['history_refs']) for x in before]==[(x['value_C'],x['history_refs']) for x in after]

@pytest.mark.parametrize('daily',[False,True])
def test_io_rotation_does_not_cold_start_real_frozen_observer(tmp_path,monkeypatch,daily):
    from datetime import datetime,timedelta,timezone
    from types import SimpleNamespace
    import threading
    from fake_source import FakeSource
    from tto.engine import engine_for
    from tto_field.observe_storage import DailyStore
    from tto_field.observe_runtime import Consumer
    import tto_field.observe_runtime as runtime
    now=[1000.];begin=datetime(2026,10,1,23,59,30,tzinfo=timezone.utc)
    wall=lambda:begin+timedelta(seconds=now[0]-1000)
    monkeypatch.setattr(runtime,'time',SimpleNamespace(monotonic=lambda:now[0]+.001))
    monkeypatch.setattr(runtime,'utc',lambda:wall().isoformat())
    options=dict(today=lambda:wall().date()) if daily else {}
    store=(DailyStore if daily else SessionStore)(tmp_path/'s',**options,budget=10000000,segment_seconds=30,min_free=0,clock=lambda:now[0])
    native=store.root/'native/run-fixture';native.mkdir(parents=True)
    config=load_config(environ={});config['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='owned synthetic')
    manifest=dict(observer_run_id='r',config=config,config_sha256='synthetic',source_identity={'sha256':'synthetic'})
    (native/'manifest.json').write_text(json.dumps(manifest))
    engine=engine_for(config,record_schema=2);source=FakeSource();phases=[]
    monkeypatch.setattr(Consumer,'publish',lambda self,inputs,frame,state,deadline:phases.append((frame['t'],state['observer']['phase'])))
    consumer=Consumer(store,dict(session_id='fixture',device_id='synthetic',thermal_config_id='synthetic',observer_host_id='offline'),SimpleNamespace(domain='fixture'),threading.Event(),SimpleNamespace(call_soon_threadsafe=lambda f:f()))
    try:
        ordinal=0
        for n in range(180):
            now[0]=1000.+n;stamp=wall().isoformat()
            packet=source.packet();packet['timestamp']=packet['telemetry_meta']['received_at']=packet['gpu']['sampled_at_utc']=stamp
            for kind,payload in [('fan',source.payload('fan')),('temp',source.payload('temp')),('orin',packet)]:
                ordinal+=1;raw=dict(kind=kind,payload=payload,mono_s=now[0],received_at_utc=stamp,observer_run_id='r',ref=f'r/observation:{ordinal}',connection_epoch=1)
                store.append(native,'observations',raw);consumer.on_record(raw,engine.process(raw),engine);consumer.queue.join()
            if daily:store.seal_days(consumer.ready_days)
    finally:
        closed=consumer.close();store.close()
    assert closed and consumer.fatal is None and consumer.model_errors==0
    assert consumer.stateful_observers==consumer.observer.starts==1
    assert consumer.engine_id==id(engine) and consumer.ledger.identity['run_id']=='r'
    assert any(t<1030 and phase=='tracking' for t,phase in phases)
    assert all(phase=='tracking' for t,phase in phases if t>=1030)
    if daily:assert (store.root/'days/2026-10-01/files.json').exists()
    else:assert store.rotation_count>=5

def test_invalid_business_row_becomes_unknown(tmp_path):
    from tto_field.observe_workload import EventTail
    f=tmp_path/'events';f.write_text('');outputs=[];tail=EventTail(f,dict(session_id='r',clock_domain='d',complete_from_session_start=True),'o',lambda k,x:outputs.append(x));tail.tick()
    with f.open('a') as stream:stream.write('[]\n')
    tail.tick();assert tail.current['event']=='source_unknown' and tail.current['client_inflight'] is None

@pytest.mark.parametrize('pending',[False,True])
def test_low_disk_stops_data_but_uses_reserved_final_metadata(tmp_path,monkeypatch,pending):
    import asyncio,time
    from types import SimpleNamespace
    from fake_source import FakeSource
    from tto_field.observe_cli import archive
    from tto_field.observe_runtime import Consumer,run_observe
    from tto_field.observe_storage import history_files
    import tto_field.observe_storage as module
    free=[2*1024**3];stores=[];expected=set()
    monkeypatch.setattr(module.shutil,'disk_usage',lambda p:SimpleNamespace(free=free[0]))
    on_record=Consumer.on_record;close=Consumer.close
    def stop_after_samples(self,*args):
        on_record(self,*args)
        if self.valid_TJ>=2:self.loop.call_soon_threadsafe(self.stop.set)
    def close_with_low_space(self):
        stopped=close(self);assert stopped and self.ledger and self.ledger.day_stats
        expected.update(p['prediction_id'] for b in self.ledger.pending for p in b['items'])
        assert expected
        if not pending:self.ledger.finish(time.monotonic())
        free[0]=256*1024
        with pytest.raises(LimitReached):self.store.append(self.store.root,'observations',dict(unexpected=True))
        stores.append(self.store);return stopped
    monkeypatch.setattr(Consumer,'on_record',stop_after_samples)
    monkeypatch.setattr(Consumer,'close',close_with_low_space)
    async def run():
        async with FakeSource() as source:
            config=load_config(environ={})
            config['orin'].update(base_url=source.url,source_sample_interval_ms=1000,source_interval_evidence='owned fixture')
            config['tianshan']['base_url']=source.url
            registration=dict(device_id='fixture',thermal_config_id='fixture',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
            summary=await run_observe(config,registration,tmp_path/'s',None,local_loopback=True,storage_options=dict(min_free=1024**2))
            assert summary['reason']=='external_stop' and summary['consumer_stopped']
    asyncio.run(run())
    root=tmp_path/'s';status=json.loads((root/'status.json').read_text())
    assert status['running'] is False and (root/'summary.json').exists()
    scores=[row for path,live in history_files(root,'scores') for row in read_records(path,live=live)]
    assert {row['prediction_id'] for row in scores}==expected and len(scores)==len(expected)
    assert all((path/'scoring.json').exists() for path in (root/'days').iterdir())
    assert archive(root,tmp_path/'s.zip')['files_verified']>0
    free[0]=0
    with pytest.raises(LimitReached):stores[0].metadata(root/'no-space.json',{},final=True)
    assert not (root/'no-space.json').exists()


def test_continuous_ledger_outlives_test_origin_budget_without_error_growth():
    l,rows=make();l.daily=True
    for n in range(17285):
        day=f'2026-10-{1+n//8640:02d}'
        t=n*10
        l.consume(frame(t),t+.01,outputs(),state_status='tracking',wall_clock=dict(utc=day+'T00:00:00Z',mono_s=t+.01))
        l.advance(t,day);rows.clear()
    assert l.counts['scheduled_TJ_origins']==17285 and l.last_anchor>86400
    assert len(l.pending)<=18 and len(l.day_stats)<=2 and not l.stats and not l.common
    assert max(v.n for stats in l.day_stats.values() for name in ('per_method','same_set_G2_B0') for v in stats[name].values())<=8640


def test_rendered_service_separates_continuous_from_timed_test():
    import runpy
    from types import SimpleNamespace
    script=Path(__file__).resolve().parents[1]/'scripts/install_observe.py'
    render=runpy.run_path(str(script))['render_unit']
    a=SimpleNamespace(prefix=Path('/local/prefix'),config=Path('/local/config'),registration=Path('/local/registration'),grant=Path('/local/grant'),session_output=Path('/local/history'),publication_descriptor=Path('/local/pub/active.json'),duration=None)
    permanent=render(a)
    assert 'RuntimeMaxSec' not in permanent and '--duration' not in permanent and 'Restart=on-failure' in permanent
    assert '--publication-descriptor' in permanent and 'WantedBy=default.target' in permanent
    a.duration=60;timed=render(a)
    assert 'RuntimeMaxSec=70' in timed and 'Restart=no' in timed and '--duration' in timed
