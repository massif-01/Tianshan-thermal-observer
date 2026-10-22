"""Real supervisor CLI, frozen 24h plan, user STOP during background; no time scaling."""
import asyncio,json,sys,socket,time,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
from program import source_sha,digest,WHEEL_SHA
sys.path.insert(0,str(Path(__file__).parent))
from fake_source import FakeSource

async def main(prefix,out):
    out.mkdir();program=HERE/'program.py';py=prefix/'bin/python';entry=prefix/'bin/tto-observe'
    async with FakeSource() as server:
        config=out/'observer-config.json';config.write_text(json.dumps(dict(orin=dict(base_url=server.url,source_sample_interval_ms=1000,source_interval_evidence='owned synthetic source'),tianshan=dict(base_url=server.url))))
        reg=dict(device_id='lifecycle-owned',thermal_config_id='owned-config',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()));registration=out/'registration.json';registration.write_text(json.dumps(reg))
        proc=await asyncio.create_subprocess_exec(str(entry),'preview','--config',str(config),'--registration',str(registration),'--duration','86280',stdout=asyncio.subprocess.PIPE);data,_=await proc.communicate();assert proc.returncode==0
        now=datetime.now(timezone.utc);grant=json.loads(data)['grant_template'];grant.update(explicit_user_start=True,evidence='OWNED LOOPBACK ONLY',self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=86520)).isoformat())
        og=out/'observe-grant.json';og.write_text(json.dumps(grant));req=dict(model='OWNED-MOCK-NOT-QUERIED',stream=True,base_url=server.url,sampling={});request=out/'request.json';request.write_text(json.dumps(req));plan=json.loads((HERE/'executor/frozen-plan.json').read_text())
        run=out/'run';c=dict(observe_prefix=str(prefix),observe_config=str(config),registration=str(registration),observe_grant=str(og),request_config=str(request),plan=str(HERE/'executor/frozen-plan.json'),output=str(run),cleanup_seconds=120);cp=out/'supervisor-config.json';cp.write_text(json.dumps(c))
        g=dict(action='auto-workday',explicit_user_start=True,program_sha256=source_sha(),plan_sha256=plan['plan_sha256'],request_config_sha256=digest(req),observer_wheel_sha256=WHEEL_SHA,evidence='OWNED LOOPBACK ONLY',max_duration_s=86400,self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=86520)).isoformat(),**{k:reg[k] for k in ('device_id','thermal_config_id','session_id')});gp=out/'load-grant.json';gp.write_text(json.dumps(g))
        with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
            p=await asyncio.create_subprocess_exec(str(py),str(program),'run','--config',str(cp),'--grant',str(gp),'--allow-network','--self-owned-loopback',stdout=stdout,stderr=stderr)
            try:
                start=time.monotonic()
                while time.monotonic()-start<13:
                    assert p.returncode is None,(out/'stderr').read_text()
                    await asyncio.sleep(.2)
                control=await asyncio.create_subprocess_exec(str(py),str(program),'control','--output',str(run),'stop');assert await control.wait()==0
                await asyncio.wait_for(p.wait(),20)
            except BaseException:
                if p.returncode is None:p.kill();await p.wait()
                raise
        assert p.returncode==0,(out/'stderr').read_text()
        s=json.loads((run/'summary.json').read_text());assert s['reason']=='user_stop' and s['archive']['returncode']==0 and s['driver']['submissions']==0
        assert server.posts==server.model_gets==0
        assert len(list((run/'observe/native').glob('*/manifest.json')))==1
        index=json.loads((run/'files.json').read_text());assert index['observer_index']=='observe/files.json'
        (out/'receipt.json').write_text(json.dumps(dict(scope=__doc__,summary=s,requests=server.posts,model_queries=server.model_gets,one_native_run=True,original_wheel_unchanged=True,independent_read_and_load_grants=True,no_interactive_confirmation=True),indent=2)+'\n')
    print('supervisor actual CLI / one observe / controls / STOP / archive passed')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
