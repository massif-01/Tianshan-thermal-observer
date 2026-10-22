"""Real native collector/observer/Requester over self-owned loopback; test-only shortened waiting profile."""
import asyncio,json,sys,copy,uuid
from pathlib import Path
from fake_source import FakeSource
from tto.config import load_config
from tto_field.cpu_cli import preview
from tto_field.cpu_pilot import pilot_profile,PilotScheduler
from tto_field.runtime import run
from tto_field import cpu_pilot
from tto_field.support import write

async def check(root,scenario):
    root.mkdir(parents=True)
    async with FakeSource('unknown' if scenario=='unknown' else 'normal') as service:
        c=load_config(environ={})
        for k in ('orin','tianshan'):c[k]['base_url']=service.url
        c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC own 1s timer')
        mode='diagnose' if scenario=='capability' else 'execute';b=preview(c,'capability' if mode=='diagnose' else 'execute');command='SYNTHETIC-'+str(uuid.uuid4())
        b.update(command_id=command,synthetic_loopback_only=True,request_actor_thread='01a1331a-f937-7d91-aef0-ac4f5e50bd8a')
        b['authorization'].update(command_id=command,explicit_user_start=True,evidence='LOCAL OWN FAKE SERVICES ONLY')
        b['inference']=dict(base_url=service.url,model='SIMULATED-MODEL',max_tokens=256,request_timeout_s=30,stream=True,messages=[dict(role='user',content='SYNTHETIC')],sampling={})
        b['sidecar']=dict(query_target_s=.2,command_id=command,argv=[sys.executable,str(Path(__file__).with_name('fake_sidecar.py')),command])
        if scenario=='missing':b['sidecar']['argv']=[]
        out=root/'run'
        # No live override exists: shorten in this test interpreter only, after validating original plan hash.
        original=cpu_pilot.pilot_profile
        def short():
            p=pilot_profile();p['preparation_reserve_seconds']=32;p['hard_limit_seconds']=90;p['cleanup_reserve_seconds']=5
            for s in p['stages']:s['seconds']=.2 if s['kind']!='work' else 30
            return p
        cpu_pilot.pilot_profile=short
        async def stopper():
            await asyncio.sleep(34);(out/'STOP').touch()
        st=asyncio.create_task(stopper()) if scenario=='stop' else None
        try:result=await run(c,b,mode,out,duration=60,cpu_pilot=True)
        finally:
            cpu_pilot.pilot_profile=original
            if st:st.cancel();await asyncio.gather(st,return_exceptions=True)
        assert result['native_run_directories']==1 and result['observer_instances_created']==1 and result['own_async_tasks_remaining']==0
        assert result['request_executor_instances_created']==(mode=='execute') and result['requester_instances_created']==(mode=='execute')
        if scenario=='normal':assert result['successful_requests']==12 and result['schedule_completed'] and service.peak==1
        if scenario=='unknown':assert result['server_completion_unknown'] and service.posts==1 and result['reason']=='request_termination_unknown'
        if scenario=='missing':assert service.posts==0 and result['reason']=='sidecar_unavailable_no_meaningful_pilot'
        if scenario=='stop':assert result['reason']=='user_stop' and service.posts<12
        if scenario=='capability':assert service.posts==service.model_gets==0 and result['protocol_requests']==0
        if scenario!='missing':assert (out/'cpu-sidecar-arrivals.jsonl').exists()
        write(root/'verification.json',dict(scenario=scenario,actual_fake_service_posts=service.posts,peak=service.peak,summary=result,test_only_shortened_waits=True,production_plan_untouched=True))
        print('PASS',scenario,service.posts,flush=True)

async def main():
    root=Path(sys.argv[1])
    for scenario in sys.argv[2:] or ['normal','unknown','missing','stop','capability']:await check(root/scenario,scenario)
if __name__=='__main__':asyncio.run(main())
