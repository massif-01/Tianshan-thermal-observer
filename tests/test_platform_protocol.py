"""New contract through actual Socket.IO / HTTP loopback and Journal/report."""
import asyncio
import socketio
from aiohttp import web
from tto.collector import collect
from tto.demo import fan_packet, temp_packet
from tto.dataset import replay
from tto.report import run_report
from tto.util import read_json, file_hash
from test_platform_curve import new_packet


async def test_new_wire_contract_auto_period_curve_record_report(config, tmp_path):
    sio=socketio.AsyncServer(async_mode='aiohttp',ping_interval=.2,ping_timeout=.5)
    app=web.Application();sio.attach(app);requests=[]
    async def fan(request):
        requests.append((request.method,request.path));p=fan_packet(0)
        p['data']['fans'][0]['mode']='curve';p['data']['fans'][0].pop('controller_gain')
        return web.json_response(p)
    async def temp(request):
        requests.append((request.method,request.path));return web.json_response(temp_packet())
    app.router.add_get('/api/v1/fan/status',fan);app.router.add_get('/api/v1/temp/status',temp)
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    origin=f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    config['orin'].update(base_url=origin,source_sample_interval_ms=None,source_interval_evidence=None)
    config['tianshan']['base_url']=origin
    async def emit():
        seq=0
        while True:
            seq+=1;p=new_packet(seq)
            if seq==2:p['gpu'].update(status='error',utilization_pct=None,sampled_at_utc=None,age_at_telemetry_receive_ms=None)
            await sio.emit('tegrastats_update',p)
            await sio.emit('model_status_update',{'private_text':'DO_NOT_RECORD'})
            await asyncio.sleep(1)
    task=asyncio.create_task(emit())
    try:
        run,stats=await collect(config,3.2,data_root=tmp_path/'runs')
        assert stats['stop_reason']=='duration' and all(method=='GET' for method,path in requests)
        result=replay(run);m=result['manifest'];profile=read_json(run/'input-profile.json')
        assert m['record_schema']==2 and m['source_period_ms'] is None
        assert profile['input_contract']['source_period_ms']==1000 and profile['source_period_evidence']['basis']=='wire_telemetry_meta'
        assert result['quality']['new_samples']>=2 and not result['platform_state']['mixed_profiles']
        assert any(r['control_scope']=='curve' and r['control_eligible'] for r in result['rows'])
        before={p.name:file_hash(p) for p in run.iterdir() if p.is_file()}
        report=run_report(run,tmp_path/'report')
        assert report['input_diagnostics']['gpu_unavailable_reasons'].get('gpu_source_error',0)>0
        assert 'DO_NOT_RECORD' not in ''.join(p.read_text() for p in run.glob('*.jsonl'))
        assert before=={p.name:file_hash(p) for p in run.iterdir() if p.is_file()}
    finally:
        task.cancel();await asyncio.gather(task,return_exceptions=True);await sio.shutdown();await runner.cleanup()
        pings=[t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(),'__qualname__','')]
        for pending in pings:pending.cancel()
        await asyncio.gather(*pings,return_exceptions=True)
