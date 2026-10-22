import copy,json,sys
from pathlib import Path
import pytest
from tto_field.cpu_pilot import PilotScheduler,pilot_profile
import tto_field.cpu_pilot as pilot
from tto_field.cpu_source import utilization
from tto_field.cpu_interface import causal_inputs

def gate(*a,**k):return dict(start_allowed=True,explicit_stop=False)
@pytest.fixture(autouse=True)
def ready(monkeypatch):monkeypatch.setattr(pilot,'readiness',gate)

def simulation(duration=30):
    s=PilotScheduler(pilot_profile(),{},'FAKE-RUN','FAKE-COMMAND');now=0.;next_complete=None;submitted=[];ends=[]
    for _ in range(30000):
        complete=[]
        if next_complete is not None and now>=next_complete:
            complete=[dict(request_id=submitted[-1]['request_id'],status='completed',client_end_mono_s=now)];ends.append(now);next_complete=None
        actions,_=s.tick(now,None,complete)
        for a in actions:
            assert a['kind']=='submit';submitted.append(a);next_complete=now+duration
        if s.terminal:break
        # exact virtual integer seconds, no wall-clock waiting or real model
        now+=1
    return s,submitted,ends,now

def test_frozen_waits_and_full_worst_budget():
    s,requests,ends,now=simulation()
    assert len(requests)==12 and s.reason=='completed' and s.peak==1
    waits=[requests[i+1]['submit_mono_s']-ends[i] for i in range(5)]
    assert waits==[31,61,36,56,41] # >= exact frozen waits, one scheduler dispatch tick
    assert requests[6]['submit_mono_s']-ends[5]==51
    assert all(0<=requests[i+1]['submit_mono_s']-ends[i]<=1 for i in range(6,11))
    assert now==1062 and now+120==1182 and now+120<=1200
    assert pilot_profile()['nominal_worst_normal_s']==1170

def test_stop_drains_and_unknown_does_not_dispatch():
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(60,None);s.tick(240,None);a,_=s.tick(241,None);ident=a[0]['request_id']
    a,_=s.tick(242,None,user_stop=True);assert not a and s.pending
    a,_=s.tick(243,None,[dict(request_id=ident,status='completed')]);assert not a and s.terminal and s.reason=='user_stop'
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(60,None);s.tick(240,None);a,_=s.tick(241,None)
    a,_=s.tick(242,None,[dict(request_id=a[0]['request_id'],status='termination_unknown')]);assert not a and s.terminal and s.reason=='request_termination_unknown'

def test_deadline_reserves_cleanup_even_pending():
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(60,None);s.tick(240,None);s.tick(241,None)
    actions,_=s.tick(1080,None);assert s.terminal and actions[0]['kind']=='cancel_client' and s.unknown_requests
    assert s.stopping_at==1080

def test_no_60_second_warmup_rule_bypass(monkeypatch):
    monkeypatch.setattr(pilot,'readiness',lambda *a,**k:dict(start_allowed=False,explicit_stop=False))
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(0,None);s.tick(60,None)
    assert s.terminal and s.submitted==0

def test_counter_guest_iowait_reset_and_online():
    a=dict(counters={'cpu0':[100,10,20,200,20,3,2,0,30,5]},per_core_online={'cpu0':True},read_start_mono_s=1,read_end_mono_s=1.001)
    b=copy.deepcopy(a);b.update(read_start_mono_s=1.2,read_end_mono_s=1.201);b['counters']['cpu0']=[110,10,20,210,20,3,2,0,40,5]
    r=utilization(a,b);assert r['mean_percent']==50 and r['max_percent']==50
    b['counters']['cpu0'][4]=19;assert utilization(a,b)['mean_percent'] is None
    b['per_core_online']['cpu0']=False;assert utilization(a,b)['mean_percent'] is None

def test_causality_missing_stale_unknown_clocks_not_zero():
    row=dict(field='gpu_percent',value=80,valid=True,observed_window_end_s=8,available_at_s=9,decision_generated_s=9.1,clock_domain='N305')
    rows=[row,dict(row,field='cpu_max_percent',value=90,available_at_s=11,decision_generated_s=11),dict(row,field='cpu_mean_percent',clock_domain=None),dict(row,field='vdd_gpu_W',observed_window_end_s=1)]
    x=causal_inputs(rows,10,'N305');assert x['INPUT-BASE']['gpu_percent']==row
    assert x['INPUT-CORE']['cpu_max_percent'] is None and x['INPUT-MEAN']['cpu_mean_percent'] is None and x['INPUT-BASE']['vdd_gpu_W'] is None
    x2=causal_inputs(rows+[dict(row,available_at_s=99,decision_generated_s=99)],10,'N305');assert x==x2
    assert x['deployable'] is False

def test_no_video_or_yet_dependency_and_single_thermal_history():
    p=json.loads((Path(pilot.__file__).with_name('plans')/'cpu-pilot.json').read_text())
    assert p['jtop_video_required']==p['YET_required']==False and p['single_run_and_single_thermal_history']
    assert p['existing_run_is_development']=='5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3'

def test_grants_are_specific_and_not_model_green(tmp_path):
    from tto.config import load_config
    from tto_field.cpu_cli import preview
    from tto_field.cpu_pilot import verify_pilot_grant
    c=load_config(environ={})
    for k in ('orin','tianshan'):c[k]['base_url']='http://127.0.0.1:9'
    b=preview(c,'capability');b.update(command_id='SYNTHETIC',synthetic_loopback_only=True,sidecar=dict(query_target_s=.2,argv=[]))
    b['authorization'].update(command_id='SYNTHETIC',explicit_user_start=True,evidence='LOCAL TEST')
    with pytest.raises(ValueError):verify_pilot_grant(c,copy.deepcopy(b),'diagnose',61)
    bad=copy.deepcopy(b);bad['authorization']['explicit_user_start']=False
    with pytest.raises(ValueError):verify_pilot_grant(c,bad,'diagnose',60)
    bad=copy.deepcopy(b);bad['profile_sha256']='wrong'
    with pytest.raises(ValueError):verify_pilot_grant(c,bad,'diagnose',60)
    verify_pilot_grant(c,b,'diagnose',60);assert b['cpu_pilot_verified']
    with pytest.raises(ValueError):verify_pilot_grant(c,b,'diagnose',60)

def test_source_missing_clock_or_regressed_sequence_is_preserved():
    import asyncio
    from tto_field.cpu_transport import Sidecar
    class Clock:
        domain='SYNTHETIC-RECEIVER'
        def now(self):return 31
    class Ev:
        def __init__(self):self.rows=[]
        def append(self,*a):self.rows.append(a)
    class Pipe:run_id='SYNTHETIC';fan_success_times=[]
    class Process:
        returncode=0
        def __init__(self,rows):
            self.stdout=asyncio.StreamReader()
            for row in rows:self.stdout.feed_data((json.dumps(row)+'\n').encode())
            self.stdout.feed_eof()
    row=dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host='FAKE',boot_id='FAKE',source_session='FAKE',clock=None,command_id='C'),seq=1,resources={})
    async def check(rows,expected):
        ev=Ev();s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipe(),ev);s.process=Process(rows);s.started=30
        await s.receive();assert s.status==expected;assert any(x[0]=='sidecar-events.jsonl' for x in ev.rows)
    asyncio.run(check([row],'source_invalid'))
    row['identity']['clock']='CLOCK_MONOTONIC';row['resources']=dict(elapsed_s=1,read_duration_s=.0001,rss_bytes=100,cpu_seconds=.0001)
    asyncio.run(check([row,row],'source_invalid'))

def test_stale_transport_and_budget_stop_only_sidecar():
    import asyncio
    from tto_field.cpu_transport import Sidecar
    class Clock:
        domain='SYNTHETIC'
        def now(self):return 36
    class Ev:
        def append(self,*a):pass
    class Pipe:run_id='SYNTHETIC';fan_success_times=[]
    class Process:
        returncode=None
        terminated=False
        def terminate(self):self.terminated=True
    async def test():
        s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipe(),Ev());s.started=30;s.process=Process();s.owned=[('source_start',s.process)];s.last_arrival=30;s.startup_task=asyncio.create_task(asyncio.sleep(10))
        s.status='running';s.source_started=30
        s.reader=asyncio.create_task(asyncio.sleep(10))
        await s.tick(36,None);assert s.closed and s.status=='source_stale_or_blocked' and s.process.terminated
        s.reader.cancel();await asyncio.gather(s.reader,return_exceptions=True)
        s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipe(),Ev());s.process=Process();s.owned=[('source_start',s.process)]
        await s.resource(9,100);assert s.closed and s.process.terminated and s.status=='receiver_total_resource_budget_exceeded'
    asyncio.run(test())

def test_existing_mux_command_and_identity_bootstrap_are_real(tmp_path,monkeypatch):
    import asyncio,socket,sys,hashlib,shlex,subprocess
    from tto_field.cpu_transport import Sidecar
    import tempfile
    short=tempfile.TemporaryDirectory(prefix='cpu-mux-',dir='/private/tmp');mux=Path(short.name)/'mux'
    sock=socket.socket(socket.AF_UNIX);sock.bind(str(mux))
    fake=tmp_path/'source.py';fake.write_text("print('SYNTHETIC BOOTSTRAP OK')\n")
    config=tmp_path/'source.json';config.write_text('{}');permit=tmp_path/'permission.json';permit.write_text('{"command_id":"C"}')
    h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    calls=[]
    class Clock:
        domain='FAKE'
        def now(self):return 30
    class Ev:
        def append(self,*a):pass
    class Pipe:run_id='FAKE';fan_success_times=[]
    class Process:
        returncode=0
        def __init__(self):
            self.stdout=asyncio.StreamReader();self.stdout.feed_eof();self.stderr=asyncio.StreamReader();self.stderr.feed_eof()
        async def wait(self):return 0
    async def spawn(*args,**kwargs):calls.append(args);return Process()
    monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
    s=Sidecar(dict(transport='existing_ssh_mux',host='rm01@10.10.99.98',existing_control_socket=str(mux),remote_python=sys.executable,
        remote_source_script=str(fake),source_script_sha256=h(fake),remote_source_config=str(config),source_config_sha256=h(config),
        remote_source_permission=str(permit),command_id='C'),tmp_path,Clock(),Pipe(),Ev())
    async def check():
        await s.tick(30,None);await s.startup_task;await asyncio.sleep(0);await s.close()
    asyncio.run(check());sock.close();short.cleanup()
    assert calls[0][:5]==('ssh','-S',str(mux),'-O','check') and 'ProxyCommand=false' in calls[1]
    remote=shlex.split(calls[1][-1]);r=subprocess.run(remote,capture_output=True,text=True,check=True);assert 'SYNTHETIC BOOTSTRAP OK' in r.stdout
    remote[4]='wrong-script-hash';r=subprocess.run(remote,capture_output=True,text=True);assert r.returncode and 'source SHA' in r.stderr

def test_original_four_slot_capacity_can_supply_one_pilot_client(tmp_path):
    from tto.config import load_config
    from tto_field.cpu_cli import preview
    from tto_field.cpu_pilot import verify_pilot_grant,sidecar_identity
    from tto_field.support import digest_file
    from tto_field.runtime import ROOT,ACTOR
    c=load_config(environ={});b=preview(c,'execute');b.update(command_id='OFFLINE-FAKE',request_actor_thread=ACTOR)
    b['authorization'].update(command_id='OFFLINE-FAKE',explicit_user_start=True,evidence='UNIT VALIDATION ONLY, NO IO')
    original=json.loads((ROOT/'plans/model-profiles.json').read_text())['existing-dense-27b-confirm-before-live']
    b['inference']=dict(model='RM-01 VLM',max_tokens=256,request_timeout_s=30,stream=True,messages=original['payload']['messages'],sampling=original['sampling'],identity_evidence='SYNTHETIC',confirmed_client_slots=4)
    side=dict(query_target_s=.2,transport='existing_ssh_mux',host='rm01@10.10.99.98',existing_control_socket='/tmp/NOT-OPENED',command_id='OFFLINE-FAKE',remote_python='/fake/python',remote_source_script='/fake/source.py',source_script_sha256='fake',remote_source_config='/fake/cfg.json',source_config_sha256='fake',remote_source_permission='/fake/grant.json')
    b['sidecar']=side
    cap=tmp_path/'cap.json';cap.write_text(json.dumps(dict(candidate_version='0.2.4+cpu.2',config_sha256=b['config_sha256'],sidecar_config_sha256=sidecar_identity(side),qualified=True,evaluation_scope='source_potential',measured_resolution_evidence='SYNTHETIC',resource_check_evidence='SYNTHETIC')))
    b['capability_receipt']=dict(path=str(cap),sha256=digest_file(cap));b['capability_user_decision_evidence']='SYNTHETIC UNIT ONLY'
    good=copy.deepcopy(b);verify_pilot_grant(c,good,'execute',60);assert good['cpu_pilot_verified'] and good['inference']['confirmed_client_slots']==4
    b['inference']['confirmed_client_slots']=0
    with pytest.raises(ValueError):verify_pilot_grant(c,b,'execute',60)
