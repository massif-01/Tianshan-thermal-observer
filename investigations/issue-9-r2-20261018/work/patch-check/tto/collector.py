"""Two bounded inputs; the only ESP32 business operations are two exact GETs."""
import asyncio
import contextlib
import json
import math
import random
import signal
import ssl
import time
from pathlib import Path
from urllib.parse import urlsplit
from .config import headers, require_live
from .engine import engine_for
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



async def collect(config, duration, model=None, data_root=None, episode=None, deployment=None, run_type=None,
                  stop_event=None, on_record=None):
    require_live(config, duration)
    # No networking is constructed until this explicitly live function is called.
    with InstanceLock():
        recorded_deployment = dict(deployment or {})
        recorded_deployment['polling_contract'] = {'version': 'TTO-POLL-INDEPENDENT-v1',
            'max_inflight_per_endpoint': 1, 'max_total_inflight': 2,
            'fan_interval_s': config['tianshan']['fan_poll_interval_s'],
            'temp_interval_s': config['tianshan']['temp_poll_interval_s'],
            'legacy_config_max_inflight_esp32': config['network']['max_inflight_esp32']}
        journal = Journal(config, data_root, episode=episode, deployment=recorded_deployment, run_type=run_type or ('shadow' if model else 'collect'), model_sha256=model['sha256'] if model else None, record_schema=2)
        engine = engine_for(config, model, record_schema=2)
        q = BoundedQueue(config['storage']['queue_max_items'], config['storage']['queue_max_bytes'])
        stop = stop_event if stop_event is not None else asyncio.Event()
        stats = {'stop_reason': 'duration', 'poll_missed': 0, 'poll_count': 0, 'connection_attempts': 0, 'payload_oversize': 0, 'orin_event_count': 0, 'business_payload_bytes_sum': 0, 'business_payload_bytes_max': 0, 'poll_rtt_ms': [], 'prediction_ms': [], 'rss_mib': [], 'cpu_pct_single_core': []}
        clock_start = time.monotonic()
        polls = {key: {'sent': [], 'received': [], 'rtt_ms': [], 'http_ok': 0, 'errors': 0,
                       'skipped': 0, 'cancelled': 0, 'inflight': 0, 'peak_inflight': 0}
                 for key in ('fan', 'temp')}
        esp_inflight = 0
        esp_peak = 0
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
            journal.processing_output(r, out)
            if on_record is not None:
                # Synchronous observation of this same processed stream, no second poller.
                on_record(r, out, engine)
            if out['prediction']:
                stats['prediction_ms'].append((time.perf_counter() - before) * 1000)

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
            paths = {'fan': c['fan_status_path'], 'temp': c['temp_status_path']}
            h = headers(config, 'tianshan')
            async def endpoint(key):
                nonlocal esp_inflight, esp_peak
                period = c[key + '_poll_interval_s']
                due = clock_start
                detail = polls[key]
                # Each restricted session still permits only one HTTP request;
                # two independent endpoint workers bound the collector total at two.
                async with sessions(config, 'tianshan') as session:
                    while not stop.is_set():
                        delay = due - time.monotonic()
                        if delay > 0:
                            try:
                                await asyncio.wait_for(stop.wait(), delay)
                                break
                            except asyncio.TimeoutError:
                                pass
                        if stop.is_set():
                            break
                        planned, sent = due, time.monotonic()
                        detail['sent'].append(sent)
                        detail['inflight'] += 1
                        detail['peak_inflight'] = max(detail['peak_inflight'], detail['inflight'])
                        esp_inflight += 1
                        esp_peak = max(esp_peak, esp_inflight)
                        try:
                            async with session.get(c['base_url'].rstrip('/') + paths[key], headers=h, allow_redirects=False) as response:
                                if response.status in (401, 403):
                                    stats['stop_reason'] = 'authorization_failed'
                                    stop.set()
                                if response.status != 200:
                                    raise ValueError('HTTP_status_unusable')
                                raw = await response.read()
                                payload = json.loads(raw)
                                received = time.monotonic()
                                detail['http_ok'] += 1
                                put(key, payload, planned_mono_s=planned, sent_mono_s=sent,
                                    received_mono_s=received, round_trip_ms=(received-sent)*1000)
                        except asyncio.CancelledError:
                            detail['cancelled'] += 1
                            put('polling_event', endpoint=key, reason='cancelled', planned_mono_s=planned,
                                sent_mono_s=sent, cancelled_mono_s=time.monotonic())
                            raise
                        except Exception as e:
                            received = time.monotonic()
                            detail['errors'] += 1
                            put(key, {}, planned_mono_s=planned, sent_mono_s=sent,
                                received_mono_s=received, round_trip_ms=(received-sent)*1000,
                                error_class=type(e).__name__)
                        finally:
                            detail['inflight'] -= 1
                            esp_inflight -= 1
                        detail['received'].append(received)
                        detail['rtt_ms'].append((received-sent)*1000)
                        stats['poll_count'] += 1
                        stats['poll_rtt_ms'].append((received-sent)*1000)
                        skipped = max(0, math.floor((received-planned)/period))
                        detail['skipped'] += skipped
                        stats['poll_missed'] += skipped
                        # Skip missed slots, never catch up or sleep a whole period
                        # after receiving. Actual launches remain >= one period apart.
                        due = max(planned+(skipped+1)*period, sent+period)
            workers = [asyncio.create_task(endpoint(key)) for key in ('fan', 'temp')]
            try:
                await asyncio.gather(*workers)
            finally:
                for worker in workers:
                    worker.cancel()
                await asyncio.gather(*workers, return_exceptions=True)

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
            if stop_event is not None and stats['stop_reason'] == 'duration':
                stats['stop_reason'] = 'external_stop'
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
            def summary(values):
                ordered = sorted(values)
                def percentile(q):
                    if not ordered:
                        return None
                    i = (len(ordered)-1)*q
                    lo, hi = math.floor(i), math.ceil(i)
                    return ordered[lo]+(ordered[hi]-ordered[lo])*(i-lo)
                return {'n': len(values), 'p50': percentile(.5), 'p95': percentile(.95),
                        'min': min(values) if values else None, 'max': max(values) if values else None}
            stats['polling_health'] = {'contract': 'TTO-POLL-INDEPENDENT-v1',
                'max_inflight_per_endpoint': 1, 'max_total_inflight_limit': 2,
                'max_total_inflight_observed': esp_peak, 'end_inflight': esp_inflight,
                'legacy_config_max_inflight_esp32': config['network']['max_inflight_esp32'],
                'endpoints': {key: {'sent': len(p['sent']), 'returned': len(p['received']),
                    'http_ok': p['http_ok'], 'errors': p['errors'], 'skipped': p['skipped'],
                    'cancelled': p['cancelled'], 'peak_inflight': p['peak_inflight'],
                    'rtt_ms': summary(p['rtt_ms']),
                    'send_interval_s': summary([b-a for a,b in zip(p['sent'],p['sent'][1:])]),
                    'return_interval_s': summary([b-a for a,b in zip(p['received'],p['received'][1:])])}
                    for key,p in polls.items()}}
            journal.close(stats)
        print('本轮TTO已停止；现有风扇控制未被修改。', flush=True)
        return journal.path, stats
