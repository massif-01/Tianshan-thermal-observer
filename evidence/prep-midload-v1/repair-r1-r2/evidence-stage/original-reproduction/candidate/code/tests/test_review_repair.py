"""F2: fixed input identity is independent of temperature usability."""
import json
from pathlib import Path
import pytest
from tto.dataset import build_dataset
from tto.demo import record_demo
from tto.engine import engine_for
from tto.storage import Journal
from tto.report import run_report
from tto.util import read_json, file_hash
from test_platform_curve import row, feed_control


@pytest.mark.parametrize('unusable', ['missing_tj', 'stale_source'])
def test_lifecycle_change_on_unusable_measurement_reaches_report(tmp_path, unusable):
    source = record_demo(tmp_path/'source', count=1, seconds=620,
                         record_schema=2, family='jetson_thor', scope='curve')[0]
    c = read_json(source/'manifest.json')['config']
    c['orin']['source_sample_interval_ms'] = None
    j = Journal(c, tmp_path/'recorded', simulated=True, run_type='shadow', record_schema=2)
    e = engine_for(c, record_schema=2)
    rejected = None
    for path in sorted(source.glob('observations-*')):
        for line in path.read_text().splitlines():
            r = json.loads(line)
            changed = r['kind'] == 'orin' and r['mono_s'] == 350
            if changed:
                r['payload']['telemetry_meta']['source_sample_interval_ms'] = 3000
                if unusable == 'missing_tj':
                    r['payload']['temperature'].pop('tj')
                else:
                    r['payload']['telemetry_meta'].update(fresh=False, sample_age_ms=5000)
            saved = j.observation(r)
            out = e.process(saved)
            j.processing_output(saved, out)
            if changed:
                rejected = out['quality']
    for score in e.invalidate('run_end'):
        j.append('scores', score)
    j.close({'elapsed_s': 620})
    before = {p.name: file_hash(p) for p in j.path.iterdir() if p.is_file()}
    report = run_report(j.path, tmp_path/'report')
    recorded = report['recorded_results']
    assert rejected['accepted'] is False
    assert rejected.get('lifecycle_violation') is True
    assert rejected['measurement_reason'] == 'stale_or_missing_tj'
    assert report['platform_state']['mixed_profiles'] is True
    assert report['input_diagnostics']['model_readiness'] == 'blocked_by_mixed_profiles'
    assert '正式建库拒绝' in report['conclusion']
    assert recorded['log_evidence_complete'] and not recorded['issues']
    assert recorded['quality_excluded_method_horizon_records'] > 0
    assert recorded['scored_method_horizon_records'] > 0
    isolated = {(x['run_id'], x['segment']) for x in recorded['quality_isolations']}
    assert all((p['run_id'], p['segment']) not in isolated for p in recorded['scored_records'])
    assert any(p['origin_t'] > 351 for p in recorded['scored_records'])
    with pytest.raises(ValueError, match='mixed_profiles'):
        build_dataset([j.path])
    assert before == {p.name: file_hash(p) for p in j.path.iterdir() if p.is_file()}


def test_retired_identity_cannot_change_current_lifecycle(config):
    config['orin']['source_sample_interval_ms'] = None
    e = engine_for(config, record_schema=2)
    for seq, stream in [(1, 'old-stream'), (2, 'current-stream')]:
        feed_control(e, seq)
        r = row(seq)
        r['payload']['telemetry_meta']['stream_id'] = stream
        e.process(r)
    late = row(3)
    late['payload']['telemetry_meta'].update(stream_id='old-stream', source_sample_interval_ms=3000)
    late['payload']['temperature'].pop('tj')
    out = e.process(late)
    assert out['quality']['reason'] == 'retired_stream'
    assert not out['quality'].get('lifecycle_violation') and not e.mixed_profiles
    assert e.q.lifecycle_stream == 'current-stream'


def test_pre_repair_saved_scores_keep_recovery_identity(tmp_path):
    """Frozen 0.2.0 synthetic logs: revoke eligibility without rewriting facts."""
    source = Path(__file__).parent/'fixtures/review-repair/pre-repair-run'
    before = {p.name: file_hash(p) for p in source.iterdir() if p.is_file()}
    result = run_report(source, tmp_path/'report')
    saved = result['recorded_results']
    assert saved['log_evidence_complete'] and not saved['issues']
    assert saved['historical_scored_method_horizon_records'] == 132
    assert saved['quality_excluded_method_horizon_records'] == 54
    assert saved['scored_method_horizon_records'] == 78
    assert all(p['origin_t'] >= 101 for p in saved['scored_records'])
    assert result['platform_state']['mixed_profiles']
    assert before == {p.name: file_hash(p) for p in source.iterdir() if p.is_file()}
