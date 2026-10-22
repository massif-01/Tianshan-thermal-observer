"""Explicit self-built local test service. No actual device URL or real inference exists."""
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['TTO_WEB_TEST_BOOT_ID']='tto-web-browser-self-test'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor'),str(ROOT/'tests')]
from aiohttp import web
from tto_web.server import app_for
from tto_web.source import observe,Publication,follow
from tto_web.state import State
from tto_web.common import atomic_json
from producer import FakeSource,web_config,native_config


async def main():
    out=ROOT/'evidence/browser-service';out.mkdir(exist_ok=True)
    async with FakeSource() as producer:
        native=out/'native-test.json';atomic_json(native,native_config(producer.url))
        owner_config=web_config();owner_config['source'].update(mode='observe',observation_config=str(native))
        owner=State(owner_config);owner_stop=asyncio.Event();stop=asyncio.Event()
        loop=asyncio.get_running_loop()
        for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
        descriptor=Path('/private/tmp')/('tto-web-browser-'+str(os.getuid()))/'active.json'
        async with Publication(descriptor) as publication:
            source_task=asyncio.create_task(observe(owner_config,owner,owner_stop,publication))
            config=web_config();config['source']['active_descriptor']=str(descriptor)
            state=State(config);app=app_for(config,state=state)
            runner=web.AppRunner(app,access_log=None,shutdown_timeout=2);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',59009);await site.start()
            atomic_json(out/'process.json',dict(pid=os.getpid(),clock='explicit test clock',loopback_only=True))
            print('SELF-BUILT TEST SERVICE 127.0.0.1:59009; no real devices',flush=True)
            start=time.monotonic()
            async def stats():
                while not stop.is_set():
                    atomic_json(out/'counters.json',dict(elapsed_s=time.monotonic()-start,status_gets=producer.gets,ws_clients=len(producer.connections),inference_posts=producer.posts,model_gets=producer.model_gets,sse_clients=len(app['sse_clients']),snapshots=state.seq,prediction_count=len(state.predictions),source_status=state.source_status))
                    command=out/'command.json'
                    if command.exists():
                        c=json.loads(command.read_text());command.unlink()
                        producer.silent=c.get('silent',False);producer.fan_invalid=c.get('fan_invalid',False)
                        if c.get('stop'):stop.set()
                    await asyncio.sleep(1.)
            stats_task=asyncio.create_task(stats())
            try:await stop.wait()
            finally:
                stats_task.cancel();await asyncio.gather(stats_task,return_exceptions=True)
                await runner.cleanup();owner_stop.set();await source_task
                atomic_json(out/'final-dto.json',state.snapshot())
                atomic_json(out/'predictions.json',state.prediction_view(45))


if __name__=='__main__':asyncio.run(main())
