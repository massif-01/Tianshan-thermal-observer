import asyncio
import copy
import json
import pytest
from aiohttp import web
from tto.collector import collect
from tto.engine import Engine
from tto.storage import Journal
from tto.dataset import replay
from tto.util import read_json
from tto.demo import packet
from conftest import aux, record


def test_stale_duplicate_suspends_and_cannot_restore(config):
    e = Engine(config)
    e.process(aux('fan', 0)); e.process(aux('temp', 0))
    e.process(record(1, t=0))
    r = record(1, t=1, fresh=False)
    result = e.process(r)
    assert result['prediction'] is None and not e.pending
    r = record(1, t=2, fresh=True)
    assert e.process(r)['prediction'] is None
    assert not e.features.history


def test_temp_testing_manual_fault_and_unknown_duty_block_full_scope(config):
    for key, value in [('mode', 'manual'), ('enabled', False), ('fault', True), ('duty_valid', False), ('guard_active', True), ('temp_stale', True)]:
        e = Engine(config)
        f = aux('fan', 0); f['payload']['data']['fans'][0][key] = value
        e.process(f); e.process(aux('temp', 0))
        p = e.process(record(1, t=0))['prediction']
        assert not p['origin']['normal_auto']
        assert p['actual_method'] == 'persist'
    e = Engine(config)
    e.process(aux('fan', 0)); d = aux('temp', 0)
    d['payload']['data']['manual_mode'] = True; e.process(d)
    assert not e.process(record(1, t=0))['prediction']['origin']['normal_auto']


def test_binding_change_invalidates_pending_and_history(config):
    e = Engine(config)
    e.process(aux('fan', 0)); e.process(aux('temp', 0)); e.process(record(1, t=0))
    d = aux('temp', 1); d['payload']['data']['bound_variable'] = 'different.sensor'
    result = e.process(d)
    assert len(result['scores']) == 3 and not e.features.history


@pytest.mark.parametrize('slow_endpoint', ['fan', 'temp'])
async def test_bounded_disconnect_storm_and_slow_api(config, tmp_path, slow_endpoint):
    app = web.Application()
    active = dict(fan=0, temp=0)
    peak = dict(fan=0, temp=0, total=0)
    requests = []
    async def slow(request):
        key = request.path.split('/')[-2]
        requests.append((request.method, key))
        active[key] += 1
        peak[key] = max(peak[key], active[key])
        peak['total'] = max(peak['total'], sum(active.values()))
        try:
            await asyncio.sleep(1.8 if key == slow_endpoint else .01)
            return web.json_response({'code': 1})
        finally:
            active[key] -= 1
    app.router.add_get('/api/v1/fan/status', slow)
    app.router.add_get('/api/v1/temp/status', slow)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
    origin = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    # Keep both default 1s/5s schedules active long enough to repeat. The third
    # failed Socket.IO connection stops collection while a slow poll is pending.
    config['network'].update(reconnect_initial_s=2.05, reconnect_max_s=2.05,
                             reconnect_jitter_ratio=0, reconnect_max_attempts=3)
    try:
        path, stats = await collect(config, 9, data_root=tmp_path)
        assert stats['connection_attempts'] == 3
        assert stats['stop_reason'] == 'reconnect_attempt_budget'
        assert peak['fan'] == peak['temp'] == 1
        assert all(method == 'GET' for method, key in requests)
        assert stats['processing'].get('fan_unavailable', 0) >= 1
        rows = [json.loads(line) for p in path.glob('observations-*.jsonl') for line in p.read_text().splitlines()]
        by_endpoint = {key: [r for r in rows if r['kind'] == key] for key in ('fan', 'temp')}
        for key, period in [('fan', 1), ('temp', 5)]:
            sent = [r['sent_mono_s'] for r in by_endpoint[key]]
            assert sent and all(b - a >= period for a, b in zip(sent, sent[1:]))
            assert requests.count(('GET', key)) <= int(stats['elapsed_s'] / period) + 1
        if 'polling_health' in stats:
            # observe's two endpoint workers must actually be independent;
            # the legacy 0.2.2 entry below still promises one shared request.
            health = stats['polling_health']
            assert health['contract'] == 'TTO-POLL-INDEPENDENT-v1'
            assert health['max_inflight_per_endpoint'] == 1 and health['max_total_inflight_limit'] == 2
            assert peak['total'] == health['max_total_inflight_observed'] == 2
            assert health['end_inflight'] == 0
            fast_endpoint = 'temp' if slow_endpoint == 'fan' else 'fan'
            completed = {key: [r for r in rs if not r.get('error_class')] for key, rs in by_endpoint.items()}
            assert completed[fast_endpoint][0]['received_mono_s'] < completed[slow_endpoint][0]['received_mono_s']
            for key in ('fan', 'temp'):
                poll = health['endpoints'][key]
                assert poll['sent'] == requests.count(('GET', key)) >= 2
                assert poll['peak_inflight'] == 1
                assert poll['sent'] == poll['returned'] + poll['cancelled']
            assert health['endpoints'][slow_endpoint]['cancelled'] == 1
            if slow_endpoint == 'fan':
                assert health['endpoints']['fan']['skipped'] >= 2
                # A 1.8s response misses the 1s slot; the next send belongs to
                # the 2s slot, rather than an immediate catch-up on return.
                fan = by_endpoint['fan']
                assert all(b['sent_mono_s'] >= a['planned_mono_s'] + 2 for a, b in zip(fan, fan[1:]))
        else:
            assert peak['total'] == 1
        sent_at_stop = len(requests)
        await asyncio.sleep(1)
        assert len(requests) == sent_at_stop
    finally:
        await runner.cleanup()


async def test_full_disk_stops_observer_only(config, tmp_path, monkeypatch):
    from tto.storage import LimitReached
    def fail(self, name, row):
        raise LimitReached('injected_full_disk')
    monkeypatch.setattr(Journal, 'append', fail)
    config['orin']['base_url'] = config['tianshan']['base_url'] = 'http://127.0.0.1:1'
    path, stats = await collect(config, 2, data_root=tmp_path)
    assert stats['stop_reason'].startswith('LimitReached:')
    assert (path / 'summary.json').exists()


def test_queue_drop_marker_replay_matches_live(config, tmp_path):
    journal = Journal(config, tmp_path, simulated=True)
    engine = Engine(config); engine.retain_origins = True
    for t in range(20):
        for r in [aux('fan', t), aux('temp', t), record(t + 1, t=t)]:
            if t == 10 and r['kind'] == 'orin':
                r['preceding_queue_gap'] = True
            engine.process(journal.observation(r))
    journal.close({})
    offline = replay(journal.path)
    assert [p['origin']['features'] for p in engine.origins] == [r['features'] for r in offline['rows']]
    assert [p['origin']['segment'] for p in engine.origins] == [r['segment'] for r in offline['rows']]
    assert offline['quality']['boundary_queue_drop'] == 1
