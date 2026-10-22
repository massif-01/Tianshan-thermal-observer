import copy
import pytest
from pathlib import Path
from tto.dataset import freeze_split, load_dataset
from tto.demo import record_demo
from tto.training import train
from tto.evaluation import evaluate, value_conclusion
from tto.util import read_json, write_json, seal


@pytest.fixture(scope='module')
def r2_data(tmp_path_factory):
    root = tmp_path_factory.mktemp('r2')
    runs = record_demo(root/'runs', count=5, seconds=720)
    frozen = freeze_split(runs,root/'frozen')
    model = train(frozen/'dataset.json',frozen/'split.json',root/'model.json')
    return root, frozen, model


@pytest.mark.parametrize('loss', ['all', 'partial', 'none', 'baseline_only'])
def test_layered_same_origin_comparisons_and_formats(r2_data, tmp_path, loss):
    root,frozen,original_model = r2_data
    d,s = load_dataset(frozen/'dataset.json'),read_json(frozen/'split.json')
    test_ids = set(s['partitions']['test'])
    field = next(c for c in original_model['methods']['ridge_full']['columns'] if c.startswith('vdd_'))
    for index,r in enumerate(d['rows']):
        if r['id'] in test_ids and (loss == 'all' or loss == 'partial' and index%2 == 0):
            for key in list(r['features']):
                if key==field or key.startswith(field+'_mean_'):r['features'][key]=None
    d.pop('sha256');d=seal(d);s.pop('sha256');s['dataset_sha256']=d['sha256'];s=seal(s)
    write_json(tmp_path/'dataset.json',d);write_json(tmp_path/'split.json',s)
    if loss != 'baseline_only':
        model = train(tmp_path/'dataset.json',tmp_path/'split.json',tmp_path/'model.json')
        assert model['methods'] == original_model['methods']
    result = evaluate(tmp_path/'dataset.json',tmp_path/'split.json',tmp_path/'model.json' if loss!='baseline_only' else None,tmp_path/'eval')
    layers = result['comparisons']
    baseline = layers['baseline']['horizons']['45'];m0=layers['m0']['horizons']['45'];m1=layers['m1']['horizons']['45']
    assert baseline['matched_count'] > 0
    if loss == 'baseline_only':
        assert m0['matched_count']==m1['matched_count']==0
    else:
        assert m0['matched_count']==198
        if loss=='all':assert m1['matched_count']==0
        elif loss=='partial':assert 0<m1['matched_count']<m0['matched_count']
        else:assert m1['matched_count']==m0['matched_count']
        assert set(m1['origin_ids'])<=set(m0['origin_ids'])<=set(baseline['origin_ids'])
        assert m0['metrics']['ridge_tj']['episode_equal_macro']['mae']==pytest.approx(.29303183723102977)
    # Explicit decision-only synthetic copy; never save it as real telemetry.
    unit_data=copy.deepcopy(d);unit_data['simulated']=False
    for r in unit_data['runs']:r['deployment_status']='user_recorded_not_independently_verified'
    rows=[r for r in d['rows'] if r['id'] in test_ids]
    decision=value_conclusion(unit_data,s,rows,layers)
    if loss=='all':assert 'M0有初步价值' in decision and 'M1层缺少' in decision
    if loss=='baseline_only':assert '基线层已有可读结果' in decision
    assert result['simulated'] and '模拟' in result['conclusion']
    for fmt in ('md','html'):
        content=(tmp_path/'eval'/f'report.{fmt}').read_text()
        if fmt=='md':
            assert len(content.splitlines()) > 20 and '\\n' not in content.splitlines()[0]
        assert all(label in content for label in ('基线层','M0层','M1层'))
        assert '不同层MAE不能直接比较' in content
        if loss in ('all','baseline_only'):assert '未覆盖' in content
    for layer in layers.values():
        for horizon in layer['horizons'].values():
            assert all(m['time_pooled']['n']==horizon['matched_count'] for m in horizon['metrics'].values())
            assert horizon['phase_diagnostics'] and horizon['episodes']


def test_markdown_table_has_real_lines_and_escapes_scene_pipe():
    from tto.report import markdown_table
    assert markdown_table(['name'],[['A|B']]) == '|name|\n|---|\n|A\\|B|\n'
