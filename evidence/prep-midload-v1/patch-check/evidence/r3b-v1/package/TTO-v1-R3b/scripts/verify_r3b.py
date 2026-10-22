#!/usr/bin/env python3
"""R3b repair assertions, adapted from the unchanged independent review script.
Synthetic Engine/Journal -> production quality replay -> formal tto report.
No network, device access or model training. Output must be a new directory.
"""
import argparse
import copy
import json
from datetime import datetime, timedelta
from pathlib import Path
from tto.cli import main
from tto.engine import Engine
from tto.model import load_model
from tto.storage import Journal
from tto.util import file_hash, read_json

FIXTURE = Path(__file__).resolve().parent.parent / 'tests/fixtures/r3b'


def create_run(output, mode):
    config = read_json(FIXTURE / 'config.json')
    model = load_model(FIXTURE / 'synthetic-model.json')
    source = [json.loads(line) for line in (FIXTURE / 'synthetic-observations.jsonl').read_text().splitlines()]
    limit = 620 if mode in ('conflict_then_recovery', 'sequence_regression') else 350
    j = Journal(config, output / mode, simulated=True, episode='review-synthetic-shadow', run_type='shadow', model_sha256=model['sha256'])
    e = Engine(config, model)
    collision = label_ref = None
    def process(row):
        row = j.observation(row); out = e.process(row)
        if out['quality']: j.append('events', dict(ref=row['ref'], **out['quality']))
        if out['prediction']: j.append('predictions', out['prediction'])
        for score in out['scores']: j.append('scores', score)
        return row, out
    for row in source:
        if row['mono_s'] > limit: break
        saved, out = process(row)
        if row['kind'] == 'orin' and row['mono_s'] == 350:
            label_ref = saved['ref']
            if mode != 'normal':
                bad = copy.deepcopy(saved); bad['mono_s'] += .2
                bad['received_at_utc'] = (datetime.fromisoformat(bad['received_at_utc']) + timedelta(seconds=.2)).isoformat()
                bad['payload']['telemetry_meta']['sample_age_ms'] = 200
                if mode == 'sequence_regression': bad['payload']['telemetry_meta']['sample_seq'] -= 1
                else: bad['payload']['temperature']['tj'] += 10
                _, out = process(bad); collision = out['quality']
    for score in e.invalidate('run_end'): j.append('scores', score)
    j.close({'stop_reason':'synthetic_run_end', 'elapsed_s':limit + .2})
    return j.path, label_ref, collision


def log_hashes(run):
    return {p.name:file_hash(p) for p in run.glob('*.jsonl')}


def verify_case(output, mode):
    run, label_ref, collision = create_run(output, mode)
    before = log_hashes(run)
    report_path = output / (mode + '-report')
    assert main(['report', '--run', str(run), '--output', str(report_path)]) == 0
    report = read_json(report_path / 'report.json'); rec = report['recorded_results']
    total, valid, excluded = (510, 510, 0) if mode == 'normal' else ((510, 0, 510) if mode == 'conflict' else (816, 306, 510))
    assert rec['historical_scored_method_horizon_records'] == total
    assert rec['scored_method_horizon_records'] == valid
    assert rec['quality_excluded_method_horizon_records'] == excluded
    assert rec['log_evidence_complete'] and not rec['missing_logs'] and not rec['issues']
    assert before == log_hashes(run)
    if mode != 'normal':
        reason = 'sequence_regression' if mode == 'sequence_regression' else 'identity_conflict'
        assert collision['reason'] == reason
        assert len([p for p in rec['quality_excluded_records'] if p['label_ref'] == label_ref]) == 12
        isolated = {(x['run_id'], x['segment']) for x in rec['quality_isolations']}
        observation_refs = before_refs(run)
        assert all((p['run_id'], p['segment']) not in isolated for p in rec['scored_records'])
        assert all((p['run_id'], p['segment']) in isolated and p['quality_exclusion'][0]['reason'] == reason and p['quality_exclusion'][0]['trigger_ref'] in observation_refs for p in rec['quality_excluded_records'])
    for group in rec['models'].values():
        for h, hd in group['horizons'].items():
            for method, mc in hd['methods'].items():
                points = [p for p in rec['scored_records'] if p['model_sha256'] == group['model_sha256'] and p['method'] == method and p['horizon_s'] == int(h)]
                assert mc['historical_scored'] == mc['scored'] + mc['quality_excluded']
                assert mc['metrics']['time_pooled']['n'] == len(points)
                assert mc['coverage_denominator'] == hd['issued_origins']
                assert mc['coverage_numerator'] == len(points)
                assert mc['coverage_fraction'] == len(points)/hd['issued_origins']
                if points:
                    assert abs(mc['metrics']['time_pooled']['mae'] - sum(abs(p['error']) for p in points)/len(points)) < 1e-12
                else:
                    assert 'mae' not in mc['metrics']['time_pooled']
    for fmt in ('md', 'html'):
        text = (report_path / ('report.' + fmt)).read_text()
        assert '历史评分' in text and '质量排除' in text and '当前有效' in text
        assert '分母为当时计划起点（包含隔离段）' in text
        if mode == 'conflict': assert '当前没有可用成绩' in text
    return {'mode':mode, 'run_relative':str(run.relative_to(output)), 'report_relative':str(report_path.relative_to(output)), 'simulated':True, 'issued_prediction_origins':rec['issued_prediction_origins'], 'terminal_score_records':rec['terminal_score_records'], 'historical_scored':total, 'currently_eligible':valid, 'quality_excluded':excluded, 'disputed_label_excluded':len([p for p in rec['quality_excluded_records'] if p['label_ref']==label_ref]), 'log_evidence_complete':rec['log_evidence_complete'], 'log_hashes_before':before, 'log_hashes_after':log_hashes(run), 'quality_isolations':rec['quality_isolations']}


def before_refs(run):
    return {json.loads(line)['ref'] for path in run.glob('observations-*.jsonl') for line in path.read_text().splitlines()}


def verify(output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    findings = {mode:verify_case(output, mode) for mode in ('normal','conflict','conflict_then_recovery','sequence_regression')}
    (output / 'findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':True,'synthetic_only':True,'findings':findings},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output',required=True)
    verify(parser.parse_args().output)
