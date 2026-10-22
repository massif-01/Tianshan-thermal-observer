"""One approved autonomous window: own observe.2 subprocess plus delegated one-requester Runner."""
import argparse,asyncio,datetime,hashlib,json,os,signal,socket,sys,time,uuid,zipfile,shlex
from pathlib import Path
import psutil
from supervision import read_json,Health,Controls,DiskEvidence,request_admission
from admission import evaluate
ROOT=Path(__file__).resolve().parent
WHEEL_SHA='481a9671148fe40fcc33c2a65bc98c818be3178fe3138c1cd06bc93b3d21b725'
MODEL_SHA='dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0'
SPEC_SHA='2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def file_sha(p,deadline=None):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):
            if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('final_index_deadline')
            h.update(b)
    return h.hexdigest()
def source_sha():
    return digest({p.relative_to(ROOT).as_posix():file_sha(p) for p in sorted(ROOT.rglob('*.py')) if '__pycache__' not in p.parts and 'tests' not in p.relative_to(ROOT).parts and 'fixtures' not in p.relative_to(ROOT).parts})
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
class Clock:
    def __init__(self,origin):self.origin=origin
    def now(self):return time.monotonic()-self.origin
    def utc(self):return utc()
    async def sleep(self,seconds):await asyncio.sleep(seconds)
def validate(c,g,local=False):
    from urllib.parse import urlsplit
    import ipaddress
    plan=read_json(c['plan']);reg=read_json(c['registration']);request=read_json(c['request_config']);observe_grant=read_json(c['observe_grant'])
    plain={k:v for k,v in plan.items() if k!='plan_sha256'}
    if plan['plan_sha256']!=digest(plain):raise ValueError('plan_identity')
    duration=plan['total_elapsed_seconds'];cleanup=c.get('cleanup_seconds',120)
    if not local and (duration!=86400 or plan['health_checkpoint_seconds']!=7200 or cleanup!=120):raise ValueError('field_profile_requires_frozen_24h_plan')
    if not 0<cleanup<duration or duration>86400:raise ValueError('bounded_window')
    for k,v in dict(action='auto-workday',explicit_user_start=True,program_sha256=source_sha(),plan_sha256=plan['plan_sha256'],request_config_sha256=digest(request),observer_wheel_sha256=WHEEL_SHA,device_id=reg['device_id'],thermal_config_id=reg['thermal_config_id'],session_id=reg['session_id']).items():
        if g.get(k)!=v:raise ValueError('load_permission_mismatch:'+k)
    if not g.get('evidence') or g.get('max_duration_s')!=duration:raise ValueError('load_permission_scope')
    a=datetime.datetime.fromisoformat(g['not_before_utc']);b=datetime.datetime.fromisoformat(g['expires_at_utc']);now=datetime.datetime.now(datetime.timezone.utc)
    if a.tzinfo is None or b.tzinfo is None or not a<=now or b<now+datetime.timedelta(seconds=duration):raise ValueError('load_permission_time')
    if reg['observer_host_id']!=socket.gethostname() or reg.get('workload_event_source'):raise ValueError('host_or_duplicate_event_source')
    if observe_grant['session_id']!=reg['session_id'] or observe_grant['action']!='readonly-observe':raise ValueError('separate_read_permission')
    if local:
        if not g.get('self_owned_loopback') or not observe_grant.get('self_owned_loopback'):raise ValueError('owned_loopback_permission')
        obs=read_json(c['observe_config'])
        for url in [request['base_url'],obs['orin']['base_url'],obs['tianshan']['base_url']]:
            if not ipaddress.ip_address(urlsplit(url).hostname).is_loopback:raise ValueError('owned_numeric_loopback_only')
    if request.get('stream') is not True or not request.get('model'):raise ValueError('original_stream_model_contract')
    return plan,reg,request,cleanup

async def command(args,*,timeout,stdout=None):
    p=await asyncio.create_subprocess_exec(*map(str,args),stdout=stdout or asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:
        data,err=await asyncio.wait_for(p.communicate(),timeout)
        return dict(returncode=p.returncode,stdout=data.decode() if data else None,stderr=err.decode() if err else None)
    except asyncio.TimeoutError:
        p.kill();await p.wait();return dict(returncode=p.returncode,error='owned_command_timeout')

async def run(c,g,local=False):
    plan,reg,request,cleanup=validate(c,g,local)
    permission_deadline=time.monotonic()+(datetime.datetime.fromisoformat(g['expires_at_utc'])-datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    prefix=Path(c['observe_prefix']);entry=prefix/'bin/tto-observe';out=Path(c['output']);out.mkdir(mode=0o700)
    if Path(sys.prefix).resolve()!=prefix.resolve():raise ValueError('run_with_the_observe_prefix_interpreter')
    # One program per observer registration, regardless of output-directory spelling.
    ledger=out.parent/'.autoworkday-ledger';ledger.mkdir(exist_ok=True)
    fd=os.open(ledger/reg['session_id'],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    verify=await command([entry,'verify-install',*([] if local else ['--target'])],timeout=10);write(out/'install-identity.json',verify)
    if verify['returncode']!=0:raise ValueError('observe_install_identity_rejected')
    identity_receipt=json.loads(verify['stdout'])
    if identity_receipt['candidate_version']!='0.2.4+observe.2' or identity_receipt['checked_files']!=65:raise ValueError('wrong_observe_candidate')
    from importlib.resources import files as package_files
    if hashlib.sha256(package_files('tto_field').joinpath('candidate-files.json').read_bytes()).hexdigest()!='28680be46280395e4257a4e5beaf07a30b0c4b781797604439cb7bb622eddd84':raise ValueError('unreviewed_observe_manifest')
    from tto_field.observe_runtime import boot_identity
    identity={k:reg[k] for k in ('device_id','thermal_config_id','session_id','observer_host_id')};identity.update(boot_id=boot_identity(),model_sha256=MODEL_SHA,spec_sha256=SPEC_SHA)
    if not identity['boot_id']:raise ValueError('same_boot_clock_unverified')
    ev=DiskEvidence(out);control=Controls(out/'control.json');stop=False;reason='duration';driver_summary=None;error=None;child=None;runner_task=None;origin=None
    for sig in (signal.SIGINT,signal.SIGTERM):asyncio.get_running_loop().add_signal_handler(sig,lambda:setattr(control,'stopped',True))
    write(out/'load-permission.json',g);write(out/'config.json',c);write(out/'plan.json',plan)
    native=out/'observe';duration=plan['total_elapsed_seconds'];wallstart=time.monotonic();deadline=min(permission_deadline,wallstart+duration)
    with (out/'observe.stdout').open('wb') as stdout,(out/'observe.stderr').open('wb') as stderr:
        child=await asyncio.create_subprocess_exec(str(entry),'observe','--config',c['observe_config'],'--registration',c['registration'],'--grant',c['observe_grant'],'--output',str(native),'--duration',str(duration-cleanup),'--allow-network',*(['--local-loopback'] if local else []),stdout=stdout,stderr=stderr)
    try:
        while not (native/'launch.json').exists():
            if child.returncode is not None or time.monotonic()-wallstart>10:raise ValueError('observer_start_failed')
            await asyncio.sleep(.1)
        launch=read_json(native/'launch.json');origin=launch['clock_start']['mono_before_s'];clock=Clock(origin);health=Health(identity,plan['health_checkpoint_seconds']);created=psutil.Process(child.pid).create_time()
        if launch['process_created']!=created:raise ValueError('child_process_identity')
        deadline=min(origin+duration,permission_deadline);gate=dict(action='pause',reasons=['starting']);health.load_stop=None
        sys.path.insert(0,str(ROOT/'executor'))
        from executor.runner import Runner,Control
        from executor.vendor.requester import Requester
        binding=dict(observer_session_id=reg['session_id'],native_run_id=None,device_id=reg['device_id'],config_sha256=launch['config_sha256'],clock_domain='observer-relative:'+reg['session_id'])
        # Wait for the true UUID; never fill a guessed native identity or use a prior run.
        while not binding['native_run_id']:
            if child.returncode is not None or clock.now()>10:raise ValueError('native_binding_unavailable')
            if (native/'status.json').exists():binding['native_run_id']=read_json(native/'status.json').get('native_run_id')
            await asyncio.sleep(.1)
        write(out/'run-binding.json',dict(binding,identity=identity,clock_origin_mono_s=origin,observer_directory=str(native),plan_sha256=plan['plan_sha256'],event_sink='workload_event.jsonl',source_kind='self_owned_loopback' if local else 'real_device_automatically_constructed_workload'))
        last_gate=None;last_resource=None;previous=None
        def emit(event,row):ev.emit(event,row)
        def admission():
            try:
                st=read_json(native/'status.json');return request_admission(health,launch,st,time.monotonic(),alive=child.returncode is None,created=created)
            except (OSError,ValueError,KeyError,TypeError):return request_admission(health,launch,None,time.monotonic(),alive=child.returncode is None,created=created)
        # Only the delegated requester sends API calls. A once-open resident/idle check is field-only.
        requester=Requester(request,out,clock,lambda *a,**k:None)
        original_open=requester.open
        async def opened():
            await original_open()
            if not local:emit('resident_check',dict(await requester.check_resident_idle(),at_utc=utc(),scope='one_time_startup_not_global_idle_proof_for_24h'))
        requester.open=opened
        runner=Runner(clock,requester,plan,admission,emit,Control(binding=binding,stop=lambda:control.stopped,paused=lambda:control.paused))
        runner_task=asyncio.create_task(runner.run())
        while time.monotonic()<deadline-cleanup and child.returncode is None and not control.stopped:
            try:ctl=control.read();ev.check_disk()
            except Exception as exc:health.load_stop=type(exc).__name__+':'+str(exc)
            now=time.monotonic();t=clock.now()
            try:st=read_json(native/'status.json')
            except (OSError,ValueError):st=None
            try:
                own=psutil.Process();other=psutil.Process(child.pid);a=own.cpu_times();b=other.cpu_times();tot=(a.user+a.system,b.user+b.system);rss=(own.memory_info().rss,other.memory_info().rss)
                rates=(None,None) if previous is None else tuple(100*(tot[i]-previous[1][i])/(now-previous[0]) for i in (0,1));previous=(now,tot)
                sample=dict(own_cpu=rates[0],own_rss=rss[0],total_cpu=sum(rates) if None not in rates else None,total_rss=sum(rss),observer_cpu=rates[1],observer_rss=rss[1])
            except psutil.Error:sample=dict(own_cpu=None,own_rss=None,total_cpu=None,total_rss=None)
            gate,checkpoint=health.update(t,launch,st,now,alive=child.returncode is None,created=created,resource=sample)
            ev.emit('resources',dict(elapsed_s=t,at_utc=utc(),**sample))
            if checkpoint:write(out/'automatic-two-hour-checkpoint.json',checkpoint)
            key=(gate['action'],tuple(gate['reasons']),gate.get('software_healthy'))
            if key!=last_gate:ev.emit('admission',dict(elapsed_s=t,**gate));last_gate=key
            if runner_task.done() and driver_summary is None:
                try:driver_summary=runner_task.result()
                except Exception as exc:driver_summary=dict(reason='driver_error',error=type(exc).__name__+':'+str(exc),completed=False);health.load_stop='driver_error'
                write(out/'driver-summary.json',driver_summary)
            await asyncio.sleep(min(1,max(0,deadline-cleanup-time.monotonic())))
        reason='user_stop' if control.stopped else 'observer_exited' if child.returncode is not None else 'cleanup_boundary'
    except Exception as exc:reason='supervisor_error';error=type(exc).__name__+':'+str(exc)
    finally:
        if runner_task and not control.stopped:health.load_stop='planned_cleanup_boundary' if reason=='cleanup_boundary' else reason
        if runner_task and not runner_task.done():
            try:driver_summary=await asyncio.wait_for(asyncio.shield(runner_task),min(31,max(0,(deadline if origin else min(permission_deadline,wallstart+15))-time.monotonic())))
            except Exception as exc:
                runner_task.cancel();await asyncio.gather(runner_task,return_exceptions=True);driver_summary=dict(reason='bounded_request_cleanup',server_state='unknown',error=type(exc).__name__)
        if child and child.returncode is None:
            child.send_signal(signal.SIGTERM)
            try:await asyncio.wait_for(child.wait(),8)
            except asyncio.TimeoutError:child.kill();await child.wait();error=error or 'observer_forced_cleanup'
        if runner_task and runner_task.done() and driver_summary is None:
            try:driver_summary=runner_task.result()
            except Exception as exc:driver_summary=dict(reason='driver_error',error=type(exc).__name__+':'+str(exc),completed=False)
        if driver_summary and driver_summary.get('reason')=='driver_error':error=error or driver_summary.get('error')
        remaining=max(0,(deadline if origin else min(permission_deadline,wallstart+20))-time.monotonic())
        archive=dict(skipped='observer_summary_unavailable')
        if (native/'summary.json').exists() and remaining>0:
            archive=await command([entry,'archive','--session',native,'--output',out/'observe.zip'],timeout=min(60,remaining))
        ev.close()
        summary=dict(load_result='work_stages_finished' if driver_summary and driver_summary.get('reason') in ('completed','admission_stop:planned_cleanup_boundary') and not driver_summary.get('unknown_server_end') else 'incomplete',reason=reason,error=error,driver=driver_summary,archive=archive,observer_returncode=child.returncode if child else None,elapsed_s=time.monotonic()-origin if origin else None,observer_session_id=reg['session_id'],model_training=False,collector_count=1,request_executor_count=1,field=not local,actual_ending_utc=utc())
        write(out/'summary.json',summary)
        files={}
        try:
            for p in sorted(out.rglob('*')):
                if not p.is_file() or p.name=='files.json' or native in p.parents or p.name=='observe.zip':continue
                files[p.relative_to(out).as_posix()]=dict(bytes=p.stat().st_size,sha256=file_sha(p,deadline if origin else min(permission_deadline,wallstart+20)))
            write(out/'files.json',dict(driver_files=files,observer_index='observe/files.json',observer_archive_receipt=archive))
        except TimeoutError:
            summary['final_index_complete']=False;summary['error']=summary.get('error') or 'final_index_deadline';write(out/'summary.json',summary)
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('preview','run'):
        q=sub.add_parser(name);q.add_argument('--config',type=Path,required=True)
        if name=='run':q.add_argument('--grant',type=Path,required=True);q.add_argument('--allow-network',action='store_true');q.add_argument('--self-owned-loopback',action='store_true')
    q=sub.add_parser('control');q.add_argument('--output',type=Path,required=True);q.add_argument('action',choices=['pause','resume','stop'])
    q=sub.add_parser('unit');q.add_argument('--config',type=Path,required=True);q.add_argument('--grant',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='control':
        path=a.output/'control.json';seq=read_json(path)['sequence']+1 if path.exists() else 1;tmp=path.with_suffix('.next');write(tmp,dict(sequence=seq,action=a.action,at_utc=utc()));os.replace(tmp,path);return
    if a.command=='unit':
        args=[sys.executable,str(Path(__file__).resolve()),'run','--config',str(a.config.resolve()),'--grant',str(a.grant.resolve()),'--allow-network'];quoted=' '.join('"'+x.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"' for x in args)
        a.output.write_text('[Unit]\nDescription=TTO bounded automatic workday\n[Service]\nType=simple\nExecStart='+quoted+'\nRestart=no\nTimeoutStopSec=45\nKillMode=control-group\nRuntimeMaxSec=86400\n[Install]\nWantedBy=default.target\n');return
    c=read_json(a.config)
    if a.command=='preview':
        reg=read_json(c['registration']);request=read_json(c['request_config']);plan=read_json(c['plan']);write_json=dict(software='TTO-AUTOWORKDAY-INTEGRATION-v1',network_clients_created=0,load_grant_template=dict(action='auto-workday',explicit_user_start=False,evidence=None,program_sha256=source_sha(),plan_sha256=plan['plan_sha256'],request_config_sha256=digest(request),observer_wheel_sha256=WHEEL_SHA,max_duration_s=plan['total_elapsed_seconds'],not_before_utc=None,expires_at_utc=None,**{k:reg[k] for k in ('device_id','thermal_config_id','session_id')}));print(json.dumps(write_json,indent=2));return
    if not a.allow_network:p.error('current permission plus --allow-network required')
    result=asyncio.run(run(c,read_json(a.grant),a.self_owned_loopback));print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if not result['error'] else 2
if __name__=='__main__':raise SystemExit(main())
