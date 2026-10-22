"""Review-only: actual collect/observe lifecycle with inert fake transports and lock.

Keeps the supplied reconnect_max_attempts=10. Only backoff delay is shortened
to avoid waiting several minutes. No device, SSH, original collector lock, or
59009 listener is touched; a self-owned HTTP endpoint binds numeric loopback:0.
"""
import asyncio
import contextlib
import io
import os
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

BASE = Path(os.environ['TTO_REVIEW_CANDIDATE']).resolve()
OUT = Path(os.environ.get("TTO_REVIEW_OUTPUT", str(Path(__file__).parent)))
OUT.mkdir(parents=True,exist_ok=True)
sys.path[:0] = [str(BASE/'tests')] if os.environ.get('TTO_WEB_TEST_INSTALLED') else [str(BASE/'src'),str(BASE/'vendor'),str(BASE/'tests')]

import aiohttp
from aiohttp import web
import socketio
import psutil
import tto_web.source as web_source
web_source.OBSERVE_RETRY_INITIAL_S=.05
web_source.OBSERVE_RETRY_MAX_S=.05
import tto.collector as collector
from producer import Producer, native_config, web_config
from tto_web.server import app_for
from tto_web.state import State


async def probe(scenario):
    producer = Producer()
    facts = {'scenario': scenario, 'connect_calls': 0, 'successful_connects': 0,
             'source_recovered': False, 'actual_device_network_requests': 0,
             'real_observer_lock_acquired': False,
             'host_metrics': 'actual process sampler; this is not a resource measurement'}

    class Response:
        status = 200
        def __init__(self, payload): self.payload = payload
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def read(self): return json.dumps(self.payload).encode()

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def get(self, url, **kwargs):
            return Response(producer.fan() if '/fan/' in url else producer.temp())

    class Client:
        def __init__(self, *args, **kwargs): self.callbacks = {}; self.drop_task = None; self.connected = False
        def on(self, name, handler, **kwargs): self.callbacks[name] = handler
        async def connect(self, *args, **kwargs):
            facts['connect_calls'] += 1
            if scenario == 'source_unavailable_at_boot' and not facts['source_recovered']:
                raise ConnectionError('SYNTHETIC local transport unavailable')
            self.connected = True
            facts['successful_connects'] += 1
            await self.callbacks['tegrastats_update'](producer.packet(facts['connect_calls']))
            if not facts['source_recovered']:
                async def drop():
                    await asyncio.sleep(.001)
                    await self.disconnect()
                self.drop_task = asyncio.create_task(drop())
        async def disconnect(self):
            if self.connected:
                self.connected = False
                await self.callbacks['disconnect']()
        async def shutdown(self):
            if self.drop_task:
                self.drop_task.cancel()
                await asyncio.gather(self.drop_task, return_exceptions=True)

    class Lock:
        def __enter__(self):
            facts['lock_entries']=facts.get('lock_entries',0)+1
            facts['active_locks']=facts.get('active_locks',0)+1
            facts['peak_active_locks']=max(facts.get('peak_active_locks',0),facts['active_locks'])
        def __exit__(self,*args):facts['active_locks']-=1

    old_session, old_client, old_lock, old_process = collector.sessions, socketio.AsyncClient, collector.InstanceLock, psutil.Process
    collector.sessions = lambda *args, **kwargs: Session()
    socketio.AsyncClient = Client
    collector.InstanceLock = Lock
    try:
        old_process()
    except psutil.NoSuchProcess:
        facts['host_metrics'] = 'stubbed because sandbox PID and procfs views differ; this is not a resource measurement'
        psutil.Process = lambda: SimpleNamespace(cpu_percent=lambda *args:0., cpu_times=lambda:SimpleNamespace(user=0.,system=0.), memory_info=lambda:SimpleNamespace(rss=0))
    try:
        with tempfile.TemporaryDirectory(prefix='observe-recovery-', dir=OUT) as td:
            native = native_config()
            facts['reconnect_max_attempts'] = native['network']['reconnect_max_attempts']
            facts['original_backoff_s'] = {k: native['network'][k] for k in ('reconnect_initial_s', 'reconnect_max_s')}
            native['network'].update(reconnect_initial_s=.001, reconnect_max_s=.001)
            path = Path(td)/'native.json'
            path.write_text(json.dumps(native))
            config = web_config()
            config['source'].update(mode='observe', observation_config=str(path))
            state = State(config)
            app = app_for(config, state=state)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '127.0.0.1', 0)
            await site.start()
            url = 'http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
            try:
                async def wait_ended():
                    while not (facts['connect_calls'] == facts['reconnect_max_attempts'] and '退避' in state.source_status):
                        await asyncio.sleep(.02)
                await asyncio.wait_for(wait_ended(), 5)
                facts['source_status_at_budget'] = state.source_status
                facts['run_at_budget']=state.snapshot()['run_id']
                facts['shared_web_stop_set'] = app['stop'].is_set()
                facts['calls_at_budget'] = facts['connect_calls']
                facts['source_recovered'] = True
                async def recovered():
                    while not (facts['connect_calls']>10 and state.source_connected):await asyncio.sleep(.01)
                await asyncio.wait_for(recovered(),5)
                facts['calls_after_source_recovered'] = facts['connect_calls']
                facts['run_after_recovery']=state.snapshot()['run_id']
                facts['source_connected_flag_after_recovery'] = state.source_connected
                facts['source_run_coroutines_still_active'] = sum('app_for.<locals>.startup.<locals>.source_run' in getattr(t.get_coro(), '__qualname__', '') for t in asyncio.all_tasks())
                async with aiohttp.ClientSession(headers={'Host':'127.0.0.1:59009'}) as client:
                    response = await client.get(url+'/healthz')
                    facts['health_http_status_after_recovery'] = response.status
                    facts['health_after_recovery'] = await response.json()
                    response = await client.get(url+'/api/v1/context')
                    context = await response.json()
                    facts['ui_observation_status_after_recovery'] = context['observation_status']
            finally:
                await runner.cleanup()
                stopped_calls=facts['connect_calls']
                await asyncio.sleep(.15)
                facts['no_revival_after_stop']=facts['connect_calls']==stopped_calls
                facts['source_connected_after_stop']=state.source_connected
                assert facts['peak_active_locks']==1 and facts['active_locks']==0 and facts['lock_entries']==2
                assert facts['run_at_budget']!=facts['run_after_recovery']
                assert facts['calls_at_budget']==10 and not facts['shared_web_stop_set']
                assert facts['calls_after_source_recovered']>10 and facts['source_connected_flag_after_recovery']
                assert facts['no_revival_after_stop'] and not facts['source_connected_after_stop']
    finally:
        collector.sessions, socketio.AsyncClient, collector.InstanceLock, psutil.Process = old_session, old_client, old_lock, old_process
    return facts


async def main():
    return [await probe('source_unavailable_at_boot'), await probe('ten_successful_connections_then_disconnects')]

with contextlib.redirect_stdout(io.StringIO()):
    results = asyncio.run(main())
print(json.dumps(results, ensure_ascii=False, indent=2))
(OUT/'observe_recovery_result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
