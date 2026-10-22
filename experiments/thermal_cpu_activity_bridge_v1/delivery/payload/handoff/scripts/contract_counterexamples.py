"""Review-only, no source modification. All processes/sockets below are test doubles."""
import asyncio,json,sys,tempfile,socket,time
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
R=Path('/mnt/data/tto_cpu_prep_independent_review_20261020')
sys.path.insert(0,str(R/'work/model'))
from activity import Processor,load_candidate
from tto_field.cpu_interface import causal_inputs
from tto_field.cpu_transport import Sidecar
out={}
# 1. Actual emitted receipt (self-created loopback) does not match new model-side consumer.
a=R/'work/loopback_run/capability/run/cpu-sidecar-arrivals.jsonl'
rows=[json.loads(x) for x in a.read_text().splitlines()]
c,f=load_candidate();processor=Processor(c,f)
answers=[processor.process(row) for row in rows]
out['actual_field_envelope_to_model']={'input_path':str(a),'rows':len(rows),'source_schema':rows[0]['source']['schema'],'field_has_received_at': 'received_at_mono_s' in rows[0], 'field_has_model_arrival_field':'arrival_mono_s' in rows[0], 'model_UNKNOWN_by_variant':{n:sum(x['variants'][n]['activity']['state']=='UNKNOWN' for x in answers) for n in c['variants']},'reasons':sorted(set(x['variants']['INPUT-CORE']['activity']['reason'] for x in answers)), 'scope':'actual candidate field emitter and actual candidate model consumer; loopback-only payload, not field measurements'}
# 2. Newer explicit invalidity must revoke current eligibility, not be skipped in as-of selection.
domain='SYNTHETIC-N305';good=dict(field='cpu_mean_percent',value=42.,valid=True,clock_domain=domain,observed_window_end_s=10.,available_at_s=10.01,decision_generated_s=10.02)
bad=dict(good,value=None,valid=False,observed_window_end_s=10.3,available_at_s=10.31,decision_generated_s=10.32,reason='counter_reset')
view=causal_inputs([good,bad],10.5,domain)
out['latest_invalid_does_not_revoke']={'older_valid':good,'new_invalid':bad,'origin':10.5,'actual_choice':view['INPUT-MEAN']['cpu_mean_percent'],'expected_current_choice':None,'note':'cpu_interface helper currently unused by live runtime, so does not assert unsafe device control; must not be used unchanged in field-to-model adapter'}
# 3. SSH mux precheck wait is inside the only scheduling loop, with no timeout.
class Clock:
 domain='FAKE-N305'
 def now(self):return 30.
class Evidence:
 def __init__(self):self.rows=[]
 def append(self,name,row):self.rows.append([name,row])
class HangingCheck:
 returncode=None
 def __init__(self):self.terminated=False;self.waiting=False
 async def wait(self):self.waiting=True;await asyncio.Future()
 def terminate(self):self.terminated=True
async def mux_case():
 with tempfile.TemporaryDirectory(prefix='tto-rvw-',dir='/tmp') as d:
  sock=socket.socket(socket.AF_UNIX);name=str(Path(d)/'mux');sock.bind(name)
  ev=Evidence();pr=HangingCheck();calls=[]
  async def spawn(*args,**kw):calls.append(list(args));return pr
  s=Sidecar(dict(transport='existing_ssh_mux',existing_control_socket=name,host='TEST_ONLY_NO_SSH'),Path(d),Clock(),SimpleNamespace(fan_success_times=[],run_id='FAKE'),ev)
  timedout=False
  try:
   with patch('asyncio.create_subprocess_exec',spawn):
    try:await asyncio.wait_for(s.tick(30.,None),timeout=.06)
    except asyncio.TimeoutError:timedout=True
   return {'review_timeout_needed':timedout,'commands_intercepted':calls,'check_waiting':pr.waiting,'candidate_owns_check_process':s.process is pr,'candidate_terminated_check':pr.terminated,'candidate_closed':s.closed,'candidate_status':s.status,'events':ev.rows,'note':'review wait_for only; candidate itself has no wait bound. No SSH command was executed.'}
  finally:sock.close()
out['unbounded_mux_startup']=asyncio.run(mux_case())
# 4. Explicit negative source rows are not retained by transport before validation.
async def invalid_row_case():
 ev=Evidence();s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),SimpleNamespace(fan_success_times=[],run_id='FAKE'),ev)
 class Process:
  returncode=0
  def __init__(self,row):
   self.stdout=asyncio.StreamReader();self.stdout.feed_data((json.dumps(row)+'\n').encode());self.stdout.feed_eof()
 row=dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host='test',boot_id='test',source_session='test',clock=None,command_id='C'),seq=1,resources={})
 s.process=Process(row);s.started=30.;await s.receive()
 return {'status':s.status,'emitted_events':ev.rows,'raw_invalid_frame_retained':any(x[0]=='cpu-sidecar-arrivals.jsonl' for x in ev.rows),'note':'diagnostic completeness issue only; valid activity input correctly not accepted'}
out['invalid_frame_audit_detail']=asyncio.run(invalid_row_case())
(R/'deliverable/results/contract-counterexamples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
