"""Verify extracted files, without device/network, dependency install or execution."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent
manifest=json.loads((r/'SHA256.json').read_text())
for n,x in manifest.items():
 p=r/n
 assert p.stat().st_size==x['bytes'],n
 assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],n
print(f'{len(manifest)} files: bytes and SHA256 pass')
