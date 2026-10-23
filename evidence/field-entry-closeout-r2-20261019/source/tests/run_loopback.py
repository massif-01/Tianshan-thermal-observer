"""Actual collector/engine/observer/clock/gate/scheduler/Requester, no real endpoint."""
import asyncio,copy,json,sys,time,hashlib
from pathlib import Path
import psutil,numpy,scipy,socketio
from tto.config import load_config,public_config
from tto.storage import source_identity
from tto.util import digest
from tto_field.runtime import run,ROOT,ACTOR
from tto_field.cli import preview
from tto_field.support import write,digest_file
from fake_source import FakeSource

HERE=Path(__file__).resolve().parents[1]

def configuration(service):
    c=load_config(environ={})
    for k in ['orin','tianshan']:c[k]['base_url']=service.url
    c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC own 1s timer')
    return c

def binding(c,mode,root,command):
    b=preview(c,mode);b.update(command_id=command,synthetic_loopback_only=True)
    b['authorization'].update(command_id=command,explicit_user_start=True,evidence='OWN LOOPBACK TEST, never a real device grant')
    if mode=='execute':
        anchor=root/'SYNTHETIC-clock.txt';anchor.write_text('SYNTHETIC CLOCK ANCHOR, NOT INSTRUMENT EVIDENCE')
        b.update(request_actor_thread=ACTOR,instrument=dict(recording=True,probe_fixed=True,clock_start=dict(command_id=command,path=str(anchor),sha256=digest_file(anchor),timezone='UTC',display_resolution_s=1,uncertainty_s=None)),
                 inference=dict(base_url=c['orin']['base_url'],model='SIMULATED-MODEL',messages=[{'role':'user','content':'SYNTHETIC ONLY'}],max_tokens=256,request_timeout_s=30,stream=True,sampling={},headers_file=None,ca_file=None))
    return b

def probe(work=4,background=0):
    return dict(id='INTEGRATION-PLUMBING-PROBE-NOT-FROZEN-EXPERIMENT',stages=[dict(kind='background',seconds=background),dict(kind='work',seconds=work,concurrency=4),dict(kind='final_recovery',seconds=.5)],
                nominal_seconds=background+work+.5,hard_limit_seconds=65,preparation_reserve_seconds=30,drain_per_work_max_seconds=3,cleanup_reserve_seconds=5)

async def check(root,scenario):
    root.mkdir(parents=True)
    async with FakeSource(scenario) as service:
        c=configuration(service);mode='diagnose' if scenario in ['diagnose','disconnect'] else 'execute'
        b=binding(c,mode,root,'LOOPBACK-'+scenario);out=root/'output'
        async def user_stop():
            await asyncio.sleep(18);(out/'STOP').touch()
        stopper=asyncio.create_task(user_stop()) if scenario=='user_stop' else None
        result=await run(c,b,mode,out,duration=12 if scenario=='disconnect' else 9,
                         probe_profile=probe(20,8) if scenario=='short_gap' else probe(12) if scenario in ('guard','user_stop') else probe() if mode=='execute' else None)
        if stopper:stopper.cancel();await asyncio.gather(stopper,return_exceptions=True)
        states=[json.loads(x) for x in (out/'states.jsonl').read_text().splitlines()]
        admissions=[json.loads(x) for x in (out/'admission.jsonl').read_text().splitlines()]
        assert result['own_async_tasks_remaining']==0 and result['native_callbacks']==len(states)
        assert result['native_run_id'] and all(s['native_run_id']==result['native_run_id'] for s in states)
        engine_ids={s['generation_evidence']['native_engine_instance_id'] for s in states};assert len(engine_ids)==1
        if mode=='diagnose':assert service.posts==service.model_gets==result['requester_instances_created']==0
        if scenario=='normal':assert result['reason']=='completed' and service.posts>0
        if scenario=='unknown':assert result['reason']=='request_termination_unknown' and result['server_completion_unknown']
        if scenario=='guard':assert result['reason']=='explicit_protection_or_mode_binding'
        if scenario=='user_stop':assert result['reason']=='user_stop'
        if scenario=='short_gap':
            assert result['reason']=='completed' and result['time_coverage']['work_paused_s']>0
            assert any(s['state']['observer']['available'] and not (s['state']['measurement']['last_successful_pwm'] or {}).get('raw_valid',False) for s in states)
        if scenario=='disconnect':
            boundaries=[s for s in states if s['state']['observer']['reasons'] and any('socketio_disconnected' in str(x) for x in s['state']['observer']['reasons'])]
            assert boundaries and all(s['state']['measurement']['tj'] is None for s in boundaries)
            assert any(s['state']['measurement']['tj'] for s in states if s['clock']['observer_input_mono_s']>boundaries[0]['clock']['observer_input_mono_s'])
        native_manifest=next((out/'native').rglob('manifest.json'));m=json.loads(native_manifest.read_text())
        assert m['source_identity']['sha256']==b['collector_source_sha256']
        originals=[json.loads(x) for p in (out/'native').rglob('observations-*.jsonl') for x in p.read_text().splitlines()]
        fan=[r for r in originals if r['kind']=='fan'];assert fan and all('poll_diagnostics' in r for r in fan)
        receipt=dict(scenario=scenario,summary=result,server_posts=service.posts,server_peak_handler_count=service.peak,
                     actual_collector_engine_ids=list(engine_ids),native_refs_all_same_run=True,diagnostic_fields_all_fan=True)
        write(root/'verification.json',receipt);return receipt

async def main(root,scenarios):
    receipts=[]
    for scenario in scenarios:
        print('START',scenario,flush=True)
        receipts.append(await check(root/scenario,scenario));print('PASS',scenario,flush=True)
    write(root/'summary.json',dict(loopback_only=True,results=receipts))

if __name__=='__main__':
    root=Path(sys.argv[1]);asyncio.run(main(root,sys.argv[2:] or ['diagnose','normal','disconnect','short_gap','guard','user_stop','unknown']))
