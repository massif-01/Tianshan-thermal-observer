"""Bounded loopback fake, no source-device discovery or upstream network."""
import asyncio,json
from aiohttp import web

class FakeService:
    def __init__(self,behavior='normal'):
        self.behavior=behavior;self.running=0;self.peak=0;self.posts=0;self.started=[];self.finished=[];self.runner=None
    async def models(self,r):return web.json_response({'data':[{'id':'SIMULATED-MODEL','root':'synthetic-fixture'}]})
    async def metrics(self,r):return web.Response(text=f'vllm:num_requests_running {self.running}\nvllm:num_requests_waiting 0\n')
    async def request(self,r):
        self.posts+=1;idx=self.posts;self.running+=1;self.peak=max(self.peak,self.running);self.started.append(asyncio.get_running_loop().time())
        payload=await r.json();assert payload['model']=='SIMULATED-MODEL' and payload['max_tokens']==256
        if self.behavior=='http503':
            self.running-=1;return web.Response(status=503,text='synthetic unavailable')
        response=web.StreamResponse(headers={'Content-Type':'text/event-stream'});await response.prepare(r)
        try:
            await asyncio.sleep(.025)
            await response.write(('data: '+json.dumps({'id':f'mock-{idx}','choices':[{'delta':{'content':'test'},'finish_reason':None}]})+'\n\n').encode())
            await asyncio.sleep(.055)
            if self.behavior=='incomplete' and idx==1:return response
            await response.write(('data: '+json.dumps({'id':f'mock-{idx}','choices':[{'delta':{},'finish_reason':'length'}],'usage':{'prompt_tokens':5,'completion_tokens':256,'total_tokens':261}})+'\n\n').encode())
            await response.write(b'data: [DONE]\n\n');return response
        except (ConnectionResetError,RuntimeError):return response
        finally:self.running-=1;self.finished.append(asyncio.get_running_loop().time())
    async def __aenter__(self):
        app=web.Application();app.router.add_get('/v1/models',self.models);app.router.add_get('/metrics',self.metrics);app.router.add_post('/v1/chat/completions',self.request)
        self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]);return self
    async def __aexit__(self,*args):await self.runner.cleanup()
