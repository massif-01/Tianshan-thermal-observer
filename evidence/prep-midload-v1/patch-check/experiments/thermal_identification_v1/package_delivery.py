"""Build and read back the bounded evidence ZIP, excluding raw archive recursion."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from common import read,write,sha,stamp


def main():
    root=Path(__file__).resolve().parent;repo=root.parents[1]
    before=read(root/'protected-before.json');changed=[]
    for name,expected in before['files'].items():
        p=repo/name
        if not p.is_file() or sha(p)!=expected:changed.append(name)
    assert not changed,changed
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();assert head==before['head']
    write(root/'protected-after.json',dict(checked_at=stamp(),head=head,checked_files=len(before['files']),changed=changed,
                branch=subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip(),
                no_git_write=True))
    source_files=sorted([p for p in root.iterdir() if p.suffix in ('.py','.c')]+[root/'README.md',root/'experiment-spec.json',root/'research-requirements.txt']+list((root/'tests').glob('*.py')))
    patch=b''
    for p in source_files:
        result=subprocess.run(['git','diff','--no-index','--','/dev/null',str(p.relative_to(repo))],cwd=repo,capture_output=True)
        assert result.returncode==1
        patch+=result.stdout
    (root/'research-code.patch').write_bytes(patch)
    with tempfile.TemporaryDirectory(prefix='tto-greybox-patch-') as tmp:
        subprocess.run(['git','init','-q',tmp],check=True)
        p=subprocess.run(['git','apply','--check',str(root/'research-code.patch')],cwd=tmp,capture_output=True,text=True)
        assert p.returncode==0,p.stderr
    write(root/'patch-verification.json',dict(new_files=len(source_files),sha256=sha(root/'research-code.patch'),git_apply_check='passed_in_empty_temporary_repository',applied_to_current_worktree=False))
    excluded={'handoff','inputs','preflight','deliverables','.matplotlib','.pytest_cache','test-tmp-numeric','test-tmp-contracts','test-tmp-related','test-tmp-final','__pycache__'}
    files={}
    for p in root.iterdir():
        if p.is_file() and p.suffix in ('.py','.c','.md','.json','.txt','.log','.patch') and p.name not in ('delivery-receipt.json',):files[p.name]=p
    for p in (root/'tests').glob('*.py'):files[str(p.relative_to(root))]=p
    for p in (root/'runs/main').rglob('*'):
        if p.is_file() and not any(part in ('input-cache','__pycache__') for part in p.relative_to(root/'runs/main').parts) and p.suffix!='.so':files[str(p.relative_to(root))]=p
    for p in (root/'handoff').rglob('*'):
        if p.is_file() and p.suffix!='.zip' and p.name!='verify_handoff.py':files[str(p.relative_to(root))]=p
    reference=root/'inputs/previous-exploration-evidence/sources/tto-reference'
    for p in reference.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:files['sources/tto-reference/'+str(p.relative_to(reference))]=p
    for name in ('conftest.py','test_review_repair.py','test_platform_curve.py'):
        files['sources/related-tests/'+name]=repo/'tests'/name
    fixture=repo/'tests/fixtures/review-repair'
    for p in fixture.rglob('*'):
        if p.is_file():files['sources/related-tests/fixtures/review-repair/'+str(p.relative_to(fixture))]=p
    hashes={name:dict(bytes=p.stat().st_size,sha256=sha(p)) for name,p in sorted(files.items())}
    dest=root/'deliverables';dest.mkdir(exist_ok=True)
    archive=dest/'TTO-首轮灰箱实际辨识与对照实验证据包.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,p in sorted(files.items()):z.write(p,name)
        z.writestr('SHA256.json',json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,entry in read_manifest(z).items():
            blob=z.read(name);assert len(blob)==entry['bytes'] and hashlib.sha256(blob).hexdigest()==entry['sha256']
        report='TTO-首轮灰箱实际辨识与对照实验报告.md'
        assert z.read(report)==(root/report).read_bytes()
    write(root/'delivery-receipt.json',dict(checked_at=stamp(),archive=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),
          verified_files=len(hashes),CRC='passed',report_sha256=sha(root/report),report_matches_archive=True,
          raw_archives_recursively_packaged=False,protected_files_unchanged=len(before['files'])))
    print(json.dumps(read(root/'delivery-receipt.json'),ensure_ascii=False,indent=2))


def read_manifest(z):return json.loads(z.read('SHA256.json'))


if __name__=='__main__':main()
