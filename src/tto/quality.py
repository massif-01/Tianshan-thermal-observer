"""Monotonic identity/freshness state, shared by replay and live observation."""
from collections import Counter
from datetime import datetime
from .util import digest, finite

RAILS = ('vdd_gpu_soc', 'vdd_cpu_cv', 'vin_sys_5v0')


def numbers(payload):
    temp = payload.get('temperature') or {}
    values = {'tj': temp.get('tj') if finite(temp.get('tj')) else None}
    for k in ('cpu', 'gpu', 'soc0', 'soc1', 'soc2'):
        values['temp_' + k] = temp.get(k) if finite(temp.get(k)) else None
    cpu = payload.get('cpu') or {}
    cores = cpu.get('cores') or []
    cores = [x for x in cores if isinstance(x, dict)] if isinstance(cores, list) else []
    for field in ('usage', 'freq'):
        valid = [x[field] for x in cores if finite(x.get(field)) and x[field] >= 0 and (field != 'usage' or x[field] <= 100)]
        values['cpu_' + field] = sum(valid) / len(valid) if valid else None
    values['cpu_reported_cores'] = len(cores) if cores else None
    g = (payload.get('gpu') or {}).get('gr3d_freq')
    values['gpu_busy'] = g if finite(g) and 0 <= g <= 100 else None
    power = payload.get('power') or {}
    for rail in RAILS:
        p = power.get(rail) or {}
        v = p.get('current')
        values[rail] = v / 1000 if finite(v) and v >= 0 and p.get('unit') == 'mW' else None
    return values


def api_data(payload):
    if not isinstance(payload, dict) or type(payload.get('code')) is not int or payload['code'] != 0 or not isinstance(payload.get('data'), dict):
        raise ValueError('API success envelope missing')
    return payload['data']


def fan_data(payload):
    data = api_data(payload)
    if 'fans' in data:
        if not isinstance(data['fans'], list):
            raise ValueError('invalid fans')
        matches = [f for f in data['fans'] if isinstance(f, dict) and type(f.get('id')) is int and f['id'] == 0]
        if len(matches) != 1:
            raise ValueError('fan 0 must be uniquely identified')
        data = matches[0]
    if type(data.get('id')) is not int or data['id'] != 0:
        raise ValueError('only fan 0 is supported')
    duty = data.get('duty')
    return dict(data, successful_duty=duty if data.get('duty_valid') is True and finite(duty) and 0 <= duty <= 100 else None)


def temp_data(payload):
    d = api_data(payload)
    # Actual temp.status uses temperature_c/valid/timestamp_ms, not temp.sources names.
    if 'temperature_c' in d and 'valid' in d and 'timestamp_ms' in d:
        return dict(d, normalized_temp=d.get('temperature_c'), normalized_valid=d.get('valid'), clock='esp32_update_ms')
    if 'current_temp_c' in d and 'current_valid' in d and 'current_timestamp_ms' in d:
        return dict(d, normalized_temp=d.get('current_temp_c'), normalized_valid=d.get('current_valid'), clock='esp32_update_ms')
    raise ValueError('unrecognized temperature status contract')


class Quality:
    def __init__(self, config):
        self.c = config
        self.counts = Counter()
        self.segment = 0
        self.stream = None
        self.retired = set()
        self.last_seq = 0
        self.last_t = None
        self.last_event_t = None
        self.key = None
        self.fingerprint = None
        self.anchor_t = None
        self.anchor_age = 0
        self.blocked = False
        self.quarantined = False
        self.epoch = None
        self.timeout_ms = 0

    def boundary(self, reason):
        self.segment += 1
        self.last_t = None
        self.counts['boundary_' + reason] += 1

    def measurement_fingerprint(self, payload):
        return digest({k: payload.get(k) for k in ('temperature', 'cpu', 'gpu', 'power', 'memory')})

    def extract_values(self, payload):
        return numbers(payload)

    def observe_identity(self, record):
        """Optional contract observation after current stream/sequence checks."""
        pass

    def accept(self, record):
        t = record['mono_s']
        epoch = record.get('connection_epoch', 0)
        if self.epoch is not None and epoch < self.epoch:
            return self.reject('late_connection_callback')
        if self.epoch is not None and epoch != self.epoch:
            self.boundary('connection_epoch')
        self.epoch = epoch
        if self.last_event_t is not None and t < self.last_event_t:
            self.boundary('monotonic_regression')
            return self.reject('monotonic_regression')
        self.last_event_t = t
        p = record['payload']
        if not isinstance(p, dict):
            return self.invalid('invalid_object')
        m = p.get('telemetry_meta')
        if not isinstance(m, dict) or type(m.get('schema_version')) is not int or m.get('schema_version') != 1:
            return self.invalid('unsupported_schema')
        if m.get('time_basis') != 'collector_receive':
            return self.invalid('time_basis_unknown')
        stream, seq = m.get('stream_id'), m.get('sample_seq')
        if not isinstance(stream, str) or not stream or len(stream) > 128 or type(seq) is not int or seq <= 0:
            return self.invalid('no_sample_identity')
        if stream in self.retired:
            return self.reject('retired_stream')
        if self.stream != stream:
            if self.stream is not None:
                if len(self.retired) >= 128:
                    raise ValueError('source lifecycle budget exceeded')
                self.retired.add(self.stream)
            self.boundary('stream')
            self.stream, self.last_seq, self.key = stream, 0, None
            self.quarantined = False
        if seq < self.last_seq:
            self.boundary('sequence_regression')
            return self.reject('sequence_regression')
        age, timeout = m.get('sample_age_ms'), m.get('freshness_timeout_ms')
        self.timeout_ms = timeout if finite(timeout) and timeout > 0 else 0
        valid = m.get('fresh') is True and m.get('collector_state') == 'running' and finite(age) and age >= 0 and finite(timeout) and timeout > 0 and age < timeout
        try:
            if not isinstance(m.get('received_at'), str):
                raise ValueError('source receive time missing')
            stamp = datetime.fromisoformat(m['received_at'].replace('Z', '+00:00'))
            valid = valid and stamp.utcoffset() is not None
        except (ValueError, TypeError, KeyError):
            valid = False
        key = [self.c['orin']['source_id'], stream, seq]
        # Only measurements are compared. Sender timestamp and age may legitimately differ.
        try:
            if key != self.key:
                self.observe_identity(record)
            fp = self.measurement_fingerprint(p)
            v = self.extract_values(p)
        except (ValueError, TypeError, AttributeError):
            return self.invalid('invalid_numeric_contract')
        if key == self.key:
            self.anchor_age = max(self.anchor_age + (t - self.anchor_t) * 1000, age if finite(age) else 0)
            self.anchor_t = t
            if fp != self.fingerprint:
                self.boundary('identity_conflict')
                self.quarantined = True
                self.blocked = True
                return self.reject('identity_conflict')
            if not valid or self.anchor_age >= (timeout if finite(timeout) else 0):
                if not self.blocked:
                    self.boundary('stale_duplicate')
                self.blocked = True
            return self.reject('duplicate', age_lower_bound_ms=self.anchor_age)
        if seq > self.last_seq + 1 and self.last_seq:
            self.counts['missing_sequences'] += seq - self.last_seq - 1
        self.last_seq = seq
        self.key, self.fingerprint = key, fp
        self.anchor_t, self.anchor_age = t, age if finite(age) else 0
        self.blocked = not valid
        if not valid or v['tj'] is None:
            return self.invalid('stale_or_missing_tj')
        self.quarantined = False
        period = self.c['orin']['source_sample_interval_ms']
        gap = max(5, 3 * period / 1000) if period else 5
        if self.last_t is not None and t - self.last_t > gap:
            self.boundary('long_gap')
        self.last_t = t
        self.counts['new_samples'] += 1
        return {'accepted': True, 'reason': 'new_sample', 'key': key, 'segment': self.segment, 'values': v, 'age_lower_bound_ms': age, 'period_known': period is not None}

    def reject(self, reason, **extra):
        self.counts[reason] += 1
        return dict(accepted=False, reason=reason, segment=self.segment, **extra)

    def invalid(self, reason):
        self.boundary(reason)
        return self.reject(reason)
