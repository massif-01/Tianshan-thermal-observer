import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def read(p):
    return json.loads(Path(p).read_text())


def lines(p):
    if not Path(p).exists():return []
    return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]


def write(p,obj):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def jsonl(p,rows):
    with Path(p).open('w') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
