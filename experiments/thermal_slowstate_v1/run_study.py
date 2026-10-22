"""Frozen-state replay, four-way ablation and offline demand. Never fits dynamics."""
from pathlib import Path
import bisect
from collections import defaultdict, Counter
import datetime as dt
import hashlib
import json
import os
import platform
import resource
import sys
import time
import numpy as np

ROOT = Path(__file__).absolute().parent
sys.path.insert(0, str(ROOT / 'vendor'))
from greybox import build_kernel, propagate, arrays, forecast
from initialize import path_between
from prepare import read, write, jsonlines, write_lines, digest, MODELS
from core import BRANCHES, filters_at_origins, shape, reversal_count, error_metrics

PARAM_NAMES = ['a', 'c', 'd0', 'd1', 'b_g', 'b_c']
OUT = ROOT / 'results'
SRC = ROOT / 'sources'


def parameters(model):
    return [model['dynamic'][key] for key in PARAM_NAMES]


def load_inputs():
    data = read(SRC / 'registered/data.json')
    models = {name: read(SRC / f'models/{name}.json') for name in MODELS}
    return data, models


def distributions(values):
    v = np.array(values, dtype=float)
    return dict(n=len(v), min=float(v.min()), median=float(np.median(v)),
                p95=float(np.percentile(v, 95)), max=float(v.max())) if len(v) else dict(n=0)


def export_states(data, models):
    accepted = {r['ref']: r for r in data['accepted']}
    segments = {s['id']: s for s in data['segments']}
    all_causal, all_long, jump_records, replay_checks = [], [], [], []
    specs = read(ROOT / 'slowstate-spec.json')
    tol = specs['implementation_freeze']['state_replay_tolerance_C']
    for name, model in models.items():
        p = parameters(model)
        source = SRC / f'evaluation/{name}'
        cals = read(source / 'calibrations.json')['G2']
        sealed_long = {r['ref']: r for r in jsonlines(source / 'A-long.jsonl') if 'G2' in r['A']}
        causal = [r for r in jsonlines(source / 'states.jsonl') if r['model'] == 'G2']
        causal_by_ref = {r['ref']: r for r in causal}
        long_errors = []
        for sid, cal in cals.items():
            segment = segments[sid]
            a = arrays(segment)
            z = propagate('G2', p, cal['E'], a['dt'], a['u'],
                          [a['y'][0], cal['Ts_initial']])
            for row, state in zip(segment['rows'], z[a['index']]):
                if row['ref'] not in sealed_long:
                    continue
                old = sealed_long[row['ref']]
                error = float(state[0] - old['A']['G2'])
                long_errors.append(abs(error))
                all_long.append(dict(model=name, model_sha256=specs['model_sha256'][name],
                    mode='A-long_no_temperature_feedback_after_prefix', ref=row['ref'], run=row['run'],
                    segment=sid, t=row['mono_s'], utc=row['utc'], wall=row['wall'],
                    Tf=float(state[0]), Ts=float(state[1]), measured_TJ=row['values']['tj'],
                    Tf_error=float(state[0] - row['values']['tj']), sealed_Tf=old['A']['G2'],
                    E=cal['E'], current_inputs=segment['timeline'][row['timeline_index']]['inputs'],
                    source_valid_until=row['source_valid_until'],
                    current_input_valid_until=segment['timeline'][row['timeline_index']]['valid_until'],
                    prefix=cal, no_TJ_feedback=True, state_truth_available=False))
        assert long_errors and max(long_errors) <= tol, (name, max(long_errors))
        previous = {}
        for old in causal:
            row = accepted[old['ref']]
            segment = segments[old['segment']]
            node = segment['timeline'][next(i for i, n in enumerate(segment['timeline']) if n['t'] == row['mono_s'])]
            state = dict(model=name, model_sha256=specs['model_sha256'][name],
                mode='causal_past60_observed_Tf_anchor', ref=row['ref'], run=row['run'],
                segment=old['segment'], t=row['mono_s'], utc=row['utc'], wall=row['wall'],
                Tf=row['values']['tj'], Tf_is_observation_anchor=True, Ts=old['state'][1],
                unanchored_prefix_end_Tf=old['evidence']['state'][0],
                E=old['E'], current_inputs=node['inputs'], current_input_valid_until=node['valid_until'],
                source_valid_until=row['source_valid_until'], source_epoch=row['source_epoch'],
                source_identity=row['source_identity'], evidence=old['evidence'],
                fan_ref=node['fan_ref'], temp_ref=node['temp_ref'], power_ref=node['power_ref'],
                input_cutoff=old['input_cutoff'], parameter_learning=False, state_truth_available=False)
            assert state['input_cutoff'] <= state['t'] + 1e-9
            assert state['evidence']['end'] <= state['t'] + 1e-9
            assert state['Tf'] == old['state'][0]
            all_causal.append(state)
            if state['segment'] in previous:
                prev = previous[state['segment']]
                dts, u = path_between(segment, prev['t'], state['t'])
                pred = propagate('G2', p, state['E'], dts, u, [prev['Tf'], prev['Ts']])[-1]
                jump_records.append(dict(model=name, run=row['run'], segment=state['segment'],
                    ref=state['ref'], previous_ref=prev['ref'], wall=state['wall'], dt=state['t'] - prev['t'],
                    delta_Ts=state['Ts'] - prev['Ts'],
                    correction_after_already_observed_path=state['Ts'] - float(pred[1]),
                    previous_window_first=prev['evidence']['first_ref'], window_first=state['evidence']['first_ref'],
                    initial_Ts=state['evidence']['Ts_initial'], previous_initial_Ts=prev['evidence']['Ts_initial'],
                    bounds_hit=state['evidence']['bounds_hit']))
            previous[state['segment']] = state
        replay_checks.append(dict(model=name, A_long_n=len(long_errors), max_abs_Tf_replay_error_C=max(long_errors),
                                  tolerance_C=tol, causal_n=len(causal_by_ref), match=True))
        print(name, 'A-long', len(long_errors), 'causal', len(causal_by_ref), 'replay error', max(long_errors), flush=True)
    write_lines(OUT / 'states-A-long.jsonl', all_long)
    write_lines(OUT / 'states-causal60.jsonl', all_causal)
    write_lines(OUT / 'rolling-jumps.jsonl', jump_records)
    write(OUT / 'replay-checks.json', replay_checks)
    write(ROOT / 'stage2-state-export.json', dict(finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
          spec_sha256=digest((ROOT / 'slowstate-spec.json').read_bytes()), no_fit=True,
          checks=replay_checks, outputs={n: digest((OUT / n).read_bytes()) for n in
          ['states-A-long.jsonl', 'states-causal60.jsonl', 'rolling-jumps.jsonl']}))
    return all_causal, all_long, jump_records


def ablate(data, model, causal):
    p = parameters(model)
    segments = {s['id']: s for s in data['segments']}
    primary = [r for r in causal if r['model'] == 'primary']
    primary_by_ref = {r['ref']: r for r in primary}
    state_values = {}
    for sid, segment in segments.items():
        selected = [r for r in primary if r['segment'] == sid]
        if not selected:
            continue
        E = selected[0]['E']
        assert all(r['E'] == E for r in selected)
        filters = filters_at_origins(segment, E, p)
        for state in selected:
            state_values[state['ref']] = dict(filters[state['ref']], **{'STATE-G2': state['Ts']})
    write_lines(OUT / 'four-state-origins.jsonl', [dict(ref=r['ref'], run=r['run'], segment=r['segment'],
        t=r['t'], utc=r['utc'], wall=r['wall'], E=r['E'], current_TJ=r['Tf'],
        current_inputs=r['current_inputs'], states=state_values[r['ref']],
        input_cutoff=r['input_cutoff'], initialization_window=r['evidence'],
        parameter_model_sha256=r['model_sha256']) for r in primary])
    points, a_replay, b_replay = [], [], []
    sealed = jsonlines(SRC / 'evaluation/primary/predictions.jsonl')
    for original in sealed:
        ref = original['ref']
        current_state = primary_by_ref.get(ref)
        item = dict(original)
        item['reference_B'] = item.pop('B')
        item['reference_A'] = item.pop('A')
        item['B_HOLD'], item['A_roll'] = {}, {}
        item['ablation_available'] = current_state is not None
        item['unavailable_reason'] = None if current_state is not None else 'original_60s_state_unavailable'
        if current_state is not None:
            h, E = original['h'], current_state['E']
            segment = segments[original['segment']]
            B_valid = item['reference_B'].get('G2-HOLD') is not None
            A_valid = item['reference_A'].get('G2') is not None
            item['state_values'] = state_values[ref]
            item['common_current_TJ'] = current_state['Tf']
            item['common_E'] = E
            item['current_inputs'] = current_state['current_inputs']
            if A_valid:
                dts, future = path_between(segment, original['t'], original['t'] + h)
            for branch in BRANCHES:
                initial = [current_state['Tf'], state_values[ref][branch]]
                if B_valid:
                    item['B_HOLD'][branch] = float(forecast('G2', p, E, initial,
                        np.array(current_state['current_inputs']), h, 'HOLD', model['P10_fit']))
                if A_valid:
                    item['A_roll'][branch] = float(propagate('G2', p, E, dts, future, initial)[-1, 0])
            if B_valid:
                b_replay.append(abs(item['B_HOLD']['STATE-G2'] - item['reference_B']['G2-HOLD']))
            if A_valid:
                a_replay.append(abs(item['A_roll']['STATE-G2'] - item['reference_A']['G2']))
        for kind in ['B_HOLD', 'A_roll']:
            assert len(item[kind]) in (0, 4)
        points.append(item)
    check = dict(A_roll_n=len(a_replay), A_roll_max_replay_error_C=max(a_replay),
                 B_HOLD_n=len(b_replay), B_HOLD_max_replay_error_C=max(b_replay), tolerance_C=1e-10)
    assert max(a_replay + b_replay) <= check['tolerance_C'], check
    write(OUT / 'ablation-replay-check.json', check)
    write_lines(OUT / 'four-branch-predictions.jsonl', points)
    return primary, state_values, points


def calculate_prediction_metrics(points):
    groups = defaultdict(list)
    for r in points:
        if r['label'] is None:
            continue
        # Side-by-side groups are complete four-branch cohorts, independently per h.
        for kind in ['A_roll', 'B_HOLD']:
            if not r[kind]:
                continue
            for stratum in [r['control_context'], 'all_contexts'] + (['legacy_strict'] if r['strict_label'] else []):
                for scale, value in [('all', 'LSM'), ('run', r['run']),
                                     ('macro', r['run'] + '/' + r['macro']),
                                     ('phase', r['run'] + '/' + str(r['phase'])),
                                     ('regime', r['run'] + '/' + str(r['regime']))]:
                    groups[(kind, r['h'], stratum, scale, value)].append(r)
    summary = []
    for (kind, h, stratum, scale, value), rows in sorted(groups.items()):
        cohort = '\n'.join(f"{r['ref']}|{h}|{r['label']['ref']}" for r in rows)
        metrics = {b: error_metrics([r[kind][b] - r['label']['value'] for r in rows]) for b in BRANCHES}
        refs = ['B0', 'B1', 'R_TJ', 'R_IO', 'G2-RELAX30']
        reference = {}
        for b in refs:
            pairs = [r for r in rows if r['reference_B'].get(b) is not None]
            reference[b] = dict(error_metrics([r['reference_B'][b] - r['label']['value'] for r in pairs]),
                                same_cohort=len(pairs) == len(rows))
        summary.append(dict(kind=kind, h=h, stratum=stratum, scale=scale, group=value,
            cohort_sha256=hashlib.sha256(cohort.encode()).hexdigest(), n=len(rows),
            support_seconds=sum(r['duration'] for r in rows), metrics=metrics, references=reference,
            paired_MAE_G2_minus={b: metrics['STATE-G2']['MAE'] - metrics[b]['MAE'] for b in BRANCHES[1:]}))
    write(OUT / 'temperature-metrics.json', summary)
    coverage = []
    for run in ['L', 'S', 'M']:
        for h in [15, 45, 90]:
            rows = [r for r in points if r['run'] == run and r['h'] == h]
            coverage.append(dict(run=run, h=h, accepted_origins=len(rows),
                qualified_temperature_labels=sum(r['label'] is not None for r in rows),
                legal_causal_state_origins=sum(r['ablation_available'] for r in rows),
                A_roll_all_four=sum(bool(r['A_roll']) for r in rows),
                B_HOLD_all_four=sum(bool(r['B_HOLD']) for r in rows),
                A_roll_scored=sum(bool(r['A_roll']) and r['label'] is not None for r in rows),
                B_HOLD_scored=sum(bool(r['B_HOLD']) and r['label'] is not None for r in rows),
                B_contexts=dict(Counter(r['control_context'] for r in rows if r['B_HOLD'])),
                independent_horizon=True))
    write(OUT / 'coverage.json', coverage)
    return summary


def observed_flags(node, raw):
    fan_payload = (raw.get(node['fan_ref']) or {}).get('payload') or {}
    fans = (fan_payload.get('data') or {}).get('fans') or []
    fan = next((f for f in fans if f.get('id') == 0), {})
    temp_payload = (raw.get(node['temp_ref']) or {}).get('payload') or {}
    temp = temp_payload.get('data') or {}
    duty = fan.get('duty') if fan.get('duty_valid') is True else None
    return dict(fan_ref=node['fan_ref'], temp_ref=node['temp_ref'],
        fault=fan.get('fault'), guard_active=fan.get('guard_active'), temp_stale=fan.get('temp_stale'),
        enabled=fan.get('enabled'), mode=fan.get('mode'), successful_PWM_percent=duty,
        duty_valid=fan.get('duty_valid'), manual_temperature=temp.get('manual_mode'),
        active_source=temp.get('active_source'), bound_variable=temp.get('bound_variable'),
        control_temperature_valid=temp.get('valid'),
        current_input_qualified=bool(node['good']), original_control_eligible=node['control_eligible'],
        observed_abnormal_or_changed=node['observed_abnormal_or_changed'],
        context_known=node['context_known'], context_change=node['context_change'],
        source_epoch=node['source_epoch'])


def demand_and_fast_ledger(data, primary, state_values):
    state_by_ref = {r['ref']: r for r in primary}
    accepted = {r['ref']: r for r in data['accepted']}
    demand = []
    reference, previous = {}, {}
    for state in primary:
        sid, ref = state['segment'], state['ref']
        if sid not in reference:
            reference[sid] = state_values[ref].copy()
            previous[sid] = (state['t'], {b: 0.0 for b in BRANCHES})
        tprev, zprev = previous[sid]
        dt_s = state['t'] - tprev
        branches = {b: shape(state_values[ref][b], reference[sid][b], zprev[b], dt_s) for b in BRANCHES}
        previous[sid] = (state['t'], {b: branches[b]['z_output'] for b in BRANCHES})
        demand.append(dict(ref=ref, run=state['run'], segment=sid, t=state['t'], wall=state['wall'],
            utc=state['utc'], measured_TJ=state['Tf'], branches=branches,
            reference_is_not_equilibrium=True, normal_only=True, deployable=False,
            source_epoch=state['source_epoch'], valid_until=state['current_input_valid_until']))
    dbyref = {r['ref']: r for r in demand}
    ledger = []
    for run in ['L', 'S', 'M']:
        evidence = read(SRC / f'registered/evidence-{run}.json')
        raw = {r['ref']: r for r in jsonlines(SRC / f'control-{run}.jsonl')}
        sample_times = [r['mono_s'] for r in evidence['samples']]
        offset = evidence['samples'][0]['wall'] - sample_times[0]
        held = None
        last_source = None
        last_node = None
        for node in evidence['nodes']:
            t = node['t']
            # This event is scheduled from an ALREADY KNOWN expiry, never backdated from a future gap.
            if last_node is not None and last_node['good'] and last_node['valid_until'] < t - 1e-9:
                deadline = last_node['valid_until']
                expiry_i = bisect.bisect_right(sample_times, deadline) - 1
                expiry_sample = evidence['samples'][expiry_i] if expiry_i >= 0 else None
                ledger.append(dict(run=run, t=deadline, wall=deadline + offset,
                    ref=None, trigger_ref=last_node['ref'], event='known_input_expiry',
                    derived_event=True, fast_status=dict(observed_flags(last_node, raw), current_input_qualified=False),
                    ordinary_available=False, reason='known_input_validity_expired',
                    normal_extra_demand_index=None, shape_ref=None, segment=None,
                    current_input_valid_until=deadline,
                    measured_TJ=expiry_sample['values']['tj'] if expiry_sample else None,
                    measured_TJ_ref=expiry_sample['ref'] if expiry_sample else None,
                    measured_TJ_valid=bool(expiry_sample and deadline < expiry_sample['source_valid_until'] and
                                           expiry_sample['source_epoch'] == last_node['source_epoch']),
                    measured_TJ_valid_until=expiry_sample['source_valid_until'] if expiry_sample else None))
                held = None
            flags = observed_flags(node, raw)
            si = bisect.bisect_right(sample_times, t + 1e-9) - 1
            sample = evidence['samples'][si] if si >= 0 else None
            source_change = last_source is not None and last_source != node['source_epoch']
            current_good = (node['good'] and node['valid_until'] > t and
                            not node['observed_abnormal_or_changed'] and not node['context_change'] and
                            not source_change)
            reasons = list(node['reasons'])
            if source_change:
                reasons.append('source_identity_changed')
            if not current_good:
                held = None
            elif node['ref'] in dbyref:
                held = dbyref[node['ref']]
            available = current_good and held is not None and held['source_epoch'] == node['source_epoch']
            ledger.append(dict(run=run, t=t, wall=t + offset, ref=node['ref'], trigger_ref=node['trigger_ref'],
                event='original_observation', derived_event=False, fast_status=flags,
                measured_TJ=sample['values']['tj'] if sample else None,
                measured_TJ_ref=sample['ref'] if sample else None,
                measured_TJ_valid=bool(sample and t < sample['source_valid_until'] and sample['source_epoch'] == node['source_epoch']),
                measured_TJ_valid_until=sample['source_valid_until'] if sample else None,
                current_input_valid_until=node['valid_until'],
                ordinary_available=available,
                reason=None if available else (';'.join(reasons) if reasons else 'original_60s_history_unavailable'),
                normal_extra_demand_index={b: held['branches'][b]['z_output'] for b in BRANCHES} if available else None,
                shape_ref=held['ref'] if available else None, segment=held['segment'] if available else None))
            last_node, last_source = node, node['source_epoch']
        runledger = [r for r in ledger if r['run'] == run]
        for i, r in enumerate(runledger):
            r['duration_s'] = (runledger[i + 1]['t'] - r['t']) if i + 1 < len(runledger) else 0.0
            assert r['duration_s'] >= 0
    write_lines(OUT / 'normal-demand-origins.jsonl', demand)
    write_lines(OUT / 'fast-status-and-demand-ledger.jsonl', ledger)
    # Complete accepted-origin availability, including otherwise valid TJ without legal state.
    origins = []
    ledger_by_ref = {r['ref']: r for r in ledger if r['ref'] is not None}
    for row in data['accepted']:
        l = ledger_by_ref[row['ref']]
        origins.append(dict(ref=row['ref'], run=row['run'], t=row['mono_s'], wall=row['wall'], utc=row['utc'],
            measured_TJ=row['values']['tj'], source_identity=row['source_identity'],
            ordinary_available=l['ordinary_available'], reason=l['reason'], segment=l['segment'],
            shape_ref=l['shape_ref'], branches=dbyref[row['ref']]['branches'] if row['ref'] in dbyref else None,
            fast_status=l['fast_status']))
    write_lines(OUT / 'accepted-demand-availability.jsonl', origins)
    return demand, ledger


def signal_stats(rows, ledger, branch):
    byref = {r['ref']: r for r in rows}
    runs = sorted({l['run'] for l in ledger})
    available = [l for l in ledger if l['ordinary_available'] and l['shape_ref'] in byref]
    support = sum(l['duration_s'] for l in ledger)
    available_s = sum(l['duration_s'] for l in available)
    result = dict(total_seconds=support, available_seconds=available_s,
                  unavailable_seconds=support - available_s,
                  available_fraction=available_s / support if support else None,
                  unavailable_reason_seconds={})
    for l in ledger:
        if not l['ordinary_available']:
            key = l['reason']
            result['unavailable_reason_seconds'][key] = result['unavailable_reason_seconds'].get(key, 0) + l['duration_s']
    for field in ['z_raw', 'z_target', 'z_output']:
        sequences, values, weighted = [], [], []
        seq, last = [], None
        for l in ledger:
            if not l['ordinary_available'] or l['shape_ref'] not in byref:
                if seq:
                    sequences.append(seq)
                seq, last = [], None
                continue
            d = byref[l['shape_ref']]
            key = (l['run'], l['segment'])
            v = d['branches'][branch][field]
            if last is not None and key != last:
                sequences.append(seq)
                seq = []
            seq.append(v)
            values.append(v)
            weighted.append((v, l['duration_s']))
            last = key
        if seq:
            sequences.append(seq)
        result[field] = dict(min=min(values) if values else None, max=max(values) if values else None,
            amplitude=max(values) - min(values) if values else None,
            weighted_mean=sum(v * s for v, s in weighted) / available_s if available_s else None,
            total_variation=sum(sum(abs(b - a) for a, b in zip(s, s[1:])) for s in sequences),
            significant_reversals=sum(reversal_count(s) for s in sequences))
    result['lower_clipped_s'] = sum(l['duration_s'] for l in available if byref[l['shape_ref']]['branches'][branch]['lower_clipped'])
    result['upper_clipped_s'] = sum(l['duration_s'] for l in available if byref[l['shape_ref']]['branches'][branch]['upper_clipped'])
    result['at_zero_target_s'] = sum(l['duration_s'] for l in available if byref[l['shape_ref']]['branches'][branch]['z_target'] == 0)
    result['at_one_target_s'] = sum(l['duration_s'] for l in available if byref[l['shape_ref']]['branches'][branch]['z_target'] == 1)
    return result


def events_for_runs(data):
    events = []
    for run in data['runs']:
        for ph in run['phases']:
            if ph.get('macro') == 'work' or (run['run'] == 'S' and ph['id'] in ['pilot','sparse','continuous']):
                events.append(dict(run=run['run'], id='phase-' + str(ph['id']), kind='work_phase',
                                   start=ph['start'], end=ph['end']))
        for req in run['requests']:
            events.append(dict(run=run['run'], id=req['id'], kind='request',
                               start=req['start'], end=req['end']))
    return events


def demand_metrics(data, demand, ledger):
    metrics = []
    for run in data['runs']:
        r = run['run']
        ranges = [('whole-run', None, None)] + [('phase-' + str(p['id']), p['start'], p['end']) for p in run['phases']]
        for label, start, end in ranges:
            ls = [l for l in ledger if l['run'] == r and (start is None or
                  (l['wall'] < end and l['wall'] + l['duration_s'] > start))]
            if start is not None:
                if ls:
                    clock_offset=ls[0]['wall']-ls[0]['t']
                    start_mono,end_mono=start-clock_offset,end-clock_offset
                    ls = [dict(l, duration_s=max(0,min(l['t']+l['duration_s'],end_mono)-max(l['t'],start_mono))) for l in ls]
            rows = [d for d in demand if d['run'] == r]
            metrics.append(dict(run=r, group=label, branches={b: signal_stats(rows, ls, b) for b in BRANCHES}))
    write(OUT / 'demand-signal-metrics.json', metrics)
    events = events_for_runs(data)
    tails = []
    byref = {d['ref']: d for d in demand}
    for ev in events:
        r, end = ev['run'], ev['end']
        requests = [e for e in events if e['run'] == r and e['kind'] == 'request' and e['start'] > end + 1e-6]
        next_start = min((e['start'] for e in requests), default=float('inf'))
        runls = [l for l in ledger if l['run'] == r and l['wall'] >= end]
        if not runls:
            continue
        if not runls[0]['ordinary_available']:
            tails.append(dict(event=ev, status='unavailable_at_end', reason=runls[0]['reason'], branches=None))
            continue
        sid = runls[0]['segment']
        valid = []
        censor = '300s_window_end'
        censor_wall = min(end+300, next_start, runls[-1]['wall'])
        for l in runls:
            if l['wall'] >= end + 300:
                break
            if l['wall'] >= next_start:
                censor = 'next_request'
                break
            if not l['ordinary_available'] or l['segment'] != sid:
                censor = 'qualification_or_reference_changed'
                censor_wall = min(censor_wall, l['wall'])
                break
            valid.append(l)
        if runls[-1]['wall'] < end+300 and censor == '300s_window_end':
            censor = 'record_end'
        clock_offset=runls[0]['wall']-runls[0]['t']
        end_mono=end-clock_offset
        censor_relative=censor_wall-clock_offset-end_mono
        bs = {}
        for b in BRANCHES:
            fieldstats = {}
            for field in ['z_raw', 'z_target', 'z_output']:
                vals = [(l['wall'] - end, byref[l['shape_ref']]['branches'][b][field]) for l in valid]
                cross = next((i for i, (t, v) in enumerate(vals) if v <= .02), None)
                fieldstats[field] = dict(at_first=vals[0][1] if vals else None,
                    first_return_s=vals[cross][0] if cross is not None else None,
                    recrosses_above_after_return=bool(cross is not None and any(v > .02 for _, v in vals[cross + 1:])),
                    final_value=vals[-1][1] if vals else None)
            bs[b] = fieldstats
        tails.append(dict(event=ev, status='observed_until_censor', segment=sid,
            observed_tail_s=valid[-1]['wall'] - end if valid else 0,
            censor=censor, branches=bs,
            bins={f'{lo}-{hi}s': dict(available_seconds=sum(max(0,min(l['t']-end_mono+l['duration_s'],hi,censor_relative)-
                                                            max(l['t']-end_mono,lo)) for l in valid))
                  for lo, hi in [(0,5),(5,15),(15,45),(45,90),(90,300)]}))
    write(OUT / 'post-task-tail-metrics.json', tails)
    return metrics, tails


def diagnostics(data, models, causal, long, jumps, points, ledger):
    # No threshold-based exclusions: retain extrema and distributions of all re-estimation corrections.
    jump_summary = []
    for model in MODELS:
        for run in ['L','S','M']:
            selected = [j for j in jumps if j['model'] == model and j['run'] == run]
            states = [r for r in causal if r['model'] == model and r['run'] == run]
            jump_summary.append(dict(model=model, run=run, Ts=distributions([r['Ts'] for r in states]),
                delta_Ts=distributions([abs(j['delta_Ts']) for j in selected]),
                delta_Ts_rate_C_s=distributions([abs(j['delta_Ts'])/j['dt'] for j in selected]),
                correction=distributions([abs(j['correction_after_already_observed_path']) for j in selected]),
                initial_Ts=distributions([r['evidence']['Ts_initial'] for r in states]),
                bounds_hit_n=sum(bool(r['evidence']['bounds_hit']) for r in states),
                largest_corrections=sorted(selected, key=lambda j:abs(j['correction_after_already_observed_path']), reverse=True)[:20]))
    write(OUT / 'state-window-diagnostics.json', jump_summary)
    init_diagnostics=[]
    segments={s['id']:s for s in data['segments']}
    for model in MODELS:
        cals=read(SRC/f'evaluation/{model}/calibrations.json')['G2']
        p=parameters(models[model])
        for sid,cal in cals.items():
            seg=segments[sid];start=seg['rows'][0]['mono_s']
            response=[]
            for offset in [60,105,150,300]:
                if start+offset>seg['rows'][-1]['mono_s']:continue
                ds,u=path_between(seg,start,start+offset)
                zero=u.copy();zero[:,:2]=0
                response.append(dict(seconds_from_strict_start=offset,
                    per_1C_initial_Tf=propagate('G2',p,0,ds,zero,[1,0])[-1].tolist(),
                    per_1C_initial_Ts=propagate('G2',p,0,ds,zero,[0,1])[-1].tolist(),
                    per_1C_fixed_E=propagate('G2',p,1,ds,zero,[0,0])[-1].tolist()))
            init_diagnostics.append(dict(model=model,run=seg['run'],segment=sid,
                original_causal_calibration=cal,unit_sensitivity=response,
                sensitivity_is_dimensionless_linear_response=True,no_refit=True,
                prefix_is_not_equilibrium=True))
    write(OUT/'prefix-and-unit-initialization-sensitivity.json',init_diagnostics)
    sensitivity = []
    for mode, records in [('causal60', causal), ('A-long', long)]:
        for run in ['L','S','M']:
            maps = {m: {r['ref']:r for r in records if r['model'] == m and r['run'] == run} for m in MODELS}
            refs = sorted(set.intersection(*(set(v) for v in maps.values())), key=lambda k:maps['primary'][k]['t'])
            for other in ['old_LS','A24']:
                first = refs[0]
                absolute = [maps['primary'][r]['Ts'] - maps[other][r]['Ts'] for r in refs]
                incremental = [(maps['primary'][r]['Ts'] - maps['primary'][first]['Ts']) -
                    (maps[other][r]['Ts'] - maps[other][first]['Ts']) for r in refs]
                sensitivity.append(dict(mode=mode, run=run, other=other, n=len(refs),
                    fixed_reference_ref=first, reference_primary=maps['primary'][first]['Ts'],
                    reference_other=maps[other][first]['Ts'], absolute_difference=error_metrics(absolute),
                    incremental_difference=error_metrics(incremental), no_per_segment_recentring=True,
                    Tf_difference=error_metrics([maps['primary'][r]['Tf']-maps[other][r]['Tf'] for r in refs]) if mode=='A-long' else None,
                    Tf_TJ_errors_common={m:error_metrics([maps[m][r]['Tf_error'] for r in refs]) for m in MODELS} if mode=='A-long' else None,
                    causal_Tf_is_observation_anchor=mode=='causal60'))
    write(OUT / 'frozen-model-state-sensitivity.json', sensitivity)
    q_rows, qsummary = [], []
    for run in ['L','S','M']:
        rows = [r for r in data['accepted'] if r['run'] == run]
        evidence_nodes = {n['ref']:n for n in read(SRC/f'registered/evidence-{run}.json')['nodes']}
        P = np.array([[r['values']['vdd_gpu'], r['values']['vdd_cpu_soc_mss']] for r in rows])
        qs = {m:P @ np.array(parameters(v)[4:]) for m,v in models.items()}
        for i, row in enumerate(rows):
            q_rows.append(dict(run=run, ref=row['ref'], wall=row['wall'], t=row['mono_s'],
                VDD_GPU_W=float(P[i,0]), VDD_CPU_SOC_MSS_W=float(P[i,1]),
                power_qualified=evidence_nodes[row['ref']]['power_ok'],
                full_current_input_qualified=evidence_nodes[row['ref']]['good'],
                q_equiv_C_per_s={m:float(v[i]) for m,v in qs.items()}))
        qsummary.append(dict(run=run, n=len(rows), power_correlation=float(np.corrcoef(P.T)[0,1]),
            VDD_GPU_W=distributions(P[:,0]), VDD_CPU_SOC_MSS_W=distributions(P[:,1]),
            ratio_gpu_to_cpu_soc_mss=distributions(P[:,0]/P[:,1]),
            q_equiv={m:distributions(v) for m,v in qs.items()},
            primary_vs={m:dict(correlation=float(np.corrcoef(qs['primary'],qs[m])[0,1]),
                signed_difference_C_per_s=distributions(qs['primary']-qs[m]),
                MAE_C_per_s=float(np.mean(abs(qs['primary']-qs[m])))) for m in ['old_LS','A24']},
            attribution='combined-drive support only; not independent CPU or GPU thermal contribution'))
        qsummary[-1]['population']='all original accepted TJ records with their recorded rail values; qualification flags retained'
        legal=np.array([evidence_nodes[row['ref']]['good'] for row in rows])
        qsummary[-1]['strict_current_input_population']=dict(n=int(legal.sum()),power_correlation=float(np.corrcoef(P[legal].T)[0,1]),
            VDD_GPU_W=distributions(P[legal,0]),VDD_CPU_SOC_MSS_W=distributions(P[legal,1]),
            ratio_gpu_to_cpu_soc_mss=distributions(P[legal,0]/P[legal,1]),
            q_equiv={m:distributions(v[legal]) for m,v in qs.items()})
    write_lines(OUT / 'combined-drive.jsonl', q_rows)
    write(OUT / 'combined-drive-diagnostics.json', qsummary)
    boundaries = []
    pc = [r for r in causal if r['model'] == 'primary']
    for run in data['runs']:
        for ph in run['phases']:
            candidates = [r for r in pc if r['run'] == run['run']]
            before = [r for r in candidates if r['wall'] < ph['start']]
            after = [r for r in candidates if r['wall'] >= ph['start']]
            boundaries.append(dict(run=run['run'], phase=ph['id'], wall=ph['start'],
                previous_ref=before[-1]['ref'] if before else None, next_ref=after[0]['ref'] if after else None,
                previous_segment=before[-1]['segment'] if before else None,
                next_segment=after[0]['segment'] if after else None,
                phase_does_not_reset_state=True))
    write(OUT / 'phase-boundary-audit.json', boundaries)
    long_by_ref = {r['ref']:r for r in long if r['model']=='primary'}
    peaks = []
    for ev in events_for_runs(data):
        rows = [r for r in data['accepted'] if r['run']==ev['run'] and ev['start']<=r['wall']<=ev['end']+5]
        if not rows:
            continue
        peak = max(rows,key=lambda r:r['values']['tj'])
        matched = long_by_ref.get(peak['ref'])
        peaks.append(dict(event=ev, actual_peak_C=peak['values']['tj'], actual_peak_ref=peak['ref'],
            at_actual_peak_Tf_error_C=matched['Tf_error'] if matched else None,
            A_long_available_at_actual_peak=matched is not None,
            qualification_coverage=len([r for r in rows if r['ref'] in long_by_ref])/len(rows)))
    write(OUT / 'original-Tf-peak-errors.json', peaks)
    # Explicit event windows, all v2 contexts kept. No inference uses these future annotations.
    event_metrics = []
    for ev in events_for_runs(data):
        for window, lo, hi in [('work',ev['start'],ev['end'])] + [
            (f'tail-{a}-{b}',ev['end']+a,ev['end']+b) for a,b in [(0,5),(5,15),(15,45),(45,90),(90,300)]]:
            selected = [p for p in points if p['run']==ev['run'] and lo<=p['wall']<hi]
            for kind in ['A_roll','B_HOLD']:
                for h in [15,45,90]:
                    subset = [p for p in selected if p['h']==h and p[kind] and p['label'] is not None]
                    event_metrics.append(dict(event=ev, window=window, kind=kind,h=h,n=len(subset),
                        context_counts=dict(Counter(p['control_context'] for p in subset)),
                        metrics={b:error_metrics([p[kind][b]-p['label']['value'] for p in subset]) for b in BRANCHES}))
    write(OUT / 'event-temperature-metrics.json',event_metrics)
    bad = [l for l in ledger if l['event']=='original_observation' and
           (l['fast_status']['observed_abnormal_or_changed'] or l['fast_status']['temp_stale'] is True or l['fast_status']['guard_active'] is True or l['fast_status']['fault'] is True)]
    assert bad and all(l['normal_extra_demand_index'] is None for l in bad)
    write(OUT / 'risk-invalidation-audit.json',dict(observed_abnormal_nodes=len(bad),
        ordinary_null_same_node=sum(l['normal_extra_demand_index'] is None for l in bad),
        examples=bad[:10], artificial_temperature_thresholds=False, hardware_commands=False))
    return sensitivity


def main():
    started=time.perf_counter()
    before=resource.getrusage(resource.RUSAGE_SELF)
    assert read(ROOT/'stage1-freeze.json')['spec_sha256']==digest((ROOT/'slowstate-spec.json').read_bytes())
    OUT.mkdir(exist_ok=True)
    build_kernel(ROOT/'build')
    data,models=load_inputs()
    causal,long,jumps=export_states(data,models)
    primary,values,points=ablate(data,models['primary'],causal)
    calculate_prediction_metrics(points)
    demand,ledger=demand_and_fast_ledger(data,primary,values)
    demand_metrics(data,demand,ledger)
    diagnostics(data,models,causal,long,jumps,points,ledger)
    after=resource.getrusage(resource.RUSAGE_SELF)
    write(OUT/'resources.json',dict(wall_seconds=time.perf_counter()-started,
        user_cpu_s=after.ru_utime-before.ru_utime,system_cpu_s=after.ru_stime-before.ru_stime,
        maxrss_bytes_macos=after.ru_maxrss,python=sys.version,executable=sys.executable,
        platform=platform.platform(),machine=platform.machine(),
        single_thread_env={k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']},
        numpy=np.__version__,cuda_used=False,optimization_runs=0,network_requests=0))
    write(ROOT/'stage3-complete.json',dict(finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        spec_sha256=digest((ROOT/'slowstate-spec.json').read_bytes()),parameter_refits=0,
        results={p.name:digest(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()}))
    print('Offline state / ablation / demand complete.',flush=True)


if __name__=='__main__':
    main()
