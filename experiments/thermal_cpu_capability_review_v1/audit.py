"""Finite audit of this recorded capability run; calls the unique CPU-window validator."""
import argparse
import collections
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent
MODEL = ROOT.parent/'thermal_cpu_activity_bridge_v1'
sys.path.insert(0, str(MODEL))
from bridge import cpu_window
from io_utils import read, lines, write, jsonl, sha


def stats(values):
    return dict(n=len(values), minimum=min(values), median=statistics.median(values),
                mean=statistics.mean(values), p95=sorted(values)[int(.95*(len(values)-1))], maximum=max(values))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adapted', type=Path, required=True)
    p.add_argument('--joint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    frozen = read(ROOT/'input-freeze.json')
    for item in frozen['files']:
        assert sha(ROOT/'inputs'/item['path']) == item['sha256'], item['path']
    added = read(ROOT/'resource-addendum-freeze.json')
    assert sha(ROOT/added['path']) == added['sha256']
    run = ROOT/'inputs/remote-result/run'
    arrivals, wire = lines(run/'cpu-sidecar-arrivals.jsonl'), lines(run/'cpu-sidecar-wire.jsonl')
    frames, outputs = lines(a.adapted/'frames.jsonl'), lines(a.joint/'processor.jsonl')
    origins = lines(a.adapted/'thermal-origins.jsonl')
    states, resources, events = lines(run/'states.jsonl'), lines(run/'resources.jsonl'), lines(run/'sidecar-events.jsonl')
    summary = read(run/'summary.json')
    assert summary['native_run_id'] == frozen['run_id'] and summary['command_id'] == frozen['command_id']
    assert summary['protocol_requests'] == 0 and summary['requester_instances_created'] == 0
    windows, invalid = [], []
    for index, row in enumerate(arrivals, 1):
        source = row['source']
        assert row['native_run_id'] == frozen['run_id'] and row['command_id'] == frozen['command_id']
        assert source['identity']['command_id'] == frozen['command_id']
        assert row['decision_generated_mono_s'] >= row['received_at_mono_s']
        try:
            window = cpu_window(source)
        except ValueError as exc:
            invalid.append(dict(seq=source['seq'], reason=str(exc), row=index))
            continue
        window.update(seq=source['seq'], row=index, received_at_mono_s=row['received_at_mono_s'],
                      decision_generated_mono_s=row['decision_generated_mono_s'],
                      raw_ref=frozen['run_id']+'/cpu-sidecar-arrivals.jsonl:'+str(index))
        windows.append(window)
    assert len(arrivals) == len(wire) == 27 and len(windows) == 26
    assert invalid == [dict(seq=1, reason='missing_complete_raw_counter_window', row=1)]
    assert [x['source']['seq'] for x in arrivals] == list(range(1, 28))
    source_domains = {tuple(x['source']['identity'][k] for k in ('host', 'boot_id', 'source_session', 'clock')) for x in arrivals}
    receiver_domains = {x['receiver_domain'] for x in arrivals}
    assert len(source_domains) == len(receiver_domains) == 1
    pre_source = json.loads((ROOT/'inputs/field/thor-clock-source-hashes.stdout').read_text())
    pre_receiver = json.loads((ROOT/'inputs/field/preflight-clock-locks.stdout').read_text().splitlines()[0])['clock']
    source_domain = next(iter(source_domains))
    assert source_domain[:2] == (pre_source['host'], pre_source['boot_id'])
    assert all(x['receiver_identity']['boot_id'] == pre_receiver['boot_id'] for x in arrivals)
    assert all(x['receiver_identity']['host'] == pre_receiver['host'] for x in arrivals)
    assert all(x['source']['identity']['source_script_sha256'] == pre_source['files']['cpu_source.py'] for x in arrivals)
    config = ROOT/'inputs/remote-result/payload/source-config.json'
    assert sha(config) == pre_source['files']['source-config.json']
    assert all(len(x['online']) == 12 and len(x['possible_online_map']) == 14 for x in windows)
    assert all({k for k, v in x['possible_online_map'].items() if not v} == {'cpu12', 'cpu13'} for x in windows)
    stop = next(x for x in events if x['event'] == 'stop_sidecar_only')
    session = states[0]['clock']['session_origin_mono_s']
    stop_t = session+stop['mono_s']
    revocations = lines(a.adapted/'revocations.jsonl')
    revoke = next(x for x in revocations if x['reason'] == 'transport_receiver_total_resource_budget_exceeded')
    assert revoke['available_at_mono_s'] == stop_t
    coarse_checks = supports = 0
    latest_native = None
    cpu_support_s = 0.
    for index, frame in enumerate(frames):
        features = frame['features']
        t = frame['arrival_mono_s']
        if frame['adapter_event'] == 'native':
            latest_native = features
        if frame['adapter_event'] == 'cpu':
            for name in ('gpu_pct', 'gpu_W', 'cpu_soc_mss_W'):
                assert features.get(name) == latest_native.get(name)
                coarse_checks += 1
        for name in ('cpu_mean_pct', 'cpu_max_pct'):
            f = features.get(name, {})
            if f.get('valid'):
                assert f['valid_until_mono_s'] <= f['receiver_received_at_mono_s']+1
                assert f['available_at_mono_s'] >= f['receiver_decision_generated_mono_s'] >= f['receiver_received_at_mono_s']
                assert f['source_age_s'] is None and f['network_latency_s'] is None
                supports += 1
            if t >= stop_t:
                assert f.get('valid') is not True
        f = features.get('cpu_mean_pct', {})
        if index+1 < len(frames) and f.get('valid'):
            cpu_support_s += max(0., min(frames[index+1]['arrival_mono_s'], f['valid_until_mono_s'])-t)
    assert len(origins) == 60 and len({x['ref'] for x in origins}) == 60
    assert all(x['t'] >= x['measurement_received_mono_s'] for x in origins)
    assert all(x['variants']['INPUT-MEAN']['activity']['state'] == x['variants']['INPUT-CORE']['activity']['state'] for x in outputs)
    durations = {name: collections.Counter() for name in ('INPUT-BASE', 'INPUT-MEAN', 'INPUT-CORE')}
    for current, after in zip(outputs, outputs[1:]):
        t, end = current['arrival_mono_s'], after['arrival_mono_s']
        for name in durations:
            state = current['variants'][name]['activity']
            until = state['supported_until_mono_s']
            if state['state'] == 'UNKNOWN' or until is None:
                durations[name]['UNKNOWN'] += end-t
            else:
                split = max(t, min(end, until))
                durations[name][state['state']] += split-t
                durations[name]['UNKNOWN'] += end-split
    first_active = next(x for x in outputs if x['variants']['INPUT-MEAN']['activity']['state'] == 'ACTIVE')
    source_resources = [x['source']['resources'] for x in arrivals]
    phase = {}
    for label, rows in [('baseline_before30', [x for x in resources if x['mono_s'] < 30]),
                        ('actual_sidecar', [x for x in resources if 30 <= x['mono_s'] <= stop['mono_s']]),
                        ('post_sidecar_stop', [x for x in resources if x['mono_s'] > stop['mono_s']])]:
        phase[label] = dict(rows=len(rows), cpu_single_core=stats([x['cpu_pct_single_core'] for x in rows if x['cpu_pct_single_core'] is not None]),
                            rss_peak_MiB=max(x['rss_bytes'] for x in rows)/1024**2)
    trigger = max((x for x in resources if x['mono_s'] <= stop['mono_s']), key=lambda x:x['mono_s'])
    assert trigger['cpu_pct_single_core'] > 8 and trigger['rss_bytes'] < 128*1024**2
    owner = read(ROOT/'inputs/field/metrics.json')
    for name in phase:
        assert abs(phase[name]['cpu_single_core']['mean']-owner['receiver_resources_by_actual_phase'][name]['cpu_single_core_mean_pct']) < 1e-8
    points = lines(a.joint/'evaluate-stream/actual-arrived-points.jsonl')
    assert all(x['prediction'].get('INPUT-MEAN') == x['prediction'].get('INPUT-CORE') for x in points)
    common = lines(a.joint/'evaluate-stream/actual-arrived-common.jsonl')
    assert [(x['h'], x['n']) for x in common] == [(15, 5), (45, 0), (90, 0)]
    result = dict(run_id=frozen['run_id'], command_id=frozen['command_id'], role=frozen['role'],
                  frozen_candidate_unchanged=True, new_fits=0, new_parameter_search=0,
                  source_declaration=read(a.joint/'joint-receipt.json')['data_source']['category'],
                  independent_identity_refs_checked=dict(source_host_boot_match=True, receiver_host_boot_match=True,
                                                        source_code_and_config_SHA_match=True, cross_clock_mapping_verified=False),
                  packets=27, complete_CPU_windows=26, invalid_CPU_windows=invalid,
                  source_domain=dict(zip(('host', 'boot_id', 'source_session', 'clock'), source_domain)),
                  receiver_domains=sorted(receiver_domains), online_cores=12, possible_cores=14, offline_cores=['cpu12', 'cpu13'],
                  source_period_s=stats([b['source']['read_start_mono_s']-a['source']['read_start_mono_s'] for a, b in zip(arrivals, arrivals[1:])]),
                  source_span_s=arrivals[-1]['source']['read_start_mono_s']-arrivals[0]['source']['read_start_mono_s'],
                  received_span_s=arrivals[-1]['received_at_mono_s']-arrivals[0]['received_at_mono_s'],
                  cpu_receiver_support_s=cpu_support_s, receive_plus1s_support_is_source_age=False,
                  source_mean_pct=stats([x['mean_percent'] for x in windows]), source_max_pct=stats([x['max_percent'] for x in windows]),
                  source_rss_peak_MiB=max(x['rss_bytes'] for x in source_resources)/1024**2,
                  source_read_s=stats([x['read_duration_s'] for x in source_resources]),
                  source_CPU_after5s_pct=stats([100*x['cpu_seconds']/x['elapsed_s'] for x in source_resources if x['elapsed_s'] >= 5]),
                  cpu_support_checks=supports, coarse_features_unchanged_on_CPU_events=coarse_checks,
                  stop=stop, stop_revoke_mono_s=stop_t, CPU_revoked_immediately=True,
                  latest_pre_stop_CPU_deadline=next(x for x in reversed(frames) if x['arrival_mono_s'] < stop_t)['features']['cpu_mean_pct']['valid_until_mono_s'],
                  activity_state_seconds={k:dict(v) for k, v in durations.items()},
                  MEAN_CORE_states_and_predictions_identical=True,
                  first_MEAN_active=dict(ref=first_active['native_ref'], mono_s=first_active['arrival_mono_s'],
                                         activity=first_active['variants']['INPUT-MEAN']['activity']),
                  background_CPU_activity_cause='unknown; existing jtop included, no attribution from aggregate CPU',
                  receiver_phases=phase, resource_trigger=trigger,
                  receipt_qualified=read(ROOT/'inputs/remote-result/capability-receipt.json')['qualified'],
                  original_TJ_origins=60, current_TJ_C=stats([x['current'] for x in origins]),
                  horizon_label_counts={str(h):sum(x['label'] is not None for x in points if x['h'] == h) for h in (15,45,90)},
                  common_results=common, cadence_joint=read(a.joint/'evaluate-stream/cadence-joint-common.json'),
                  inference_detection_delay_and_recall='unknown; no new inference requests/ground truth in this capability run',
                  recommend_12_requests=False, blocker='receiver_total_resource_budget_exceeded; total CPU already high before sidecar',
                  physical_CPU_GPU_lead_proven=False, new_control_benefit=False, model_line_device_access=False)
    jsonl(a.output/'CPU-counter-windows.jsonl', windows)
    write(a.output/'audit.json', result)
    print('Finite recorded-run audit passed:27 actual packets,26 complete windows, immediate revoke; qualification=false,12-request recommendation=false.')


if __name__ == '__main__':
    main()
