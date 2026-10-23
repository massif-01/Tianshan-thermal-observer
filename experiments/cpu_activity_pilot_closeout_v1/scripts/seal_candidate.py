from pathlib import Path
import difflib,hashlib,json,zipfile
R=Path(__file__).resolve().parents[1];S=R/'src';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(S)):h(p) for p in sorted(S.rglob('*')) if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts and p.name!='candidate-files.json'}
(S/'tto_field/candidate-files.json').write_text(json.dumps(dict(version='0.2.4+cpu.2',files=files),indent=2)+'\n')
w=R/'vendor-reference/cpu1.whl';assert h(w)=='3a0d118a50a93a8d77a3dc714a546bd98d28f7b9254acb69084da9806628ac92'
with zipfile.ZipFile(w) as z:
 old=json.loads(z.read('tto_field/candidate-files.json'))['files'];changed={};diff=[]
 for name,digest in old.items():
  if h(S/name)!=digest:
   changed[name]=dict(before=digest,after=h(S/name))
   diff+=list(difflib.unified_diff(z.read(name).decode().splitlines(True),(S/name).read_text().splitlines(True),fromfile='cpu.1/'+name,tofile='cpu.2/'+name))
 assert set(changed)=={'tto_field/__init__.py','tto_field/cpu_pilot.py','tto_field/cpu_transport.py','tto_field/cpu_interface.py'}
(R/'docs/cpu2.patch').write_text(''.join(diff))
(R/'docs/source-identity.json').write_text(json.dumps(dict(cpu1_wheel_sha256=h(w),files=len(files),changed=changed,native_unchanged=True,runtime_unchanged=True,activity_model_unchanged=True,requester_unchanged=True,profile_unchanged=True),indent=2)+'\n')
print('sealed',len(files),'changed',len(changed))
