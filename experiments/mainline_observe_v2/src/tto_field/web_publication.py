"""Optional, bounded local publication. All encoding and socket I/O use one worker.

Neither startup nor teardown errors propagate to the recorder. submit() takes an
owned snapshot after state commit; it never encodes or waits for a socket.
"""
import asyncio
import contextlib
import json
import os
import threading
import uuid
from collections import deque
from pathlib import Path
from tto.storage import InstanceLock
from .web_encoding import WebEncoder

CAPACITY = 8
MAX_PACKET = 512 * 1024 - 1


def atomic_json(path, row):
    tmp = path.with_suffix('.next')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(row, stream, allow_nan=False)
    os.replace(tmp, path)


class Publication:
    def __init__(self, descriptor, boot, observed_device=None, *, test_replay=False, process_clock_domain=None):
        self.descriptor = Path(descriptor)
        self.socket = self.descriptor.parent / 'publication.sock'
        self.process_clock_domain = process_clock_domain
        self.boot = boot
        self.observed_device = observed_device
        self.test_replay = test_replay
        self.pending = deque()
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self.thread = None
        self.clients = set()
        self.handlers = set()
        self.latest = None
        self.encoder = None
        self.gap_pending = False
        self.gap_next = False
        self.stats = dict(submitted=0, published=0, dropped=0, errors=0, last_error=None,
                          slow_clients=0, connected=0, max_pending=0, running=False)

    def error(self, exc):
        with self.lock:
            self.stats['errors'] += 1
            self.stats['last_error'] = type(exc).__name__

    def start(self):
        try:
            self.thread = threading.Thread(target=self._run, name='web-publication', daemon=True)
            self.thread.start()
        except Exception as exc:
            self.error(exc)
            self.ready.set()
        return self

    def submit(self, raw, processed, frame, state, deadline):
        # Caller transfers ownership; none of these objects may be changed later.
        with self.lock:
            self.stats['submitted'] += 1
            if len(self.pending) == CAPACITY:
                self.stats['dropped'] += len(self.pending)
                self.pending.clear()
                self.gap_pending = True
            self.pending.append((raw, processed, frame, state, deadline))
            self.stats['max_pending'] = max(self.stats['max_pending'], len(self.pending))

    def invalidate(self):
        with self.lock:
            self.stats['dropped'] += len(self.pending)
            self.pending.clear()
            self.gap_pending = True

    def snapshot(self):
        with self.lock:
            return dict(self.stats, pending=len(self.pending), worker_stopped=not self.thread or not self.thread.is_alive())

    def close(self):
        self.stopping.set()
        if self.thread:
            self.thread.join(timeout=2)
        return self.snapshot()

    def _run(self):
        try:
            asyncio.run(self._serve())
        except Exception as exc:
            self.error(exc)
        finally:
            with self.lock:
                self.stats['running'] = False
                self.stats['dropped'] += len(self.pending)
                self.pending.clear()
            self.ready.set()

    async def _serve(self):
        if not self.boot or self.boot.startswith('test:') and not self.test_replay:
            raise ValueError('publication needs a real boot identity')
        if len(os.fsencode(self.socket)) >= 100:
            raise ValueError('publication directory too long')
        if self.descriptor.name in ('publication.sock', 'publisher.lock'):
            raise ValueError('descriptor conflicts with publication resources')
        directory = self.descriptor.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        st = directory.stat()
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise ValueError('publication directory must be private and owned')
        with InstanceLock(str(directory / 'publisher.lock')):
            server = None
            try:
                if self.socket.exists():
                    self.socket.unlink()
                server = await asyncio.start_unix_server(self._client, path=str(self.socket), limit=MAX_PACKET+1)
                os.chmod(self.socket, 0o600)
                atomic_json(self.descriptor, dict(schema='TTO-WEB-ACTIVE-v1', socket='publication.sock',
                    boot_id=self.boot, publisher_id=str(uuid.uuid4()), ended=False))
                with self.lock:
                    self.stats['running'] = True
                self.ready.set()
                await self._pump()
            finally:
                if server:
                    server.close()
                for task in tuple(self.handlers):
                    task.cancel()
                await asyncio.gather(*tuple(self.handlers), return_exceptions=True)
                if server:
                    await server.wait_closed()
                try:
                    atomic_json(self.descriptor, dict(schema='TTO-WEB-ACTIVE-v1', boot_id=self.boot, ended=True))
                finally:
                    if self.socket.exists():
                        self.socket.unlink()

    def _broadcast(self, row):
        data = json.dumps(row, allow_nan=False, separators=(',', ':')).encode() + b'\n'
        if len(data) > MAX_PACKET:
            raise ValueError('publication packet exceeds budget')
        self.latest = data
        for client in tuple(self.clients):
            queue, writer = client
            if queue.full():
                # Disconnect rather than accumulate transport data for a slow reader.
                self.stats['slow_clients'] += 1
                writer.transport.abort()
                self.clients.discard(client)
            else:
                queue.put_nowait(data)

    def _gap(self):
        if self.encoder:
            self.encoder.reset()
        self.gap_next = True
        self._broadcast(dict(schema='TTO-WEB-DISPLAY-GAP-v1', boot_id=self.boot,
                             clock_domain_id='host-monotonic:' + self.boot, error_class='PublicationGap'))

    async def _pump(self):
        while not self.stopping.is_set():
            with self.lock:
                gap = self.gap_pending
                self.gap_pending = False
                rows = list(self.pending)
                self.pending.clear()
            if gap:
                self._gap()
            for raw, processed, frame, state, deadline in rows:
                try:
                    if self.encoder is None:
                        self.encoder = WebEncoder(frame['identity']['run_id'], frame['identity']['config_sha256'],
                                                  self.boot, self.observed_device, self.test_replay)
                    if frame['source_reset']:
                        self.encoder.reset()
                        self.gap_next = True
                    packet = self.encoder.encode(raw, processed, frame, frame['_communication'], state, deadline)
                    if self.process_clock_domain is not None:
                        packet['process_clock_domain'] = self.process_clock_domain
                    packet['frozen_state_clock_literal'] = state.get('generated_clock_domain')
                    if self.gap_next:
                        packet['publication_gap'] = True
                    self._broadcast(packet)
                    self.gap_next = False
                    self.stats['published'] += 1
                except Exception as exc:
                    self.error(exc)
                    self._gap()
            await asyncio.sleep(.01)

    async def _client(self, reader, writer):
        if len(self.clients) >= 4:
            writer.close()
            return
        queue = asyncio.Queue(maxsize=CAPACITY+1)
        if self.latest is not None:
            queue.put_nowait(self.latest)
        client = (queue, writer)
        self.clients.add(client)
        self.stats['connected'] += 1
        handler = asyncio.current_task()
        self.handlers.add(handler)
        async def send():
            while True:
                writer.write(await queue.get())
                try:
                    await asyncio.wait_for(writer.drain(), .2)
                except asyncio.TimeoutError:
                    self.stats['slow_clients'] += 1
                    return
        sender = asyncio.create_task(send())
        closed = asyncio.create_task(reader.read(1))
        try:
            await asyncio.wait((sender, closed), return_when=asyncio.FIRST_COMPLETED)
        finally:
            sender.cancel()
            closed.cancel()
            await asyncio.gather(sender, closed, return_exceptions=True)
            self.clients.discard(client)
            self.handlers.discard(handler)
            writer.transport.abort()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
