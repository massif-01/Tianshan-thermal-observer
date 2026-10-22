from pathlib import Path
import json,hashlib,zipfile,difflib,argparse
R=Path(__file__).resolve().parents[1];S=R/'src';E=R.parents[1]/'evidence/cpu-runtime-threads-20261020'
ap=argparse.ArgumentParser();ap.add_argument('--reference-wheel',type=Path,default=E/'inputs/cpu2.whl');args=ap.parse_args()
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(args.reference_wheel)=='b265045129c67f62fd28bdb15f5f6288a29ef5a682a54175c1e998529bfe35fa'
files={str(p.relative_to(S)):h(p) for p in sorted(S.rglob('*')) if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts and p.name!='candidate-files.json'}
(S/'tto_field/candidate-files.json').write_text(json.dumps({'version':'0.2.4+cpu.3','files':files},indent=2)+'\n')
with zipfile.ZipFile(args.reference_wheel) as z:
 old=json.loads(z.read('tto_field/candidate-files.json'))['files'];changed={};patch=[]
 for n,sha in files.items():
  if old.get(n)!=sha:
   before=z.read(n).decode() if n in old else '';changed[n]={'before':old.get(n),'after':sha}
   patch+=list(difflib.unified_diff(before.splitlines(True),(S/n).read_text().splitlines(True),fromfile='cpu.2/'+n,tofile='cpu.3/'+n))
 for n in old:assert n in files
 protected=[n for n in old if n.startswith('tto/') or '/research/' in n or n.endswith(('cpu_source.py','cpu_transport.py','requester.py','projection.py','comm_bridge.py','scheduler.py')) or '/plans/' in n or '/upstream_comm/' in n]
 assert all(files[n]==old[n] for n in protected)
(R/'docs/cpu3.patch').write_text(''.join(patch));(R/'docs/source-identity.json').write_text(json.dumps({'version':'0.2.4+cpu.3','files':len(files),'changed':changed,'protected_files_unchanged':protected},indent=2)+'\n')
print('sealed',len(files),'changed',len(changed))
