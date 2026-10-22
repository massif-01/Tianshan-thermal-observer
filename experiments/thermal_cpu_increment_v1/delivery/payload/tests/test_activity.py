import copy
from contextlib import closing
import http.client
import json
import socket
import threading
import time
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from activity import Activity, Processor, load_candidate
from fixtures import frame
from consume import make_server
from evaluate_stream import evaluate, downsample_1s
from stream_metrics import metrics


def test_features_are_incremental_same_clock_and_no_best_core():
    c,f=load_candidate();p=Processor(c,f)
    x=frame(1.,core_only=True)
    r=p.process(x)['variants']
    assert r['INPUT-BASE']['activity']['state']=='IDLE'
    assert r['INPUT-MEAN']['activity']['state']=='IDLE'
    assert r['INPUT-CORE']['activity']['state']=='ACTIVE'
    assert c['variants']['INPUT-CORE']==c['variants']['INPUT-MEAN']+['cpu_max_pct']
    # No phase, schedule or future answer is in the feature allowlist.
    a=Processor(c,f);b=Processor(c,f)
    for t in (1.,2.,3.):
        x=frame(t,active=t>=2)
        other=copy.deepcopy(x)
        other.update(next_submit=999,future_temperature_C=999,posthoc_phase='future-work')
        assert a.process(x)==b.process(other)


def test_repeated_buffer_cannot_renew_support_and_equal_new_values_are_kept():
    c,_=load_candidate();a=Activity(c,'INPUT-CORE')
    x=frame(1.,active=True,sequence=1,until=1.5)
    assert a.step(x)['state']=='ACTIVE'
    y=copy.deepcopy(x);y['arrival_mono_s']=2.
    for f in y['features'].values():f.update(available_at_mono_s=2.,valid_until_mono_s=7.)
    r=a.step(y)
    assert r['state']=='UNKNOWN' and 'repeated_identity' in r['reason']
    r=a.step(frame(2.2,active=True,sequence=2))
    assert r['state']=='ACTIVE' and r['new_evidence']


def test_hysteresis_does_not_count_duplicate_reads_as_new_observations():
    c,_=load_candidate();a=Activity(c,'INPUT-CORE')
    a.step(frame(0.,active=True))
    low=frame(1.,sequence=1,until=10.)
    assert a.step(low)['state']=='ACTIVE'
    repeated=copy.deepcopy(low);repeated['arrival_mono_s']=4.1
    assert a.step(repeated)['state']=='ACTIVE'
    assert a.step(frame(4.2,sequence=2))['state']=='IDLE'


@pytest.mark.parametrize('case',['source_only','clock_unknown','expired','future_feature','missing','negative'])
def test_missing_or_not_arrived_is_unknown(case):
    c,_=load_candidate();a=Activity(c,'INPUT-BASE');x=frame(1.,active=True)
    if case=='source_only':x['source_only']=True
    elif case=='clock_unknown':x['arrival_clock_id']=None
    elif case=='expired':x['features']['gpu_W']['valid_until_mono_s']=.5
    elif case=='future_feature':x['features']['gpu_W']['available_at_mono_s']=1.1
    elif case=='missing':del x['features']['gpu_W']
    else:x['features']['gpu_W']['value']=-1
    assert a.step(x)['state']=='UNKNOWN'


def test_future_cutoff_and_epoch_and_gap():
    c,_=load_candidate();a=Activity(c,'INPUT-CORE')
    with pytest.raises(ValueError,match='future frame'):a.step(frame(2.),cutoff=1.)
    a=Activity(c,'INPUT-CORE')
    a.step(frame(0.,active=True,until=1.))
    assert a.step(frame(10.))['state']=='IDLE'
    x=frame(11.);x['epoch']=2
    assert a.step(x)['state']=='IDLE'
    with pytest.raises(ValueError,match='regression'):a.step(frame(9.))


@pytest.mark.parametrize('mode',['ACTIVE','IDLE','HOLD'])
def test_future_input_conversion_against_independent_ODE(mode):
    c,f=load_candidate();thermal=frame(0.)['thermal'];p=f.p
    idle=c['levels']['idle'];active=c['levels']['active'];u=thermal['conditional_inputs_rails_W_PWM']
    def ode(t,x):
        if mode=='ACTIVE':powers=[max(u[0],active['gpu_W']),max(u[1],active['cpu_soc_mss_W'])]
        elif mode=='HOLD':powers=u[:2]
        else:powers=[idle['gpu_W']+(u[0]-idle['gpu_W'])*np.exp(-t/30),idle['cpu_soc_mss_W']+(u[1]-idle['cpu_soc_mss_W'])*np.exp(-t/30)]
        loss=p['d0']+p['d1']*u[2]
        return [-p['a']*(x[0]-x[1])+p['b_g']*powers[0]+p['b_c']*powers[1],p['c']*(x[0]-x[1])-loss*(x[1]-x[2]),0.]
    init=[thermal['current_TJ_C'],thermal['Ts_C'],thermal['E_C']]
    answer=solve_ivp(ode,(0,90),init,t_eval=[15,45,90],rtol=1e-11,atol=1e-12).y[0]
    for h,truth in zip((15,45,90),answer):assert abs(f.predict(thermal,mode,h)-truth)<1e-8


def test_no_forecast_when_state_unavailable_or_wrong_model():
    _,f=load_candidate();x=frame(0.)['thermal']
    assert f.predict(x,'UNKNOWN',45) is None
    x['available']=False
    assert f.predict(x,'ACTIVE',45) is None
    x['available']=True;x['model_sha256']='wrong'
    with pytest.raises(ValueError,match='identity'):f.predict(x,'ACTIVE',45)


def test_loopback_explicit_permission_and_actual_arrival_and_unknown_clock():
    c,f=load_candidate()
    with pytest.raises(PermissionError):make_server(Processor(c,f),allow_loopback=False)
    with pytest.raises(ValueError,match='loopback'):make_server(Processor(c,f),allow_loopback=True,host='0.0.0.0')
    srv=make_server(Processor(c,f),allow_loopback=True)
    thread=threading.Thread(target=srv.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
    try:
        now=time.monotonic();x=frame(now,active=True)
        x['ingress_clock_id']='local_monotonic_current_boot'
        with closing(http.client.HTTPConnection(*srv.server_address,timeout=3)) as conn:
            conn.request('POST','/observe',json.dumps(x),{'Content-Type':'application/json'})
            res=conn.getresponse();r=json.loads(res.read());assert res.status==200
        assert r['ingress_received_mono_s']>=now
        assert all(v['activity']['state']=='ACTIVE' for v in r['variants'].values())
        x=frame(time.monotonic()+1,active=True)
        with closing(http.client.HTTPConnection(*srv.server_address,timeout=3)) as conn:
            conn.request('POST','/observe',json.dumps(x),{'Content-Type':'application/json'})
            res=conn.getresponse();r=json.loads(res.read());assert res.status==200
        assert all(v['activity']['state']=='UNKNOWN' for v in r['variants'].values())
    finally:
        srv.shutdown();srv.server_close();thread.join(timeout=3)


def test_future_stream_keeps_45s_labels_without_90s_and_never_uses_late_features():
    c,f=load_candidate()
    origins=[]
    for t in range(61):
        x=frame(float(t))
        origins.append(dict(ref=f'origin:{t}',t=float(t),current=50.,source_valid=True,
            epoch=1,source_key=['synthetic','synthetic-stream'],thermal=x['thermal'],arrival_clock_id=x['arrival_clock_id']))
    frames=[frame(i/5,active=i>=13,core_only=10<=i<13) for i in range(301)]
    actual=evaluate(frames,origins,c,f)
    b0_45=next(r for r in actual['coverage'] if r['h']==45 and r['method']=='B0')
    b0_90=next(r for r in actual['coverage'] if r['h']==90 and r['method']=='B0')
    assert b0_45['scored']==16 and b0_90['scored']==0
    changed=copy.deepcopy(frames)
    for x in changed:
        if x['arrival_mono_s']>20:
            for v in x['features'].values():v['value']=0.
    again=evaluate(changed,origins,c,f)
    a=[r['prediction'] for r in actual['points'] if r['t']<=20]
    b=[r['prediction'] for r in again['points'] if r['t']<=20]
    assert a==b
    coarse=downsample_1s(frames)
    assert all(x['actual_original_arrival_mono_s']<=x['arrival_mono_s'] for x in coarse)
    assert all(x['features']['gpu_W']['valid_until_mono_s']<=x['actual_original_arrival_mono_s']+5. for x in coarse)


def test_common_activity_delay_can_detect_increment_and_unknown_clock_is_not_aligned():
    c,f=load_candidate();p=Processor(c,f)
    frames=[frame(i/5,active=i>=13,core_only=10<=i<13) for i in range(31)]
    trace=[]
    for x in frames:
        r=p.process(x)
        trace.append(dict(states={n:v['activity'] for n,v in r['variants'].items()}))
    events=[dict(event_id='synthetic',submit_mono_s=1.5,done_mono_s=5.,arrival_clock_id='synthetic-receiver-clock',continuous_group='one')]
    r=metrics(frames,trace,events,list(c['variants']))
    delays={x['variant']:x['delay_s'] for x in r['events']}
    assert abs(delays['INPUT-CORE']-.5)<1e-12
    assert abs(delays['INPUT-MEAN']-1.1)<1e-12
    events[0]['arrival_clock_id']='unknown other host'
    assert metrics(frames,trace,events,list(c['variants']))['status'].startswith('unknown')
