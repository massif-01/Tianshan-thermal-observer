"""Four finite input profiles; one definition for recording and modeling."""
from datetime import datetime
from .features import TJ_COLUMNS, FULL_REQUIRED
from .quality import numbers
from .util import digest, finite

CONTRACT = 'TTO-PLATFORM-CURVE-v2.0'
FAMILIES = {'jetson_orin': ('tegra234', 'tegrastats'), 'jetson_thor': ('tegra264', 'nvml')}
TEMPERATURES = {'jetson_orin': ('cpu', 'gpu', 'soc0', 'soc1', 'soc2'),
                'jetson_thor': ('cpu', 'gpu', 'soc012', 'soc345')}
RAILS = {'jetson_orin': ('vdd_gpu_soc', 'vdd_cpu_cv', 'vin_sys_5v0'),
         'jetson_thor': ('vdd_gpu', 'vdd_cpu_soc_mss', 'vin_sys_5v0')}
UNITS = {'temperature': 'C', 'power': 'W', 'gpu_busy': 'percent', 'cpu_freq': 'MHz', 'duty': 'logical_percent'}
PROFILES = {}
for family in FAMILIES:
    for scope in ('auto', 'curve'):
        id_ = family.removeprefix('jetson_') + '_' + scope + '_v2'
        fields = tuple('temp_' + x for x in TEMPERATURES[family]) + ('cpu_usage', 'cpu_freq', 'cpu_reported_cores', 'gpu_busy') + RAILS[family]
        required = list(FULL_REQUIRED if scope == 'auto' else FULL_REQUIRED[:-1])
        groups = {f: [f, f+'_mean_30', f+'_mean_120'] for f in fields}
        PROFILES[id_] = {'family': family, 'control_scope': scope, 'required': required,
                         'optional': groups, 'columns': TJ_COLUMNS + required + [c for g in groups.values() for c in g]}
assert [len(PROFILES[p]['columns']) for p in ('orin_auto_v2', 'orin_curve_v2', 'thor_auto_v2', 'thor_curve_v2')] == [54, 53, 51, 50]


GPU_FIELDS = {'schema_version', 'utilization_pct', 'source', 'status', 'sampled_at_utc',
              'age_at_telemetry_receive_ms', 'sample_interval_ms', 'freshness_timeout_ms', 'device_uuid'}


def positive_ms(value):
    return type(value) is int and value > 0


def new_contract(payload):
    g = payload.get('gpu')
    return 'platform' in payload or isinstance(g, dict) and bool(GPU_FIELDS.intersection(g))


def source_period(payload, configured):
    if not new_contract(payload):
        return {'period_ms': configured, 'basis': 'operator_legacy' if configured else 'unknown', 'reason': None if configured else 'legacy_source_period_unknown'}
    reported = (payload.get('telemetry_meta') or {}).get('source_sample_interval_ms')
    if not positive_ms(reported):
        return {'period_ms': None, 'basis': 'wire_telemetry_meta', 'reason': 'source_period_missing_or_invalid'}
    return {'period_ms': reported, 'basis': 'wire_telemetry_meta', 'reason': 'configured_source_period_conflict' if configured is not None and configured != reported else None}


def identified_family(payload):
    p = payload.get('platform')
    if not isinstance(p, dict) or type(p.get('schema_version')) is not int or p['schema_version'] != 1:
        return None, 'platform_contract_missing_or_invalid'
    family = p.get('family')
    compatible = p.get('compatible')
    if not isinstance(compatible, list) or not all(isinstance(x, str) for x in compatible):
        return None, 'platform_evidence_conflict'
    matches = [token for token in ('nvidia,tegra234', 'nvidia,tegra264') if token in compatible]
    if family == 'unknown':
        if p.get('soc') is None and p.get('identification_source') is None and p.get('gpu_backend') == 'unavailable' and len(matches) != 1:
            return None, 'platform_unconfirmed'
        return None, 'platform_evidence_conflict'
    if family not in FAMILIES:
        return None, 'platform_evidence_conflict'
    soc, backend = FAMILIES[family]
    if p.get('soc') != soc or p.get('gpu_backend') != backend or p.get('identification_source') != 'device_tree_compatible' or matches != ['nvidia,'+soc]:
        return None, 'platform_evidence_conflict'
    return family, None


def platform_contract(payload, source_period_ms):
    family, reason = identified_family(payload)
    if family is None: return None, reason
    if not positive_ms(source_period_ms): return None, 'source_period_missing_or_invalid'
    g = payload.get('gpu')
    g = g if isinstance(g, dict) else {}
    period, timeout = g.get('sample_interval_ms'), g.get('freshness_timeout_ms')
    if not positive_ms(period) or not positive_ms(timeout) or timeout != max(5000, 3*period):
        period = timeout = None
    soc, backend = FAMILIES[family]
    return {'schema_version': 2, 'processing_contract': CONTRACT, 'platform_schema': 1,
            'family': family, 'soc': soc, 'gpu_backend': backend, 'gpu_schema': 1,
            'source_period_ms': source_period_ms, 'source_period_basis': 'wire_telemetry_meta',
            'gpu_period_ms': period, 'gpu_timeout_ms': timeout, 'units': dict(UNITS)}, None


def profile_id(contract, scope):
    return contract['family'].removeprefix('jetson_')+'_'+scope+'_v2' if contract and scope in ('auto', 'curve') else None


def utc_stamp(value):
    try:
        return isinstance(value, str) and value.endswith(('Z', '+00:00')) and datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset().total_seconds() == 0
    except (ValueError, TypeError, AttributeError):
        return False


def uniform_gpu(payload, family, t):
    """Validate the sealed state, then calculate its consumer age/deadline."""
    g = payload.get('gpu') or {}
    empty = {'value': None, 'reason': None, 'source_status': None, 'age_lower_bound_ms': None,
             'timeout_ms': None, 'sample_interval_ms': None, 'device_uuid': None, 'valid_until': None, 'contract_valid': False}
    if not isinstance(g, dict): return dict(empty, reason='gpu_invalid_object')
    m = payload.get('telemetry_meta') or {}
    outer = m.get('sample_age_ms')
    if not new_contract(payload):
        value, ttl = g.get('gr3d_freq'), m.get('freshness_timeout_ms')
        reason = None
        if not finite(value) or not 0 <= value <= 100: reason = 'legacy_gpu_missing_or_invalid'
        elif not finite(outer) or outer < 0 or not finite(ttl) or ttl <= 0: reason = 'gpu_age_invalid'
        elif outer >= ttl: reason = 'gpu_effective_stale'
        return dict(empty, value=value if reason is None else None, reason=reason, source_status='legacy_no_independent_status', age_lower_bound_ms=outer, timeout_ms=ttl,
                    valid_until=t+(ttl-outer)/1000 if reason is None else None)
    status, value = g.get('status'), g.get('utilization_pct')
    period, ttl, base = g.get('sample_interval_ms'), g.get('freshness_timeout_ms'), g.get('age_at_telemetry_receive_ms')
    result = dict(empty, source_status=status, sample_interval_ms=period, timeout_ms=ttl, device_uuid=g.get('device_uuid'))
    def failed(reason):return dict(result, reason=reason)
    if not GPU_FIELDS.issubset(g) or type(g.get('schema_version')) is not int or g['schema_version'] != 1:
        return failed('gpu_contract_missing_or_invalid')
    backend = FAMILIES.get(family, (None, 'unavailable'))[1]
    if status not in ('valid', 'stale', 'error', 'unavailable'): return failed('gpu_status_invalid')
    if backend == 'unavailable':
        if period is not None or ttl is not None: return failed('gpu_period_or_timeout_invalid')
    elif not positive_ms(period) or not positive_ms(ttl) or ttl != max(5000, 3*period):
        return failed('gpu_period_or_timeout_invalid')
    if family == 'jetson_orin' and positive_ms(m.get('source_sample_interval_ms')) and period != m['source_sample_interval_ms']:
        return failed('gpu_orin_source_period_mismatch')
    expected_source = 'unavailable' if status == 'unavailable' else backend
    if g['source'] != expected_source or status != 'unavailable' and backend == 'unavailable':
        return failed('gpu_source_platform_mismatch')
    uuid = g['device_uuid']
    if backend == 'nvml':
        if uuid is not None and (not isinstance(uuid, str) or not uuid): return failed('gpu_device_identity_invalid')
        if status in ('valid', 'stale') and uuid is None: return failed('gpu_device_identity_missing')
    elif uuid is not None: return failed('gpu_device_identity_invalid')
    if status in ('error', 'unavailable'):
        if value is not None or g['sampled_at_utc'] is not None or base is not None:
            return failed('gpu_state_fields_inconsistent')
        return dict(result, reason='gpu_source_'+status, contract_valid=True)
    if not utc_stamp(g['sampled_at_utc']): return failed('gpu_timestamp_invalid')
    if not finite(base) or base < 0: return failed('gpu_age_invalid')
    if status == 'stale':
        if value is not None or base < ttl: return failed('gpu_state_fields_inconsistent')
        return dict(result, reason='gpu_source_stale', age_lower_bound_ms=base+outer if finite(outer) else None, contract_valid=True)
    if not finite(value) or not 0 <= value <= 100: return failed('gpu_value_invalid')
    if base >= ttl: return failed('gpu_state_fields_inconsistent')
    old = g.get('gr3d_freq')
    if backend == 'tegrastats' and finite(old) and 0 <= old <= 100 and old != value:
        return failed('gpu_same_source_value_conflict')
    age = base+outer if finite(outer) and outer >= 0 else None
    if age is None: return failed('gpu_age_invalid')
    if age >= ttl: return dict(result, reason='gpu_effective_stale', age_lower_bound_ms=age, contract_valid=True)
    return dict(result, value=value, age_lower_bound_ms=age, valid_until=t+(ttl-age)/1000, contract_valid=True)


def lifecycle_signature(payload):
    g, m = payload.get('gpu') or {}, payload.get('telemetry_meta') or {}
    g = g if isinstance(g, dict) else {}
    return digest({'platform': payload.get('platform'), 'source_period_ms': m.get('source_sample_interval_ms'),
                   'gpu_period_ms': g.get('sample_interval_ms'), 'gpu_timeout_ms': g.get('freshness_timeout_ms')})


def lifecycle_evidenced(payload):
    family, reason = identified_family(payload)
    if reason not in (None, 'platform_unconfirmed'): return False
    m, g = payload.get('telemetry_meta') or {}, payload.get('gpu') or {}
    if not positive_ms(m.get('source_sample_interval_ms')) or not isinstance(g, dict): return False
    if family is None: return g.get('sample_interval_ms') is None and g.get('freshness_timeout_ms') is None
    period, ttl = g.get('sample_interval_ms'), g.get('freshness_timeout_ms')
    return positive_ms(period) and positive_ms(ttl) and ttl == max(5000, 3*period)


def platform_numbers(payload, family):
    # Keep the existing CPU aggregation and target definition exactly.
    values = numbers(dict(payload, gpu={}))
    for key in list(values):
        if key.startswith('temp_') or key in RAILS['jetson_orin']:
            del values[key]
    temp, power = payload.get('temperature') or {}, payload.get('power') or {}
    for k in TEMPERATURES.get(family, ()):
        values['temp_'+k] = temp.get(k) if finite(temp.get(k)) else None
    for k in RAILS.get(family, ()):
        rail = power.get(k) or {}
        value = rail.get('current')
        values[k] = value/1000 if finite(value) and value >= 0 and rail.get('unit') == 'mW' else None
    values['gpu_busy'] = None
    return values


def compatible_contract(expected, actual, gpu_selected=True):
    if not isinstance(expected, dict) or not isinstance(actual, dict): return False
    # A model without gpu_busy does not require a currently evidenced GPU cadence.
    keys = set(expected) | set(actual)
    if not gpu_selected:
        keys -= {'gpu_period_ms', 'gpu_timeout_ms'}
    return digest({k: expected.get(k) for k in keys}) == digest({k: actual.get(k) for k in keys})


def validate_profile(identity):
    p = PROFILES.get(identity.get('feature_profile_id'))
    contract = identity.get('input_contract')
    if (p is None or not isinstance(contract, dict) or contract.get('family') != p['family']
            or identity.get('control_scope') != p['control_scope'] or identity.get('input_contract_sha256') != digest(contract)):
        raise ValueError('platform/profile/input contract mismatch')
    if type(contract.get('schema_version')) is not int or contract['schema_version'] != 2 or contract.get('processing_contract') != CONTRACT:
        raise ValueError('unsupported platform input contract')
    soc, backend = FAMILIES[p['family']]
    if (set(contract) != {'schema_version', 'processing_contract', 'platform_schema', 'family', 'soc', 'gpu_backend', 'gpu_schema', 'source_period_ms', 'source_period_basis', 'gpu_period_ms', 'gpu_timeout_ms', 'units'}
            or contract['soc'] != soc or contract['gpu_backend'] != backend or type(contract['platform_schema']) is not int or contract['platform_schema'] != 1
            or type(contract['gpu_schema']) is not int or contract['gpu_schema'] != 1 or contract['units'] != UNITS
            or not positive_ms(contract['source_period_ms']) or contract['source_period_basis'] != 'wire_telemetry_meta'
            or (contract['gpu_period_ms'] is not None and not positive_ms(contract['gpu_period_ms']))
            or (contract['gpu_timeout_ms'] is not None and (not positive_ms(contract['gpu_timeout_ms']) or contract['gpu_period_ms'] is None or contract['gpu_timeout_ms'] != max(5000, 3*contract['gpu_period_ms'])))):
        raise ValueError('invalid platform units/backend/period contract')
    return p
