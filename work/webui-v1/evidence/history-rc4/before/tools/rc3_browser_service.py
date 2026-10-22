"""Loopback browser fault harness around the installed app, never a production source.
Stalled SSE sends one real snapshot then heartbeats; live mode uses delivered SSE.
"""
import asyncio,json,os,signal,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from aiohttp import web
from producer import Producer,web_config
from tto_web.state import State
from tto_web.server import app_for
from tto_web.common import atomic_json
from tto.util import digest

async def main():
    out=ROOT/'evidence/supplement-rc3';stop=asyncio.Event();mode='live';transports=set();state=State(web_config());producer=None;seconds=30
    def reset(epoch=False):
        nonlocal producer,seconds
        if not epoch:
            producer=Producer(time.monotonic()-30)
            for t in range(31):state.accept(producer.step(t))
            seconds=30
            curve=dict(method_id='CURVE-REFERENCE-v1',verified=True,temperature_binding='agx_info.temperature.tj',device_id='SYNTHETIC-THOR',curve_id='SYNTHETIC-BROWSER-ONLY',source_config_sha256=state.packet['config_id'],fan_id=0,points=[[20,10],[80,70]])
            curve['sha256']=digest(curve);state.validate_curve(curve);state.curve=curve;state.refresh()
        else:
            producer.row('boundary',seconds,None,reason='socketio_disconnected')
            state.accept(producer.step(seconds))
    reset()
    @web.middleware
    async def faults(request,handler):
        if mode!='live' and request.path=='/api/v1/predictions':raise web.HTTPServiceUnavailable()
        if request.path=='/api/v1/stream':
            if mode=='drop':request.transport.close();raise ConnectionResetError('SYNTHETIC browser disconnect')
            transports.add(request.transport)
            if mode=='stall':
                response=web.StreamResponse(headers={'Content-Type':'text/event-stream','Cache-Control':'no-store'})
                await response.prepare(request)
                await response.write(('event: snapshot\ndata: '+json.dumps(state.refresh())+'\n\n').encode())
                try:
                    while not stop.is_set():
                        await asyncio.sleep(.5);await response.write(b'event: heartbeat\ndata: {}\n\n')
                except (ConnectionError,asyncio.CancelledError):pass
                return response
        return await handler(request)
    app=app_for(web_config(),start_source=False,state=state);app.middlewares.insert(0,faults)
    runner=web.AppRunner(app,shutdown_timeout=.2);await runner.setup();await web.TCPSite(runner,'127.0.0.1',59009).start()
    async def command(request):
        nonlocal mode
        action=request.match_info['action']
        if action in ('live','drop','stall'):
            mode=action
            for transport in tuple(transports):
                if transport:transport.close()
            transports.clear()
        elif action=='new-run':reset()
        elif action=='new-epoch':reset(True)
        elif action=='event':state.event('runner','SYNTHETIC task at 20s',20000)
        elif action=='stop':stop.set()
        else:raise web.HTTPNotFound()
        return web.json_response(dict(mode=mode,run_id=state.packet['run_id'],source_epoch=state.packet['source_epoch']))
    control=web.Application();control.router.add_post('/{action}',command)
    cr=web.AppRunner(control);await cr.setup();site=web.TCPSite(cr,'127.0.0.1',0);await site.start()
    atomic_json(out/'browser-harness.json',dict(pid=os.getpid(),control_url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]),module=__import__('tto_web').__file__,synthetic_only=True))
    async def feed():
        nonlocal seconds
        while not stop.is_set():
            await asyncio.sleep(1);seconds+=1;state.accept(producer.step(seconds))
    task=asyncio.create_task(feed())
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
    try:await stop.wait()
    finally:task.cancel();await asyncio.gather(task,return_exceptions=True);await runner.cleanup();await cr.cleanup()
if __name__=='__main__':asyncio.run(main())
