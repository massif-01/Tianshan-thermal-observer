"""Own numeric-loopback Socket.IO + ESP status + SSE service. All values SYNTHETIC."""
import asyncio,copy,json,time,uuid
from pathlib import Path
from aiohttp import web
import socketio
from tto_field.support import utc
FIX=Path(__file__).with_name('fixtures')

class FakeSource:
    def __init__(self,scenario='normal'):
        self.scenario=scenario;self.seq=0;self.connections=set();self.posts=0;self.active=0;self.peak=0;self.status_gets=[];self.completions=0
        self.start=None;self.runner=None;self.ticker=None;self.model_gets=0;self.silent=False;self.did_disconnect=False
    def packet(self):
        p=json.loads((FIX/'orin.json').read_text());self.seq+=1
        p['telemetry_meta'].update(sample_seq=self.seq,stream_id=str(uuid.UUID(int=1)),received_at=utc(),sample_age_ms=0.,fresh=True,collector_state='running')
        p['gpu'].update(sampled_at_utc=utc(),age_at_telemetry_receive_ms=0.,device_uuid='SYNTHETIC-GPU')
        p['timestamp']=utc();p['temperature']['tj']=44.3;p['temperature']['gpu']=44.3
        return p
    def payload(self,kind):
        p=json.loads((FIX/(kind+'.json')).read_text())
        if kind=='fan':
            p['data']['fans'][0].update(mode='auto',enabled=True,guard_active=self.scenario=='guard' and self.elapsed()>=18,
                                      fault=False,temp_stale=False,successful_duty=17,duty=17,duty_valid=True,controller_gain=.82)
        else:p['data'].update(manual_mode=False,normalized_valid=True,valid=True,active_source='variable',bound_variable='agx_info.temperature.tj')
        return p
    def elapsed(self):return time.monotonic()-self.start
    async def status(self,r):
        self.status_gets.append(dict(path=r.path,at_s=self.elapsed()));kind=r.match_info['kind']
        if kind=='fan' and self.scenario=='short_gap' and 20<=self.elapsed()<26:return web.Response(status=503)
        return web.json_response(self.payload(kind))
    async def models(self,r):self.model_gets+=1;return web.json_response({'data':[{'id':'SIMULATED-MODEL','root':'SYNTHETIC-ONLY'}]})
    async def metrics(self,r):return web.Response(text=f'vllm:num_requests_running {self.active}\nvllm:num_requests_waiting 0\n')
    async def request(self,r):
        self.posts+=1;idx=self.posts;self.active+=1;self.peak=max(self.peak,self.active)
        payload=await r.json();assert payload['max_tokens']==256 and payload['stream_options']['include_usage']
        response=web.StreamResponse(headers={'Content-Type':'text/event-stream'});await response.prepare(r)
        try:
            await asyncio.sleep(.1)
            await response.write(('data: '+json.dumps({'id':f'SYNTHETIC-{idx}','choices':[{'delta':{'content':'synthetic'},'finish_reason':None}]})+'\n\n').encode())
            await asyncio.sleep(.15)
            if self.scenario=='unknown' and idx==1:return response
            await response.write(('data: '+json.dumps({'id':f'SYNTHETIC-{idx}','choices':[{'delta':{},'finish_reason':'length'}],'usage':{'completion_tokens':256,'prompt_tokens':1,'total_tokens':257}})+'\n\n').encode())
            await response.write(b'data: [DONE]\n\n');self.completions+=1;return response
        except (ConnectionResetError,RuntimeError):return response
        finally:self.active-=1
    async def tick(self):
        while True:
            if self.connections and not self.silent:await self.sio.emit('tegrastats_update',self.packet())
            if self.scenario=='disconnect' and self.elapsed()>=5 and not self.did_disconnect:
                self.did_disconnect=True
                for sid in list(self.connections):await self.sio.disconnect(sid)
            await asyncio.sleep(1.)
    async def __aenter__(self):
        app=web.Application();self.sio=socketio.AsyncServer(async_mode='aiohttp',logger=False,engineio_logger=False);self.sio.attach(app)
        @self.sio.event
        async def connect(sid,environ):self.connections.add(sid)
        @self.sio.event
        async def disconnect(sid,*args):self.connections.discard(sid)
        app.router.add_get('/api/v1/{kind}/status',self.status);app.router.add_get('/v1/models',self.models);app.router.add_get('/metrics',self.metrics);app.router.add_post('/v1/chat/completions',self.request)
        self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]);self.start=time.monotonic();self.ticker=asyncio.create_task(self.tick());return self
    async def __aexit__(self,*args):
        self.ticker.cancel();await asyncio.gather(self.ticker,return_exceptions=True);await self.sio.shutdown();await self.runner.cleanup()
