"""Seal the authored candidate before build; no networking, no device actions."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1];src=root/'src';files={}
for p in sorted(src.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json') and p.name!='candidate-files.json':files[str(p.relative_to(src))]=hashlib.sha256(p.read_bytes()).hexdigest()
(src/'tto_field/candidate-files.json').write_text(json.dumps(dict(version='0.2.4+closeout.1',files=files),indent=2)+'\n')
print('Sealed',len(files),'source/data files')
