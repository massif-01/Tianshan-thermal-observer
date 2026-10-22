import hashlib,json,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];H=R/'handoff';checks=[]
for entry in json.loads((H/'SOURCE-MANIFEST.json').read_text()):
 if 'path' in entry:b=(H/entry['path']).read_bytes();label=entry['path']
 else:
  with zipfile.ZipFile(H/entry['archive']) as z:b=z.read(entry['member'])
  label=entry['archive']+'!'+entry['member']
 assert hashlib.sha256(b).hexdigest()==entry['sha256'],label;assert len(b)==entry['bytes'];checks.append(label)
runs={}
for key in ['Y-raw','M-raw']:
 d=next((R/'sources'/key).rglob('manifest.json')).parent;manifest=json.loads((d/'files.json').read_text());n=0
 for name,digest in manifest.items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==digest,name;n+=1
 runs[key]={'files_verified':n,'observer_run_id':json.loads((d/'manifest.json').read_text())['observer_run_id']}
(R/'analysis/integrity.json').write_text(json.dumps({'source_manifest_checked':checks,'run_file_manifests':runs,'integrity_not_field_validation':True},ensure_ascii=False,indent=2)+'\n');print('verified sources',len(checks),runs)
