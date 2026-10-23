import asyncio,json,sys,tempfile,time,unittest
from pathlib import Path
from aiohttp import web
import psutil,socketio  # Warm optional imports before short timed test window.
ROOT=Path(__file__).resolve().parents[1];variant=sys.argv.pop(1);sys.path.insert(0,str(ROOT/('work/runtime-024' if variant=='candidate' else 'sources/candidate-wheel')))
from tto.collector import sessions,collect
DATA=json.loads(next((ROOT/'sources/Y-raw').rglob('manifest.json')).read_text())['config']
ROWS=[json.loads(x) for x in next((ROOT/'sources/Y-raw').rglob('observations-0001.jsonl')).read_text().splitlines()]
PAYLOAD={k:next(x['payload'] for x in ROWS if x['kind']==k and not x.get('error_class')) for k in ['fan','temp']}
RESULT=[]
class Tests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.mode='fast';self.lock=asyncio.Lock();self.generation=0;self.active=0;self.peak=0;self.requests=[]
  async def handler(req):
   self.requests.append(req.path);self.active+=1;self.peak=max(self.peak,self.active)
   try:
    if self.mode=='redirect':raise web.HTTPFound('/api/v1/temp/status')
    if self.mode=='headers' and 'fan' in req.path:await asyncio.sleep(.2)
    if self.mode=='queue':
     async with self.lock:await asyncio.sleep(.14)
    if self.mode=='body' and 'fan' in req.path:
     response=web.StreamResponse();await response.prepare(req);await response.write(b'{');await asyncio.sleep(.2)
     try:await response.write(b'}')
     except (ConnectionResetError,RuntimeError):pass
     return response
    if self.mode=='oversize':return web.Response(body=b'x'*70000)
    self.generation+=1
    if self.mode=='coherent':return web.json_response({'generation':self.generation,'paired':self.generation})
    return web.json_response(PAYLOAD['fan' if 'fan' in req.path else 'temp'])
   finally:self.active-=1
  app=web.Application();app.router.add_get('/api/v1/{endpoint}/status',handler);self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1];self.origin=f'http://127.0.0.1:{port}';self.c=json.loads(json.dumps(DATA));self.c['tianshan']['base_url']=self.origin;self.c['orin']['base_url']=self.origin;self.c['network'].update(request_timeout_s=.07,connect_timeout_s=.07,reconnect_max_attempts=1);self.c['tianshan'].update(fan_poll_interval_s=.1,temp_poll_interval_s=.1)
 async def asyncTearDown(self):await self.runner.cleanup()
 async def get(self,s,key='fan',diag=None):
  async with s.get(self.origin+'/api/v1/'+key+'/status',trace_request_ctx={'poll_diagnostics':diag},headers={'Authorization':'Bearer LOOPBACK-SECRET'}) as r:
   if diag is not None:diag['last_phase']='response_body'
   return await r.read()
 async def test_fast_reuse(self):
  d={'last_phase':'none','events':[]}
  async with sessions(self.c,'tianshan') as s:
   await self.get(s,diag=d);await self.get(s,diag=d)
  if variant=='candidate':self.assertIn('connection_reused',[x['phase'] for x in d['events']])
  self.assertNotIn('LOOPBACK-SECRET',json.dumps(d));self.assertNotIn('127.0.0.1',json.dumps(d))
  RESULT.append({'test':'fast_reuse','trace_events':d['events']})
 async def test_headers_stage(self):
  self.mode='headers';d={'last_phase':'none','events':[]}
  async with sessions(self.c,'tianshan') as s:
   with self.assertRaises(TimeoutError):await self.get(s,diag=d)
   self.mode='fast';await self.get(s,'temp')
  self.assertEqual(d['last_phase'],'request_headers_sent' if variant=='candidate' else 'none');RESULT.append({'test':'headers_timeout','phase':d['last_phase'],'recovery':True})
 async def test_body_stage(self):
  self.mode='body';d={'last_phase':'none','events':[]}
  async with sessions(self.c,'tianshan') as s:
   with self.assertRaises(TimeoutError):await self.get(s,diag=d)
   self.mode='fast';await self.get(s,'temp')
  self.assertEqual(d['last_phase'],'response_body');RESULT.append({'test':'body_timeout','phase':d['last_phase'],'recovery':True})
 async def test_connector_cancel_recovery(self):
  self.mode='body';a={'last_phase':'none','events':[]};b={'last_phase':'none','events':[]}
  async with sessions(self.c,'tianshan') as s:
   first=asyncio.create_task(self.get(s,diag=a));await asyncio.sleep(.02);queued=asyncio.create_task(self.get(s,'temp',b));await asyncio.sleep(.02);queued.cancel();await asyncio.gather(queued,return_exceptions=True);await asyncio.gather(first,return_exceptions=True);self.mode='fast';await self.get(s,'temp')
  if variant=='candidate':self.assertEqual(b['last_phase'],'connector_queue')
  RESULT.append({'test':'connector_queue_cancel_recovery','queued_phase':b['last_phase'],'recovery':True})
 async def test_server_queue(self):
  self.mode='queue';d={'last_phase':'none','events':[]}
  async with sessions(self.c,'tianshan') as a,sessions(self.c,'tianshan') as b:
   r=await asyncio.gather(self.get(a,diag=d),self.get(b,'temp'),return_exceptions=True);self.assertTrue(all(isinstance(x,TimeoutError) for x in r))
  self.assertGreaterEqual(self.peak,2);RESULT.append({'test':'serialized_server_resource','two_requests_timed_out':True,'client_phase':d['last_phase'],'note':'in-memory server lock; not field ESP proof'})
 async def test_limits_and_redirect_recovery(self):
  async with sessions(self.c,'tianshan') as s:
   for mode in ['oversize','redirect']:
    self.mode=mode
    with self.assertRaises(ValueError):await self.get(s)
   self.mode='fast';await self.get(s)
  RESULT.append({'test':'oversize_redirect_recovery','passed':True})
 async def test_concurrent_snapshots(self):
  self.mode='coherent'
  async with sessions(self.c,'tianshan') as a,sessions(self.c,'tianshan') as b:
   for _ in range(5):
    result=await asyncio.gather(self.get(a),self.get(b,'temp'))
    for raw in result:
     d=json.loads(raw);self.assertEqual(d['generation'],d['paired'])
  RESULT.append({'test':'concurrent_host_snapshot_coherence','responses':10,'note':'synthetic immutable response; does not prove firmware atomicity'})
 async def test_real_collector_records(self):
  self.mode='body';seen=[]
  # No real device: both origins use this test's ephemeral 127.0.0.1 server.
  with tempfile.TemporaryDirectory() as tmp:
   path,stats=await collect(self.c,.6,data_root=Path(tmp),on_record=lambda r,o,e:seen.append(r))
   fan=[r for r in seen if r['kind']=='fan'];temp=[r for r in seen if r['kind']=='temp'];self.assertTrue(any(r.get('error_class') for r in fan));self.assertTrue(any(not r.get('error_class') for r in temp))
   if variant=='candidate':
    self.assertTrue(all(r['poll_diagnostics']['last_phase']=='response_body' for r in fan if r.get('error_class')))
   else:self.assertTrue(all('poll_diagnostics' not in r for r in fan))
   self.assertEqual(stats['polling_health']['end_inflight'],0);self.assertLessEqual(stats['polling_health']['max_total_inflight_observed'],2)
   RESULT.append({'test':'real_collector','fan_errors':sum(bool(r.get('error_class')) for r in fan),'temp_success':sum(not r.get('error_class') for r in temp),'diagnostic_fields':variant=='candidate','max_inflight':stats['polling_health']['max_total_inflight_observed']})
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);res=unittest.TextTestRunner(verbosity=2).run(suite);(ROOT/'analysis'/f'{variant}-loopback.json').write_text(json.dumps({'variant':variant,'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'results':RESULT},indent=2)+'\n');sys.exit(not res.wasSuccessful())
