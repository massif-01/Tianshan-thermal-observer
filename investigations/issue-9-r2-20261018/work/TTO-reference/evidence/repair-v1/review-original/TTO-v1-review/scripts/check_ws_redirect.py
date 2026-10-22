import asyncio,json
from pathlib import Path
import aiohttp
from aiohttp import web
from tto.collector import sessions
from tto.config import load_config

async def main():
    seen=[]; runners=[]
    async def target(r):
        seen.append({'path':r.path,'x_fixture_token':r.headers.get('X-TTO-Test-Token')})
        ws=web.WebSocketResponse();await ws.prepare(r);await ws.send_str('fixture');await ws.close();return ws
    b=web.Application();b.router.add_get('/not-authorized',target)
    rb=web.AppRunner(b);await rb.setup();runners.append(rb);sb=web.TCPSite(rb,'127.0.0.1',0);await sb.start()
    target_url=f'http://127.0.0.1:{sb._server.sockets[0].getsockname()[1]}/not-authorized'
    async def redirect(r):raise web.HTTPFound(target_url)
    a=web.Application();a.router.add_get('/socket.io/',redirect);a.router.add_get('/api/v1/fan/status',redirect)
    ra=web.AppRunner(a);await ra.setup();runners.append(ra);sa=web.TCPSite(ra,'127.0.0.1',0);await sa.start()
    origin=f'http://127.0.0.1:{sa._server.sockets[0].getsockname()[1]}'
    c=load_config(environ={});c['orin']['base_url']=origin;c['tianshan']['base_url']=origin
    try:
        async with sessions(c,'tianshan') as s:
            try:await s.get(origin+'/api/v1/fan/status');http='unexpected_pass'
            except ValueError:http='redirect_blocked'
        assert not seen
        async with sessions(c,'orin',socketio=True) as s:
            ws=await s.ws_connect(origin+'/socket.io/?EIO=4&transport=websocket',headers={'X-TTO-Test-Token':'nonsecret-fixture'})
            await ws.close()
        out={'aiohttp_version':aiohttp.__version__,'real_network_scope':'two_loopback_servers_only','esp_get':http,'ws_followed_cross_origin':len(seen)>0,'target_requests':seen}
        print(json.dumps(out,indent=2))
    finally:
        for r in runners:await r.cleanup()
asyncio.run(main())
