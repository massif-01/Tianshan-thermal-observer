"""Closed configuration contract; credentials never enter snapshots."""
import copy
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit
from .util import canonical, digest, finite, read_json

DEFAULTS = Path(__file__).with_name('defaults.json')
ENV = {
    'TTO_ORIN_URL': ('orin', 'base_url'),
    'TTO_TIANSHAN_URL': ('tianshan', 'base_url'),
    'TTO_DATA_ROOT': ('storage', 'data_root'),
    'TTO_DURATION_S': ('run', 'default_duration_s'),
    'TTO_SOURCE_INTERVAL_MS': ('orin', 'source_sample_interval_ms'),
    'TTO_SOURCE_INTERVAL_EVIDENCE': ('orin', 'source_interval_evidence'),
    'TTO_ORIN_HEADERS_FILE': ('orin', 'headers_file'),
    'TTO_TIANSHAN_HEADERS_FILE': ('tianshan', 'headers_file'),
}


def merge(base, supplied, prefix=''):
    if not isinstance(supplied, dict):
        raise ValueError(f'{prefix}: object required')
    for key, v in supplied.items():
        if key not in base:
            raise ValueError(f'unknown configuration key: {prefix}{key}')
        if isinstance(base[key], dict):
            merge(base[key], v, prefix + key + '.')
        else:
            base[key] = v


def endpoint(v):
    if v is None:
        return
    if not isinstance(v, str):
        raise ValueError('endpoint must be an explicit http(s) origin')
    try:
        u = urlsplit(v)
        port = u.port
    except ValueError:
        raise ValueError('invalid endpoint') from None
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('', '/') or (port is not None and not 1 <= port <= 65535):
        raise ValueError('endpoint must be http(s) origin without credentials/query/path')


def load_config(path=None, overrides=None, environ=None):
    c = read_json(DEFAULTS)
    if path:
        merge(c, read_json(path))
    env = os.environ if environ is None else environ
    for name, (section, field) in ENV.items():
        if name in env:
            v = env[name]
            c[section][field] = v
    for key, value in (overrides or {}).items():
        if value is not None:
            section, field = key.split('.')
            c[section][field] = value
    for section, field in (('run', 'default_duration_s'), ('orin', 'source_sample_interval_ms')):
        v = c[section][field]
        if isinstance(v, str):
            try:
                v = float(v)
                if field == 'source_sample_interval_ms' and v.is_integer():
                    v = int(v)
                c[section][field] = v
            except ValueError:
                raise ValueError(f'{section}.{field}: numeric value required') from None
    validate(c)
    return c


def validate(c):
    defaults = read_json(DEFAULTS)
    # Frozen experiment and safety values cannot be weakened by editing a config.
    fixed = [('schema_version',), ('mode',)]
    for section in ('security', 'model', 'features'):
        fixed += [(section, k) for k in defaults[section]]
    fixed += [('network', k) for k in ('max_inflight_esp32', 'follow_redirects')]
    fixed += [('storage', 'overwrite_existing'), ('run', 'single_instance')]
    fixed += [('tianshan', k) for k in ('fan_id', 'fan_status_path', 'temp_status_path')]
    fixed += [('orin', k) for k in ('event', 'namespace', 'socketio_path')]
    for keys in fixed:
        a, b = c, defaults
        for k in keys:
            a, b = a[k], b[k]
        if a != b or type(a) is not type(b):
            raise ValueError('frozen contract: ' + '.'.join(keys))
    for section in ('orin', 'tianshan'):
        endpoint(c[section]['base_url'])
        if not isinstance(c[section]['source_id'], str) or not 1 <= len(c[section]['source_id']) <= 80:
            raise ValueError('source_id must be a short string')
        for field in ('headers_file', 'ca_file'):
            v = c[section][field]
            if v is not None and (not isinstance(v, str) or not Path(v).is_file()):
                raise ValueError(f'{section}.{field}: file required')
    if c['storage']['data_root'] is not None and (not isinstance(c['storage']['data_root'], str) or not c['storage']['data_root']):
        raise ValueError('storage.data_root must be a local directory path')
    if c['orin']['transports'] not in (['websocket'], ['polling']):
        raise ValueError('select exactly websocket or explicitly polling')
    period = c['orin']['source_sample_interval_ms']
    if period is not None and (type(period) is not int or period <= 0):
        raise ValueError('source interval must be positive integer milliseconds')
    if period is not None and not c['orin']['source_interval_evidence']:
        raise ValueError('source interval needs an evidence reference')
    for section in ('network', 'storage', 'run', 'resources'):
        for k, v in c[section].items():
            d = defaults[section][k]
            if isinstance(d, (int, float)) and not isinstance(d, bool):
                if not finite(v) or v <= 0 or (type(d) is int and section != 'run' and type(v) is not int):
                    raise ValueError(f'{section}.{k}: positive finite value required')
    if not 0 < c['network']['reconnect_jitter_ratio'] <= 1:
        raise ValueError('invalid reconnect jitter')
    for k in ('fan_poll_interval_s', 'temp_poll_interval_s'):
        if not finite(c['tianshan'][k]) or c['tianshan'][k] < defaults['tianshan'][k]:
            raise ValueError('polling cannot be faster than frozen defaults')
    for k in ('max_business_payload_bytes',):
        if c['network'][k] > defaults['network'][k]:
            raise ValueError('payload budget cannot be raised')
    for k in ('queue_max_items', 'queue_max_bytes', 'chunk_bytes', 'run_max_bytes'):
        if c['storage'][k] > defaults['storage'][k]:
            raise ValueError('storage budget cannot be raised')
    if c['storage']['run_max_bytes'] < 65536:
        raise ValueError('run budget must also accommodate metadata (at least 64KiB)')
    if c['run']['max_duration_s'] > 14400 or c['run']['default_duration_s'] > c['run']['max_duration_s']:
        raise ValueError('duration exceeds four-hour budget')
    if c['network']['reconnect_max_s'] < c['network']['reconnect_initial_s']:
        raise ValueError('invalid reconnect delay range')
    if c['network']['reconnect_max_attempts'] > 10:
        raise ValueError('reconnect attempt budget cannot be raised')


def public_config(c):
    out = copy.deepcopy(c)
    for section in ('orin', 'tianshan'):
        out[section]['headers_file'] = 'local_protected_file' if c[section]['headers_file'] else None
        out[section]['ca_file'] = 'explicit_CA' if c[section]['ca_file'] else None
    return out


def headers(c, section):
    p = c[section]['headers_file']
    if not p:
        return {}
    p = Path(p)
    if p.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError('credential file must be private (chmod 600)')
    if p.stat().st_size > 16384:
        raise ValueError('credential file too large')
    h = read_json(p)
    if not isinstance(h, dict) or not all(isinstance(k, str) and isinstance(v, str) and '\n' not in k + v and '\r' not in k + v for k, v in h.items()):
        raise ValueError('invalid credential headers')
    if any(k.lower() in ('host', 'content-length', 'transfer-encoding') for k in h):
        raise ValueError('transport headers are not credentials')
    return h


def require_live(c, duration):
    if not finite(duration) or not 0 < duration <= c['run']['max_duration_s']:
        raise ValueError('duration must be bounded by configured maximum')
    if not all(c[s]['base_url'] for s in ('orin', 'tianshan')):
        raise ValueError('请先在本机配置两路明确端点；没有默认设备地址。')
    if c['orin']['source_sample_interval_ms'] is None:
        # Collection is allowed, but model eligibility remains disabled.
        return 'source_period_unknown'
    return 'source_period_user_evidence'
