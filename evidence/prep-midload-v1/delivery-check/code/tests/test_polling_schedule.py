"""Real collector path with owned loopback services and unchanged 1s/5s cadence."""
import asyncio
import importlib.util
import json
import time
from pathlib import Path
import pytest
import socketio
from aiohttp import web
from tto.collector import collect
from tto.demo import fan_packet,temp_packet
from test_platform_curve import new_packet


async def owned_server(fan_delay=.06,temp_delay=1.8,fan_status=200):
    sio=socketio.AsyncServer(async_mode='aiohttp',ping_interval=.5,ping_timeout=2)
    app=web.Application();sio.attach(app)
    trace=[];active={'fan':0,'temp':0};peak={'fan':0,'temp':0,'total':0}
    def handler(key,delay,status):
        async def get(request):
            active[key]+=1;peak[key]=max(peak[key],active[key]);peak['total']=max(peak['total'],sum(active.values()))
            trace.append(dict(endpoint=key,event='sent',t=time.monotonic()))
            try:
                await asyncio.sleep(delay)
                trace.append(dict(endpoint=key,event='return',t=time.monotonic(),status=status))
                return web.json_response(fan_packet(19) if key=='fan' else temp_packet(),status=status)
            finally:active[key]-=1
        return get
    app.router.add_get('/api/v1/fan/status',handler('fan',fan_delay,fan_status))
    app.router.add_get('/api/v1/temp/status',handler('temp',temp_delay,200))
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    async def emit():
        seq=0
        while True:
            seq+=1
            await sio.emit('tegrastats_update',new_packet(seq))
            await asyncio.sleep(1)
    worker=asyncio.create_task(emit())
    async def close():
        worker.cancel();await asyncio.gather(worker,return_exceptions=True)
        await sio.shutdown();await runner.cleanup()
    return origin,trace,peak,close


def observations(path):
    return [json.loads(line) for p in path.glob('observations-*.jsonl') for line in p.open()]


@pytest.mark.asyncio
async def test_original_counterexample_and_independent_production_schedule(config,tmp_path):
    spec=importlib.util.spec_from_file_location('tto._before_polling',Path(__file__).parent/'fixtures/polling/collector-before.py')
    before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
    result={}
    for name,implementation in [('before',before.collect),('after',collect)]:
        origin,trace,peak,close=await owned_server()
        config['orin']['base_url']=config['tianshan']['base_url']=origin
        try:
            # Include two delayed temp returns even with cold TLS-context startup.
            path,stats=await implementation(config,11.4,data_root=tmp_path/name)
            rows=observations(path);fan=[r for r in rows if r['kind']=='fan' and not r.get('error_class')]
            result[name]=dict(trace=trace,peak=peak,summary=stats,fan_return_times=[r['mono_s'] for r in fan],
                              fan_return_gaps=[b['mono_s']-a['mono_s'] for a,b in zip(fan,fan[1:])])
            if name=='after':
                for key,period in [('fan',1),('temp',5)]:
                    r=[r for r in rows if r['kind']==key]
                    assert all(b['sent_mono_s']-a['sent_mono_s']>=period for a,b in zip(r,r[1:]))
                    assert all(x['planned_mono_s']<=x['sent_mono_s']<=x['received_mono_s']<=x['mono_s'] for x in r)
                assert peak['fan']==peak['temp']==1 and peak['total']==2
                assert stats['polling_health']['end_inflight']==0
        finally:await close()
    (tmp_path/'polling-before-after.json').write_text(json.dumps(result,indent=2)+'\n')
    assert max(result['before']['fan_return_gaps'])>2.4
    assert max(result['after']['fan_return_gaps'])<1.3
    assert len(result['after']['fan_return_times'])>len(result['before']['fan_return_times'])


@pytest.mark.asyncio
async def test_slow_fan_skips_without_overlap_and_temp_independent(config,tmp_path):
    origin,trace,peak,close=await owned_server(fan_delay=1.4,temp_delay=.03)
    config['orin']['base_url']=config['tianshan']['base_url']=origin
    try:
        path,stats=await collect(config,5.4,data_root=tmp_path)
        fan=[r for r in observations(path) if r['kind']=='fan']
        assert len(fan)>=2 and all(b['sent_mono_s']-a['sent_mono_s']>=1 for a,b in zip(fan,fan[1:]))
        assert stats['polling_health']['endpoints']['fan']['skipped']>=2
        assert stats['polling_health']['endpoints']['temp']['http_ok']>=2
        assert peak['fan']==peak['temp']==1
    finally:await close()


@pytest.mark.asyncio
async def test_fan_timeout_keeps_real_errors_and_does_not_block_temp(config,tmp_path):
    origin,trace,peak,close=await owned_server(fan_delay=1.4,temp_delay=.02)
    config['orin']['base_url']=config['tianshan']['base_url']=origin;config['network']['request_timeout_s']=.4
    try:
        path,stats=await collect(config,2.4,data_root=tmp_path)
        rows=observations(path);fan=[r for r in rows if r['kind']=='fan']
        assert fan and all(r.get('error_class') and r['payload']=={} for r in fan)
        assert any(r['kind']=='temp' and not r.get('error_class') for r in rows)
        assert stats['polling_health']['max_total_inflight_observed']<=2
        assert stats['polling_health']['endpoints']['fan']['peak_inflight']==1
    finally:await close()


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[401,403])
async def test_authorization_failure_closes_both_workers(config,tmp_path,status):
    origin,trace,peak,close=await owned_server(fan_delay=.02,temp_delay=1.8,fan_status=status)
    config['orin']['base_url']=config['tianshan']['base_url']=origin
    try:
        path,stats=await collect(config,5,data_root=tmp_path)
        assert stats['stop_reason']=='authorization_failed' and stats['elapsed_s']<2
        assert stats['polling_health']['end_inflight']==0
        assert stats['polling_health']['endpoints']['temp']['cancelled']==1
    finally:await close()


@pytest.mark.asyncio
async def test_external_stop_and_same_stream_callback(config,tmp_path):
    origin,trace,peak,close=await owned_server(fan_delay=.04,temp_delay=1.8)
    config['orin']['base_url']=config['tianshan']['base_url']=origin
    stop=asyncio.Event();seen=[]
    def observer(row,out,engine):seen.append(row['ref'])
    async def finish():await asyncio.sleep(.5);stop.set()
    timer=asyncio.create_task(finish())
    try:
        path,stats=await collect(config,5,data_root=tmp_path,stop_event=stop,on_record=observer)
        assert seen==[r['ref'] for r in observations(path)]
        assert stats['polling_health']['end_inflight']==0 and stats['elapsed_s']<2
    finally:
        await timer;await close()
