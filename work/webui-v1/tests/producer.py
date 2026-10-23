"""Synthetic protocol producer used by tests and browser verification, never a fallback."""
import asyncio
import copy
import json
import time
import uuid
from pathlib import Path
from aiohttp import web
import socketio
from tto.config import load_config,public_config
from tto.engine import engine_for
from tto.storage import source_identity
from tto.util import digest
from tto_web.common import utc
from tto_web.adapter import Adapter
FIX=Path(__file__).parent/'fixtures'


def native_config(url='http://127.0.0.1:1'):
    c=load_config(environ={})
    for section in ('orin','tianshan'):c[section]['base_url']=url
    c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC 1Hz producer')
    return c


def web_config():
    return dict(web=dict(port=59009,bind='127.0.0.1',access_mode='local',timezone='Asia/Shanghai'),source=dict(mode='follow',active_descriptor=None,observation_config=None,observed_device='SYNTHETIC-THOR',test_replay=True),advisory=dict(curve_manifest=None))


class Producer:
    def __init__(self, start=None):
        self.start=time.monotonic() if start is None else start
        self.config=native_config();self.seq=0;self.ordinal=0;self.gpu_cache=None
        self.engine=engine_for(self.config,record_schema=2)
        self.manifest=dict(observer_run_id=str(uuid.uuid4()),config=public_config(self.config),config_sha256=digest(public_config(self.config)),source_identity=source_identity())
        self.adapter=Adapter(self.manifest,self.engine,observed_device='SYNTHETIC-THOR',test_replay=True)

    def row(self,kind,seconds,payload=None,**kwargs):
        self.ordinal+=1
        raw=dict(kind=kind,payload=payload,mono_s=self.start+seconds,received_at_utc=utc(),observer_run_id=self.manifest['observer_run_id'],ref=f'{self.manifest["observer_run_id"]}/observation:{self.ordinal}',episode='SYNTHETIC',**kwargs)
        output=self.engine.process(raw)
        return self.adapter.feed(raw,output)

    def packet(self,seconds,*,tj=44.3,gpu_age=0,keep_gpu=False,invalid=False):
        p=json.loads((FIX/'orin.json').read_text());self.seq+=1
        p['telemetry_meta'].update(sample_seq=self.seq,stream_id=str(uuid.UUID(int=1)),received_at=utc(),sample_age_ms=0.,fresh=not invalid,collector_state='running')
        p['temperature']['tj']=tj;p['temperature']['gpu']=tj;p['timestamp']=utc()
        if keep_gpu and self.gpu_cache:p['gpu']=copy.deepcopy(self.gpu_cache);p['gpu']['age_at_telemetry_receive_ms']=gpu_age
        else:p['gpu'].update(sampled_at_utc=utc(),age_at_telemetry_receive_ms=gpu_age,device_uuid='SYNTHETIC-GPU')
        self.gpu_cache=copy.deepcopy(p['gpu'])
        return p

    def fan(self,**kwargs):
        p=json.loads((FIX/'fan.json').read_text());p['data']['fans'][0].update(**kwargs);return p
    def temp(self,**kwargs):
        p=json.loads((FIX/'temp.json').read_text());p['data'].update(**kwargs);return p
    def step(self,seconds,**kwargs):
        self.row('fan',seconds,self.fan())
        if seconds%5==0:self.row('temp',seconds,self.temp())
        return self.row('orin',seconds,self.packet(seconds,**kwargs),connection_epoch=1)


class FakeSource:
    def __init__(self):
        self.producer=Producer();self.connections=set();self.gets={'fan':0,'temp':0};self.posts=0;self.model_gets=0;self.seq=0;self.silent=False;self.fan_invalid=False
    async def __aenter__(self):
        self.sio=socketio.AsyncServer(async_mode='aiohttp',logger=False,engineio_logger=False)
        app=web.Application();self.sio.attach(app)
        @self.sio.event
        async def connect(sid,environ):self.connections.add(sid)
        @self.sio.event
        async def disconnect(sid,*args):self.connections.discard(sid)
        async def status(r):
            kind=r.match_info['kind'];self.gets[kind]+=1
            if self.fan_invalid and kind=='fan':return web.json_response({'code':0,'data':{'fans':[]}})
            return web.json_response(self.producer.fan() if kind=='fan' else self.producer.temp())
        async def forbidden(r):
            if r.method=='POST':self.posts+=1
            else:self.model_gets+=1
            return web.Response(status=500)
        app.router.add_get('/api/v1/{kind}/status',status);app.router.add_route('*','/v1/{tail:.*}',forbidden)
        self.runner=web.AppRunner(app);await self.runner.setup();self.site=web.TCPSite(self.runner,'127.0.0.1',0);await self.site.start()
        self.url='http://127.0.0.1:'+str(self.site._server.sockets[0].getsockname()[1])
        self.ticker=asyncio.create_task(self.tick());return self
    async def tick(self):
        while True:
            if self.connections and not self.silent:
                self.seq+=1;await self.sio.emit('tegrastats_update',self.producer.packet(self.seq))
            await asyncio.sleep(1.)
    async def __aexit__(self,*args):
        self.ticker.cancel();await asyncio.gather(self.ticker,return_exceptions=True)
        await self.sio.shutdown();await self.runner.cleanup()
        pings=[t for t in asyncio.all_tasks() if t is not asyncio.current_task() and getattr(t.get_coro(),'__qualname__','').endswith('AsyncSocket._send_ping')]
        for task in pings:task.cancel()
        await asyncio.gather(*pings,return_exceptions=True)


def seed_predictions(state, packet, origins=None):
    """Synthetic committed ledger protocol fixture; it does not run a predictor."""
    origin=packet['origin_mono_s']
    at=(packet['input_mono_s']-origin)*1000
    origins=[at] if origins is None else origins
    rows=[]
    for t in origins:
        for h,value in ((15,46.),(45,48.),(90,50.)):
            rows.append(dict(prediction_id=f'SYNTHETIC-LEDGER-{t}-{h}',run_id=packet['run_id'],ledger_run_id='SYNTHETIC-RAW-RUN',
                source_epoch=packet['source_epoch'],model_id=packet['model_id'],spec_id=packet['spec_id'],backend_model_id='SYNTHETIC-G2',
                scenario='HOLD',horizon_s=h,origin_elapsed_ms=t,issued_elapsed_ms=t+.01,target_elapsed_ms=t+h*1000,
                input_cutoff_elapsed_ms=t,value_C=value,phase_at_origin='tracking',evidence_mode='test_replay',status='pending',
                observed_C=None,error_C=None,reason_code=None,revision=len(rows)+1))
    page=dict(schema='TTO-PREDICTION-PAGE-v1',boot_id=packet['boot_id'],publisher_id='SYNTHETIC-PUBLISHER',
        origin_mono_s=origin,sync_status='synced',identity={k:packet[k] for k in ('run_id','source_epoch','model_id','spec_id')},ended=False,
        cursor=len(rows),watermark=len(rows),has_more=False,retained_from_mono_s=origin-3600,records=rows,
        forecast=dict(provider='observe-ledger',status='available',stride_s=5,history_window_ms=3600000,
            remaining_valid_ms=2500,consumable_until_mono_s=packet['consumable_until_mono_s'],latest_prediction_ids=[r['prediction_id'] for r in rows[-3:]]))
    state.begin_publication(page['publisher_id']);state.accept_predictions(page,now=packet['input_mono_s']+.01)
    return page
