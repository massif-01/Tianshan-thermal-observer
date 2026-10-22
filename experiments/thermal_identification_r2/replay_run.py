"""Read-only replay, in a subprocess bound to each run's preserved TTO processor."""
import bisect
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor/v1'))
from common import read, write, sha, seconds


def metadata(label, cache):
    if label != 'M':
        import importlib.util
        p = cache / 'greybox-v1-evidence/data_adapter.py'
        sp = importlib.util.spec_from_file_location('legacy_data_adapter', p)
        mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
        base = cache / ('L-seven-conditions-original' if label == 'L' else 'S-shortqa-original-complete')
        phases, requests = mod.phase_metadata(base, label)
        return phases, requests, lambda wall: mod.classify(wall, label, phases, requests)
    # UTC joins client markers to observer samples; host monotonic clocks are not subtracted.
    events = [json.loads(x) for x in (cache / 'M-trial/events.jsonl').read_text().splitlines()]
    phases = []
    for ev in events:
        if ev['event'] == 'phase_start':
            phases.append(dict(id=ev['phase'], start=seconds(ev['occurred_at_utc']), start_ref=ev.get('ref'),
                               macro='work' if ev['phase'].startswith('M') else 'background' if ev['phase']=='resident_background' else 'recovery'))
        if ev['event'] == 'phase_end':
            p = next(p for p in reversed(phases) if p['id'] == ev['phase'])
            p['end'] = seconds(ev['occurred_at_utc']); p['actual_s'] = p['end'] - p['start']
    requests = [dict(id=q['request_id'], stage=q['request_id'].split('-')[0],
                     start=seconds(q['submitted_at_utc']), end=seconds(q['client_end_at_utc']),
                     end_semantics=q['request_end_semantics'])
                for q in map(json.loads, (cache/'M-trial/requests.jsonl').read_text().splitlines())]
    def classify(wall):
        p = next((p for p in phases if p['start'] <= wall < p['end']), None)
        if p is None: return 'background', 'unlabelled', 'background'
        return p['macro'], p['id'], ('midload_rise' if wall-p['start']<60 else 'midload_sustained') if p['macro']=='work' else 'cooldown' if p['macro']=='recovery' else 'idle'
    return phases, requests, classify


def replay(label, cache, output):
    source = cache/'M-independent-review/reference_code' if label=='M' else cache/'greybox-v1-evidence/sources/tto-reference/src'
    sys.path.insert(0, str(source))
    from tto.config import load_config, merge, validate
    from tto.engine import engine_for
    from tto.dataset import replay as original_replay
    base = cache/'M-trial/collection' if label=='M' else cache/('L-seven-conditions-original' if label=='L' else 'S-shortqa-original-complete')
    run = next(base.glob('run-*')); manifest = read(run/'manifest.json')
    for f, h in read(run/'files.json').items(): assert sha(run/f)==h, f
    original = original_replay(run)
    assert not original['platform_state']['mixed_profiles']
    assert not original['platform_state']['evidence_issues']
    isolated = {x['segment'] for x in original['quality_eligibility']['isolations']}
    config = load_config(environ={}); saved = copy.deepcopy(manifest['config'])
    for section in ('orin', 'tianshan'): saved[section]['headers_file'] = saved[section]['ca_file'] = None
    merge(config, saved); validate(config); engine = engine_for(config, record_schema=2)
    phases, requests, classify = metadata(label, cache)
    samples, nodes = [], []; latest = None; epoch = 0; identity = None; context_last = None
    for raw_count, raw in enumerate(map(json.loads, (run/'observations-0001.jsonl').read_text().splitlines()), 1):
        assert raw['ref']==f"{manifest['observer_run_id']}/observation:{raw_count}"
        blocked = engine.q.blocked; long_gap = engine.q.counts['boundary_long_gap']
        out = engine.process(raw); q = out['quality']; t = raw['mono_s']
        assert not nodes or t >= nodes[-1]['t']
        if (engine.q.blocked and not blocked) or engine.q.counts['boundary_long_gap']>long_gap: epoch += 1
        if raw['kind']=='boundary' or raw.get('preceding_queue_gap'): epoch += 1
        if q:
            if q.get('lifecycle_violation') or q['reason'] in ('identity_conflict','sequence_regression','retired_stream','stale_or_missing_tj','stale_duplicate','invalid_numeric_contract'): epoch += 1
            if q['accepted']:
                ident = (tuple(q['key'][:2]), raw.get('connection_epoch'), repr(engine.q.lifecycle_settings), engine.q.lifecycle_uuid)
                if identity is not None and ident != identity: epoch += 1
                identity = ident; s = engine.features.history[-1]
                # Anchor the expiry to the actual accepted measurement, never a later rejected message.
                until = t + (raw['payload']['telemetry_meta']['freshness_timeout_ms']-q['age_lower_bound_ms'])/1000
                latest = dict(ref=raw['ref'], t=t, mono_s=t, utc=raw['received_at_utc'], wall=seconds(raw['received_at_utc']),
                              run=label, values=dict(s['values']), segment=s['segment'], source_epoch=epoch,
                              source_identity=repr(ident), sample_seq=raw['payload']['telemetry_meta']['sample_seq'],
                              source_valid_until=until, source_age_ms=q['age_lower_bound_ms'],
                              target_valid=bool(q.get('period_known',False) and q.get('input_contract') is not None and s['segment'] not in isolated),
                              control_eligible=s['control_eligible'], node_index=len(nodes))
                latest['macro'], latest['phase'], latest['regime'] = classify(latest['wall'])
                assert latest['values']['tj']==raw['payload']['temperature']['tj']
                for f in ('vdd_gpu','vdd_cpu_soc_mss','vin_sys_5v0'): assert latest['values'][f]==raw['payload']['power'][f]['current']/1000
                samples.append(latest)
        fan = engine.fan['data'] if engine.fan else {}; temp = engine.temp['data'] if engine.temp else {}
        _, eligible, reasons = engine.control_qualification(t)
        context = (fan.get('mode'),fan.get('enabled'),temp.get('manual_mode'),temp.get('active_source'),temp.get('bound_variable'))
        known = engine.fan is not None and engine.temp is not None and all(v is not None for v in context[:4])
        changed = bool(known and context_last is not None and context!=context_last)
        if known: context_last = context
        abnormal = bool(any(fan.get(k) is True for k in ('temp_stale','guard_active','fault')) or
                        fan.get('mode') is not None and fan.get('mode')!='auto' or fan.get('enabled') is False or
                        temp.get('manual_mode') is True or temp.get('normalized_valid') is False or changed)
        source_until = latest['source_valid_until'] if latest else t
        power_ok = bool(latest and latest['target_valid'] and not engine.q.blocked and not engine.q.quarantined and latest['segment']==engine.q.segment)
        deadline = min(source_until,engine.fan['t']+2.5 if engine.fan else t,engine.temp['t']+7.5 if engine.temp else t)
        complete = bool(power_ok and eligible and fan.get('mode')=='auto' and not abnormal)
        inputs = [latest['values']['vdd_gpu'],latest['values']['vdd_cpu_soc_mss'],fan['successful_duty']/100] if complete else None
        nodes.append(dict(t=t, ref=raw['ref'], trigger_ref=raw['ref'], complete=complete, good=complete, valid_until=deadline,
                          source_until=source_until,power_ok=power_ok,control_eligible=eligible,mode=fan.get('mode'),
                          observed_abnormal_or_changed=abnormal, context_known=known,context_change=changed,reasons=reasons,
                          fan_ref=engine.fan['ref'] if engine.fan else None,temp_ref=engine.temp['ref'] if engine.temp else None,
                          power_ref=latest['ref'] if latest else None,source_epoch=epoch,segment=engine.q.segment,inputs=inputs))
    if label!='M':
        old = read(cache/'greybox-v1-evidence/runs/main/data.json')
        expected = {s['ref']:s for s in old['accepted'] if s['run']==label}
        assert len(expected)==len(samples)
        for s in samples:
            x = expected[s['ref']]
            for k in ('values','segment','control_eligible','sample_seq','mono_s','utc','macro','phase','regime'): assert s[k]==x[k], (s['ref'],k)
    source_hashes = {f.name:sha(f) for f in (source/'tto').glob('*.py')}
    manifest_hashes = manifest['source_identity']['files']
    write(output, dict(run_id=manifest['observer_run_id'],run=label,samples=samples,nodes=nodes,isolated_segments=sorted(isolated),
                       phases=phases,requests=requests,quality=original['quality'],quality_eligibility=original['quality_eligibility'],
                       raw_observations=raw_count,source=str(source),source_hashes=source_hashes,
                       source_matches_manifest={k:source_hashes.get(k)==v for k,v in manifest_hashes.items()},
                       run_hashes=read(run/'files.json'),override_used_for_qualification=False,
                       legacy_normalized_all_fields_verified=label!='M'))
    print(label, manifest['observer_run_id'],len(samples),'accepted',len(nodes),'events',flush=True)


if __name__=='__main__': replay(sys.argv[1],Path(sys.argv[2]),Path(sys.argv[3]))
