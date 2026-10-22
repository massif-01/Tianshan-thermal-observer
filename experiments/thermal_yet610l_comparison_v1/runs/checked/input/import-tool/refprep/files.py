from pathlib import Path
import datetime as dt
import hashlib
import json


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def lines(path):
    path=Path(path)
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s] if path.exists() else []


def append(path, value):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n')


def dump_lines(path, values):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for value in values:f.write(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n')
