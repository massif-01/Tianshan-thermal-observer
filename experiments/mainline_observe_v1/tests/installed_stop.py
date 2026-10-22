"""Actual installed stop/status/history/archive, one owned loopback observation."""
import asyncio,json,socket,sys,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from fake_source import FakeSource
async def main(prefix,out):
    out.mkdir()
    async with FakeSource() as server:
        cfg=out/'config.json';reg=out/'registration.json';grant=out/'grant.json';run=out/'session'
        cfg.write_text(json.dumps(dict(orin=dict(base_url=server.url,source_sample_interval_ms=1000,source_interval_evidence='owned1s'),tianshan=dict(base_url=server.url))))
        reg.write_text(json.dumps(dict(device_id='OWNED-STOP',thermal_config_id='OWNED-STOP',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))))
        base=[str(prefix/'bin/tto-observe')];p=await asyncio.create_subprocess_exec(*base,'preview','--config',str(cfg),'--registration',str(reg),'--duration','300',stdout=asyncio.subprocess.PIPE);raw,_=await p.communicate();assert p.returncode==0
        g=json.loads(raw)['grant_template'];now=datetime.now(timezone.utc);g.update(explicit_user_start=True,evidence='LOCAL STOP TEST ONLY',self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=400)).isoformat());grant.write_text(json.dumps(g))
        with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
            child=await asyncio.create_subprocess_exec(*base,'observe','--config',str(cfg),'--registration',str(reg),'--grant',str(grant),'--duration','300','--output',str(run),'--allow-network','--local-loopback',stdout=stdout,stderr=stderr)
            for _ in range(40):
                await asyncio.sleep(.1)
                if (run/'status.json').exists():break
            assert (run/'status.json').exists()
            p=await asyncio.create_subprocess_exec(*base,'status','--session',str(run),stdout=asyncio.subprocess.PIPE);status,_=await p.communicate();assert json.loads(status)['running']
            import time
            start=time.monotonic();p=await asyncio.create_subprocess_exec(*base,'stop','--session',str(run),stdout=asyncio.subprocess.PIPE);stop,_=await p.communicate();elapsed=time.monotonic()-start
            assert p.returncode==0 and json.loads(stop)['stopped'] and elapsed<10
            await asyncio.wait_for(child.wait(),3);assert child.returncode==0,(out/'stderr.log').read_text()
        p=await asyncio.create_subprocess_exec(*base,'history','--session',str(run),'--last','2',stdout=asyncio.subprocess.PIPE);history,_=await p.communicate();assert isinstance(json.loads(history),list)
        p=await asyncio.create_subprocess_exec(*base,'archive','--session',str(run),'--output',str(out/'session.zip'),stdout=asyncio.subprocess.PIPE);ar,_=await p.communicate();assert p.returncode==0
        summary=json.loads((run/'summary.json').read_text());assert summary['reason']=='SIGTERM' and summary['consumer_stopped'] and summary['Requester_count']==summary['sidecar_count']==server.posts==server.model_gets==0
        receipt=dict(scope='owned loopback, installed CLI only',stop=json.loads(stop),stop_elapsed_s=elapsed,reason=summary['reason'],same_pid=summary['pid'],history_rows=len(json.loads(history)),archive=json.loads(ar),no_inference=True,owned_tasks_closed=True)
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
