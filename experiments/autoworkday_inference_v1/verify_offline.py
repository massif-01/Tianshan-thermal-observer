"""Run the actual driver and unchanged Requester against owned memory SSE only."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

from make_plan import generate,plan_digest
from runner import Runner,Control
from fixtures.fake_runtime import VirtualClock,make_requester,Journal,BINDING

async def main(out):
    out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    clock=VirtualClock()
    requester=make_requester(out,clock)
    journal=Journal(out)
    driver=Runner(clock,requester,generate(),lambda:dict(action='pause' if clock.now()<7200 else 'allow',reasons=['synthetic_checkpoint_pending'] if clock.now()<7200 else []),journal,Control(BINDING.copy()))
    summary=await driver.run()
    raw=[row for event,row in journal.rows if event=='request_submit']
    normalized=[row for event,row in journal.rows if event=='workload_event']
    assert len(raw)==summary['submissions']==386
    assert summary['protocol_completed']==386 and summary['actual_elapsed_s']==86400
    assert summary['client_inflight_seconds']<=18000
    assert all(7200<=row['submit_mono_s']<=84570 and not 32400<=row['submit_mono_s']<64800 for row in raw)
    assert max(row['client_inflight'] for row in normalized)==1
    assert all(row['gpu_kernel_start'] is None and row['gpu_kernel_end'] is None for row in normalized)
    assert all('planned_submit_s' not in row and 'seed' not in row and 'slots' not in row for row in normalized)
    assert requester.session.closed
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'sample-actual-emit.json').write_text(json.dumps(dict(raw_submit=raw[0],normalized_submit=normalized[0],normalized_end=next(row for row in normalized if row['event']=='request_end')),ensure_ascii=False,indent=2)+'\n')
    receipt=dict(scope='virtual 24h, owned memory SSE through actual unchanged Requester; not real device or elapsed 24h',
                 python=sys.version,executable=sys.executable,platform=platform.platform(),
                 wall_seconds=time.monotonic()-started,virtual_seconds=clock.now(),
                 actual_fixture_submissions=len(raw),normalized_events=len(normalized),
                 max_client_inflight=1,model_queries=0,external_requests=0,
                 collector_instances_created=0,thermal_observer_instances_created=0,
                 requester_instances_created=1,checks_passed=True)
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    asyncio.run(main(p.parse_args().output))
