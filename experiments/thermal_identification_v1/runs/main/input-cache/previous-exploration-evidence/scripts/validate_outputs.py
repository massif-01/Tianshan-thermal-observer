"""Finite checks for this analysis only; no production test suite or device I/O."""
import ast
import hashlib
import json
import re
from pathlib import Path

from tto.dataset import load_dataset, check_split
from tto.model import load_model, model_dataset_match
from tto.util import verify_seal

OUT=Path(__file__).resolve().parents[1]


def main():
    scripts=list((OUT/'scripts').glob('*.py'))
    for p in scripts:ast.parse(p.read_text(),filename=str(p))
    q=OUT/'model-exploration/short-qa'
    d=load_dataset(q/'exploratory-split/dataset.json')
    s=json.loads((q/'exploratory-split/split.json').read_text());check_split(d,s)
    m=load_model(q/'model.json');model_dataset_match(m,d)
    e=verify_seal(json.loads((q/'evaluation/evaluation.json').read_text()))
    ledger=json.loads((q/'exploratory-split/test-used.json').read_text())
    assert m['split_sha256']==s['sha256'] and m['dataset_sha256']==d['sha256']
    assert e['model_sha256']==m['sha256']==ledger['model_sha256']
    assert e['split_sha256']==s['sha256']==ledger['split_sha256']
    assert m['train_count']==85 and m['validation_count']==5 and m['not_a_control_model'] is True
    assert {v['lambda'] for v in m['methods'].values()} <= {0.001,0.01,0.1,1.0}
    report=OUT/'TTO-短问答后续核对与有限优化方案.md'
    text=report.read_text()
    links=[]
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if link.startswith(('https://','http://')):continue
        path=report.parent/link
        assert path.exists(),link
        links.append(link)
    rows=json.loads((OUT/'results/request-tail-statistics.json').read_text())
    for r in rows:
        if r['phase']!='sparse':continue
        expected=f'| {r["id"]} | {r["duration_s"]:.3f} | {r["peak_pwm"]}% | {r["near_peak_last_s"]:.3f} | {r["return_pre_plus1_s"]:.3f} |'
        assert expected in text,expected
    qualifications=json.loads((OUT/'results/data-qualification-summary.json').read_text())
    assert f'| 所有15/45/90标签均有的TJ训练资格起点 | {qualifications[0]["all_label_TJ_eligible"]} | {qualifications[1]["all_label_TJ_eligible"]} |' in text
    comp=json.loads((OUT/'results/complement-verification.json').read_text())
    assert comp['sha256'] in text and comp['indexed_count']==60 and comp['union_coverage']==99
    assert json.loads((OUT/'results/external-statistical-comparison.json').read_text())['passed']
    assert json.loads((OUT/'results/request-sse-verification.json').read_text())['passed']
    assert json.loads((OUT/'identity/recorded-installation-to-reference-comparison.json').read_text())['passed']
    for p in (OUT/'results').glob('*.json'):json.loads(p.read_text())
    result=dict(status='passed',python_scripts_parsed=len(scripts),report_local_links_checked=len(links),
                report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                dataset_sha256=d['sha256'],split_sha256=s['sha256'],model_sha256=m['sha256'],evaluation_sha256=e['sha256'],
                limit='Checks new analysis outputs and selected identities; not whole-repository tests or device safety.')
    (OUT/'results/output-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
