"""Read-only byte checks; no network, imports of runner or model fitting."""
import hashlib
import json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
manifest=json.loads((r/'SHA256.json').read_text())
for p,d in manifest.items():
    f=r/p;assert f.is_file() and f.stat().st_size==d['bytes'],p
    h=hashlib.sha256()
    with f.open('rb') as stream:
        for b in iter(lambda:stream.read(1048576),b''):h.update(b)
    assert h.hexdigest()==d['sha256'],p
print(json.dumps(dict(files_verified=len(manifest),SHA256='passed',connected=False)))
