"""Small, offline-only experiment utilities."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    def cast(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        if isinstance(x, Path):
            return str(x)
        raise TypeError(type(x))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=cast, allow_nan=False)+'\n')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def seconds(utc):
    return datetime.fromisoformat(utc).timestamp()


def balanced_weights(rows):
    """Equal runs, equal present macroclasses, then actual supported time."""
    w = np.zeros(len(rows))
    runs = sorted({r['run'] for r in rows if r['duration'] > 0})
    for run in runs:
        classes = sorted({r['macro'] for r in rows if r['run'] == run and r['duration'] > 0})
        for macro in classes:
            ids = [i for i, r in enumerate(rows) if r['run'] == run and r['macro'] == macro]
            dt = np.array([rows[i]['duration'] for i in ids])
            if dt.sum():
                w[ids] = dt/dt.sum()/len(classes)/len(runs)
    return w
