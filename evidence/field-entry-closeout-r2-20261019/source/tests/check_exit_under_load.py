import asyncio,json,sys
from pathlib import Path
from unittest.mock import patch
from fake_source import FakeSource
from run_loopback import configuration,binding,probe
from tto_field.runtime import run
from tto_field.support import write

async def main(out):
 out.mkdir()
 async with FakeSource() as server:
  c=configuration(server);b=binding(c,'execute',out,'COLLECTOR-EXIT-WITH-INFLIGHT')
  import tto.collector
  original=tto.collector.collect
  async def limited(config,duration,**kw):return await original(config,12.,**kw)
  with patch('tto.collector.collect',limited):
   r=await run(c,b,'execute',out/'run',probe_profile=probe(20))
  e=[json.loads(x) for x in (out/'run/scheduler-events.jsonl').read_text().splitlines()]
  stopped=next(x['mono_s'] for x in e if x['event']=='stop_new_requests')
  assert not any(x['event']=='request_submit' and x['mono_s']>=stopped for x in e)
  assert server.posts>0 and r['reason'] in ('collector_exited','collector_or_signal_stop')
  assert r['own_async_tasks_remaining']==0 and r['requester_sessions_all_closed'] and r['collector_summary']['polling_health']['end_inflight']==0
  write(out/'verification.json',dict(actual_loopback_requests=server.posts,reason=r['reason'],no_scheduler_submissions_after_stop=True,
        native_poll_inflight_end=0,requester_sessions_all_closed=True,own_async_tasks_remaining=0))
 print('Actual collector exit under loopback load drains and closes; no later submission')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1])))
