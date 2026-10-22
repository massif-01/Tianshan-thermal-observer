"""Apply the narrow report fix to a fresh copy of the accepted ZIP, then compare bytes."""
from pathlib import Path
import difflib,json,subprocess,tempfile,zipfile,hashlib,sys
ROOT=Path(__file__).absolute().parent.parent;FIX=ROOT/'review_fix_v1'
files=['README.md','refprep/compare.py','tests/test_report_sources.py'];chunks=[]
for name in files:
 before=FIX/'baseline'/name;after=ROOT/name
 rel='experiments/thermal_reference_v1/'+name
 chunks.append('diff --git a/'+rel+' b/'+rel+'\n')
 if not before.exists():chunks.append('new file mode 100644\n')
 chunks.extend(difflib.unified_diff(before.read_text().splitlines(keepends=True) if before.exists() else [],
   after.read_text().splitlines(keepends=True),fromfile='a/'+rel if before.exists() else '/dev/null',tofile='b/'+rel))
patch=FIX/'software-fix.patch';patch.write_text(''.join(chunks))
work=Path(tempfile.mkdtemp(prefix='tto-ref-review-patch-'));archive=ROOT/'TTO-测温记录准备与路线图同步-证据包.zip'
with zipfile.ZipFile(archive) as z:
 for member in z.namelist():
  rel=Path(member).relative_to('thermal_reference_v1')
  target=work/'experiments/thermal_reference_v1'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
commands=[]
for args in [['git','apply','--check',str(patch.absolute())],['git','apply',str(patch.absolute())]]:
 p=subprocess.run(args,cwd=work,capture_output=True,text=True);commands.append(dict(args=args,exit_code=p.returncode))
 assert p.returncode==0,p.stderr
for name in files:assert (work/'experiments/thermal_reference_v1'/name).read_bytes()==(ROOT/name).read_bytes()
command=[sys.executable,'-m','pytest','-q','experiments/thermal_reference_v1/tests','-o','cache_dir='+str(work/'cache')]
p=subprocess.run(command,cwd=work,capture_output=True,text=True)
(FIX/'applied-patch-tests.log').write_text(p.stdout+p.stderr);assert p.returncode==0 and '30 passed' in p.stdout,p.stdout+p.stderr
receipt=dict(status='pass',accepted_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
   patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),changed_paths=files,
   actual_apply_check_and_apply=commands,all_three_applied_files_equal_current_bytes=True,
   fresh_copy_tests='30 passed',test_interpreter=sys.executable,test_python=sys.version,fresh_copy_directory=str(work),
   note='Copied accepted ZIP only; no original worktree, model or device mutation')
(FIX/'patch-application-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
