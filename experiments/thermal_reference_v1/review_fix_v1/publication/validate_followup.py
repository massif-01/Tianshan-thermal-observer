"""Final independent gate for the actual documentation-only follow-up diff."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).absolute().parent
REPO=Path('/private/tmp/tto-ref-prep-docs-20261014-wpye8z78')
FILES=['README.md','PROGRESS.md','docs/roadmap/TTO-roadmap.md','docs/research/TTO-research-status-20261014.md']
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True)
base=git('rev-parse','origin/main').strip()
assert base=='2155178eab40bc1e1ced1f4eef479d1051eba5d2'
assert git('branch','--show-current').strip()=='docs/tto-add1-review-followup-20261014'
changed=[r[3:] for r in git('status','--porcelain=v1','--untracked-files=all').splitlines()]
assert set(changed)==set(FILES),changed
assert set(git('diff','--name-only',base).splitlines())==set(FILES)
git('diff','--check');git('diff','--cached','--check')
old=git('show',base+':docs/roadmap/TTO-roadmap.md');current=(REPO/FILES[2]).read_text()
old_rows=[r for r in old.splitlines() if re.match(r'\| DEC-\d{3} \|',r)]
assert len(old_rows)==19 and all(r in current for r in old_rows)
assert re.findall(r'^\| (DEC-\d{3}) \|',current,re.M)==[f'DEC-{i:03d}' for i in range(1,21)]
assert set(re.findall(r'\b[0-9a-f]{64}\b',old))<=set(re.findall(r'\b[0-9a-f]{64}\b',current))
added='\n'.join(r[1:] for r in git('diff',base,'--',*FILES).splitlines() if r.startswith('+') and not r.startswith('+++'))
assert not re.search(r'/Users/|/private/|Bearer\s+\S+|gh[pousr]_[A-Za-z0-9]|sk-[A-Za-z0-9]{15}',added)
for name in FILES:
 p=REPO/name
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if link.startswith(('https://','http://','#')):continue
  assert (p.parent/link.split('#')[0]).exists(),(name,link)
summary=(REPO/FILES[3]).read_text()
for phrase in ['30项','真实YET文件仍未提供','输入声明也不自动证明品牌','不是新测温']:
 assert phrase in summary,phrase
receipt=dict(verdict='可以推送',base=base,files=FILES,old_DEC_rows_preserved=19,new_DEC='DEC-020',
  docs_only=True,no_original_data_or_software=True,diff_check='pass',
  doc_sha256={n:hashlib.sha256((REPO/n).read_bytes()).hexdigest() for n in FILES},
  actual_local_tests='30 passed, 4 source-category CLI cases and 20-call offline flow',
  residual_boundary='PR will remain reviewable; no automatic merge, real YET format, physical mapping, field load or control claim')
(ROOT/'final-gate.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
