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


async def test_bounded_disconnect_storm_and_slow_api(config, tmp_path):
    app = web.Application(); active = 0; peak = 0; requests = []
    async def slow(request):
        nonlocal active, peak
        requests.append(request.path)
        active += 1; peak = max(peak, active)
        try:
            await asyncio.sleep(.3)
            return web.json_response({'code': 1})
        finally:
            active -= 1
    app.router.add_get('/api/v1/fan/status', slow)
    app.router.add_get('/api/v1/temp/status', slow)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
    origin = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
    config['orin']['base_url'] = config['tianshan']['base_url'] = origin
    config['network'].update(reconnect_initial_s=.1, reconnect_max_s=.2, reconnect_max_attempts=3)
    try:
        path, stats = await collect(config, 3, data_root=tmp_path)
        assert peak == 2  # Two independent endpoints, one in flight per endpoint.
        assert stats['connection_attempts'] == 3
        assert stats['stop_reason'] == 'reconnect_attempt_budget'
        assert len(requests) <= 4 and '/api/v1/temp/status' in requests
        assert stats['processing'].get('fan_unavailable', 0) >= 1
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
