"""Synthetic loopback publication in its own process. Never contacts a device."""
import asyncio,json,os,signal,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from producer import Producer
from tto_web.source import Publication
from tto_web.common import atomic_json
async def main():
    stop=asyncio.Event();mode='live';gap_pending=False;p=Producer(time.monotonic()-3600);count=0
    for t in list(range(31))+list(range(3570,3601)):last=p.step(t)
    async with Publication(Path('/private/tmp/twh4/active.json')) as pub:
        pub.put(last)
        async def command(r):
            nonlocal mode,count,gap_pending
            action=r.match_info['action']
            t=int(time.monotonic()-p.start)
            if action in ('epoch','new-epoch'):p.row('boundary',t,None,reason='socketio_disconnected')
            elif action=='gap':gap_pending=True
            elif action in ('live','silent'):mode=action
            elif action=='stop':stop.set()
            else:raise web.HTTPNotFound()
            return web.json_response(dict(action=action,mode=mode))
        app=web.Application();app.router.add_post('/{action}',command)
        runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        out=Path(os.environ['TTO_HISTORY_OUT']);atomic_json(out/'source.json',dict(pid=os.getpid(),control='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]),module=__import__('tto_web').__file__,loopback_only=True))
        async def feed():
            nonlocal count,gap_pending
            while not stop.is_set():
                await asyncio.sleep(1)
                if mode=='live':
                    count+=1;packet=p.step(int(time.monotonic()-p.start))
                    if gap_pending:packet=dict(packet,publication_gap=True);gap_pending=False
                    pub.put(packet)
        task=asyncio.create_task(feed());loop=asyncio.get_running_loop()
        for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
        await stop.wait();task.cancel();await asyncio.gather(task,return_exceptions=True);await runner.cleanup()
        atomic_json(out/'source-exit.json',dict(published=count,publication_dropped=pub.dropped,device_requests=0))
if __name__=='__main__':asyncio.run(main())
