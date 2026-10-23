"""Real production call-chain regressions on the independent synthetic fixture."""
import importlib.util
import json
import shutil
from pathlib import Path
import pytest
from tto.report import summarize, plot_predictions
from tto.util import read_json

spec = importlib.util.spec_from_file_location('verify_r3b', Path(__file__).resolve().parent.parent/'scripts/verify_r3b.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)

@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    out = tmp_path_factory.mktemp('r3b')
    results = {mode:probe.verify_case(out, mode) for mode in ('normal','conflict','conflict_then_recovery','sequence_regression')}
    return out, results

@pytest.mark.parametrize('mode',['normal','conflict','conflict_then_recovery','sequence_regression'])
def test_production_journal_quality_and_formal_report(cases,mode):
    out, results = cases
    facts = results[mode]; r = read_json(out/facts['report_relative']/'report.json')['recorded_results']
    graph = plot_predictions(r['scored_records'])
    html = (out/facts['report_relative']/'report.html').read_text()
    assert graph in html
    if mode == 'conflict': assert '<svg' not in html
    else: assert '<svg' in graph
    assert facts['log_hashes_before'] == facts['log_hashes_after']


def test_reordered_logs_keep_quality_association(cases,tmp_path):
    out, results = cases; source = out/results['conflict_then_recovery']['run_relative']
    run = tmp_path/'copy'; shutil.copytree(source,run)
    original = summarize(run)['recorded_results']
    for name in ('scores.jsonl','predictions.jsonl'):
        p=run/name;p.write_text('\n'.join(reversed(p.read_text().splitlines()))+'\n')
    result = summarize(run)['recorded_results']
    def same(a,b):
        if isinstance(a,dict):
            assert a.keys()==b.keys()
            for key in a: same(a[key],b[key])
        elif isinstance(a,float): assert a==pytest.approx(b,abs=1e-12)
        else: assert a==b
    same(result['models'],original['models'])
    assert result['scored_method_horizon_records']==306
    assert result['quality_excluded_method_horizon_records']==510


def test_prediction_segment_and_raw_reference_must_match_quality(cases,tmp_path):
    out,results=cases;run=tmp_path/'copy';shutil.copytree(out/results['conflict']['run_relative'],run)
    rows=[json.loads(line) for line in (run/'predictions.jsonl').read_text().splitlines()]
    rows[0]['origin']['segment']+=100
    rows[1]['origin']['raw_refs']=['not-a-matching-observation']
    (run/'predictions.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    rec=summarize(run)['recorded_results']
    assert any(x['reason']=='quality_origin_identity_mismatch' for x in rec['issues'])
    assert rec['scored_method_horizon_records']==0
    assert not rec['log_evidence_complete']


def test_label_reference_is_associated_with_prediction_and_horizon(cases,tmp_path):
    out,results=cases;run=tmp_path/'copy';shutil.copytree(out/results['conflict']['run_relative'],run)
    rows=[json.loads(line) for line in (run/'scores.jsonl').read_text().splitlines()]
    score=next(row for row in rows if row['status']=='scored')
    score['label_ref']=score['label_ref'].split('/')[0]+'/observation:1'
    (run/'scores.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    rec=summarize(run)['recorded_results']
    assert any(x['reason']=='quality_score_reference_mismatch' for x in rec['issues'])
    assert not rec['scored_records']
