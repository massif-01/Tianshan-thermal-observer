"""Installed stop/status/history/archive; optional continuous restart uses the same config."""
import asyncio,json,socket,sys,time,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from fake_source import FakeSource

async def main(prefix,out,continuous=False):
    out.mkdir();receipts=[]
    async with FakeSource() as server:
        cfg=out/'config.json';reg=out/'registration.json';grant=out/'grant.json';output=out/'session'
        cfg.write_text(json.dumps(dict(orin=dict(base_url=server.url,source_sample_interval_ms=1000,source_interval_evidence='owned1s'),tianshan=dict(base_url=server.url))))
        reg.write_text(json.dumps(dict(device_id='OWNED-STOP',thermal_config_id='OWNED-STOP',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))))
        base=[str(prefix/'bin/tto-observe')];duration=[] if continuous else ['--duration','300']
        p=await asyncio.create_subprocess_exec(*base,'preview','--config',str(cfg),'--registration',str(reg),*duration,stdout=asyncio.subprocess.PIPE)
        raw,_=await p.communicate();assert p.returncode==0
        g=json.loads(raw)['grant_template'];now=datetime.now(timezone.utc)
        g.update(explicit_user_start=True,evidence='OWNED LOOPBACK ONLY',self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=400)).isoformat());grant.write_text(json.dumps(g))
        for attempt in range(2 if continuous else 1):
            previous=set(output.glob('*/status.json'))
            with (out/f'stdout-{attempt}.log').open('wb') as stdout,(out/f'stderr-{attempt}.log').open('wb') as stderr:
                child=await asyncio.create_subprocess_exec(*base,'observe','--config',str(cfg),'--registration',str(reg),'--grant',str(grant),*duration,'--output',str(output),'--allow-network','--local-loopback',stdout=stdout,stderr=stderr)
                try:
                    run=output
                    for _ in range(60):
                        await asyncio.sleep(.1)
                        if continuous:
                            new=set(output.glob('*/status.json'))-previous
                            if new:run=next(iter(new)).parent
                        if (run/'status.json').exists():break
                    assert (run/'status.json').exists()
                    p=await asyncio.create_subprocess_exec(*base,'status','--session',str(run),stdout=asyncio.subprocess.PIPE)
                    status,_=await p.communicate();assert json.loads(status)['running']
                    stopping=time.monotonic()
                    p=await asyncio.create_subprocess_exec(*base,'stop','--session',str(run),stdout=asyncio.subprocess.PIPE)
                    stop,_=await p.communicate();assert p.returncode==0 and json.loads(stop)['stopped'] and time.monotonic()-stopping<10
                    await asyncio.wait_for(child.wait(),3);assert child.returncode==0,(out/f'stderr-{attempt}.log').read_text()
                finally:
                    if child.returncode is None:child.terminate();await asyncio.wait_for(child.wait(),10)
            p=await asyncio.create_subprocess_exec(*base,'history','--session',str(run),'--last','2',stdout=asyncio.subprocess.PIPE)
            history,_=await p.communicate();assert p.returncode==0 and isinstance(json.loads(history),list)
            p=await asyncio.create_subprocess_exec(*base,'archive','--session',str(run),'--output',str(out/f'session-{attempt}.zip'),stdout=asyncio.subprocess.PIPE)
            ar,_=await p.communicate();assert p.returncode==0
            summary=json.loads((run/'summary.json').read_text())
            assert summary['reason']=='SIGTERM' and summary['consumer_stopped'] and summary['Requester_count']==summary['sidecar_count']==server.posts==server.model_gets==0
            assert summary['collector_count']==summary['stateful_observer_count']==1
            assert json.loads((run/'thread-policy.json').read_text())['pid']==summary['pid']==child.pid
            if continuous:
                from tto.dataset import replay,RecordContractError
                try:replay(next((run/'native').glob('*/manifest.json')).parent)
                except RecordContractError:pass
                else:raise AssertionError('retained daily history accepted as complete replay')
            receipts.append(dict(session=run.name,native_run_id=summary['native_run_id'],reason=summary['reason'],history_rows=len(json.loads(history)),archive=json.loads(ar)))
        if continuous:
            assert len({r['session'] for r in receipts})==len({r['native_run_id'] for r in receipts})==2
            from tto_field.observe_cli import archive
            assert archive(output/receipts[0]['session'],out/'first-after-restart.zip')['files_verified']==receipts[0]['archive']['files_verified']
            first=output/receipts[0]['session'];day=next((first/'days').iterdir());saved=out/'saved-day'
            day.rename(saved)
            try:
                destination=out/'missing-day.zip'
                p=await asyncio.create_subprocess_exec(*base,'archive','--session',str(first),'--output',str(destination),
                    stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
                _,stderr=await p.communicate()
                assert p.returncode!=0 and b'FileNotFoundError' in stderr and not destination.exists()
                receipts[0]['missing_day_archive_rejected']=True
            finally:saved.rename(day)
    result=dict(scope='actual installed CLI, owned loopback; not N305',continuous=continuous,runs=receipts)
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),'--continuous' in sys.argv))
