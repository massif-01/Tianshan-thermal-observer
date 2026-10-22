"""Read-only artifact integrity verification, no network or target device access."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256.json').read_text())
for name,v in manifest['files'].items():
 b=(root/name).read_bytes()
 assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],name
print(f"Verified {len(manifest['files'])} files. Integrity is not field authorization.")
