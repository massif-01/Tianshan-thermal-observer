import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from aiohttp import web
from requester import Requester
from trial import RealClock
from run_midload import execute
from test_schedule import FakeHealth
from tto.config import load_config


async def service(kind='sse',running=0):
    app=web.Application();calls=[];active=0;peak=0
    async def models(r):calls.append(r.path);return web.json_response({'data':[{'id':'RM-01 VLM','root':'synthetic-owned-model'}]})
    async def metrics(r):calls.append(r.path);return web.Response(text=f'vllm:num_requests_running {running}\nvllm:num_requests_waiting 0\n')
    async def request(r):
        nonlocal active,peak
        calls.append(r.path);payload=await r.json();assert payload['max_tokens']==256;assert 'temperature' not in payload and 'top_p' not in payload
        active+=1;peak=max(peak,active)
        try:
            if kind=='timeout':await asyncio.sleep(.2)
            if not payload['stream']:
                reply=web.StreamResponse(headers={'Content-Type':'application/json'});await reply.prepare(r)
                raw=json.dumps({'id':'owned','choices':[{'message':{'content':'owned test'},'finish_reason':'stop'}],'usage':{'completion_tokens':2}}).encode()
                await reply.write(raw[:20]);await asyncio.sleep(.002);await reply.write(raw[20:]);await reply.write_eof();return reply
            response=web.StreamResponse(headers={'Content-Type':'text/event-stream'});await response.prepare(r)
            await response.write(b'data: {"id":"owned","choices":[{"delta":{"content":"test"},"finish_reason":null}]}\n\n')
            await asyncio.sleep(.004)
            await response.write(b'data: {"id":"owned","choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"completion_tokens":2}}\n\n')
            if kind!='eof':await response.write(b'data: [DONE]\n\n')
            await response.write_eof();return response
        except ConnectionResetError:return web.Response()
        finally:active-=1
    app.router.add_get('/v1/models',models);app.router.add_get('/metrics',metrics);app.router.add_post('/v1/chat/completions',request)
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    cfg=dict(base_url=origin,model='RM-01 VLM',messages=[dict(role='user',content='owned synthetic request')],stream=True,headers_file=None,ca_file=None)
    return server,cfg,calls,lambda:peak


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,stream,status',[('sse',True,'completed'),('json',False,'completed'),('eof',True,'termination_unknown'),('timeout',True,'termination_unknown')])
async def test_real_owned_protocol_first_content_DONE_EOF_and_timeout(tmp_path,kind,stream,status):
    server,cfg,calls,peak=await service(kind);cfg['stream']=stream;events=[]
    requester=Requester(cfg,tmp_path,RealClock(),lambda event,**fields:events.append(dict(event=event,**fields)))
    try:
        await requester.open();await requester.check_resident_idle();r=await requester.request('owned-001',timeout_s=.04 if kind=='timeout' else 2)
        assert r['status']==status and calls.count('/v1/chat/completions')==1 and peak()==1
        if status=='completed':assert r['first_content_mono_s'] is not None and r['finish_reason']=='stop'
        else:assert r['server_status']=='unknown'
        if kind=='sse':assert r['done'] and any(e['event']=='protocol_DONE' for e in events)
        assert events[-1]['event']=='request_end'
    finally:await requester.close();await server.cleanup()


@pytest.mark.asyncio
async def test_existing_active_work_blocks_request_without_probe_workload(tmp_path):
    server,cfg,calls,peak=await service(running=1);requester=Requester(cfg,tmp_path,RealClock(),lambda *a,**k:None)
    try:
        await requester.open()
        with pytest.raises(ValueError):await requester.check_resident_idle()
        assert '/v1/chat/completions' not in calls
    finally:await requester.close();await server.cleanup()


@pytest.mark.asyncio
async def test_runner_entry_one_simulated_collector_and_real_loopback_protocol(tmp_path):
    server,inference,calls,peak=await service();c=load_config(environ={})
    c['orin'].update(base_url=inference['base_url'],source_sample_interval_ms=1000,source_interval_evidence='owned synthetic loopback')
    c['tianshan']['base_url']=inference['base_url'];config=tmp_path/'tto.json';config.write_text(json.dumps(c))
    trial=tmp_path/'trial.json';trial.write_text(json.dumps(dict(trial_id='TTO-MIDLOAD-DEV-v1.0',inference=inference)))
    args=SimpleNamespace(tto_config=config,trial_config=trial,output_root=tmp_path/'output',ambient_file=None)
    collector_calls=[]
    async def simulated_collector(c,duration,**kwargs):
        collector_calls.append(kwargs);path=kwargs['data_root']/'synthetic-run';path.mkdir(parents=True)
        (path/'scope.json').write_text('{"simulated":true,"devices":false}\n')
        await kwargs['stop_event'].wait();return path,dict(stop_reason='external_stop')
    phases=[('resident_background','passive',.03),('M20','work',.12),('cooldown_1','passive',.02),('M60','work',.12),('cooldown_2','passive',.02),('M180','work',.12),('final_cooldown','passive',.02)]
    try:
        r=await execute(args,dict(trial_id='TTO-MIDLOAD-DEV-v1.0',inference=inference),collector_factory=simulated_collector,health_factory=FakeHealth,phases=phases,hard_limit_s=5)
        assert r['status']=='completed' and len(collector_calls)==1 and peak()==1
        assert calls.count('/v1/models')==calls.count('/metrics')==1
        out=Path(r['output']);assert (out/'trial-result.zip').exists() and (out/'SHA256.json').exists()
        events=[json.loads(line) for line in (out/'events.jsonl').open()]
        assert any(e['event']=='ambient_snapshot' and e['record']['temperature_c'] is None for e in events)
        assert any(e['event']=='request_end' for e in events)
        assert r['new_model_training']=='not_performed' and r['control_authorization']=='none'
    finally:await server.cleanup()
