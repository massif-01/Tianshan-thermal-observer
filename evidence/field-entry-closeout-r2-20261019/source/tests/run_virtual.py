"""Complete frozen fixed-anchors virtual time run through native quality, #8, live adapter, gate, scheduler.
No sockets/Requester/real device. Only waiting and completions are virtual; original plan bytes unchanged.
"""
import copy,datetime,heapq,json,random,sys,time
from pathlib import Path
from unittest.mock import patch
from tto.config import load_config,public_config
from tto.engine import engine_for
from tto.storage import Journal
from tto.util import digest
from tto_field.runtime import Pipeline,profile,ROOT
from tto_field.support import Evidence,write
from tto_field.scheduler import Scheduler
from tto_field.gate import readiness
from fake_source import FakeSource
from run_loopback import binding

out=Path(sys.argv[1]);out.mkdir();ev=Evidence(out);t=[0.]
class Clock:
    origin=0.;domain='SYNTHETIC-virtual-local-monotonic'
    def now(self):return t[0]
    def utc(self):return (datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=t[0])).isoformat()
    def bracket(self):return dict(domain=self.domain,mono_before_s=t[0],mono_after_s=t[0],utc=self.utc(),synthetic=True)
clock=Clock();fake=FakeSource();fake.start=time.monotonic();fake.url='http://127.0.0.1:1'
c=load_config(environ={})
for k in ['orin','tianshan']:c[k]['base_url']=fake.url
c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC full-plan virtual timer')
b=binding(c,'execute',out,'FULL-FROZEN-PLAN-VIRTUAL');b['instrument']['clock_start']['verified_file_sha256']=b['instrument']['clock_start']['sha256']
journal=Journal(c,out/'native',simulated=True,episode=b['command_id'],record_schema=2);engine=engine_for(c,record_schema=2)
pipeline=Pipeline(out,c,b,'execute',clock,ev);q=Scheduler(profile(),dict(max_total_requests=4096,max_request_seconds=60,max_data_unready_seconds=60),journal.run_id,b['command_id'],formal=True)
rng=random.Random(61018010);pending=[];fullplanhash=digest((ROOT/'plans/mix-plan.json').read_text());calls=0
with patch('tto_field.runtime.time.monotonic',lambda:t[0]):
 while not q.terminal:
  kinds=['fan','orin']+(['temp'] if int(t[0])%5==0 else [])
  for kind in kinds:
   payload=fake.packet() if kind=='orin' else fake.payload(kind)
   r=journal.observation(dict(kind=kind,payload=payload,mono_s=t[0],received_at_utc=clock.utc(),connection_epoch=1))
   processed=engine.process(r);journal.processing_output(r,processed);pipeline.on_record(r,processed,engine);calls+=1
  completed=[]
  while pending and pending[0][0]<=t[0]:
   end,ident=heapq.heappop(pending);completed.append(dict(request_id=ident,status='completed',done=True,usage={'completion_tokens':256},finish_reason='length',server_state='SYNTHETIC-protocol-completion',client_end_mono_s=end))
  actions,gate=q.tick(t[0],pipeline.get(),completed)
  ev.append('admission.jsonl',dict(t=t[0],**gate))
  for a in actions:
   assert a['kind']=='submit';heapq.heappush(pending,(t[0]+rng.randint(12,22),a['request_id']))
  t[0]+=1
  assert t[0]<=3600
journal.close(dict(reason='SYNTHETIC-complete',no_real_requests=True))
for e in q.events:ev.append('events.jsonl',e)
for r in q.requests:ev.append('requests.jsonl',r)
ev.close()
assert q.reason=='completed' and q.peak==4 and not q.unknown_requests
assert [e['stage'] for e in q.events if e['event']=='phase_start']==profile()['stages']
assert digest((ROOT/'plans/mix-plan.json').read_text())==fullplanhash
summary=dict(reason=q.reason,elapsed_virtual_s=q.now,virtual_requests=q.submitted,peak_virtual_slots=q.peak,
             native_quality_single_engine=True,native_callbacks=calls,actual_requests=0,plan_bytes_unchanged=True,
             actual_frozen_observer=True,live_adapter_used=True,math_fits=0,all_stages=q.profile['stages'])
write(out/'summary.json',summary);print(json.dumps(summary))
