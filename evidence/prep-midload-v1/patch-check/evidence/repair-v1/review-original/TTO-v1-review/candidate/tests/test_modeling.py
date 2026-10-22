import copy
import json
from pathlib import Path
import pytest
from tto.demo import record_demo
from tto.dataset import freeze_split, load_dataset, check_split, replay
from tto.training import train
from tto.model import load_model, infer
from tto.engine import Engine
from tto.features import Features, TJ_COLUMNS
from tto.evaluation import evaluate, group_metrics, metrics
from tto.util import read_json, seal, write_json
from conftest import aux, record


@pytest.fixture(scope='module')
def fixture_data(tmp_path_factory):
    root = tmp_path_factory.mktemp('modeling')
    runs = record_demo(root / 'runs', count=5, seconds=420)
    frozen = freeze_split(runs, root / 'frozen')
    train(frozen / 'dataset.json', frozen / 'split.json', root / 'model.json')
    return root, runs


def test_causal_asof_weighted_mean_and_no_future(config):
    f = Features(1)
    for t in range(181):
        f.push({'t': t, 'values': {'tj': 40 + t / 100, 'duty': 37, 'gain': 1.1}, 'ref': str(t)})
    values, refs = f.snapshot()
    assert values['tj_lag_180'] == pytest.approx(-1.8)
    assert values['tj_mean_10'] == pytest.approx(-.055)
    assert values['tj_slope_30'] == pytest.approx(.01)
    assert f.asof(170.5)['t'] == 170
    assert len(f.history) <= 186
    original = copy.deepcopy(values)
    f.push({'t': 181, 'values': {'tj': 900, 'duty': 100, 'gain': 99}, 'ref': 'future'})
    assert values == original


def test_live_offline_features_and_frozen_predictions_equal(fixture_data):
    root, runs = fixture_data
    model = load_model(root / 'model.json')
    offline = replay(runs[0], model)
    c = offline['manifest']['config']
    engine = Engine(c, model); engine.retain_origins = True
    for path in sorted(runs[0].glob('observations-*')):
        for line in path.read_text().splitlines():
            engine.process(json.loads(line))
    assert [p['origin']['features'] for p in engine.origins] == [r['features'] for r in offline['rows']]
    assert all(p['origin']['available_at'] == p['origin']['t'] for p in engine.origins)
    for p in engine.origins:
        if 'ridge_tj' in p['values']:
            predicted, _, _ = infer(model, 'ridge_tj', p['origin']['features'])
            assert predicted == p['values']['ridge_tj']


def test_rewriting_all_future_data_cannot_change_past_predictions(fixture_data):
    root, runs = fixture_data
    model = load_model(root / 'model.json')
    original = replay(runs[0], model)
    e1, e2 = Engine(original['manifest']['config'], model), Engine(original['manifest']['config'], model)
    before1, before2 = [], []
    after1, after2 = [], []
    for path in sorted(runs[0].glob('observations-*')):
        for line in path.read_text().splitlines():
            a = json.loads(line); b = copy.deepcopy(a)
            if b['mono_s'] > 250 and b['kind'] == 'orin':
                b['payload']['temperature']['tj'] += 25
                b['payload']['cpu']['cores'][0]['usage'] = 99
            if b['mono_s'] > 250 and b['kind'] == 'fan':
                b['payload']['data']['fans'][0]['duty'] = 100
            p1, p2 = e1.process(a), e2.process(b)
            if a['mono_s'] <= 250 and p1['prediction']:
                before1.append(p1['prediction']); before2.append(p2['prediction'])
            after1.extend(p1['scores']); after2.extend(p2['scores'])
    assert before1 == before2
    assert after1 != after2


def test_test_values_do_not_change_training_coefficients(fixture_data, tmp_path):
    root, runs = fixture_data
    d, s = load_dataset(root / 'frozen/dataset.json'), read_json(root / 'frozen/split.json')
    changed = copy.deepcopy(d)
    test_ids = set(s['partitions']['test'])
    for r in changed['rows']:
        if r['id'] in test_ids:
            r['features']['tj'] += 1000
            for label in r['labels'].values():
                label['value'] -= 1000
            r['features']['temp_gpu'] = 12345
    changed.pop('sha256'); changed = seal(changed)
    s.pop('sha256'); s['dataset_sha256'] = changed['sha256']; s = seal(s)
    write_json(tmp_path / 'dataset.json', changed); write_json(tmp_path / 'split.json', s)
    altered = train(tmp_path / 'dataset.json', tmp_path / 'split.json', tmp_path / 'model.json')
    first = load_model(root / 'model.json')
    assert altered['methods'] == first['methods']
    assert altered['selected_optional_groups'] == first['selected_optional_groups']
    assert altered['validation_45s_episode_macro_mae'] == first['validation_45s_episode_macro_mae']


def test_raw_reference_and_temporal_leakage_rejected(fixture_data):
    root, _ = fixture_data
    d, s = load_dataset(root / 'frozen/dataset.json'), read_json(root / 'frozen/split.json')
    bad = copy.deepcopy(s)
    bad['partitions']['test'].append(bad['partitions']['train'][0]); bad.pop('sha256'); bad = seal(bad)
    with pytest.raises(ValueError):
        check_split(d, bad)
    changed = copy.deepcopy(d)
    first = next(r for r in d['rows'] if r['id'] == s['partitions']['train'][0])
    next(r for r in changed['rows'] if r['id'] == s['partitions']['test'][0])['raw_refs'].append(first['raw_refs'][0])
    changed.pop('sha256'); changed = seal(changed)
    bad = copy.deepcopy(s); bad.pop('sha256'); bad['dataset_sha256'] = changed['sha256']; bad = seal(bad)
    with pytest.raises(ValueError, match='raw references'):
        check_split(changed, bad)


@pytest.mark.parametrize('mutate', ['hash', 'nan', 'dimension', 'contract', 'column'])
def test_model_tampering_rejected(fixture_data, tmp_path, mutate):
    root, _ = fixture_data
    m = read_json(root / 'model.json')
    if mutate == 'hash':
        m['methods']['ridge_tj']['mean'][0] += 1
    else:
        m.pop('sha256')
        if mutate == 'nan':
            p = tmp_path / 'm.json'; p.write_text(json.dumps(dict(m, schema_version=float('nan'))))
            with pytest.raises(ValueError):
                load_model(p)
            return
        if mutate == 'dimension':
            m['methods']['ridge_tj']['mean'].pop()
        elif mutate == 'contract':
            m['feature_schema'] = 99
        elif mutate == 'column':
            m['methods']['ridge_tj']['columns'][0] = '__exec__'
        m = seal(m)
    p = tmp_path / 'm.json'; write_json(p, m)
    with pytest.raises(ValueError):
        load_model(p)


def test_missing_optional_is_unavailable_not_m1_success(fixture_data):
    root, runs = fixture_data
    m = load_model(root / 'model.json')
    rows = replay(runs[0], m)['rows']
    r = next(r for r in rows if r['history_ready'])
    f = copy.deepcopy(r['features']); f['duty'] = None
    p, reason, _ = infer(m, 'ridge_full', f)
    assert p is None and reason == 'missing_selected_features'
    assert infer(m, 'ridge_tj', f)[0] is not None


def test_no_label_before_target_and_deadline(config):
    e = Engine(config)
    for t in range(15):
        e.process(aux('fan', t)); e.process(aux('temp', t))
        out = e.process(record(t + 1, t=t))
        assert not any(s['status'] == 'scored' and s['prediction_id'].endswith(':1') for s in out['scores'])
    e.process(aux('fan', 16)); e.process(aux('temp', 16))
    out = e.process(record(16, t=16))
    scored = [s for s in out['scores'] if s['status'] == 'scored' and s['horizon_s'] == 15]
    assert scored and scored[0]['offset_s'] == 1
    assert e.expire(1000) and not e.pending


def test_episode_macro_does_not_hide_short_hard_episode():
    points = [dict(episode='idle', error=0) for _ in range(100)] + [dict(episode='load', error=10)]
    m = group_metrics(points)
    assert m['episode_equal_macro']['mae'] == 5
    assert m['time_pooled']['mae'] == pytest.approx(10 / 101)
    assert metrics([])['status'] == 'not_covered'


def test_frozen_test_evaluated_once_and_report_is_escaped(fixture_data, tmp_path):
    root, _ = fixture_data
    # Isolate ledger from other tests; the source split is never mutated.
    d = load_dataset(root / 'frozen/dataset.json'); s = read_json(root / 'frozen/split.json')
    write_json(tmp_path / 'dataset.json', d); write_json(tmp_path / 'split.json', s)
    result = evaluate(tmp_path / 'dataset.json', tmp_path / 'split.json', root / 'model.json', tmp_path / 'evaluation')
    assert result['simulated'] and '模拟' in result['conclusion']
    assert set(result['coverage']) == {'15', '45', '90'}
    assert all(n > 0 for n in result['same_origin_intersection_count'].values())
    assert (tmp_path / 'test-used.json').exists()
    with pytest.raises(FileExistsError):
        evaluate(tmp_path / 'dataset.json', tmp_path / 'split.json', root / 'model.json', tmp_path / 'evaluation2')
    from tto.report import html_page, table
    html = html_page('<script>label</script>', table(['task'], [['<img src=x onerror=bad()>']]))
    assert '<script>label' not in html and '<img src=x' not in html
    assert 'Content-Security-Policy' in html


def test_insufficient_episodes_returns_missing_evidence(tmp_path):
    runs = record_demo(tmp_path / 'runs', count=1, seconds=300)
    with pytest.raises(ValueError, match='三段'):
        freeze_split(runs, tmp_path / 'split')


def test_value_decision_requires_independent_nonidle_wins():
    from tto.evaluation import value_conclusion, METHODS
    d = {'simulated': False, 'runs': [{'deployment_status': 'user_recorded_not_independently_verified'}]}
    s = {'scope': 'chronological_episodes'}
    rows = [{'episode': 'a'}, {'episode': 'b'}]
    values = {'persist': 2., 'trend30': 1.5, 'ridge_tj': 1., 'ridge_full': .5}
    tables = {'45': {m: {'episode_equal_macro': {'mae': v}, 'episodes': {e: {'mae': v} for e in ('a', 'b')}} for m, v in values.items()}}
    pts = {'45': {m: [{'error': v, 'common': True, 'phase': 'stable'}] for m, v in values.items()}}
    assert '待机' in value_conclusion(d, s, rows, tables, {'45': ['x']}, pts)
    for m in METHODS:
        pts['45'][m][0]['phase'] = 'warming'
    assert '有初步新增价值' in value_conclusion(d, s, rows, tables, {'45': ['x']}, pts)
    tables['45']['ridge_full']['episodes']['b']['mae'] = 3
    assert '只证明小模型' in value_conclusion(d, s, rows, tables, {'45': ['x']}, pts)
    tables['45']['ridge_tj']['episodes']['b']['mae'] = 4
    assert '暂未证明' in value_conclusion(d, s, rows, tables, {'45': ['x']}, pts)


def test_value_decision_keeps_deployment_and_simulation_separate():
    from tto.evaluation import value_conclusion
    d = {'simulated': False, 'runs': [{'deployment_status': 'deployment_unverified'}]}
    assert '部署身份' in value_conclusion(d, {}, [], {}, {}, {})
    d['simulated'] = True
    assert '模拟' in value_conclusion(d, {}, [], {}, {}, {})
