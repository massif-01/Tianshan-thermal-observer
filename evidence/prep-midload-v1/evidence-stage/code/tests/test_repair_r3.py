import copy
import json
import shutil
import pytest
from tto.demo import record_demo
from tto.dataset import freeze_split
from tto.training import train
from tto.engine import Engine
from tto.storage import Journal
from tto.model import load_model
from tto.report import summarize, run_report
from tto.util import read_json, file_hash
from tto.cli import main


def write_shadow(source, root, model, degrade=False):
    m = read_json(source/'manifest.json')
    j = Journal(m['config'],root,simulated=True,episode='shadow-synthetic',run_type='shadow',model_sha256=model['sha256'])
    e = Engine(m['config'],model)
    for file in sorted(source.glob('observations-*')):
        for line in file.read_text().splitlines():
            row = json.loads(line)
            if degrade and row['kind']=='orin' and row['mono_s']>=250:
                row['payload']['power'].pop('vdd_gpu_soc',None)
            out = e.process(j.observation(row))
            if out['prediction']:j.append('predictions',out['prediction'])
            for score in out['scores']:j.append('scores',score)
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'stop_reason':'synthetic_completed','elapsed_s':400})
    return j.path


@pytest.fixture(scope='module')
def shadow_fixture(tmp_path_factory):
    root=tmp_path_factory.mktemp('r3')
    runs=record_demo(root/'runs',count=5,seconds=400)
    frozen=freeze_split(runs,root/'frozen')
    train(frozen/'dataset.json',frozen/'split.json',root/'model.json')
    model=load_model(root/'model.json')
    shadow=write_shadow(runs[1],root/'shadow',model)
    partial=write_shadow(runs[1],root/'partial',model,degrade=True)
    return root,runs,shadow,partial


def test_formal_cli_report_uses_saved_results_and_never_current_model(shadow_fixture,tmp_path):
    root,runs,shadow,_=shadow_fixture
    predictions=[json.loads(l) for l in (shadow/'predictions.jsonl').read_text().splitlines()]
    scores=[json.loads(l) for l in (shadow/'scores.jsonl').read_text().splitlines()]
    before={p.name:file_hash(p) for p in shadow.glob('*.jsonl')}
    assert main(['report','--run',str(shadow),'--output',str(tmp_path/'report')])==0
    report=read_json(tmp_path/'report/report.json')
    assert report['report_type']=='shadow' and report['simulated']
    assert report['recorded_results']['issued_prediction_origins']==len(predictions)
    model_sha=predictions[0]['model_sha256']
    assert sum(p['actual_method']=='ridge_full' for p in predictions)==44
    assert sum('ridge_full' in s.get('errors',{}) for s in scores if s['status']=='scored')==102
    for h in (15,45,90):
        actual=[s['errors']['ridge_full'] for s in scores if s['horizon_s']==h and s['status']=='scored' and 'ridge_full' in s.get('errors',{})]
        mc=report['recorded_results']['models'][model_sha]['horizons'][str(h)]['methods']['ridge_full']
        assert mc['scored']==len(actual)
        assert mc['metrics']['time_pooled']['mae']==pytest.approx(sum(abs(x) for x in actual)/len(actual))
    baseline=summarize(shadow)
    # Replace/move the exact fixture model that was loaded before this run.
    model_file = root/'model.json'; original_model_bytes = model_file.read_bytes()
    try:
        model_file.write_text('{"new_model_not_for_historical_predictions":true}')
        assert summarize(shadow)==baseline
        model_file.unlink();assert summarize(shadow)==baseline
    finally:
        model_file.write_bytes(original_model_bytes)
    assert before=={p.name:file_hash(p) for p in shadow.glob('*.jsonl')}
    for fmt in ('md','html'):
        text=(tmp_path/'report'/f'report.{fmt}').read_text()
        assert model_sha in text and '模拟' in text and '未加载当前模型重算' in text
        assert '实际方法、降级与未评分原因' in text


@pytest.mark.parametrize('missing', ['predictions.jsonl','scores.jsonl'])
def test_missing_required_logs_is_explicit_not_zero_or_replay(shadow_fixture,tmp_path,missing):
    _,_,source,_=shadow_fixture
    dst=tmp_path/'copy';shutil.copytree(source,dst)
    (dst/missing).rename(dst/(missing+'.fixture-removed'))
    r=run_report(dst,tmp_path/'report')
    assert missing in r['missing_required_logs']
    assert '证据缺失' in r['conclusion']
    assert not r['recorded_results']['log_evidence_complete']
    if missing=='scores.jsonl':
        assert r['recorded_results']['terminal_score_records'] is None
        assert all(mc['scored'] is None for g in r['recorded_results']['models'].values() for hd in g['horizons'].values() for mc in hd['methods'].values())
    else:assert r['recorded_results']['issued_prediction_origins'] is None


def test_predictions_without_scores_are_pending_and_baseline_collect_is_distinct(shadow_fixture,tmp_path):
    _,runs,source,_=shadow_fixture
    dst=tmp_path/'copy';shutil.copytree(source,dst)
    (dst/'scores.jsonl').write_text('')
    r=summarize(dst)
    assert '已有已发预测，但尚未能评分' in r['conclusion']
    assert r['recorded_results']['terminal_score_records']==0
    assert any('no_terminal_score_yet' in h['unscored_reasons'] for g in r['recorded_results']['models'].values() for h in g['horizons'].values())
    collect=run_report(runs[0],tmp_path/'collect-report')
    assert collect['report_type']=='collect'
    assert '采集质量报告' in (tmp_path/'collect-report/report.md').read_text()
    no_model=tmp_path/'no-model';shutil.copytree(runs[0],no_model)
    m=read_json(no_model/'manifest.json');m['report_type']='shadow';m['model_sha256']=None
    (no_model/'manifest.json').write_text(json.dumps(m))
    assert '只有基线' in summarize(no_model)['conclusion']


def test_partial_fallback_never_counts_as_m1_and_scores_join_by_identity(shadow_fixture,tmp_path):
    _,_,_,partial=shadow_fixture
    r=summarize(partial);g=next(iter(r['recorded_results']['models'].values()))
    assert g['actual_methods']['ridge_tj']>0 and g['unavailable_method_reasons']['ridge_full']['missing_selected_features']>0
    assert g['horizons']['45']['methods']['ridge_full']['issued']<g['horizons']['45']['methods']['ridge_tj']['issued']
    dst=tmp_path/'reordered';shutil.copytree(partial,dst)
    scores=(dst/'scores.jsonl').read_text().splitlines();(dst/'scores.jsonl').write_text('\n'.join(reversed(scores))+'\n')
    assert summarize(dst)['recorded_results']['models']==r['recorded_results']['models']
    altered=[json.loads(l) for l in scores]
    scored=next(s for s in altered if s['status']=='scored');scored['model_sha256']='b'*64
    (dst/'scores.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in altered))
    broken=summarize(dst)
    assert any(x['reason']=='score_model_identity_mismatch' for x in broken['recorded_results']['issues'])
    assert '证据缺失' in broken['conclusion']


def test_legacy_shadow_detected_from_saved_model_identity(shadow_fixture,tmp_path):
    _,_,source,_=shadow_fixture
    dst=tmp_path/'legacy';shutil.copytree(source,dst)
    m=read_json(dst/'manifest.json');m.pop('report_type');m.pop('model_sha256')
    (dst/'manifest.json').write_text(json.dumps(m))
    scores=[json.loads(l) for l in (dst/'scores.jsonl').read_text().splitlines()]
    for s in scores:s.pop('model_sha256',None)
    (dst/'scores.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in scores))
    assert summarize(dst)['report_type']=='shadow'
    (dst/'predictions.jsonl').unlink();(dst/'scores.jsonl').unlink()
    r=summarize(dst)
    assert 'predictions.jsonl' in r['missing_required_logs'] and '证据缺失' in r['conclusion']
