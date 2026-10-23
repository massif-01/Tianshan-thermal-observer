"""Real locked-aiohttp handshake checks; all targets are created loopback services."""
import asyncio
import pytest
from aiohttp import web
from tto.collector import sessions, collect


@pytest.mark.parametrize('cross_origin', [True, False])
async def test_websocket_redirect_never_sends_target_request(config, cross_origin):
    seen = []
    runners = []
    async def target(request):
        seen.append({'path': request.path, 'fixture_header': request.headers.get('X-TTO-Test')})
        ws = web.WebSocketResponse(); await ws.prepare(request); await ws.close()
        return ws
    async def start(app):
        runner = web.AppRunner(app); await runner.setup(); runners.append(runner)
        site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
        return f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    target_url = None
    async def redirect(request):
        raise web.HTTPFound(target_url)
    try:
        app = web.Application(); app.router.add_get('/socket.io/', redirect)
        app.router.add_get('/api/v1/fan/status', redirect)
        app.router.add_get('/not-authorized', target)
        origin = await start(app)
        if cross_origin:
            other = web.Application(); other.router.add_get('/not-authorized', target)
            target_url = await start(other) + '/not-authorized'
        else:
            target_url = origin + '/not-authorized'
        config['orin']['base_url'] = config['tianshan']['base_url'] = origin
        async with sessions(config, 'orin', socketio=True) as session:
            with pytest.raises(ValueError, match='redirect'):
                await session.ws_connect(origin + '/socket.io/?EIO=4&transport=websocket', headers={'X-TTO-Test': 'nonsecret-fixture'})
        assert session.closed
        assert len(seen) == 0, seen
        async with sessions(config, 'tianshan') as session:
            with pytest.raises(ValueError, match='redirect'):
                await session.get(origin + '/api/v1/fan/status')
        assert session.closed and len(seen) == 0
    finally:
        for runner in reversed(runners):
            await runner.cleanup()


async def test_redirect_failure_collect_closes_within_attempt_budget(config, tmp_path):
    seen = []
    async def target(request):
        seen.append(request.path)
        return web.Response()
    async def redirect(request):
        raise web.HTTPFound('/not-authorized')
    app = web.Application(); app.router.add_get('/socket.io/', redirect)
    app.router.add_get('/not-authorized', target)
    app.router.add_get('/api/v1/fan/status', redirect)
    app.router.add_get('/api/v1/temp/status', redirect)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
    origin = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    config['network'].update(reconnect_max_attempts=2, reconnect_initial_s=.1, reconnect_max_s=.1)
    try:
        path, stats = await asyncio.wait_for(collect(config, 3, data_root=tmp_path), 5)
        assert stats['connection_attempts'] == 2
        assert stats['stop_reason'] == 'reconnect_attempt_budget'
        assert seen == []
        assert (path / 'summary.json').exists()
    finally:
        await runner.cleanup()
