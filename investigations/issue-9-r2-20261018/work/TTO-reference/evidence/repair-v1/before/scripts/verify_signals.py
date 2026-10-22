#!/usr/bin/env python3
"""Real loopback server + installed CLI + signals to owned child PIDs only."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import socketio
from aiohttp import web
from tto.demo import packet, fan_packet, temp_packet
from tto.config import load_config
from tto.util import write_json, read_json

GUARD = '''import ipaddress,socket
_real=socket.socket.connect
_dns=socket.getaddrinfo
def _ok(host):
 if host in ('localhost',None): return
 try:
  if ipaddress.ip_address(host).is_loopback: return
 except ValueError: pass
 raise RuntimeError('loopback-only offline verification')
def _connect(self,address):
 if self.family in (socket.AF_INET,socket.AF_INET6): _ok(address[0])
 return _real(self,address)
def _resolve(host,*a,**k):
 _ok(host)
 return _dns(host,*a,**k)
socket.socket.connect=_connect
socket.getaddrinfo=_resolve
'''


async def verify(output):
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    sio = socketio.AsyncServer(async_mode='aiohttp', ping_interval=.25, ping_timeout=1)
    app = web.Application(); sio.attach(app)
    requests = []
    async def fan(r):
        requests.append([r.method, r.path])
        return web.json_response(fan_packet())
    async def temp(r):
        requests.append([r.method, r.path])
        return web.json_response(temp_packet())
    app.router.add_get('/api/v1/fan/status', fan)
    app.router.add_get('/api/v1/temp/status', temp)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
    origin = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
    c = load_config(environ={})
    c['orin'].update(base_url=origin, source_sample_interval_ms=1000, source_interval_evidence='loopback_fixture')
    c['tianshan']['base_url'] = origin
    c['storage']['data_root'] = str(out / 'runs')
    write_json(out / 'config.json', c)
    guard_dir = out / 'guard'; guard_dir.mkdir()
    (guard_dir / 'sitecustomize.py').write_text(GUARD)
    env = dict(os.environ, PYTHONPATH=str(guard_dir))
    for k in list(env):
        if k.startswith('TTO_'):
            env.pop(k)
    async def emit():
        seq = 0
        while True:
            seq += 1
            await sio.emit('tegrastats_update', packet(seq, 42))
            await asyncio.sleep(.2)
    emitter = asyncio.create_task(emit())
    results = []
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            cmd = [sys.executable, '-m', 'tto', 'collect', '--config', str(out / 'config.json'), '--duration', '20', '--episode', 'synthetic-signal-check']
            initial_files = set((out / 'runs').glob('run-*/observations-*'))
            p = await asyncio.create_subprocess_exec(*cmd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                # Wait for one real recorded source sample rather than racing imports/startup.
                ready = False
                for _ in range(100):
                    files = [f for f in (out / 'runs').glob('run-*/observations-*') if f not in initial_files]
                    if any('"kind":"orin"' in f.read_text() for f in files):
                        ready = True
                        break
                    if p.returncode is not None:
                        break
                    await asyncio.sleep(.1)
                if not ready:
                    raise RuntimeError('child did not collect a loopback sample')
                duplicate = await asyncio.create_subprocess_exec(*cmd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                duplicate_out, duplicate_err = await asyncio.wait_for(duplicate.communicate(), 8)
                assert duplicate.returncode == 2
                assert '另一个TTO' in duplicate_out.decode()
                sent = time.monotonic()
                p.send_signal(sig)
                p.send_signal(sig)
                stdout, stderr = await asyncio.wait_for(p.communicate(), 8)
                (out / f'{sig.name}.stdout.txt').write_bytes(stdout)
                (out / f'{sig.name}.stderr.txt').write_bytes(stderr)
                assert p.returncode == 0, stderr.decode()
                results.append({'signal': sig.name, 'exit_code': p.returncode, 'duplicate_exit': duplicate.returncode, 'stop_wall_s': time.monotonic() - sent})
            finally:
                if p.returncode is None:
                    p.kill(); await p.wait()
        assert all(method == 'GET' for method, path in requests)
        write_json(out / 'result.json', {'passed': True, 'scope': 'owned_cli_processes_loopback_only', 'results': results, 'esp_requests': requests, 'source_control_calls': 0})
    finally:
        emitter.cancel(); await asyncio.gather(emitter, return_exceptions=True)
        await sio.shutdown(); await runner.cleanup()
        ping_tasks = [t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(), '__qualname__', '')]
        for task in ping_tasks:
            task.cancel()
        await asyncio.gather(*ping_tasks, return_exceptions=True)
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(asyncio.run(verify(a.output)), indent=2))
