"""Bounded repair identity, preservation and incremental patch verification."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import tto

r=Path(__file__).resolve().parents[1];c=r.parent/'candidate';before=r/'original-reproduction/candidate/code'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
allowed={'README.md','pyproject.toml','install-manifest.json','scripts/install_tto.py','src/tto/__init__.py',
         'scripts/thermal_trials/health.py','scripts/thermal_trials/run_midload.py','scripts/thermal_trials/README.md',
         'scripts/thermal_trials/trial.py',
         'scripts/thermal_trials/tests/test_schedule.py',
         'docs/TTO中等负载测试操作卡.md','docs/TTO中等负载候选安装说明.md'}
original=json.loads((r/'before-code-sha256.json').read_text());changed=[p for p,h in original.items() if sha(c/p)!=h]
assert set(changed)==allowed,(changed,allowed)
new=['scripts/thermal_trials/tests/test_source_admission.py','scripts/thermal_trials/tests/test_installed_entry.py']
for rel in changed:
    for base,source in [('delta-before',before),('delta-after',c)]:
        p=r/base/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,p)
for rel in new:
    p=r/'delta-after'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(c/rel,p)
cmd=subprocess.run(['git','-c','core.quotePath=false','diff','--no-index','--binary','delta-before','delta-after'],cwd=r,capture_output=True)
assert cmd.returncode==1,cmd.stderr
patch=cmd.stdout.replace(b'a/delta-before/',b'a/').replace(b'b/delta-after/',b'b/').replace(b'a/delta-after/',b'a/')
patchfile=r/'results/R1-R2-against-0.2.3.patch';patchfile.write_bytes(patch)
check=r/'patch-check';shutil.copytree(before,check,dirs_exist_ok=True)
subprocess.run(['git','init',str(check)],check=True,capture_output=True)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=check,check=True,capture_output=True)
subprocess.run(['git','apply',str(patchfile)],cwd=check,check=True,capture_output=True)
assert all((check/p).read_bytes()==(c/p).read_bytes() for p in changed+new)
subprocess.run(['git','apply','--reverse',str(patchfile)],cwd=check,check=True,capture_output=True)
assert all((check/p).read_bytes()==(before/p).read_bytes() for p in changed)
core={str(p.relative_to(c)):sha(p) for p in (c/'src/tto').glob('*') if p.is_file()}
wheel=c/'wheels/tianshan_thermal_observer-0.2.4-py3-none-any.whl';installed=Path(tto.__file__).parent
conda=Path(json.loads((r/'conda-install/installation.json').read_text())['import_path'])
assert tto.__version__=='0.2.4' and Path(sys.prefix) in installed.parents and 'site-packages' in installed.parts
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    for n in z.namelist():
        if n.startswith('tto/') and not n.endswith('/'):
            rel=n[4:];assert z.read(n)==(c/'src/tto'/rel).read_bytes()==(installed/rel).read_bytes()==(conda/rel).read_bytes(),rel
runner={p.name:sha(p) for p in (c/'scripts/thermal_trials').iterdir() if p.is_file() and p.suffix in ('.py','.json','.md')}
assert all(sha(r/'conda-install/thermal_trials'/p)==h for p,h in runner.items())
bundle=r/'deliverables/TTO-v1-0.2.4-R1-R2返修-Conda安装候选.zip'
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    base='TTO-v1-0.2.4-Conda安装包/'
    manifest=json.loads(z.read(base+'install-manifest.json'))
    for rel,h in manifest['files'].items():
        assert hashlib.sha256(z.read(base+rel)).hexdigest()==h,rel
        if rel!='site/local-midload.json':assert z.read(base+rel)==(c/rel).read_bytes(),rel
primary=r.parents[2];pmap=json.loads((r.parent/'original-files.json').read_text())
primary_changes=[dict(path=p,previous_sha256=h,current_sha256=sha(primary/p)) for p,h in pmap['files'].items() if sha(primary/p)!=h]
assert all(Path(d['path']).name=='.DS_Store' for d in primary_changes),primary_changes
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=primary,text=True).strip()==pmap['head']
frozen=r.parent/'frozen-greybox';fm=json.loads((frozen/'SHA256.json').read_text())
assert all(sha(frozen/p)==d['sha256'] for p,d in fm.items())
previous=r.parent/'deliverables/TTO-软件修改与中等负载测试准备证据包.zip'
assert sha(previous)=='922200ee70fbed09874e0479ed16b45d7497303adf4e9dc5b13a51ded1d55ca2'
with zipfile.ZipFile(previous) as z:
    unchanged_outputs={n[8:]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('results/availability-v2/')}
assert all(sha(r.parent/'results'/p)==h for p,h in unchanged_outputs.items())
summary=dict(version='0.2.4',changed_previous_source_files=changed,new_tests=new,core_changed_from_0_2_3=['src/tto/__init__.py'],
    source_quality_TTL_collector_AB_unchanged=True,original_source_files_checked=len(original),original_primary_files_checked=len(pmap['files']),
    primary_previous_snapshot_changes=primary_changes,primary_material_files_unchanged=True,
    frozen_research_files_checked=len(fm),frozen_research_unchanged=True,AB_outputs_unchanged=unchanged_outputs,
    source_wheel_venv_conda_identical=True,wheel_sha256=sha(wheel),bundle_sha256=sha(bundle),bundle_manifest_files=len(manifest['files']),
    runner_source_installed_sha256=runner,patch_sha256=sha(patchfile),patch_paths=len(changed)+len(new),patch_forward_reverse='passed',
    previous_package_preserved=True,previous_evidence_sha256=sha(previous),runtime=dict(python=sys.version,import_path=str(installed),non_editable=True),
    conda_installation=json.loads((r/'conda-install/installation.json').read_text()),
    git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c,text=True).strip(),git_branch=subprocess.check_output(['git','branch','--show-current'],cwd=c,text=True).strip(),
    no_commit_push_PR_merge=True,field_executed=False,model_training_executed=False)
write(r/'results/repair-identity-and-preservation.json',summary)
decisions=[]
for p in sorted((r/'test-delivery').rglob('decision.json')):
    o=json.loads(p.read_text());s=o['snapshot'];decisions.append(dict(t=o['at'],current_ready=s['current_ready'],continuous_60s=s['continuous_60s'],
        new_requests=len(o['requests']),source_accepted_t=s['latest']['source_accepted_t'],source_age_ms=s['latest']['source_age_ms'],
        source_deadline=s['latest']['source_valid_until'],abnormal=s['abnormal']))
write(r/'results/R1-cross-summary.json',sorted(decisions,key=lambda d:d['t']))
shutil.copy2(r/'conda-install/tto-midload',r/'results/installed-tto-midload.sh')
print(json.dumps({k:summary[k] for k in ('version','patch_paths','patch_forward_reverse','original_primary_files_checked','frozen_research_files_checked','source_wheel_venv_conda_identical')},ensure_ascii=False))
