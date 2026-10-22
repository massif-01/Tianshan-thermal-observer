import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def seal(obj):
    obj = dict(obj)
    obj['sha256'] = digest(obj)
    return obj


def verify_seal(obj):
    body = {k: v for k, v in obj.items() if k != 'sha256'}
    if obj.get('sha256') != digest(body):
        raise ValueError('artifact hash mismatch')
    return obj
