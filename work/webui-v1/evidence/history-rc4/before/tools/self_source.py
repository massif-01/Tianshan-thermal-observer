"""Standalone self-built protocol source -> native collector/observer -> Unix publication.
Only for local installation verification. It has no real host, model or device credentials.
"""
import asyncio
import json
import os
import signal
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['TTO_WEB_TEST_BOOT_ID']='tto-web-installed-self-test'
sys.path[:0]=[str(ROOT/'tests')] if os.environ.get('TTO_WEB_TEST_INSTALLED') else [str(ROOT/'src'),str(ROOT/'vendor'),str(ROOT/'tests')]
from producer import FakeSource,web_config,native_config
from tto_web.source import Publication,observe
from tto_web.state import State
from tto_web.common import atomic_json

async def main():
    out=Path(os.environ.get('TTO_WEB_EVIDENCE_DIR',str(ROOT/'evidence/installed-chain')));out.mkdir(parents=True,exist_ok=True)
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
    async with FakeSource() as producer:
        path=out/'native-synthetic.json';atomic_json(path,native_config(producer.url));config=web_config();config['source'].update(mode='observe',observation_config=str(path))
        descriptor=Path(os.environ.get('TTO_WEB_TEST_DESCRIPTOR','/private/tmp/tto-web-installed-source/active.json'))
        async with Publication(descriptor) as publication:
            atomic_json(out/'process.json',dict(pid=os.getpid(),descriptor=str(descriptor),loopback_only=True))
            print('SYNTHETIC source publishing; no real endpoint',flush=True)
            task=asyncio.create_task(observe(config,State(config),stop,publication))
            try:await stop.wait()
            finally:
                stop.set();await task
                atomic_json(out/'counters.json',dict(status_gets=producer.gets,ws_clients=len(producer.connections),posts=producer.posts,model_gets=producer.model_gets,publisher_dropped=publication.dropped))

if __name__=='__main__':asyncio.run(main())
