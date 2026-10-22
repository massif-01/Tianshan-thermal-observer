"""Targeted verification of delivered diagnostics, ONLY a self-owned loopback server.
Does not start collect, Socket.IO, remote APIs or inference.
"""
import asyncio,sys,json,pathlib
from aiohttp import web
ROOT=pathlib.Path(__file__).resolve().parents[1]/'original'
sys.path.insert(0,str(ROOT/'integration/runtime024'))
from tto.collector import sessions
from tto.config import load_config
async def main():
 results=[];mode='normal'
 async def handler(req):
  if mode=='headers':await asyncio.sleep(.16)
  if mode=='body':
   resp=web.StreamResponse();await resp.prepare(req);await resp.write(b'{');await asyncio.sleep(.16)
   try:await resp.write(b'}')
   except (ConnectionResetError,RuntimeError):pass
   return resp
  return web.json_response({'data':{'value':42}})
 app=web.Application();app.router.add_get('/api/v1/fan/status',handler);app.router.add_get('/api/v1/temp/status',handler)
 runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
 origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
 c=load_config(environ={});c['tianshan']['base_url']=origin;c['network']['request_timeout_s']=.07;c['network']['connect_timeout_s']=.07
 try:
  async with sessions(c,'tianshan') as s:
   async def get(diag):
    async with s.get(origin+'/api/v1/fan/status',trace_request_ctx={'poll_diagnostics':diag},headers={'Authorization':'Bearer SELF-OWNED-LOOPBACK-CANARY'}) as response:
     diag['last_phase']='response_body'
     raw=await response.read();diag['response_bytes']=len(raw);return json.loads(raw)
   for case in ['normal','normal','headers','body','normal']:
    mode=case;diag={'last_phase':'before_request','events':[]}
    try:payload=await get(diag);timedout=False
    except TimeoutError:payload=None;timedout=True
    if case=='headers':assert timedout and diag['last_phase']=='request_headers_sent'
    elif case=='body':assert timedout and diag['last_phase']=='response_body'
    else:assert not timedout and payload=={'data':{'value':42}}
    assert 'SELF-OWNED-LOOPBACK-CANARY' not in json.dumps(diag) and origin not in json.dumps(diag)
    results.append({'case':case,'timed_out':timedout,'last_phase':diag['last_phase'],'events':[x['phase'] for x in diag['events']]})
   assert 'connection_reused' in results[1]['events']
 finally:await runner.cleanup()
 out={'requests':len(results),'results':results,'scope':'actual candidate.sessions tracing only; no collect/Socket.IO, no field root cause or firmware verification'}
 pathlib.Path(__file__).with_name('diagnostic-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
asyncio.run(main())
