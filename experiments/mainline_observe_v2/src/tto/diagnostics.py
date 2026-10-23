"""Input diagnostics reuse production Engine qualification, never rescore logs."""
from .recordio import log_paths, open_log
import json
from collections import Counter
from pathlib import Path
from .platform_engine import PlatformEngine
from .quality import fan_data, temp_data
from .util import finite


def input_diagnostics(run, config):
    engine = PlatformEngine(config)
    scopes, reasons, gpu_reasons, gpu_source_states, fields = Counter(), Counter(), Counter(), Counter(), Counter()
    counts = Counter()
    last_gpu, last_t, last_binding = None, None, None
    declaration, period_evidence = None, None
    for path in log_paths(run,'observations'):
        with open_log(path) as f:
            for line in f:
                r = json.loads(line)
                last_t = r['mono_s']
                out = engine.process(r)
                if r['kind'] == 'temp':
                    try:
                        d = temp_data(r['payload'])
                        counts['temperature_status_records'] += 1
                        counts['valid_temperature_status_records'] += int(d['normalized_valid'] is True)
                        last_binding = {k: d.get(k) for k in ('preferred_source', 'active_source', 'bound_variable', 'manual_mode', 'normalized_valid', 'timestamp_ms')}
                        last_binding['ref'] = r['ref']
                    except (ValueError, TypeError, AttributeError):
                        counts['unrecognized_temperature_status'] += 1
                q = out['quality']
                if q and q.get('gpu'):
                    last_gpu = dict(q['gpu'], ref=r['ref'], observer_receive_mono_s=r['mono_s'])
                    period_evidence = dict(q['source_period'], ref=r['ref'])
                if q and q['accepted']:
                    counts['new_tj_samples'] += 1
                    counts['gpu_usable_new_samples'] += int(q['gpu']['value'] is not None)
                    gpu_reasons[q['gpu']['reason'] or 'usable'] += 1
                    gpu_source_states[q['gpu']['source_status'] or 'invalid'] += 1
                    p = r['payload']
                    declaration = {'platform': p.get('platform'), 'ref': r['ref'], 'evidence_status': q['platform_reason'] or 'confirmed'}
                    # Inventory actual named sensors/rails, without using them
                    # to infer a platform or alter a modeling profile.
                    for name, value in (p.get('temperature') or {}).items():
                        if finite(value): fields['temperature.'+name+' [C]'] += 1
                    for name, rail in (p.get('power') or {}).items():
                        if isinstance(rail, dict) and rail.get('unit') == 'mW' and finite(rail.get('current')) and rail['current'] >= 0:
                            fields['power.'+name+'.current [W]'] += 1
                if out['prediction']:
                    origin = out['prediction']['origin']
                    scopes[origin['control_scope']] += 1
                    counts['planned_origins'] += 1
                    counts['eligible_origins'] += int(origin['control_eligible'] and origin['input_contract_eligible'])
                    counts['normal_auto_origins'] += int(origin['normal_auto'])
                    counts['normal_curve_origins'] += int(origin['control_eligible'] and origin['control_scope'] == 'curve')
                    reasons.update(origin['control_ineligible_reasons'])
                    if origin['source_period_evidence']['reason']:
                        reasons[origin['source_period_evidence']['reason']] += 1
    if last_gpu:
        deadline = last_gpu['valid_until']
        last_gpu['observer_current_valid'] = deadline is not None and last_t < deadline
        age = last_gpu.get('age_lower_bound_ms')
        last_gpu['observer_current_age_lower_bound_ms'] = age+(last_t-last_gpu['observer_receive_mono_s'])*1000 if finite(age) else None
    return {'kind': 'diagnostic_replay_only_not_historical_predictions', 'platform_declaration': declaration, 'source_period_evidence': period_evidence,
            'counts': dict(counts), 'control_scopes': dict(scopes), 'control_ineligible_reasons': dict(reasons),
            'last_temperature_binding': last_binding, 'gpu_source_status_counts': dict(gpu_source_states),
            'gpu_unavailable_reasons': dict(gpu_reasons), 'gpu_latest': last_gpu,
            'gpu_coverage': {'numerator': counts['gpu_usable_new_samples'], 'denominator': counts['new_tj_samples'], 'fraction': counts['gpu_usable_new_samples']/counts['new_tj_samples'] if counts['new_tj_samples'] else None},
            'named_input_coverage': {name: {'numerator': n, 'denominator': counts['new_tj_samples'], 'fraction': n/counts['new_tj_samples'] if counts['new_tj_samples'] else None} for name, n in fields.items()},
            'mixed_profiles': engine.mixed_profiles,
            'model_readiness': 'blocked_by_mixed_profiles' if engine.mixed_profiles else 'input_scope_observed_model_effect_unverified' if counts['eligible_origins'] else 'blocked_by_identity_or_control_qualification',
            'process_completeness': 'operator_start_end_and_cooldown_evidence_required',
            'note': '具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。'}
