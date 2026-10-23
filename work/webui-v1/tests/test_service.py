import asyncio
import json
import time
import aiohttp
from aiohttp import web
import pytest
from tto.storage import InstanceLock
from tto_web.server import app_for,configuration
from tto_web.state import State
from tto_web.source import observe,follow,Publication
from tto_web.common import atomic_json
from producer import Producer,FakeSource,web_config,native_config


async def start(app):
    runner=web.AppRunner(app,shutdown_timeout=.2);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    return runner,'http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])


@pytest.mark.asyncio
async def test_actual_observe_collector_quality_observer_http_sse_four_clients(tmp_path):
    async with FakeSource() as source:
        config=web_config();c=native_config(source.url);path=tmp_path/'native.json';atomic_json(path,c)
        config['source'].update(mode='observe',observation_config=str(path))
        state=State(config);stop=asyncio.Event();task=asyncio.create_task(observe(config,state,stop))
        runner,url=await start(app_for(config,start_source=False,state=state))
        try:
            async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
                await asyncio.sleep(3.3)
                # Each browser is only an SSE client. Native request counters remain time-based.
                streams=[await client.get(url+'/api/v1/stream') for _ in range(4)]
                for response in streams:
                    body=await asyncio.wait_for(response.content.readuntil(b'\n\n'),2)
                    assert b'TTO-WEB-SNAPSHOT-v1' in body
                r=await client.get(url+'/api/v1/stream');assert r.status==503;await r.release()
                await asyncio.sleep(3.1)
                snapshot=await (await client.get(url+'/api/v1/snapshot')).json()
                assert snapshot['mode']=='test_replay'
                assert snapshot['run_id'] and any(m['id']=='temperature.tj' and m['value']==44.3 for m in snapshot['metrics'])
                assert source.posts==source.model_gets==0
                assert 6<=source.gets['fan']<=8 and 1<=source.gets['temp']<=2
                assert len(source.connections)==1
                for response in streams:response.close()
                # Invalid new mainboard response withdraws prior successful PWM.
                source.fan_invalid=True;await asyncio.sleep(1.2)
                snapshot=await (await client.get(url+'/api/v1/snapshot')).json()
                assert next(m for m in snapshot['metrics'] if m['id']=='fan.pwm.actual')['value'] is None
                # Shared lock blocks another native collector owner, not just Web routes.
                with pytest.raises(ValueError):
                    with InstanceLock():pass
        finally:
            stop.set();await asyncio.gather(task,return_exceptions=False);await runner.cleanup()
        assert not source.connections
        # Observe's memory journal never creates experiment raw logs.
        assert not list(tmp_path.rglob('observations-*.jsonl'))


@pytest.mark.asyncio
async def test_observe_conflict_leaves_web_available_and_zero_network(tmp_path):
    async with FakeSource() as source:
        config=web_config();path=tmp_path/'native.json';atomic_json(path,native_config(source.url));config['source'].update(mode='observe',observation_config=str(path))
        state=State(config);stop=asyncio.Event()
        with InstanceLock():await observe(config,state,stop)
        assert '冲突' in state.source_status and source.gets=={'fan':0,'temp':0} and not source.connections


@pytest.mark.asyncio
async def test_follow_registration_and_lifecycle_never_owns_producer(publication_dir):
    config=web_config();descriptor=publication_dir/'active.json';config['source']['active_descriptor']=str(descriptor)
    state=State(config);stop=asyncio.Event();p=Producer();
    async with Publication(descriptor) as publication:
        task=asyncio.create_task(follow(config,state,stop))
        publication.put(p.step(0));await asyncio.sleep(.25)
        assert state.snapshot()['run_id']==p.adapter.run_id
        task.cancel();await asyncio.gather(task,return_exceptions=True)
        assert descriptor.exists() and not json.loads(descriptor.read_text())['ended']
        assert publication.server.is_serving()
        publication.put(p.step(.3));await asyncio.sleep(.1)
    assert json.loads(descriptor.read_text())['ended']


@pytest.mark.asyncio
async def test_sse_resync_no_ttl_renewal_and_get_only_routes(monkeypatch):
    config=web_config();state=State(config);p=Producer(time.monotonic()-1);state.accept(p.step(0))
    app=app_for(config,start_source=False,state=state)
    runner,url=await start(app)
    try:
        async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
            prepare=web.StreamResponse.prepare
            async def failed_prepare(response,request):
                if request.path=='/api/v1/stream':raise ConnectionResetError('owned SSE handshake failure')
                return await prepare(response,request)
            with monkeypatch.context() as patch:
                patch.setattr(web.StreamResponse,'prepare',failed_prepare)
                with pytest.raises(aiohttp.ServerDisconnectedError):await client.get(url+'/api/v1/stream')
            assert not app['sse_clients']  # A failed handshake must release the client slot.
            first=await (await client.get(url+'/api/v1/snapshot')).json();sample=next(m for m in first['metrics'] if m['id']=='temperature.tj')
            response=await client.get(url+'/api/v1/stream',headers={'Last-Event-ID':'obsolete:1'})
            firstevent=await asyncio.wait_for(response.content.readuntil(b'\n\n'),2)
            assert b'event: resync' in firstevent
            await asyncio.sleep(.3)
            second=await (await client.get(url+'/api/v1/snapshot')).json();m=next(m for m in second['metrics'] if m['id']=='temperature.tj')
            assert sample['sample_id']==m['sample_id'] and m['remaining_valid_ms']<sample['remaining_valid_ms']
            for method,path in [('POST','snapshot'),('PUT','model'),('DELETE','predictions')]:
                r=await client.request(method,url+'/api/v1/'+path);assert r.status==405
            r=await client.get(url+'/api/v1/snapshot',headers={'Origin':'https://evil.invalid'});assert r.status==403
            r=await client.get(url+'/api/v1/snapshot',headers={'Host':'evil.invalid'});assert r.status==403
            r=await client.get(url+'/api/v1/series?max_points=100000000');assert r.status==400
            response.close()
    finally:await runner.cleanup()


@pytest.mark.asyncio
async def test_waiting_api_and_lan_direct_access():
    config=web_config();config['web'].update(access_mode='lan',allowed_origins=['http://127.0.0.1:59009'])
    runner,url=await start(app_for(config,start_source=False))
    try:
        async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
            response=await client.get(url+'/api/v1/snapshot')
            assert response.status==200 and not response.cookies
            snapshot=await response.json()
            assert snapshot['mode']=='waiting' and not any(m['id'].startswith('temperature.') for m in snapshot['metrics'])
            assert (await client.get(url+'/api/v1/context')).status==200
            assert (await client.get(url+'/api/v1/session')).status==404
    finally:await runner.cleanup()


def test_lan_requires_origin_and_local_requires_loopback(tmp_path):
    config=web_config();config['web'].update(bind='0.0.0.0');path=tmp_path/'config.json';atomic_json(path,config)
    with pytest.raises(ValueError):configuration(path)
    config['web'].update(access_mode='lan');atomic_json(path,config)
    with pytest.raises(ValueError):configuration(path)
    config['web']['allowed_origins']=['http://10.10.99.99:59009'];atomic_json(path,config)
    assert configuration(path)['web']['access_mode']=='lan'


@pytest.mark.asyncio
async def test_quiet_source_expiry_is_prompt_without_rebuilding_every_timer_tick():
    p=Producer(time.monotonic()-12);state=State(web_config())
    for t in range(13):state.accept(p.step(t),now=p.start+t+.001)
    now=time.monotonic();packet=state.packet
    next(m for m in packet['metrics'] if m['id']=='fan.pwm.actual')['_expiry']=now+.35
    packet['consumable_until_mono_s']=now+.35
    state.refresh(now);before=state.seq
    runner,url=await start(app_for(web_config(),start_source=False,state=state))
    try:
        await asyncio.sleep(.58)
        s=state.snapshot()
        assert next(m for m in s['metrics'] if m['id']=='fan.pwm.actual')['value'] is None
        assert s['model']['phase']=='unavailable'
        assert state.seq-before<=3
    finally:await runner.cleanup()


@pytest.mark.asyncio
async def test_registered_task_context_api_does_not_claim_missing_metadata_or_server_completion():
    p=Producer();state=State(web_config());packet=p.step(0)
    packet['task']={'context':dict(task_metadata_available=True,active_requests=2,client_slots=4,planned_slots=4,phase='work',task_model='SYNTHETIC registered model')}
    state.accept(packet)
    runner,url=await start(app_for(web_config(),start_source=False,state=state))
    try:
        async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
            value=await(await client.get(url+'/api/v1/context')).json()
            assert value['task_metadata_available'] and value['active_requests']==2
            assert 'runner登记' in value['task_reason'] and '未接入' not in value['task_reason']
            assert value['server_running'] is None and value['server_queued'] is None
    finally:await runner.cleanup()
