import json
import shutil
import pytest
from tto.config import load_config, headers, public_config
from tto.collector import BoundedQueue, check_request
from tto.storage import InstanceLock, Journal, LimitReached
from tto.cli import main


def test_offline_help_doctor_and_priority(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('TTO_DURATION_S', 'bad-value')
    with pytest.raises(SystemExit) as e:
        main(['--help'])
    assert e.value.code == 0
    c = tmp_path / 'config.json'; c.write_text('{}')
    assert main(['doctor', '--config', str(c), '--duration', '8']) == 0
    assert 'connected' in capsys.readouterr().out
    with pytest.raises(ValueError):
        load_config(c)
    cfg = load_config(c, {'run.default_duration_s': 9}, {'TTO_DURATION_S': '7'})
    assert cfg['run']['default_duration_s'] == 9
    cfg = load_config(c, environ={'TEGRASTATS_INTERVAL': 'bad'})
    assert cfg['orin']['source_sample_interval_ms'] is None


@pytest.mark.parametrize('obj', [{'unknown': True}, {'security': {'business_control_writes': True}}, {'tianshan': {'fan_status_path': '/api/v1/fan/set'}}, {'orin': {'base_url': 'http://user:password@localhost'}}, {'network': {'follow_redirects': True}}, {'run': {'default_duration_s': 0}}, {'features': {'history_s': 200}}])
def test_invalid_config_rejected(tmp_path, obj):
    p = tmp_path / 'c.json'; p.write_text(json.dumps(obj))
    with pytest.raises(ValueError):
        load_config(p, environ={})


def test_credentials_private_and_redacted(config, tmp_path):
    p = tmp_path / 'headers.json'; p.write_text('{"Authorization":"secret-token"}')
    p.chmod(0o644); config['orin']['headers_file'] = str(p)
    with pytest.raises(ValueError):
        headers(config, 'orin')
    p.chmod(0o600)
    assert headers(config, 'orin') == {'Authorization': 'secret-token'}
    assert 'secret-token' not in json.dumps(public_config(config))
    assert str(p) not in json.dumps(public_config(config))


def test_policy_blocks_wrong_paths_methods_targets():
    origin = 'http://127.0.0.1:1234'
    check_request(origin, origin + '/api/v1/fan/status', 'GET')
    check_request(origin, origin + '/socket.io/?EIO=4', 'POST', True)
    for url, method in [(origin + '/api/v1/fan/set', 'GET'), (origin + '/api/v1/fan/status', 'POST'), ('http://other:1234/api/v1/fan/status', 'GET'), (origin + '/api/v1/fan/status?duty=10', 'GET')]:
        with pytest.raises(ValueError):
            check_request(origin, url, method)


async def test_queue_saturation_marks_gap():
    q = BoundedQueue(1, 200)
    assert q.put({'kind': 'a'})
    assert not q.put({'kind': 'b'})
    await q.get()
    assert q.put({'kind': 'c'})
    assert (await q.get())['preceding_queue_gap'] is True
    assert q.dropped == 1 and q.peak_items == 1
    q = BoundedQueue(3, 5)
    assert not q.put({'too_large': 'text'})


def test_storage_limits_rotation_no_overwrite(config, tmp_path, monkeypatch):
    config['storage']['chunk_bytes'] = 100
    config['storage']['min_free_bytes'] = 1
    j = Journal(config, tmp_path, simulated=True)
    config['storage']['run_max_bytes'] = j.total + j.reserve + 200
    j.append('observations', {'a': 'x' * 70})
    j.append('observations', {'a': 'x' * 70})
    assert len(list(j.path.glob('observations-*'))) == 2
    with pytest.raises(LimitReached):
        j.append('observations', {'a': 'x' * 70})
    j.close({'status': 'limit'})
    previous = {p.name: p.read_bytes() for p in j.path.iterdir()}
    j2 = Journal(config, tmp_path, simulated=True)
    assert j2.path != j.path
    j2.close({})
    assert previous == {p.name: p.read_bytes() for p in j.path.iterdir()}
    monkeypatch.setattr(shutil, 'disk_usage', lambda _: type('D', (), {'free': 0})())
    j3 = Journal(config, tmp_path, simulated=True)
    with pytest.raises(LimitReached):
        j3.append('events', {})
    j3.close({})


def test_lock_reentry_release(tmp_path):
    path = tmp_path / 'lock'
    with InstanceLock(path):
        with pytest.raises(ValueError):
            with InstanceLock(path):
                pass
    with InstanceLock(path):
        pass


def test_final_deployment_evidence_never_inferred(tmp_path):
    from tto.deployment import deployment_record
    assert deployment_record()['deployment_status'] == 'deployment_unverified'
    r = {'record_schema': 1, 'ws_candidate': {'final_after_f1_f2': True, 'wheel_sha256': 'a' * 64}}
    p = tmp_path / 'deployment.json'; p.write_text(json.dumps(r))
    assert deployment_record(p)['deployment_status'] == 'deployment_unverified'
    for key in ('parser_sha256', 'cli_sha256', 'config_sha256', 'server_sha256'):
        r['ws_candidate'][key] = 'b' * 64
    r['ws_candidate'].update(installed_import_path='/local/installed/package', final_closeout_evidence_ref='local-final-evidence')
    r['checks'] = {k: True for k in ('tj_reaches_tianshan', 'socketio_event_received', 'new_sequence_progresses', 'repeated_cache_not_new_sample', 'power_fields_valid', 'source_period_confirmed', 'fan_status_usable')}
    r['effective_service_config'] = {'evidence_ref': 'user-effective-config'}
    p.write_text(json.dumps(r))
    assert deployment_record(p)['deployment_status'] == 'user_recorded_not_independently_verified'
