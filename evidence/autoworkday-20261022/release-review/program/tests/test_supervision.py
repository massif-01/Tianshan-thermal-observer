import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from admission import evaluate
from supervision import Health,Controls,Budget

IDENTITY=dict(device_id='synthetic-device',thermal_config_id='synthetic-config',session_id='synthetic-session',observer_host_id='synthetic-host',boot_id='synthetic-boot',model_sha256='model',spec_sha256='spec')
def views(t):
    m={k:dict(raw_valid=True,observed_mono_s=t,valid_until_mono_s=t+ttl) for k,ttl in [('tj',7.5),('power',7.5),('last_successful_pwm',2.5),('control_context',7.5)]}
    m['tj']['value_C']=45;m['power'].update(names=['vdd_gpu','vdd_cpu_soc_mss'],rails_W=[2,6]);m['last_successful_pwm']['value_percent']=17
    safe=dict(guard=False,fault=False,enabled=True,mode='auto',manual_mode=False,binding='agx_info.temperature.tj',active_source='variable',fan_fresh=True,binding_fresh=True,temp_stale=False,normalized_valid=True,confirmed_normal_now=True,context_stable_s=5)
    launch=dict(registration=dict(IDENTITY),version='0.2.4+observe.2',clock_start=dict(mono_before_s=0,pid=7,domain='synthetic-domain'),authorization=dict(config_sha256='config'))
    env=dict(identity=dict(IDENTITY,run_id='synthetic-native'),process_clock_domain='synthetic-domain',clock=dict(domain='synthetic-domain',observer_input_mono_s=t,generated_at_mono_s=t),expected_identity=dict(config_sha256='config'),measurement=m,safety=safe,model=dict(available=False),native_ref='synthetic-native/observation:1')
    return launch,dict(running=True,process_created=10,pid=7,elapsed_s=t,collection=True,native_run_id='synthetic-native',latest_state=env)
def gate(l,s,now):return evaluate(l,s,now,IDENTITY,alive=True,process_created=10)
def test_no_model_yet_override_and_TTL_expiry():
    l,s=views(20);assert gate(l,s,20)['action']=='allow'
    assert gate(l,s,22.5)['action']=='pause' # unchanged exact PWM TTL
    s['latest_state']['measurement']['tj']['raw_valid']=False
    assert gate(l,s,20)['action']=='pause'
def test_protection_identity_clock_and_observer_exit():
    for key,value in [('guard',True),('fault',True),('mode','manual'),('binding','other')]:
        l,s=views(20);s['latest_state']['safety'][key]=value;assert gate(l,s,20)['action']=='stop'
    l,s=views(20);s['latest_state']['identity']['boot_id']='wrong';assert gate(l,s,20)['action']=='stop'
    l,s=views(20);s['latest_state']['clock']['domain']='wrong';assert gate(l,s,20)['action']=='stop'
    l,s=views(20);assert evaluate(l,s,20,IDENTITY,alive=False,process_created=10)['action']=='stop'
def test_automatic_checkpoint_unready_grace_recovery_and_no_human():
    h=Health(IDENTITY);check=[]
    for t in [0,3600,7199,7200,7201]:
        l,s=views(t);g,c=h.update(t,l,s,t,alive=True,created=10)
        if c:check.append(c)
    assert len(check)==1 and check[0]['active_allowed'] and not check[0]['human_confirmation_required']
    l,s=views(7210);s['latest_state']['measurement']['last_successful_pwm']['raw_valid']=False
    assert h.update(7210,l,s,7210,alive=True,created=10)[0]['action']=='pause'
    l,s=views(7220);assert h.update(7220,l,s,7220,alive=True,created=10)[0]['action']=='allow'
    for t in [7230,7289,7290]:
        l,s=views(t);s['latest_state']['measurement']['tj']['raw_valid']=False;g,c=h.update(t,l,s,t,alive=True,created=10)
    assert g['action']=='stop' and g['reasons']==['active_conditions_unready_60s']
def test_background_failure_checkpoint_does_not_silently_allow():
    h=Health(IDENTITY)
    for t in [0,7199,7200,7259,7260]:
        l,s=views(t);s['latest_state']=None;g,c=h.update(t,l,s,t,alive=True,created=10)
        if t==7200:assert not c['active_allowed'] and c['software_healthy']
    assert g['action']=='stop'
def test_driver_and_total_resources_and_controls(tmp_path):
    b=Budget(5,64*1024**2)
    for t in range(40):r=b.tick(t,6,40*1024**2)
    assert r=='sustained_CPU_budget'
    assert Budget(8,192*1024**2).tick(1,0,193*1024**2)=='RSS_budget'
    p=tmp_path/'control.json';c=Controls(p)
    for seq,action in enumerate(['pause','resume','stop'],1):
        p.write_text(json.dumps(dict(sequence=seq,action=action)));r=c.read()
        assert r['paused']==(action=='pause') and r['stopped']==(action=='stop')

def test_load_permission_is_separate_and_exact(tmp_path):
    import socket
    from datetime import datetime,timedelta,timezone
    from program import validate,source_sha,digest,WHEEL_SHA
    root=Path(__file__).resolve().parents[1];plan=json.loads((root/'executor/frozen-plan.json').read_text())
    reg=dict(device_id='d',thermal_config_id='c',session_id='s',observer_host_id=socket.gethostname())
    request=dict(model='test',base_url='http://127.0.0.1:1',stream=True,sampling={})
    files={'registration':reg,'request_config':request,'observe_grant':dict(action='readonly-observe',session_id='s')}
    c=dict(plan=str(root/'executor/frozen-plan.json'),cleanup_seconds=120)
    for k,v in files.items():
        p=tmp_path/(k+'.json');p.write_text(json.dumps(v));c[k]=str(p)
    now=datetime.now(timezone.utc)
    grant=dict(action='auto-workday',explicit_user_start=True,evidence='SYNTHETIC UNIT',program_sha256=source_sha(),plan_sha256=plan['plan_sha256'],request_config_sha256=digest(request),observer_wheel_sha256=WHEEL_SHA,device_id='d',thermal_config_id='c',session_id='s',max_duration_s=86400,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=86500)).isoformat())
    assert validate(c,grant)[0]['plan_sha256']==plan['plan_sha256']
    import pytest
    for k,v in [('action','readonly-observe'),('explicit_user_start',False),('program_sha256','other'),('plan_sha256','other'),('device_id','other'),('session_id','other'),('request_config_sha256','other'),('expires_at_utc',now.isoformat())]:
        g=dict(grant);g[k]=v
        with pytest.raises(ValueError):validate(c,g)


def test_first_opportunity_waits_for_automatic_checkpoint():
    from supervision import request_admission
    h=Health(IDENTITY);l,s=views(7200)
    assert request_admission(h,l,s,7200,alive=True,created=10)['reasons']==['automatic_checkpoint_pending']
    h.update(7200,l,s,7200,alive=True,created=10)
    assert request_admission(h,l,s,7200,alive=True,created=10)['action']=='allow'
    h.load_stop='explicit_protection'
    assert request_admission(h,l,None,7200,alive=True,created=10)['action']=='stop'
