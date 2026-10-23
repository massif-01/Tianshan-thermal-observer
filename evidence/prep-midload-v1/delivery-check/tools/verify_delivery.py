"""Verify extracted evidence bytes; no imports of runner/model/network code."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'SHA256.json').read_text());count=0
for rel,item in manifest.items():
    p=root/rel;assert p.is_file() and p.stat().st_size==item['bytes'],rel
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    assert h.hexdigest()==item['sha256'],rel;count+=1
print(json.dumps({'files_verified':count,'SHA256':'passed','connected':False}))
