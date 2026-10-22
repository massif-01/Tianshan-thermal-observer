"""Installed-app verification harness; synthetic prefill is not production history."""
import asyncio,json,os,signal,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from producer import web_config
from tto_web.state import State
from tto_web.source import follow
from tto_web.server import app_for
from tto_web.common import atomic_json
async def main():
    out=Path(os.environ['TTO_HISTORY_OUT']);stop=asyncio.Event();c=web_config();c['source']['active_descriptor']='/private/tmp/twh5/active.json'
    s=State(c);source=asyncio.create_task(follow(c,s,stop))
    for _ in range(150):
        if s.packet:break
        await asyncio.sleep(.1)
    assert s.packet,'synthetic source not ready'
    elapsed=(time.monotonic()-s.packet['origin_mono_s'])*1000
    # Fill existing metrics at 5 Hz for the saturated one-hour comparison.
    for id,history in s.history.items():
        if history and history[-1]['value'] is not None:
            template=history[-1]
            for i in range(18002):history.append(dict(template,t=elapsed-3599800+i*(3599800/18001),sample_id='prefill:'+str(i)))
    if hasattr(s,'model_history'):
        from tto_web.state import ModelRow
        # Include strings allocated per sample, rather than sharing artificial lineage.
        s.model_history.clear()
        for i in range(18002):
            s.model_history.append(ModelRow(elapsed-3599800+i*(3599800/18001),(44.3,44.2,40.,32.),'prefill:'+str(i),'2026-10-21T00:00:00Z','prefill/ref/'+str(i),'tracking',None))
    s.refresh();app=app_for(c,start_source=False,state=s)
    async def page(r):return web.FileResponse(ROOT/'tools/history_view.html')
    async def script(r):return web.FileResponse(ROOT/'tools/history_view.js')
    app.router.add_get('/__history',page);app.router.add_get('/__history.js',script)
    runner=web.AppRunner(app,shutdown_timeout=.2);await runner.setup();await web.TCPSite(runner,'127.0.0.1',59009,reuse_address=True).start()
    atomic_json(out/'service.json',dict(pid=os.getpid(),module=__import__('tto_web').__file__,version=__import__('tto_web').__version__,identity=__import__('tto_web.identity',fromlist=['verify']).verify(),history_prefill=True,model_rows=len(s.model_history) if hasattr(s,'model_history') else 0,production_cli=False))
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
    await stop.wait();source.cancel();await asyncio.gather(source,return_exceptions=True);await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
