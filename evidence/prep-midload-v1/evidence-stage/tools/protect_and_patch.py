"""Hash protection and a reviewable patch against the local candidate base."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root=Path(__file__).resolve().parents[1];original=root.parents[1];c=root/'candidate'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def git(*args,cwd=c,check=True):return subprocess.run(['git',*args],cwd=cwd,check=check,capture_output=True)

baseline=json.loads((root/'original-files.json').read_text());changed=[]
for path,digest in baseline['files'].items():
    if not (original/path).is_file() or sha(original/path)!=digest:changed.append(path)
assert not changed,changed
head=git('rev-parse','HEAD',cwd=original).stdout.decode().strip();assert head==baseline['head']
old=json.loads((root/'frozen-greybox/SHA256.json').read_text())
for path,d in old.items():assert sha(root/'frozen-greybox'/path)==d['sha256'],path
base=json.loads((root/'baseline.json').read_text());assert git('rev-parse','HEAD').stdout.decode().strip()==base['base']
protected={p:d for p,d in base['source_hashes'].items() if p not in ('src/tto/collector.py','src/tto/__init__.py')}
assert all(sha(c/p)==d for p,d in protected.items())
assert git('diff','--','requirements-locked.txt','config','src/tto/defaults.json').stdout==b''
patch=git('diff','--binary').stdout
files=git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0');added=[]
for rel in sorted(p for p in files if p):
    if rel.endswith('.whl'):continue
    assert Path(rel).suffix in ('.py','.c','.json','.txt','.md'),rel
    part=git('diff','--no-index','--binary','--','/dev/null',rel,check=False)
    assert part.returncode in (0,1),(rel,part.stderr)
    patch+=part.stdout;added.append(rel)
patchfile=root/'results/midload-prep-v1.patch';patchfile.write_bytes(patch)
checkdir=root/'patch-check'
if not checkdir.exists():
    git('clone','--no-hardlinks',str(c),str(checkdir),cwd=root)
git('apply','--check',str(patchfile),cwd=checkdir)
git('apply',str(patchfile),cwd=checkdir)
tracked=[p for p in git('diff','--name-only').stdout.decode().splitlines() if p]
for rel in tracked+added:assert (checkdir/rel).read_bytes()==(c/rel).read_bytes(),rel
for p in (c/'wheels').glob('*0.2.3*.whl'):shutil.copy2(p,checkdir/'wheels'/p.name)
shutil.copy2(root/'conda-clean-final/installation.json',root/'results/conda-clean-install-identity.json')
result=dict(original_head=head,original_files_checked=len(baseline['files']),original_files_changed=changed,
    frozen_greybox_files_checked=len(old),frozen_greybox_unchanged=True,production_unchanged_files=protected,
    dependency_lock_unchanged=True,source_quality_control_qualification_evaluate_report_unchanged=True,
    candidate_branch=git('branch','--show-current').stdout.decode().strip(),candidate_head=base['base'],
    git_commit_push_PR_merge_performed=False,patch_sha256=sha(patchfile),patch_apply_check='passed',patch_applied_files_match=True,
    tracked_files=tracked,new_source_files=added,new_wheel_separate='wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl',
    private_site_config_in_patch=False)
write(root/'results/protection-and-patch.json',result)
print(json.dumps({k:result[k] for k in ('original_files_checked','original_files_changed','frozen_greybox_files_checked','patch_apply_check','candidate_branch')},ensure_ascii=False))
