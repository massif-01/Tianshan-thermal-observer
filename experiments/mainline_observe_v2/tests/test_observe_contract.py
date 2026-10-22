import copy,json,math,queue,socket,time,uuid
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
    consume(l,15,value=45,valid=False);consume(l,16,value=42)
    scored=[x for k,x in rows if k=='scores' and x['status']=='scored'];assert len(scored)==3 and all(x['label_ref']=='r/16' and x['error_C']==-2 for x in scored)
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
        store.append(store.root,'observations',dict(native_run_id='one',n=n));now[0]+=.5
    store.close();index=json.loads((store.root/'stream-index.json').read_text());assert index['rotations']>=2 and index['heat_state_reset_by_rotation'] is False
    records=[]
    for p in index['streams']['./observations']:records += [json.loads(x) for x in (store.root/p).read_text().splitlines()]
    assert [x['n'] for x in records]==list(range(20))
    assert {x['native_run_id'] for x in records}=={'one'}
    small=SessionStore(tmp_path/'small',budget=1000,chunk_bytes=500,min_free=0)
    with pytest.raises(LimitReached):
        for _ in range(100):small.append(small.root,'raw',{'v':'a'*100})

def test_disk_and_storage_error_not_silent(tmp_path,monkeypatch):
    import tto_field.observe_storage as module
    s=SessionStore(tmp_path/'x',min_free=1)
    monkeypatch.setattr(module.shutil,'disk_usage',lambda p:type('D',(),{'free':0})())
    with pytest.raises(LimitReached,match='min_free'):s.append(s.root,'raw',{})

def test_legacy_four_hour_guard_unchanged():
    c=load_config(environ={});c['orin']['base_url']='http://127.0.0.1:1';c['tianshan']['base_url']='http://127.0.0.1:2'
    with pytest.raises(ValueError):require_live(c,86400)
    require_live(c,86400,observe=True)
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
    now=datetime.now(timezone.utc);g=dict(action='readonly-observe',explicit_user_start=True,evidence='LOCAL TEST',candidate_version='0.2.4+observe.2',config_sha256=digest(public_config(c)),max_duration_s=60,session_max_bytes=8*1024**3,self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=90)).isoformat(),**{k:reg[k] for k in ['device_id','thermal_config_id','session_id']})
    import tto_field,hashlib
    package=Path(tto_field.__file__).parent
    g.update(candidate_manifest_sha256=hashlib.sha256((package/'candidate-files.json').read_bytes()).hexdigest(),model_manifest_sha256=hashlib.sha256((package/'g2_model/frozen-model-manifest.json').read_bytes()).hexdigest())
    validate_start(c,reg,g,60,True)
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

def test_io_rotation_does_not_cold_start_real_frozen_observer(tmp_path):
    from tto_field.g2_model.g2_runtime import Predictor,ThermalObserver
    root=Path(__file__).resolve().parents[3]/'evidence/mainline-observe-20261021/integration/model-golden/cases.json'
    source=json.loads(root.read_text())['cases'][0]['input']['state'];api=Predictor();a=ThermalObserver(api.spec);b=ThermalObserver(api.spec)
    io_clock=[0.];store=SessionStore(tmp_path/'s',budget=500000,chunk_bytes=64000,segment_seconds=14400,min_free=0,clock=lambda:io_clock[0]);start=source['generated_at_mono_s']
    for n in range(6):
        t=start+n;m=copy.deepcopy(source['measurement'])
        for name,v in m.items():
            if v is not None:v.update(observed_mono_s=t,valid_until_mono_s=t+({'last_successful_pwm':2.5,'control_context':7.5}.get(name,5)),raw_valid=True,source_ref=f'rotation-fixture/{n}')
        m['tj']['value_C']+=n*.01
        f=dict(t=t,utc=source['generated_at_utc'],ref=f'rotation-fixture/{n}',stream_started_mono_s=start,identity=source['identity'],source_reset=False,new_TJ=True,reset_reason=None,measurement=m,safety=source['safety'])
        left=a.step(copy.deepcopy(f));right=b.step(copy.deepcopy(f));assert left==right
        store.append(store.root,'states',left);io_clock[0]+=15000
    store.close();assert store.rotation_count==5 and a.starts==b.starts==1

def test_invalid_business_row_becomes_unknown(tmp_path):
    from tto_field.observe_workload import EventTail
    f=tmp_path/'events';f.write_text('');outputs=[];tail=EventTail(f,dict(session_id='r',clock_domain='d',complete_from_session_start=True),'o',lambda k,x:outputs.append(x));tail.tick()
    with f.open('a') as stream:stream.write('[]\n')
    tail.tick();assert tail.current['event']=='source_unknown' and tail.current['client_inflight'] is None

def test_low_disk_stops_data_but_uses_reserved_final_metadata(tmp_path,monkeypatch):
    import tto_field.observe_storage as module
    s=SessionStore(tmp_path/'s',min_free=1024*1024)
    monkeypatch.setattr(module.shutil,'disk_usage',lambda p:type('D',(),{'free':8192})())
    with pytest.raises(LimitReached):s.append(s.root,'raw',{'x':1})
    s.metadata(s.root/'summary.json',dict(reason='min_free_bytes'),final=True);s.close()
    assert json.loads((s.root/'summary.json').read_text())['reason']=='min_free_bytes' and (s.root/'files.json').exists()
