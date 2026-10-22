"""Whole virtual window: real Runner+Requester+event Adapter wired to the new Health gate."""
import asyncio,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'executor'));sys.path.insert(0,str(Path(__file__).parent))
from test_supervision import views,IDENTITY
from supervision import Health,request_admission
from runner import Runner,Control
from fixtures.fake_runtime import VirtualClock,make_requester,Journal

async def main(out):
    out.mkdir();clock=VirtualClock();health=Health(IDENTITY);checkpoints=[];events=Journal()
    def admission():
        t=clock.now();launch,status=views(t);gate,check=health.update(t,launch,status,t,alive=True,created=10)
        if check:checkpoints.append(check)
        return request_admission(health,launch,status,t,alive=True,created=10)
    binding=dict(observer_session_id=IDENTITY['session_id'],native_run_id='synthetic-native',device_id=IDENTITY['device_id'],config_sha256='config',clock_domain='synthetic-virtual-domain')
    requester=make_requester(out,clock,'complete',3)
    driver=Runner(clock,requester,json.loads((HERE/'executor/frozen-plan.json').read_text()),admission,events,Control(binding))
    summary=await driver.run();raw=[x for name,x in events.rows if name=='request_submit'];normalized=[x for name,x in events.rows if name=='workload_event']
    assert summary['reason']=='completed' and clock.now()==86400 and len(checkpoints)==1 and checkpoints[0]['elapsed_s']==7200
    assert len(raw)<=600 and summary['client_inflight_seconds']<=18000
    assert all(7200<=x['mono_s']<=84570 and not 32400<=x['mono_s']<64800 for x in raw)
    assert all(not any(k in x for k in ('seed','slots','planned_submit_s')) for x in normalized)
    (out/'actual-emits.jsonl').write_text(''.join(json.dumps(dict(event=e,row=x),ensure_ascii=False)+'\n' for e,x in events.rows))
    (out/'receipt.json').write_text(json.dumps(dict(scope=__doc__+' Synthetic measurement fixture, no physical time/temperature claim.',checkpoint=checkpoints,summary=summary,stage_counts={s['id']:sum(x['stage_id']==s['id'] for x in raw) for s in driver.plan['stages']},single_requester=True,second_collector=False,predictor_received_future_schedule=False,human_required=False),indent=2)+'\n')
    print('joint virtual checkpoint + all stages + actual requester events passed')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve()))
