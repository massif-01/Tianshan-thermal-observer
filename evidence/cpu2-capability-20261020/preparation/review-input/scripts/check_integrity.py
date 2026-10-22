from pathlib import Path
import hashlib, json, zipfile
R=Path('/mnt/data/tto_cpu2_independent_review_20261020'); results={}
def sha(b):return hashlib.sha256(b).hexdigest()
for typ in ('field','model'):
 root=R/'original'/typ;m=json.loads((root/'SHA256.json').read_text())
 items=m['files'] if typ=='model' else [dict(path=k,**v) for k,v in m.items()]
 bad=[]
 for x in items:
  p=root/x['path'];b=p.read_bytes()
  if len(b)!=x['bytes'] or sha(b)!=x['sha256']:bad.append(x['path'])
 actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
 listed={x['path'] for x in items}|{'SHA256.json'}
 results[typ]={'checked':len(items),'mismatches':bad,'unlisted':sorted(actual-listed),'missing':sorted(listed-actual)}
 assert not bad and not(actual-listed) and not(listed-actual)
root=R/'original/field';w=root/'candidate/tto_field_candidate-0.2.4+cpu.2-py3-none-any.whl'
manifest=json.loads((root/'source/src/tto_field/candidate-files.json').read_text())['files']
z2=zipfile.ZipFile(w);z1=zipfile.ZipFile(root/'source/vendor-reference/cpu1.whl')
changes=[]
for n,h in manifest.items():
 b=(root/'source/src'/n).read_bytes(); assert sha(b)==h and z2.read(n)==b
 if z1.read(n)!=b:changes.append(n)
results['candidate']={'sha256':sha(w.read_bytes()),'bytes':w.stat().st_size,'checked_files':len(manifest),'cpu1_changed':changes}
# Verify model code assembled into test-side bundle is truly same.
embedded=root/'model-adapter';standalone=R/'original/model';compared=0;extras=[]
for p in embedded.rglob('*'):
 if p.is_file():
  rel=p.relative_to(embedded)
  if not (standalone/rel).exists():
   extras.append(str(rel));continue
  assert (standalone/rel).read_bytes()==p.read_bytes(),str(rel);compared+=1
results['model_embedded']={'checked_files':compared,'identical':True,'extra':extras}
for outer,inner in [('TTO-CPU旁录与分析衔接-收尾报告.md',root/'TTO-CPU旁录与分析衔接-收尾报告.md'),('TTO-CPU旁录离线适配与失效撤销-模型线收尾报告.md',standalone/'TTO-CPU旁录离线适配与失效撤销-模型线收尾报告.md'),('操作卡.md',root/'操作卡.md')]:
 assert (Path('/mnt/data')/outer).read_bytes()==inner.read_bytes()
results['loose_reports_and_card_identical']=True
# Materialize accepted old dependency wheelhouse only for offline reuse.
old=Path('/mnt/data/TTO-CPU旁录与针对性补测-运行准备证据包.zip')
expected=json.loads((root/'candidate/dependency-reference.json').read_text())['accepted_cpu1_archive_sha256']
assert sha(old.read_bytes())==expected
with zipfile.ZipFile(old) as z:
 for name in z.namelist():
  if name.startswith('candidate/wheelhouse/') and not name.endswith('/'):
   p=R/'work/old-wheelhouse'/Path(name).name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(z.read(name))
results['old_archive_sha256']=expected
(R/'results/integrity.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
