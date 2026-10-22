"""Two bounded inputs; the only ESP32 business operations are two exact GETs."""
import asyncio
import contextlib
import json
import random
import signal
import ssl
import time
from pathlib import Path
from urllib.parse import urlsplit
from .config import headers, require_live
from .engine import Engine
from .storage import InstanceLock, Journal, LimitReached
from .util import canonical, utc_now

ESP_PATHS = frozenset(('/api/v1/fan/status', '/api/v1/temp/status'))


def check_request(origin, url, method, socketio=False):
    expected, actual = urlsplit(origin), urlsplit(str(url))
    # Engine.IO derives ws(s) URLs from the explicitly configured http(s) origin.
    equivalent_scheme = {'ws': 'http', 'wss': 'https'}.get(actual.scheme, actual.scheme)
    expected_port = expected.port or (443 if expected.scheme == 'https' else 80)
    actual_port = actual.port or (443 if equivalent_scheme == 'https' else 80)
    if (equivalent_scheme, (actual.hostname or '').lower(), actual_port) != (expected.scheme, (expected.hostname or '').lower(), expected_port):
        raise ValueError('request target outside configured origin')
    if socketio:
        if method not in ('GET', 'POST') or actual.path != '/socket.io/':
            raise ValueError('only Engine.IO transport is allowed')
    elif method != 'GET' or actual.path not in ESP_PATHS or actual.query:
        raise ValueError('only verified ESP32 status GET paths are allowed')


def tls_context(c, section):
    return ssl.create_default_context(cafile=c[section]['ca_file'])


class BoundedQueue:
    def __init__(self, items, bytes_limit):
        self.queue = asyncio.Queue(maxsize=items)
        self.bytes_limit = bytes_limit
        self.bytes = 0
        self.dropped = 0
        self.peak_items = 0
        self.peak_bytes = 0
        self.gap = False

    def put(self, row):
        if self.gap:
            row = dict(row, preceding_queue_gap=True)
        try:
            size = len(canonical(row))
        except (ValueError, TypeError):
            self.dropped += 1
            self.gap = True
            return False
        if self.queue.full() or self.bytes + size > self.bytes_limit:
            self.dropped += 1
            self.gap = True
            return False
        self.gap = False
        self.queue.put_nowait((row, size))
        self.bytes += size
        self.peak_items = max(self.peak_items, self.queue.qsize())
        self.peak_bytes = max(self.peak_bytes, self.bytes)
        return True

    async def get(self):
        row, size = await self.queue.get()
        self.bytes -= size
        return row


def sessions(c, section, socketio=False):
    import aiohttp
    origin = c[section]['base_url']
    max_bytes = c['network']['max_business_payload_bytes'] + (1024 if socketio else 0)

    class LimitedResponse(aiohttp.ClientResponse):
        async def read(self):
            if self._body is None:
                parts, n = [], 0
                async for chunk in self.content.iter_chunked(16384):
                    n += len(chunk)
                    if n > max_bytes:
                        self.close()
                        raise ValueError('transport response exceeds receive budget')
                    parts.append(chunk)
                self._body = b''.join(parts)
            return self._body

    class RestrictedSession:
        def __init__(self):
            # _ws_connect performs its own session.request; intercept the actual
            # handshake, including the redirect branch before a second request.
            trace = aiohttp.TraceConfig()
            async def check_start(session, context, params):
                check_request(origin, params.url, params.method, socketio)
            async def reject_redirect(session, context, params):
                params.response.close()
                raise ValueError('redirects are forbidden')
            trace.on_request_start.append(check_start)
            trace.on_request_redirect.append(reject_redirect)
            connector = aiohttp.TCPConnector(ssl=tls_context(c, section), limit=2 if socketio else 1, enable_cleanup_closed=True)
            self._session = aiohttp.ClientSession(connector=connector, response_class=LimitedResponse, timeout=aiohttp.ClientTimeout(total=c['network']['request_timeout_s'], connect=c['network']['connect_timeout_s']), trust_env=False, read_bufsize=16384, trace_configs=[trace])

        @property
        def closed(self):
            return self._session.closed

        @property
        def cookie_jar(self):
            return self._session.cookie_jar

        async def close(self):
            await self._session.close()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.close()

        def get(self, url, **kwargs):
            return aiohttp.client._RequestContextManager(self._request('GET', url, **kwargs))

        def post(self, url, **kwargs):
            return aiohttp.client._RequestContextManager(self._request('POST', url, **kwargs))

        async def _request(self, method, url, **kwargs):
            check_request(origin, url, method, socketio)
            kwargs['allow_redirects'] = False
            response = await self._session.request(method, url, **kwargs)
            if 300 <= response.status < 400:
                response.close()
                raise ValueError('redirects are forbidden')
            return response

        async def ws_connect(self, url, **kwargs):
            check_request(origin, url, 'GET', socketio)
            kwargs['max_msg_size'] = max_bytes
            return await self._session.ws_connect(url, **kwargs)

    return RestrictedSession()



async def collect(config, duration, model=None, data_root=None, episode=None, deployment=None, run_type=None):
    require_live(config, duration)
    # No networking is constructed until this explicitly live function is called.
    with InstanceLock():
        journal = Journal(config, data_root, episode=episode, deployment=deployment, run_type=run_type or ('shadow' if model else 'collect'), model_sha256=model['sha256'] if model else None)
        engine = Engine(config, model)
        q = BoundedQueue(config['storage']['queue_max_items'], config['storage']['queue_max_bytes'])
        stop = asyncio.Event()
        stats = {'stop_reason': 'duration', 'poll_missed': 0, 'poll_count': 0, 'connection_attempts': 0, 'payload_oversize': 0, 'orin_event_count': 0, 'business_payload_bytes_sum': 0, 'business_payload_bytes_max': 0, 'poll_rtt_ms': [], 'prediction_ms': [], 'rss_mib': [], 'cpu_pct_single_core': []}
        clock_start = time.monotonic()
        loop = asyncio.get_running_loop()
        signals = []
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda s=sig: (stats.update(stop_reason=s.name), stop.set()))
                signals.append(sig)
            except NotImplementedError:
                pass

        def put(kind, payload=None, **extra):
            q.put(dict(kind=kind, payload=payload, mono_s=time.monotonic(), received_at_utc=utc_now(), **extra))

        def process(row):
            if row.get('preceding_queue_gap'):
                journal.append('events', {'reason': 'queue_drop', 'mono_s': row['mono_s'], 'dropped_so_far': q.dropped})
            r = journal.observation(row)
            before = time.perf_counter()
            out = engine.process(r)
            if out['quality']:
                journal.append('events', dict(ref=r['ref'], mono_s=r['mono_s'], **out['quality']))
            if out['prediction']:
                # Write predictions now, before the worker can consume any future observation.
                journal.append('predictions', out['prediction'])
                stats['prediction_ms'].append((time.perf_counter() - before) * 1000)
            for score in out['scores']:
                journal.append('scores', score)

        async def writer():
            while not stop.is_set() or not q.queue.empty():
                try:
                    row = await asyncio.wait_for(q.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                try:
                    await asyncio.to_thread(process, row)
                except (OSError, LimitReached, ValueError) as e:
                    stats['stop_reason'] = type(e).__name__ + ':' + (str(e) if isinstance(e, LimitReached) else 'observation_processing_failed')
                    stop.set()
                    break
                finally:
                    q.queue.task_done()

        async def orin():
            import socketio
            network = config['network']
            epoch = 0
            while not stop.is_set() and stats['connection_attempts'] < network['reconnect_max_attempts']:
                epoch += 1
                this_epoch = epoch
                stats['connection_attempts'] += 1
                disconnected = asyncio.Event()
                async with sessions(config, 'orin', socketio=True) as session:
                    sio = socketio.AsyncClient(handle_sigint=False, reconnection=False, http_session=session, logger=False, engineio_logger=False, request_timeout=network['connect_timeout_s'])

                    async def on_data(payload, *unused, callback_epoch=this_epoch):
                        stats['orin_event_count'] += 1
                        try:
                            size = len(canonical(payload))
                        except (ValueError, TypeError):
                            put('boundary', reason='invalid_json_object')
                            return
                        stats['business_payload_bytes_sum'] += size
                        stats['business_payload_bytes_max'] = max(stats['business_payload_bytes_max'], size)
                        if size > network['max_business_payload_bytes']:
                            stats['payload_oversize'] += 1
                            put('boundary', reason='business_payload_oversize')
                            return
                        put('orin', payload, connection_epoch=callback_epoch)

                    async def on_disconnect(*args):
                        put('boundary', reason='socketio_disconnected')
                        disconnected.set()

                    sio.on(config['orin']['event'], handler=on_data, namespace='/')
                    sio.on('disconnect', handler=on_disconnect, namespace='/')
                    try:
                        put('boundary', reason='socketio_connecting')
                        await asyncio.wait_for(sio.connect(config['orin']['base_url'], headers=headers(config, 'orin'), transports=config['orin']['transports'], namespaces=['/'], socketio_path='socket.io', wait_timeout=network['connect_timeout_s']), network['connect_timeout_s'] + 1)
                        print('已连接，正在等待第一份有效温度数据。', flush=True)
                        while not stop.is_set() and not disconnected.is_set():
                            await asyncio.sleep(0.1)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        # Exceptions can contain credential-bearing request reprs: retain class only.
                        put('boundary', reason='socketio_connection_failed', error_class=type(e).__name__)
                    finally:
                        with contextlib.suppress(Exception):
                            await asyncio.wait_for(sio.disconnect(), timeout=3)
                        with contextlib.suppress(Exception):
                            await asyncio.wait_for(sio.shutdown(), timeout=3)
                if not stop.is_set():
                    delay = min(network['reconnect_max_s'], network['reconnect_initial_s'] * 2 ** (epoch - 1))
                    delay *= random.uniform(1 - network['reconnect_jitter_ratio'], 1 + network['reconnect_jitter_ratio'])
                    with contextlib.suppress(asyncio.TimeoutError):
                        await asyncio.wait_for(stop.wait(), delay)
            if not stop.is_set():
                stats['stop_reason'] = 'reconnect_attempt_budget'
                stop.set()

        async def esp32():
            c = config['tianshan']
            due = {'fan': clock_start, 'temp': clock_start}
            paths = {'fan': c['fan_status_path'], 'temp': c['temp_status_path']}
            h = headers(config, 'tianshan')
            async with sessions(config, 'tianshan') as session:
                while not stop.is_set():
                    now = time.monotonic()
                    overdue = [key for key in ('fan', 'temp') if due[key] <= now]
                    if not overdue:
                        await asyncio.sleep(min(0.1, min(due.values()) - now))
                        continue
                    # Fan priority on ties; oldest deadline ensures temp never starves on slow fan.
                    key = min(overdue, key=lambda x: (due[x], x != 'fan'))
                    sent = time.monotonic()
                    try:
                        async with session.get(c['base_url'].rstrip('/') + paths[key], headers=h, allow_redirects=False) as response:
                            if response.status in (401, 403):
                                stats['stop_reason'] = 'authorization_failed'
                                stop.set()
                            if response.status != 200:
                                raise ValueError('HTTP_status_unusable')
                            raw = await response.read()
                            payload = json.loads(raw)
                            put(key, payload, sent_mono_s=sent, round_trip_ms=(time.monotonic() - sent) * 1000)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        put(key, {}, sent_mono_s=sent, round_trip_ms=(time.monotonic() - sent) * 1000, error_class=type(e).__name__)
                    stats['poll_count'] += 1
                    stats['poll_rtt_ms'].append((time.monotonic() - sent) * 1000)
                    interval = c[key + '_poll_interval_s']
                    end = time.monotonic()
                    skipped = max(0, int((end - due[key]) // interval))
                    stats['poll_missed'] += skipped
                    due[key] = end + interval

        async def monitor():
            import psutil
            p = psutil.Process()
            prev = p.cpu_times()
            previous_message = None
            pt = time.monotonic()
            while not stop.is_set():
                await asyncio.sleep(1)
                now = time.monotonic()
                cpu = p.cpu_times()
                stats['rss_mib'].append(p.memory_info().rss / 1024 ** 2)
                stats['cpu_pct_single_core'].append(100 * (cpu.user + cpu.system - prev.user - prev.system) / (now - pt))
                prev, pt = cpu, now
                available = engine.q.key is not None and not engine.q.blocked and engine.q.anchor_t is not None and engine.q.anchor_age + (now - engine.q.anchor_t) * 1000 < engine.q.timeout_ms
                message = None
                if not available and now - clock_start > 5:
                    message = '数据暂不可用，预测已暂停。'
                elif available and model and (not engine.features.history or now - engine.features.history[0]['t'] < 180):
                    message = '正在积累最近3分钟的温度历史。'
                if message is not None and message != previous_message:
                    print(message, flush=True)
                previous_message = message
                # Keep freshness/label timeouts visible during silence, without fabricating data.
                put('tick')

        writer_task = asyncio.create_task(writer())
        tasks = [asyncio.create_task(f()) for f in (orin, esp32, monitor)]
        def task_done(task):
            if not task.cancelled() and task.exception() is not None:
                stats['stop_reason'] = 'task_failed:' + type(task.exception()).__name__
                stop.set()
        for task in tasks:
            task.add_done_callback(task_done)
        try:
            await asyncio.wait_for(stop.wait(), duration)
        except asyncio.TimeoutError:
            stop.set()
        finally:
            for task in tasks:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
                    stats['stop_reason'] = 'task_failed:' + type(r).__name__
            # Worker drains a finite queue; slow/full disks stop rather than blocking callbacks.
            await writer_task
            for sig in signals:
                loop.remove_signal_handler(sig)
            try:
                for score in engine.invalidate('run_end'):
                    journal.append('scores', score)
            except (OSError, LimitReached):
                pass
            stats.update(elapsed_s=time.monotonic() - clock_start, queue_peak_items=q.peak_items, queue_peak_bytes=q.peak_bytes, dropped=q.dropped, quality=dict(engine.q.counts), processing=dict(engine.counts), target_host_verified=False)
            journal.close(stats)
        print('本轮TTO已停止；现有风扇控制未被修改。', flush=True)
        return journal.path, stats
