import asyncio
import json
from pathlib import Path
import socketio
from aiohttp import web
import pytest
from tto.collector import collect, sessions
from tto.dataset import replay
from tto.demo import packet, fan_packet, temp_packet
from tto.util import read_json


async def make_server():
    sio = socketio.AsyncServer(async_mode='aiohttp', ping_interval=.2, ping_timeout=.5)
    app = web.Application()
    sio.attach(app)
    requests = []
    async def get_fan(request):
        requests.append((request.method, request.path))
        return web.json_response(fan_packet())
    async def get_temp(request):
        requests.append((request.method, request.path))
        return web.json_response(temp_packet())
    app.router.add_get('/api/v1/fan/status', get_fan)
    app.router.add_get('/api/v1/temp/status', get_temp)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return sio, runner, f'http://127.0.0.1:{port}', requests


async def test_actual_socketio_heartbeat_reconnect_readonly(config, tmp_path):
    sio, runner, origin, requests = await make_server()
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    connected = []
    @sio.event
    async def connect(sid, environ):
        connected.append(sid)
    async def emit():
        seq = 0
        while True:
            seq += 1
            await sio.emit('tegrastats_update', packet(seq, 40))
            await sio.emit('model_status_update', {'private_task_text': 'DO_NOT_SAVE'})
            if seq == 8 and connected:
                await sio.disconnect(connected[-1])
            await asyncio.sleep(.1)
    task = asyncio.create_task(emit())
    try:
        path, stats = await collect(config, 3.5, data_root=tmp_path)
        assert len(connected) >= 2
        assert stats['connection_attempts'] >= 2
        assert all(m == 'GET' for m, p in requests)
        text = ''.join(p.read_text() for p in path.glob('*.jsonl'))
        assert 'DO_NOT_SAVE' not in text and 'private_task_text' not in text
        r = replay(path)
        assert r['quality']['new_samples'] > 0
        assert r['quality'].get('boundary_socketio_disconnected', 0) > 0
        assert stats['queue_peak_items'] <= 256
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await sio.shutdown()
        await runner.cleanup()
        ping_tasks = [t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(), '__qualname__', '')]
        for pending in ping_tasks:
            pending.cancel()
        await asyncio.gather(*ping_tasks, return_exceptions=True)


async def test_redirect_and_large_transport_response_blocked(config):
    app = web.Application()
    called = []
    async def redirect(r):
        raise web.HTTPFound('/control')
    async def control(r):
        called.append(True)
        return web.json_response({})
    async def large(r):
        return web.Response(text='x' * 70000)
    app.router.add_get('/api/v1/fan/status', redirect)
    app.router.add_get('/control', control)
    app.router.add_get('/api/v1/temp/status', large)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
    origin = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
    config['tianshan']['base_url'] = origin
    try:
        async with sessions(config, 'tianshan') as s:
            with pytest.raises(ValueError):
                await s.get(origin + '/api/v1/fan/status')
            assert not called
            async with s.get(origin + '/api/v1/temp/status') as r:
                with pytest.raises(ValueError):
                    await r.read()
    finally:
        await runner.cleanup()
        ping_tasks = [t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(), '__qualname__', '')]
        for pending in ping_tasks:
            pending.cancel()
        await asyncio.gather(*ping_tasks, return_exceptions=True)


async def test_explicit_polling_transport(config, tmp_path):
    sio, runner, origin, requests = await make_server()
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    config['orin']['transports'] = ['polling']
    async def emit():
        seq = 0
        while True:
            seq += 1
            await sio.emit('tegrastats_update', packet(seq, 40))
            await asyncio.sleep(.1)
    task = asyncio.create_task(emit())
    try:
        path, stats = await collect(config, 1.3, data_root=tmp_path)
        assert replay(path)['quality']['new_samples'] > 0
        assert stats['connection_attempts'] == 1
    finally:
        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        await sio.shutdown(); await runner.cleanup()
        ping_tasks = [t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(), '__qualname__', '')]
        for t in ping_tasks:
            t.cancel()
        await asyncio.gather(*ping_tasks, return_exceptions=True)


async def test_oversize_socketio_frame_does_not_enter_journal(config, tmp_path):
    sio, runner, origin, requests = await make_server()
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    async def emit():
        while True:
            oversized = packet(1, 40)
            oversized['oversize_marker'] = 'x' * 70000
            await sio.emit('tegrastats_update', oversized)
            await asyncio.sleep(.1)
    task = asyncio.create_task(emit())
    try:
        path, stats = await collect(config, 1.5, data_root=tmp_path)
        assert not replay(path)['quality'].get('new_samples', 0)
        assert 'oversize_marker' not in ''.join(p.read_text() for p in path.glob('observations-*'))
        assert stats['connection_attempts'] <= 10
    finally:
        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        await sio.shutdown(); await runner.cleanup()
        ping_tasks = [t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(), '__qualname__', '')]
        for t in ping_tasks:
            t.cancel()
        await asyncio.gather(*ping_tasks, return_exceptions=True)


async def test_slow_writer_queue_drop_is_preserved_and_bounded(config, tmp_path, monkeypatch):
    import time
    from tto.storage import Journal
    original = Journal.append
    def slow(self, name, row):
        time.sleep(.03)
        return original(self, name, row)
    monkeypatch.setattr(Journal, 'append', slow)
    config['storage']['queue_max_items'] = 1
    sio, runner, origin, requests = await make_server()
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    async def emit():
        seq = 0
        while True:
            seq += 1
            await sio.emit('tegrastats_update', packet(seq, 40))
            await asyncio.sleep(.01)
    task = asyncio.create_task(emit())
    try:
        path, stats = await collect(config, 1, data_root=tmp_path)
        assert stats['dropped'] > 0 and stats['queue_peak_items'] == 1
        data = ''.join(p.read_text() for p in path.glob('observations-*'))
        assert 'preceding_queue_gap' in data
        assert replay(path)['quality'].get('boundary_queue_drop', 0) > 0
    finally:
        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        await sio.shutdown(); await runner.cleanup()
        ping_tasks = [t for t in asyncio.all_tasks() if 'AsyncSocket._send_ping' in getattr(t.get_coro(), '__qualname__', '')]
        for t in ping_tasks:
            t.cancel()
        await asyncio.gather(*ping_tasks, return_exceptions=True)
