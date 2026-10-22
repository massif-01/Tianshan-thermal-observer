"""Actual 2s header/body timeouts and recovery through the diagnostic entry on owned loopback."""
import asyncio,json,sys
from pathlib import Path
from aiohttp import web
from fake_source import FakeSource
from run_loopback import configuration,binding
from tto_field.runtime import run
from tto_field.support import write

class Timeouts(FakeSource):
 def __init__(self):super().__init__();self.fan_calls=0
 async def status(self,r):
  if r.match_info['kind']=='fan':
   self.fan_calls+=1
   if self.fan_calls==1:await asyncio.sleep(2.3)
   elif self.fan_calls==2:
    response=web.StreamResponse();await response.prepare(r);await response.write(b'{');await asyncio.sleep(2.3)
    try:await response.write(b'}')
    except ConnectionResetError:pass
    return response
  return await super().status(r)
async def main(root):
 root.mkdir()
 async with Timeouts() as service:
  c=configuration(service);b=binding(c,'diagnose',root,'DIAGNOSTIC-REAL-2S-TIMEOUTS')
  credential=root/'synthetic-private-headers.json';write(credential,{'Authorization':'Bearer SYNTHETIC-DONT-LOG'});credential.chmod(0o600)
  c['tianshan']['headers_file']=str(credential);b=binding(c,'diagnose',root,'DIAGNOSTIC-REAL-2S-TIMEOUTS')
  s=await run(c,b,'diagnose',root/'run',duration=9)
  rows=[json.loads(x) for f in (root/'run/native').rglob('observations-*.jsonl') for x in f.read_text().splitlines()]
  errors=[r for r in rows if r['kind']=='fan' and r.get('error_class')]
  phases=[r['poll_diagnostics']['last_phase'] for r in errors]
  assert 'request_headers_sent' in phases and 'response_body' in phases
  assert all(r['error_class']=='TimeoutError' for r in errors)
  assert any(r['kind']=='fan' and not r.get('error_class') for r in rows)
  assert service.posts==0 and s['requester_instances_created']==0 and s['own_async_tasks_remaining']==0
  assert all('SYNTHETIC-DONT-LOG' not in p.read_text() for p in (root/'run').rglob('*.jsonl'))
  write(root/'verification.json',dict(raw_request_budget_s=c['network']['request_timeout_s'],timeout_phases=phases,fan_recovered=True,
       inference_requests=0,credential_not_in_logs=True,temporary_failure_not_root_cause_proof=True))
 print('Real original-2s headers/body timeout stages and recovery passed; no inference')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1])))
