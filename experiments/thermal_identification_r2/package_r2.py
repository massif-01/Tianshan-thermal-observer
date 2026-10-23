"""Package review evidence with SHA, using original archive references, never recursive inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

root=Path(__file__).resolve().parent;repo=root.parents[1];out=root/'runs/main'
files=[*root.glob('*.py'),root/'README-R2.md',root/'protected-before.json',root/'git-status-before.txt',
       root/'TTO-旧模型新数据检验与第二轮辨识报告.md']
files += [p for name in ('vendor','tests','runs/main','handoff') for p in (root/name).rglob('*') if p.is_file()
          and '__pycache__' not in p.parts and p.suffix not in ('.zip','.so')]
files=sorted(set(files))
patchfiles=[p for p in files if p.suffix in ('.py','.c') and 'handoff' not in p.parts]+[root/'README-R2.md']
patch=[]
for p in patchfiles:
    result=subprocess.run(['git','diff','--no-index','--','/dev/null',str(p.relative_to(repo))],cwd=repo,capture_output=True,text=True)
    assert result.returncode==1
    patch.append(result.stdout)
(root/'code.patch').write_text(''.join(patch));files.append(root/'code.patch')
blank=Path(tempfile.mkdtemp(prefix='tto-r2-final-patch-check-',dir='/private/tmp'))
check=subprocess.run(['git','apply','--check',str(root/'code.patch')],cwd=blank,capture_output=True,text=True)
assert check.returncode==0,(check.stdout,check.stderr)
(out/'patch-check.json').write_text(json.dumps({'status':'passed','command':['git','apply','--check','code.patch'],
    'patch_sha256':hashlib.sha256((root/'code.patch').read_bytes()).hexdigest(),'new_files_only':True},indent=2)+'\n')
if out/'patch-check.json' not in files:files.append(out/'patch-check.json')
manifest={'schema':'TTO-ID-R2-DELIVERY-SHA-v1','files':{str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}}
(root/'SHA256.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');files.append(root/'SHA256.json')
archive=root/'TTO-旧模型新数据检验与第二轮辨识证据包.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,str(p.relative_to(root)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,entry in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==entry['sha256'],name
receipt={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
         'members':len(files),'zip_crc':'passed','member_SHA':'all_passed','raw_archive_policy':'original handoff inputs SHA referenced, no recursive ZIP'}
(root/'delivery-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
