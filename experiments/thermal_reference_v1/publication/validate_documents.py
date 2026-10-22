"""Narrow final documentation gate: intended paths, history, added links and no private additions."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

ROOT=Path(__file__).absolute().parents[1]


def git(repo,*args):return subprocess.run(['git',*args],cwd=repo,capture_output=True,text=True,check=True).stdout


def validate():
    repo=Path(json.loads((ROOT/'publication/local-checkout.json').read_text())['directory'])
    allowed=json.loads((ROOT/'publication/docs-allowlist.json').read_text())
    status=git(repo,'status','--porcelain=v1','--untracked-files=all')
    changed=[row[3:] for row in status.splitlines() if row]
    assert set(changed)==set(allowed),(changed,allowed)
    assert all(Path(n).suffix=='.md' for n in changed)
    assert git(repo,'branch','--show-current').strip()=='docs/tto-ref-prep-roadmap-20261014'
    git(repo,'diff','--check');git(repo,'diff','--cached','--check')
    base=git(repo,'rev-parse','origin/main').strip()
    original=git(repo,'show',base+':docs/roadmap/TTO-roadmap.md')
    current=(repo/'docs/roadmap/TTO-roadmap.md').read_text()
    old_dec=[line for line in original.splitlines() if re.match(r'\| DEC-0(?:0[1-9]|1[0-3]) \|',line)]
    assert len(old_dec)==13 and all(line in current for line in old_dec)
    ids=re.findall(r'^\| (DEC-\d{3}) \|',current,re.M)
    assert ids==[f'DEC-{i:03d}' for i in range(1,21)],ids
    assert '\n\n| DEC-014' not in current
    for value in ['bfe55c967c017c45ebe0287a886eb17e30d7e44a0ca7af01d385fd4ad97ab465',
        '92aed2e4a943b9cc615f3c969081ce4c05a934e0fed26322f443a530f83b5684']:
        assert value in current
    checked_links=[]
    for name in allowed:
        path=repo/name;text=path.read_text()
        old=subprocess.run(['git','show',base+':'+name],cwd=repo,capture_output=True,text=True).stdout
        links=lambda value:set(re.findall(r'\]\(([^\)]+)\)',value))
        for target in links(text)-links(old):
            if target.startswith(('https://','http://','#')):continue
            local=unquote(target.split('#')[0])
            assert (path.parent/local).exists(),(name,target)
            checked_links.append(dict(file=name,target=target))
    additions=git(repo,'diff','HEAD','--',*allowed)
    added='\n'.join(line[1:] for line in additions.splitlines() if line.startswith('+') and not line.startswith('+++'))
    added+='\n'+(repo/'docs/research/TTO-research-status-20261014.md').read_text()
    assert not re.search(r'/Users/|/private/|/home/|Bearer\s+\S+|gh[pousr]_[A-Za-z0-9]|sk-[A-Za-z0-9]{15}',added)
    assert re.search(r'在线参数学习[^。\n]{0,80}(?:未实施|未完成)',current)
    assert '不是TTO软件' in current or '不是软件/建模' in (repo/'README.md').read_text()
    assert 'YET-610L' in current and '聚酰亚胺胶带' in current
    assert '真实YET-610L格式待' in current and '不将采购事实写成现场验证' in current
    report=dict(verdict='可以推送',scope='four Markdown documents only; local software excluded',
        base=base,branch=git(repo,'branch','--show-current').strip(),files=allowed,
        content_sha256={n:hashlib.sha256((repo/n).read_bytes()).hexdigest() for n in allowed},
        original_DEC_001_013_rows_preserved=13,total_decisions=20,historical_SHA_preserved=True,
        new_local_links_checked=checked_links,no_private_paths_or_tokens_added=True,
        diff_check='pass',software_tests='separate local candidate, not PR runtime evidence',
        residual_risk='documentation reflects accepted local evidence; no new physical/cross-hardware/control validation; PR remains unmerged')
    (ROOT/'publication/final-docs-gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':validate()
