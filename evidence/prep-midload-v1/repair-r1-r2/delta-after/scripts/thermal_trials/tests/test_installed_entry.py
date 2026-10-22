"""R2: use the installed operation-card launcher, not an identity helper."""
import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import time
import pytest
import socketio
from aiohttp import web
sys.path.insert(0,str(Path(__file__).parents[3]/'tests'))
from tto.config import load_config
from tto.demo import fan_packet,temp_packet
from test_platform_curve import new_packet


@pytest.fixture
def installed():
    prefix=Path(os.environ['TTO_MIDLOAD_INSTALLED_PREFIX'])
    legacy=Path(os.environ['TTO_MIDLOAD_LEGACY_SOURCE'])
    assert (prefix/'tto-midload').is_file() and (legacy/'tto/__init__.py').is_file()
    assert '0.2.2' in (legacy/'tto/__init__.py').read_text()
    env=dict(os.environ,PYTHONPATH=str(legacy))
    return prefix,legacy,env


async def child(command,env,timeout=20):
    process=await asyncio.create_subprocess_exec(*map(str,command),env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:out,err=await asyncio.wait_for(process.communicate(),timeout)
    finally:
        if process.returncode is None:process.kill();await process.wait()
    return process.returncode,out.decode(),err.decode()


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['--plan','--dry-run'])
async def test_operation_card_preview_isolated_with_real_old_PYTHONPATH(tmp_path,installed,mode):
    prefix,legacy,env=installed;calls=[]
    app=web.Application()
    async def hit(request):calls.append(request.path);return web.Response()
    app.router.add_route('*','/{path:.*}',hit);server=web.AppRunner(app);await server.setup()
    site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    cfg=tmp_path/'trial.json';cfg.write_text(json.dumps(dict(trial_id='TTO-MIDLOAD-DEV-v1.0',inference=dict(base_url=origin,model='owned-fixture',messages=[dict(role='user',content='not sent')],headers_file=str(tmp_path/'must-not-be-read.json')))))
    try:
        code,out,err=await child([prefix/'tto-midload',mode,'--trial-config',cfg,'--tto-config',tmp_path/'absent-tto-config.json'],env)
        result=json.loads(out);assert code==0,(out,err)
        assert result['runtime']['version']=='0.2.4' and result['runtime']['isolated'] and result['runtime']['non_editable']
        assert Path(result['runtime']['import_path']).is_relative_to(prefix/'conda-env')
        assert not result['connected'] and not result['credentials_read'] and not calls
        (tmp_path/'entry-result.json').write_text(json.dumps(dict(returncode=code,preview=result,stderr=err,loopback_calls=calls,legacy_source=str(legacy)),indent=2)+'\n')
    finally:await server.cleanup()


@pytest.mark.asyncio
async def test_old_direct_entry_reports_loaded_version_and_correct_action(tmp_path,installed):
    prefix,legacy,env=installed
    code,out,err=await child([prefix/'conda-env/bin/python',prefix/'thermal_trials/run_midload.py','--plan'],env)
    assert code==2 and '实际导入0.2.2' in err and str(legacy) in err and 'tto-midload' in err
    assert '本地配置不完整或不可用' not in err and not out
    (tmp_path/'wrong-entry-result.json').write_text(json.dumps(dict(returncode=code,stdout=out,stderr=err),ensure_ascii=False,indent=2)+'\n')


@pytest.mark.asyncio
async def test_operation_card_entry_real_owned_collect_loopback_and_operator_stop(tmp_path,installed):
    prefix,legacy,env=installed;calls=[]
    sio=socketio.AsyncServer(async_mode='aiohttp',ping_interval=.1,ping_timeout=1);app=web.Application();sio.attach(app)
    async def fan(request):calls.append(request.path);return web.json_response(fan_packet(19))
    async def temp(request):calls.append(request.path);return web.json_response(temp_packet())
    async def models(request):calls.append(request.path);return web.json_response({'data':[{'id':'owned-fixture'}]})
    async def metrics(request):calls.append(request.path);return web.Response(text='vllm:num_requests_running 0\nvllm:num_requests_waiting 0\n')
    async def inference(request):calls.append(request.path);raise AssertionError('The unchanged 600s passive phase must send no load.')
    app.router.add_get('/api/v1/fan/status',fan);app.router.add_get('/api/v1/temp/status',temp)
    app.router.add_get('/v1/models',models);app.router.add_get('/metrics',metrics);app.router.add_post('/v1/chat/completions',inference)
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    async def emit_source():
        seq=0
        while True:
            seq+=1;await sio.emit('tegrastats_update',new_packet(seq));await asyncio.sleep(1)
    emitter=asyncio.create_task(emit_source())
    c=load_config(environ={});c['orin'].update(base_url=origin,source_sample_interval_ms=1000,source_interval_evidence='owned-loopback-fixture');c['tianshan']['base_url']=origin
    tto=tmp_path/'tto.json';tto.write_text(json.dumps(c));trial=tmp_path/'trial.json'
    trial.write_text(json.dumps(dict(trial_id='TTO-MIDLOAD-DEV-v1.0',inference=dict(base_url=origin,model='owned-fixture',messages=[dict(role='user',content='not sent')],stream=True))))
    command=[prefix/'tto-midload','--live','--trial-config',trial,'--tto-config',tto,'--output-root',tmp_path/'output']
    process=await asyncio.create_subprocess_exec(*map(str,command),env=env,start_new_session=True,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            paths=list((tmp_path/'output').rglob('observations-*.jsonl'))
            if paths and any('"kind":"orin"' in p.read_text() or '"kind": "orin"' in p.read_text() for p in paths):break
            assert process.returncode is None
            await asyncio.sleep(.05)
        else:raise AssertionError('Installed entry did not receive owned WS input within budget.')
        os.killpg(process.pid,signal.SIGINT)
        out,err=await asyncio.wait_for(process.communicate(),15)
        summaries=list((tmp_path/'output').glob('midload-*/summary.json'));assert len(summaries)==1,(out.decode(),err.decode())
        result=json.loads(summaries[0].read_text());folder=summaries[0].parent;identity=json.loads((folder/'identity.json').read_text())
        assert result['status']=='stopped' and result['requests']==0 and (folder/'trial-result.zip').is_file()
        assert identity['tto_version']=='0.2.4' and Path(identity['tto_import_path']).is_relative_to(prefix/'conda-env')
        assert identity['runner_sha256']==__import__('hashlib').sha256((prefix/'thermal_trials/run_midload.py').read_bytes()).hexdigest()
        assert calls.count('/v1/models')==calls.count('/metrics')==1 and '/v1/chat/completions' not in calls
        assert '/api/v1/fan/status' in calls and '/api/v1/temp/status' in calls
        (tmp_path/'installed-loopback-entry.json').write_text(json.dumps(dict(command=[str(x) for x in command],returncode=process.returncode,stdout=out.decode(),stderr=err.decode(),calls=calls,
            identity=identity,summary=result,scope='actual installed operation-card entry; production collector; owned loopback only; passive phase stopped, no inference request'),ensure_ascii=False,indent=2)+'\n')
    finally:
        if process.returncode is None:
            os.killpg(process.pid,signal.SIGTERM);await process.wait()
        emitter.cancel();await asyncio.gather(emitter,return_exceptions=True);await sio.shutdown();await server.cleanup()
        await asyncio.sleep(.15)  # Owned server's already-closing ping task finishes.
