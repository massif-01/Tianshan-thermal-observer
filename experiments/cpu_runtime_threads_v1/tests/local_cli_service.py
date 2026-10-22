"""One real installed CLI capability over owned numeric-loopback. No fake clocks or resource values.
Only locks are namespaced by test-sitecustomize to coexist with another local observer.
Source fixture is synthetic/proc files, not actual Thor. No model API permitted.
"""
import asyncio,json,os,sys,uuid
from pathlib import Path
from fake_source import FakeSource
from tto.config import load_config

async def main(prefix,out):
    out.mkdir(parents=True,exist_ok=False);site=out/'test-site';site.mkdir();locks=out/'private-locks';locks.mkdir()
    (site/'sitecustomize.py').write_text("import tto.storage as s\nfrom pathlib import Path\noriginal=s.InstanceLock\ndef isolated(path=None):\n return original(Path("+repr(str(locks))+ ")/('native.lock' if path is None else Path(path).name))\ns.InstanceLock=isolated\n")
    async with FakeSource() as server:
        c=load_config(environ={})
        for k in ('orin','tianshan'):c[k]['base_url']=server.url
        c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='OWNED SYNTHETIC LOOPBACK, NO FIELD')
        cfg=out/'config.json';cfg.write_text(json.dumps(c));preview=out/'preview.json';env=os.environ.copy();env['PYTHONPATH']=str(site)
        for k in ['OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='8'
        # Actual installed console script supplies preview identities; parent imports no numeric libraries.
        cmd=[str(prefix/'bin/tto-cpu-pilot'),'preview','--mode','capability','--config',str(cfg)]
        proc=await asyncio.create_subprocess_exec(*cmd,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE);data,err=await proc.communicate();assert proc.returncode==0,err.decode();preview.write_bytes(data);b=json.loads(data)
        command='SYNTHETIC-CLI-'+str(uuid.uuid4());b.update(command_id=command,synthetic_loopback_only=True)
        b['authorization'].update(command_id=command,explicit_user_start=True,evidence='LOCAL SELF-OWNED SERVICE TEST ONLY, NO REAL DEVICES')
        b['sidecar']=dict(transport='synthetic',query_target_s=.2,command_id=command,argv=[str(prefix/'bin/python'),str(Path(__file__).with_name('source_fixture.py').resolve()),str(out/'synthetic-proc'),command])
        bind=out/'binding.json';bind.write_text(json.dumps(b));run=out/'run';cmd=[str(prefix/'bin/tto-cpu-pilot'),'capability','--config',str(cfg),'--binding',str(bind),'--output',str(run),'--allow-network']
        with (out/'cli.stdout').open('wb') as stdout,(out/'cli.stderr').open('wb') as stderr:
            proc=await asyncio.create_subprocess_exec(*cmd,env=env,stdout=stdout,stderr=stderr)
            await asyncio.wait_for(proc.wait(),90)
        assert proc.returncode==0,(out/'cli.stderr').read_text();s=json.loads((run/'summary.json').read_text());pol=json.loads((run/'thread-policy.json').read_text());baseline=json.loads((run/'baseline-resource-admission.json').read_text())
        assert pol['verified'] and pol['pid']==s['clock_end']['pid']
        assert s['requester_instances_created']==s['request_executor_instances_created']==0 and s['native_run_directories']==s['observer_instances_created']==1
        assert s['reason']=='diagnostic_duration' and s['own_async_tasks_remaining']==0
        assert server.posts==server.model_gets==0
        receipt=dict(scope='ACTUAL installed CPU3 CLI, owned loopback only; NOT field',returncode=proc.returncode,pid=pol['pid'],numeric_policy_verified=True,baseline=baseline,summary=s,
                     inference_posts=server.posts,model_gets=server.model_gets,lock_namespace='TEST-ONLY sitecustomize; release locks unchanged',real_resources_and_clock=True)
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(baseline=baseline['reason'],sidecar_status=s['sidecar_status'],elapsed_s=s['elapsed_s'],pid=pol['pid']),indent=2))
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
