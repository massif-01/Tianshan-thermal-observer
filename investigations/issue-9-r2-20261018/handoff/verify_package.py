from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256.json').read_text(encoding='utf-8'))
for x in manifest['files']:
 p=root/x['path']
 if not p.is_file():raise SystemExit('Missing: '+x['path'])
 b=p.read_bytes()
 if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']:raise SystemExit('Mismatch: '+x['path'])
print('Verified',len(manifest['files']),'files; integrity only, not software/field validation.')
