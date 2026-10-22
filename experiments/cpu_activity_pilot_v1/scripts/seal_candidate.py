from pathlib import Path
import hashlib,json,difflib,zipfile
ROOT=Path(__file__).resolve().parents[1];src=ROOT/'src'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={str(p.relative_to(src)):h(p) for p in sorted(src.rglob('*')) if p.is_file() and p.suffix in ('.py','.json') and p.name!='candidate-files.json' and '__pycache__' not in p.parts}
(src/'tto_field/candidate-files.json').write_text(json.dumps({'version':'0.2.4+cpu.1','files':manifest},indent=2)+'\n')
# compare with the immutable accepted wheel, not the mutable checkout.
wheel=ROOT/'vendor-reference/accepted-closeout2.whl'
assert h(wheel)=='de1c67c143c97733b9c14501253ef0216157462c77eff7bbee2124e146d5d9db'
with zipfile.ZipFile(wheel) as z:
 baseline=json.loads(z.read('tto_field/candidate-files.json'))['files'];changed={};patch=[]
 for name,old_hash in baseline.items():
  if h(src/name)!=old_hash:
   changed[name]={'before':old_hash,'after':h(src/name)}
   patch.extend(difflib.unified_diff(z.read(name).decode().splitlines(True),(src/name).read_text().splitlines(True),fromfile='closeout.2/'+name,tofile='cpu.1/'+name))
 assert set(changed)=={'tto_field/__init__.py','tto_field/runtime.py','tto_field/gate.py'}
 for name in ['tto_field/research/models/primary.json','tto_field/research/observer-spec.json']:
  assert h(src/name)==baseline[name]
(ROOT/'docs/closeout2-extension.patch').write_text(''.join(patch))
(ROOT/'docs/source-identity.json').write_text(json.dumps(dict(accepted_wheel_sha256=h(wheel),accepted_runtime_files=len(baseline),changed=changed,unchanged_accepted_files=len(baseline)-len(changed),native_source_unchanged=True,fixed_anchors_plan_unchanged=True,requester_unchanged=True,I02_unchanged=True,model_unchanged=True,spec_unchanged=True,new_files=sorted(set(manifest)-set(baseline))),indent=2)+'\n')
print('SEALED',len(manifest),'files; old42:',len(baseline)-len(changed),'unchanged,3 explicit extension changes')
