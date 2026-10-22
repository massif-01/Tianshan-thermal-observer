import hashlib
import json
import math
import os
import time
import sys
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
import psutil


def utc():
    return datetime.now(timezone.utc).isoformat()


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def short(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


@lru_cache(maxsize=1)
def boot_id():
    p = Path('/proc/sys/kernel/random/boot_id')
    if p.exists():return p.read_text().strip()
    # Only self-built tests may supply an explicit local clock identity on a
    # sandboxed non-Linux host. It must never authorize live observations.
    if sys.platform != 'linux' and os.environ.get('TTO_WEB_TEST_BOOT_ID'):
        return 'test:'+os.environ['TTO_WEB_TEST_BOOT_ID']
    raise ValueError('source clock identity unavailable; Linux boot_id required')


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix('.tmp')
    fd = os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False)
    os.replace(tmp, path)


def load(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
