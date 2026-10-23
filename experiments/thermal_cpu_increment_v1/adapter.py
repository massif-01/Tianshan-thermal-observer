"""Adapt sealed source-valid observations and states; no native processor replay."""
import statistics
from common import ROOT, read, lines


def old_frames(root=ROOT):
    samples = {s['ref']:s for s in lines(root/'inputs/results/samples-and-causal-states.jsonl') if s['source_valid']}
    quality = {q['ref']:q['quality'] for q in lines(root/'inputs/results/quality-ledger.jsonl')}
    config = read(root/'candidate.json')
    run = read(root/'analysis-spec.json')['run_id']
    for raw in lines(root/'inputs/inputs/native/observations-0001.jsonl'):
        if raw['ref'] not in samples:
            continue
        s, p, q = samples[raw['ref']], raw['payload'], quality[raw['ref']]
        assert q['accepted'] and raw['kind']=='orin'
        meta, gpu, t = p['telemetry_meta'], p['gpu'], raw['mono_s']
        cpu = [c['usage'] for c in p['cpu']['cores']]
        until = t+(meta['freshness_timeout_ms']-q['age_lower_bound_ms'])/1000
        common = dict(available_at_mono_s=t, valid=True, transport_delay_ms=None,
            source_host='Thor', source_clock_id=None, source_boot_id=None,
            source_sample_mono_s=None, source_read_start_mono_s=None, source_read_end_mono_s=None,
            window_start_mono_s=None, window_end_mono_s=None, source_window_verified=False,
            original_ref=raw['ref'], original_seq=meta['sample_seq'],
            source_received_at_utc=meta['received_at'], source_recorded_at_utc=p['timestamp'],
            raw_unit=None, effective_backend_update_interval_ms=None,
            unknowns=['source monotonic/read/statistical window','transport delay','cross-host UTC offset','CPU backend update independence'])
        values = dict(gpu_pct=gpu['utilization_pct'], gpu_W=p['power']['vdd_gpu']['current']/1000,
            cpu_soc_mss_W=p['power']['vdd_cpu_soc_mss']['current']/1000,
            cpu_mean_pct=statistics.mean(cpu), cpu_max_pct=max(cpu))
        features = {}
        for name, value in values.items():
            features[name] = dict(common, value=value, valid_until_mono_s=until,
                update_id=f"{meta['stream_id']}:{meta['sample_seq']}:{name}", source_order=meta['sample_seq'],
                feature_source='original cpu.cores[].usage; backend/window unverified' if name.startswith('cpu_') and name.endswith('_pct') else 'original independent rail',
                reported_period_ms=meta['source_sample_interval_ms'],
                age_lower_bound_ms=q['age_lower_bound_ms'], raw_unit='percent' if name.endswith('_pct') else 'mW',
                update_evidence='new original accepted telemetry sequence; backend window not verified')
        features['gpu_pct'].update(feature_source=gpu['source'],
            update_id=f"{gpu['device_uuid']}:{gpu['sampled_at_utc']}",
            source_order=None, sampled_at_utc=gpu['sampled_at_utc'],
            age_at_source_receive_ms=gpu['age_at_telemetry_receive_ms'],
            age_lower_bound_ms=q['gpu']['age_lower_bound_ms'], valid_until_mono_s=q['gpu']['valid_until'],
            reported_period_ms=gpu['sample_interval_ms'],
            update_evidence='original sampled_at identity; statistics window unknown')
        ob=s['states']['AUGMENTED-KF']
        yield dict(schema='TTO-CPU-ACTIVITY-FRAME-v1', synthetic=False, source_only=False,
            native_ref=raw['ref'], epoch=s['epoch'], arrival_clock_id='recorded-N305-monotonic:'+run,
            arrival_host='N305', arrival_boot_id=None,
            arrival_mono_s=t, arrived_at_utc=raw['received_at_utc'], source_original=raw,
            original_origin_eligible=True, features=features,
            thermal=dict(available=ob['available'], current_TJ_C=s['current'], Ts_C=ob['Ts_C'], E_C=ob['E_C'],
                conditional_inputs_rails_W_PWM=ob['conditional_inputs_rails_W_PWM'],
                model_sha256=config['immutable']['model_sha256'],
                observer_spec_sha256=config['immutable']['observer_spec_sha256'],
                state_native_ref=raw['ref'], phase=ob['phase'],
                safety=s['safety'], thermal_state_updated_by_activity=False))
