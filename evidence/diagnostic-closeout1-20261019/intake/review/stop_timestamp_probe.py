"""Review-only instrumentation of actual installed runner; no candidate changes.
Confirms chronological stop vs legacy Scheduler.now timestamp using own loopback.
"""
import asyncio, json, sys, time
from pathlib import Path
from unittest.mock import patch
SRC=Path('/mnt/data/tto_field_review_20261019/original/source/tests')
sys.path.insert(0,str(SRC))
from fake_source import FakeSource
from run_loopback import configuration,binding,probe
from tto_field import runtime
from tto_field.scheduler import Scheduler
from tto_field.support import write

async def main(root):
 root.mkdir()
 clocks=[]; stops=[]
 OriginalClock=runtime.Clock
 class ReviewClock(OriginalClock):
  def __init__(self): super().__init__();clocks.append(self)
 original_stop=Scheduler.stop
 def observed_stop(self,reason):
  if self.reason is None:
   stops.append({'reason':reason,'actual_observed_mono_s':clocks[0].now(), 'scheduler_cached_mono_s':self.now,'submitted_before_stop':self.submitted})
  return original_stop(self,reason)
 async with FakeSource() as service:
  c=configuration(service);b=binding(c,'execute',root,'REVIEW-COLLECTOR-EXIT-TIMESTAMP')
  import tto.collector
  original_collect=tto.collector.collect
  async def shortened(config,duration,**kw):return await original_collect(config,12.,**kw)
  with patch('tto.collector.collect',shortened),patch('tto_field.runtime.Clock',ReviewClock),patch.object(Scheduler,'stop',observed_stop):
   r=await runtime.run(c,b,'execute',root/'run',probe_profile=probe(20))
 events=[json.loads(x) for x in (root/'run/scheduler-events.jsonl').read_text().splitlines()]
 protocol=[json.loads(x) for x in (root/'run/protocol.jsonl').read_text().splitlines()]
 ix=next(i for i,x in enumerate(events) if x['event']=='stop_new_requests')
 stop_event=events[ix]; actual=stops[0]['actual_observed_mono_s']
 chronological=[e for e in events[ix+1:] if e['event']=='request_submit']
 actual_after=[e for e in protocol if e['event']=='request_submit' and e['submit_mono_s']>=actual]
 false_positive=[e['request_id'] for e in events[:ix] if e['event']=='request_submit' and e['mono_s']>=stop_event['mono_s']]
 out={'candidate_changed':False,'own_loopback_only':True,'reason':r['reason'],'stop_instrumentation':stops,'stop_event':stop_event,'event_order_submissions_after_stop':chronological,'protocol_submissions_after_actual_observed_stop':actual_after,'old_test_false_positive_requests':false_positive,'timestamp_backdate_s':actual-stop_event['mono_s'],'sessions_closed':r['requester_sessions_all_closed'],'tasks_remaining':r['own_async_tasks_remaining']}
 assert not chronological and not actual_after and r['requester_sessions_all_closed'] and r['own_async_tasks_remaining']==0
 write(root/'verification.json',out);print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(main(Path(sys.argv[1])))
