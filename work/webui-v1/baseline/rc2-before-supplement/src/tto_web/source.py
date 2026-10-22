"""Bounded local publication and explicit single-owner observation. No Requester import."""
import asyncio
import contextlib
import copy
import json
import os
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from tto.collector import collect
from tto.storage import InstanceLock, source_identity
from tto.config import public_config, load_config
from tto.util import digest
from .adapter import Adapter
from .display import DisplayPublisher
from .common import atomic_json, boot_id, load, utc


class Publication:
    """The producer callback only inserts into a bounded deque, never writes a socket."""
    def __init__(self, descriptor):
        self.descriptor=Path(descriptor)
        self.socket=self.descriptor.parent/'publication.sock'
        self.pending=deque(maxlen=8);self.lock=threading.Lock();self.clients=set();self.latest=None
        self.dropped=0;self.task=None;self.server=None;self.owner=None;self.handlers=set()

    def put(self, packet):
        with self.lock:
            if len(self.pending)==self.pending.maxlen:
                self.dropped+=len(self.pending);self.pending.clear();packet=dict(packet,publication_gap=True)
            self.pending.append(packet)

    async def __aenter__(self):
        if len(os.fsencode(self.socket))>=100:raise ValueError('Unix发布目录过长，请配置短路径，例如/run/user/UID/tto-web')
        self.descriptor.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.owner=InstanceLock(str(self.descriptor.parent/'publisher.lock'));self.owner.__enter__()
        try:
            if self.socket.exists():self.socket.unlink()
            self.server=await asyncio.start_unix_server(self.client,path=str(self.socket),limit=512*1024)
            os.chmod(self.socket,0o600)
            atomic_json(self.descriptor,dict(schema='TTO-WEB-ACTIVE-v1',socket='publication.sock',boot_id=boot_id(),publisher_id=str(uuid.uuid4()),ended=False))
            self.task=asyncio.create_task(self.pump())
            return self
        except BaseException:
            self.owner.__exit__();raise

    async def client(self, reader, writer):
        if len(self.clients)>=4:writer.close();await writer.wait_closed();return
        queue=asyncio.Queue(maxsize=8);self.clients.add(queue)
        handler=asyncio.current_task();self.handlers.add(handler)
        async def send():
            if self.latest is not None:queue.put_nowait(self.latest)
            while True:
                packet=await queue.get()
                writer.write(json.dumps(packet,allow_nan=False,separators=(',',':')).encode()+b'\n')
                await asyncio.wait_for(writer.drain(),1.)
        sender=asyncio.create_task(send());closed=asyncio.create_task(reader.read(1))
        try:
            await asyncio.wait((sender,closed),return_when=asyncio.FIRST_COMPLETED)
        finally:
            sender.cancel();closed.cancel();await asyncio.gather(sender,closed,return_exceptions=True)
            self.clients.discard(queue);self.handlers.discard(handler);writer.close()
            with contextlib.suppress(OSError):await writer.wait_closed()

    async def pump(self):
        while True:
            with self.lock:
                rows=list(self.pending);self.pending.clear()
            for row in rows:
                self.latest=row
                for queue in tuple(self.clients):
                    outgoing=row
                    if queue.full():
                        self.dropped+=queue.qsize()
                        while not queue.empty():queue.get_nowait()
                        outgoing=dict(row,publication_gap=True)
                    queue.put_nowait(outgoing)
            await asyncio.sleep(.05)

    async def __aexit__(self,*args):
        if self.task:self.task.cancel();await asyncio.gather(self.task,return_exceptions=True)
        if self.server:self.server.close();await self.server.wait_closed()
        for handler in tuple(self.handlers):handler.cancel()
        await asyncio.gather(*tuple(self.handlers),return_exceptions=True)
        atomic_json(self.descriptor,dict(schema='TTO-WEB-ACTIVE-v1',ended=True,boot_id=boot_id()))
        if self.socket.exists():self.socket.unlink()
        self.owner.__exit__()


class MemoryJournal:
    """Observe does not record raw data. Only an in-memory native manifest/ordinal."""
    def __init__(self,config,root=None,**kwargs):
        self.run_id=str(uuid.uuid4());self.episode=self.run_id;self.path=Path(root or '.')
        self.count=0
        self.manifest=dict(observer_run_id=self.run_id,config=public_config(config),config_sha256=digest(public_config(config)),source_identity=source_identity(),firmware_identity=None)
    def observation(self,row):
        self.count+=1
        return dict(row,observer_run_id=self.run_id,episode=self.episode,ref=f'{self.run_id}/observation:{self.count}')
    def processing_output(self,*args):pass
    def append(self,*args):pass
    def close(self,*args):pass


# Owner-level recovery does not alter the native collector's per-round budget.
OBSERVE_RETRY_INITIAL_S = 1.
OBSERVE_RETRY_MAX_S = 30.


async def observe(config, state, stop, publication=None):
    native=load_config(config['source']['observation_config'],environ={})
    delay=OBSERVE_RETRY_INITIAL_S
    while not stop.is_set():
        journal=None;adapter=None
        queue=deque(maxlen=8);lock=threading.Lock()
        def factory(*args,**kwargs):
            nonlocal journal
            journal=MemoryJournal(*args,**kwargs);return journal
        def sink(packet):
            if publication:publication.put(packet)
            else:
                with lock:
                    if len(queue)==queue.maxlen:queue.clear();packet=dict(packet,publication_gap=True)
                    queue.append(packet)
        publisher=DisplayPublisher(sink)
        def record(raw,processed,engine):
            def encode():
                nonlocal adapter
                if adapter is None:
                    adapter=Adapter(journal.manifest,engine,config['source'].get('observed_device'),config['source'].get('test_replay',False))
                return adapter.feed(raw,processed)
            publisher.publish(encode)
        async def drain():
            with lock:rows=list(queue);queue.clear()
            if rows:await asyncio.to_thread(state.prepare_model)
            for row in rows:state.accept(row)
        round_stop=asyncio.Event()
        task=asyncio.create_task(collect(native,native['run']['max_duration_s'],stop_event=round_stop,on_record=record,journal_factory=factory,continuous=True,manage_signals=False,run_type='web-observe'))
        result=None
        try:
            while not task.done() and not stop.is_set():
                await drain()
                try:await asyncio.wait_for(stop.wait(),.05)
                except asyncio.TimeoutError:pass
        finally:
            # Always join the old owner and read its result, even if both stop
            # signals arrive together. Never acquire a new lock while it lives.
            round_stop.set()
            try:
                _,result=await task
                await drain()
            except (ValueError,OSError):
                state.disconnect('观察来源冲突或配置无效；未启动第二采集器')
        if result is None:return
        reason=result['stop_reason']
        if stop.is_set():
            state.disconnect('观察已停止',ended=True);return
        if reason!='reconnect_attempt_budget':
            state.disconnect('观察已结束：'+reason,ended=True);return
        state.disconnect('来源暂不可达；等待退避后重新观察')
        try:await asyncio.wait_for(stop.wait(),delay)
        except asyncio.TimeoutError:pass
        if stop.is_set():
            state.disconnect('观察已停止',ended=True);return
        delay=min(OBSERVE_RETRY_MAX_S,delay*2)


async def follow(config, state, stop):
    descriptor=config['source'].get('active_descriptor')
    if not descriptor:
        state.source_status='尚未配置观察来源';await stop.wait();return
    path=Path(descriptor)
    while not stop.is_set():
        writer=None
        try:
            meta=load(path)
            if meta.get('schema')!='TTO-WEB-ACTIVE-v1' or meta.get('boot_id')!=boot_id():raise ValueError('descriptor identity')
            if meta.get('ended'):
                state.disconnect('已结束，等待生产者注册',ended=True);await asyncio.sleep(1);continue
            if meta.get('socket')!='publication.sock':raise ValueError('descriptor socket must be local fixed basename')
            reader,writer=await asyncio.open_unix_connection(str(path.parent/'publication.sock'),limit=512*1024)
            await asyncio.to_thread(state.prepare_model)
            while not stop.is_set():
                line=await asyncio.wait_for(reader.readline(),3.)
                if not line:raise ConnectionError('producer closed')
                if len(line)>512*1024:raise ValueError('publication exceeds budget')
                state.accept(json.loads(line))
        except (OSError,ValueError,asyncio.TimeoutError):
            state.disconnect('等待已注册的TTO生产者或发布流暂断')
        finally:
            if writer:
                writer.close()
                with contextlib.suppress(OSError):await writer.wait_closed()
        await asyncio.sleep(.5)
