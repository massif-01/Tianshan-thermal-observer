"""Seal this isolated source, not the user's mutable production checkout."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];src=root/'src';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(src)):sha(p) for p in sorted(src.rglob('*')) if p.is_file() and p.suffix in ('.py','.json') and p.name!='candidate-files.json' and '__pycache__' not in p.parts}
(src/'tto_field/candidate-files.json').write_text(json.dumps(dict(version='0.2.4+observe.6',files=files),indent=2)+'\n')
print(json.dumps(dict(version='0.2.4+observe.6',files=len(files),manifest_sha256=sha(src/'tto_field/candidate-files.json')),indent=2))
