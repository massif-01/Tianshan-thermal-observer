import copy
import pytest
from tto.quality import Quality, fan_data, temp_data, numbers
from tto.engine import Engine
from conftest import record, aux


def test_duplicate_age_never_rejuvenates(config):
    q = Quality(config)
    r = record(1, t=0, age=100)
    assert q.accept(r)['accepted']
    r['mono_s'] = 4
    r['payload']['telemetry_meta']['sample_age_ms'] = 0
    assert q.accept(r)['age_lower_bound_ms'] == 4100
    r['mono_s'] = 5
    assert q.accept(r)['age_lower_bound_ms'] == 5100
    assert q.blocked
    r['mono_s'] = 6
    assert not q.accept(r)['accepted']
    assert q.counts['new_samples'] == 1
    assert q.accept(record(2, t=7))['accepted']


def test_identical_value_new_sequence_is_new(config):
    q = Quality(config)
    assert q.accept(record(1))['accepted']
    assert q.accept(record(2))['accepted']
    assert q.counts['new_samples'] == 2


def test_identity_conflict_quarantines_stream(config):
    q = Quality(config)
    r = record(1)
    q.accept(r)
    r = copy.deepcopy(r)
    r['mono_s'] += 1
    r['payload']['temperature']['tj'] += 1
    assert q.accept(r)['reason'] == 'identity_conflict'
    assert q.accept(record(2, t=3))['accepted']
    assert q.accept(record(1, t=4, stream='new'))['accepted']
    assert q.accept(record(3, t=5))['reason'] == 'retired_stream'


def test_regression_gap_epoch_and_late_callback(config):
    q = Quality(config)
    q.accept(record(2, t=1))
    assert q.accept(record(1, t=2))['reason'] == 'sequence_regression'
    assert q.accept(record(3, t=3))['accepted']
    q = Quality(config)
    q.accept(record(1, t=0))
    assert q.accept(record(4, t=1))['accepted']
    assert q.counts['missing_sequences'] == 2
    s = q.segment
    q.accept(record(5, t=8))
    assert q.segment > s
    r = record(6, t=9); r['connection_epoch'] = 2
    q.accept(r)
    assert q.accept(record(7, t=10))['reason'] == 'late_connection_callback'


@pytest.mark.parametrize('field,value', [('schema_version', 2), ('schema_version', True), ('sample_seq', 0), ('sample_seq', True), ('fresh', False), ('collector_state', 'stopped'), ('sample_age_ms', 5000), ('sample_age_ms', -1), ('time_basis', 'hardware'), ('received_at', None)])
def test_bad_meta_never_enters_history(config, field, value):
    r = record(1)
    r['payload']['telemetry_meta'][field] = value
    assert not Quality(config).accept(r)['accepted']


def test_missing_zero_and_successful_duty():
    r = record(1)
    r['payload']['power']['vdd_gpu_soc']['current'] = 0
    v = numbers(r['payload'])
    assert v['vdd_gpu_soc'] == 0
    assert v['temp_gpu'] is None
    del r['payload']['power']['vdd_cpu_cv']
    assert numbers(r['payload'])['vdd_cpu_cv'] is None
    f = fan_data(aux('fan', 0)['payload'])
    assert f['successful_duty'] == 37 and f['target_duty'] == 70 and f['rpm'] == 0
    r = aux('fan', 0)['payload']; r['data']['fans'][0]['duty_valid'] = False
    assert fan_data(r)['successful_duty'] is None
    r['code'] = 1
    with pytest.raises(ValueError):
        fan_data(r)


def test_actual_temp_contract():
    d = temp_data(aux('temp', 0)['payload'])
    assert d['normalized_temp'] == 42 and d['clock'] == 'esp32_update_ms'


def test_future_fan_cannot_backfill_and_duplicate_no_prediction(config):
    e = Engine(config)
    first = e.process(record(1, t=0))['prediction']
    frozen = copy.deepcopy(first)
    e.process(aux('fan', 1)); e.process(aux('temp', 1))
    assert first == frozen
    assert first['origin']['features']['duty'] is None
    assert e.process(record(1, t=2))['prediction'] is None


def test_disconnect_and_stream_boundary_cancel_labels(config):
    e = Engine(config)
    e.process(aux('fan', 0)); e.process(aux('temp', 0))
    p = e.process(record(1, t=0))['prediction']
    out = e.process({'kind': 'boundary', 'mono_s': 5, 'reason': 'disconnect'})
    assert len(out['scores']) == 3 and all(s['status'] == 'cross_segment' for s in out['scores'])
    assert not e.pending and not e.features.history


def test_utc_does_not_affect_age(config):
    q = Quality(config)
    r = record(1, t=0); q.accept(r)
    r['received_at_utc'] = '1990-01-01T00:00:00Z'; r['mono_s'] = 1
    assert q.accept(r)['age_lower_bound_ms'] == 1000
    r['mono_s'] = .5
    assert q.accept(r)['reason'] == 'monotonic_regression'
