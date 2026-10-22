"""Verify extracted bundle bytes; read-only, no network."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256.json').read_text())
for name,expected in manifest['files'].items():
 p=root/name;b=p.read_bytes()
 assert len(b)==expected['bytes'] and hashlib.sha256(b).hexdigest()==expected['sha256'],name
print(f"Verified {len(manifest['files'])} file hashes/lengths; this is integrity only, not field authorization.")
