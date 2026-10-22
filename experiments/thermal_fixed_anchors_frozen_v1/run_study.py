"""Frozen current-run replay and evaluation. This program never constructs a network client."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'
import argparse
import bisect
import collections
import copy
import datetime as dt
import hashlib
import json
import math
import platform
import resource
import sys
import time
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor/src'))
import numpy as np
import scipy
from scipy.linalg import expm
from prepare import read, write, sha
from tto.config import load_config, merge, validate
from tto.engine import engine_for
from tto.storage import source_identity
from tto_field.projection import SavedStream
from tto_field.comm_bridge import CommunicationBridge
from tto_field.research.observer import ThermalObserver


def lines(p):
    with Path(p).open() as f:
        for s in f:
            if s.strip():
                yield json.loads(s)


def jsonl(p, rows):
    with Path(p).open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')


def seconds(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def compare(a, b, path='', differences=None):
    """Structure/flags exact; scientific floating-point tolerance for CPU/platform replay."""
    differences = [] if differences is None else differences
    if isinstance(a, dict):
        assert set(a) == set(b), path
        for k in a:
            compare(a[k], b[k], path + '/' + str(k), differences)
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, path + '/' + str(i), differences)
    elif isinstance(a, float):
        assert isinstance(b, (int, float)) and math.isfinite(a) and math.isfinite(b), path
        d = abs(a - b)
        assert d <= 1e-8, (path, a, b, d)
        differences.append(d)
    else:
        assert a == b, (path, a, b)
    return differences


def phase_table():
    events = list(lines(ROOT / 'inputs/field/scheduler-events.jsonl'))
    out = []
    for e in events:
        if e['event'] == 'phase_start':
            end = next(x for x in events if x['event'] == 'phase_end' and x['index'] == e['index'])
            out.append(dict(index=e['index'], name=f"{e['index']}-{e['stage']['kind']}",
                            start=seconds(e['recorded_at_utc']), end=seconds(end['recorded_at_utc']),
                            stage=e['stage']))
    return out


def phase_at(phases, wall):
    return next((p['name'] for p in phases if p['start'] <= wall < p['end']), 'preparation_or_tail')


class Dynamics:
    def __init__(self, spec):
        self.p = spec['dynamic']

    @lru_cache(maxsize=65536)
    def operator(self, span, pwm):
        p = self.p
        d = p['d0'] + p['d1'] * pwm
        m = np.zeros((4, 4))
        m[:3, :3] = [[-p['a'], p['a'], 0], [p['c'], -p['c']-d, d], [0, 0, 0]]
        m[0, 3] = 1
        e = expm(m * span)
        return e[:3, :3], e[:3, 3]

    def step(self, x, u, span):
        F, g = self.operator(float(span), float(u[2]))
        return F @ np.asarray(x) + g * (self.p['b_g'] * u[0] + self.p['b_c'] * u[1])


class PhysicalPath:
    def __init__(self, nodes, dyn):
        self.nodes, self.dyn = nodes, dyn
        self.times = [n['t'] for n in nodes]

    def pieces(self, start, end):
        lo = bisect.bisect_right(self.times, start) - 1
        hi = bisect.bisect_left(self.times, end)
        if lo < 0 or end > self.times[-1] or end < start:
            return None
        edges = [start] + self.times[lo+1:hi] + [end]
        used = self.nodes[lo:hi]
        if len(used) != len(edges)-1:
            return None
        epoch = used[0]['epoch'] if used else None
        if any(n['u'] is None or n['until'] < right-1e-9 or n['epoch'] != epoch
               for n, right in zip(used, edges[1:])):
            return None
        return [(right-left, n) for left, right, n in zip(edges, edges[1:], used)]

    def propagate(self, x, pieces):
        # Support a matrix of initial states so all branches share identical actual inputs.
        x = np.asarray(x, float)
        for span, n in pieces:
            F, g = self.dyn.operator(float(span), float(n['u'][2]))
            q = self.dyn.p['b_g']*n['u'][0] + self.dyn.p['b_c']*n['u'][1]
            x = x @ F.T + g*q if x.ndim == 2 else F @ x + g*q
        return x


def replay(out, spec, phases):
    m = read(ROOT / 'inputs/native/manifest.json')
    assert source_identity()['sha256'] == spec['native_source_sha256']
    c = load_config(environ={})
    saved = copy.deepcopy(m['config'])
    for section in ('orin', 'tianshan'):
        saved[section]['headers_file'] = saved[section]['ca_file'] = None
    merge(c, saved)
    validate(c)
    engine = engine_for(c, record_schema=m['record_schema'])
    ospec = read(ROOT / 'vendor/src/tto_field/research/observer-spec.json')
    stream = SavedStream(m, ospec, engine)
    comm = CommunicationBridge(m, engine)
    observers = {method: ThermalObserver(ospec, method) for method in spec['state_methods']}
    samples, nodes, signals, quality, resets = [], [], [], [], []
    count, max_diff = 0, 0.
    filters = None
    filter_last = None
    previous_cold = None
    state_phase = collections.Counter()
    flags_mismatch = 0
    # No Pipeline/collector/Requester runtime invocation: only the same pure processing calls.
    saved_states = iter(lines(ROOT / 'inputs/field/states.jsonl'))
    for raw in lines(ROOT / 'inputs/native/observations-0001.jsonl'):
        processed = engine.process(raw)
        communication = comm.feed(raw, processed)
        frame = stream.feed(raw, processed)
        before = {k: (v or {}).get('raw_valid', False) for k, v in frame['measurement'].items()}
        if not communication['measurement']['TJ_and_rails']['raw_valid']:
            for name in ('tj', 'power'):
                if frame['measurement'][name]:
                    frame['measurement'][name]['raw_valid'] = False
            frame['new_TJ'] = False
        states = {name: observer.step(frame) for name, observer in observers.items()}
        recorded = next(saved_states)
        assert recorded['generation_evidence']['native_ref'] == raw['ref']
        assert before == recorded['native_projected_validity_before_I02']
        d = compare(states['AUGMENTED-KF'], recorded['state'])
        max_diff = max(max_diff, max(d, default=0))
        # Verify the owner's I02 record, not just its final Boolean.
        compare(communication, recorded['communication'])
        tj, power, fan = (frame['measurement'][k] for k in ('tj', 'power', 'last_successful_pwm'))
        physical = bool(power and power['raw_valid'] and fan and fan['raw_valid'])
        node = dict(t=frame['t'], wall=seconds(frame['utc']), ref=raw['ref'], epoch=frame['identity']['source_epoch'],
                    u=power['rails_W'] + [fan['value_percent']/100] if physical else None,
                    until=min(power['valid_until_mono_s'], fan['valid_until_mono_s']) if physical else frame['t'],
                    context='confirmed_normal' if frame['safety']['confirmed_normal_now'] else 'observed_abnormal_or_unknown',
                    safety=frame['safety'])
        if nodes and nodes[-1]['t'] == node['t']:
            nodes[-1] = node
        else:
            nodes.append(node)
        ob = states['AUGMENTED-KF']['observer']
        available = ob['available']
        if frame['source_reset'] or previous_cold != ob['cold_starts'] or not available:
            filters = filter_last = None
        if available and tj:
            if filter_last is not None:
                elapsed = frame['t'] - filter_last[0]
                filters = [filter_last[1] + (v-filter_last[1])*math.exp(-elapsed/tau)
                           for v, tau in zip(filters, (30, 120))]
            p = ospec['dynamic']
            u = ob['conditional_inputs_rails_W_PWM']
            loss = p['d0'] + p['d1']*u[2]
            qs = (p['c']*tj['value_C'] + loss*ob['E_C'])/(p['c']+loss)
            if filters is None:
                filters = [qs, qs]
            filter_last = (frame['t'], qs)
        else:
            qs = None
        previous_cold = ob['cold_starts']
        substitutions = dict(QS=qs, LP30=filters[0] if filters else None, LP120=filters[1] if filters else None)
        signal = dict(t=frame['t'], wall=node['wall'], ref=raw['ref'], epoch=node['epoch'],
                      phase=phase_at(phases, node['wall']), model_phase=ob['phase'], available=available,
                      current_TJ_C=tj['value_C'] if tj and tj['raw_valid'] else None,
                      TJ_until=tj['valid_until_mono_s'] if tj and tj['raw_valid'] else frame['t'],
                      values=dict(KF_Tf=ob['Tf_C'], KF_Ts=ob['Ts_C'], E=ob['E_C'],
                                  CONDITIONAL_Ts=states['CONDITIONAL-HOLD']['observer']['Ts_C'], **substitutions),
                      state_std_C=ob['uncertainty']['marginal_std_C'], safety=frame['safety'],
                      boundary_projected=ob['boundary_projected'], cold_starts=ob['cold_starts'])
        signals.append(signal)
        state_phase[ob['phase']] += 1
        q = processed['quality']
        if q:
            quality.append(dict(ref=raw['ref'], t=raw['mono_s'], quality=q, I02_source_valid=communication['measurement']['TJ_and_rails']['raw_valid']))
        if frame['source_reset']:
            resets.append(dict(ref=raw['ref'], t=raw['mono_s'], reason=frame['reset_reason'], cold_starts=ob['cold_starts']))
        if q and q['accepted']:
            assert tj and tj['source_ref'] == raw['ref']
            valid = bool(frame['new_TJ'] and tj['raw_valid'] and power and power['raw_valid'])
            samples.append(dict(t=frame['t'], wall=node['wall'], ref=raw['ref'], utc=raw['received_at_utc'],
                                epoch=node['epoch'], source_key=q['key'][:2], source_valid=valid,
                                current=tj['value_C'], phase=signal['phase'], states={k:v['observer'] for k,v in states.items()},
                                filters=substitutions, raw_input=node['u'], physical_until=node['until'],
                                safety=frame['safety']))
        count += 1
    assert next(saved_states, None) is None
    jsonl(out/'samples-and-causal-states.jsonl', samples)
    jsonl(out/'physical-input-nodes.jsonl', nodes)
    jsonl(out/'signal-frames.jsonl', signals)
    jsonl(out/'quality-ledger.jsonl', quality)
    write(out/'state-replay-verification.json', dict(raw_events=count, single_native_process_per_event=True,
          I02_views=comm.view.process_calls, recorded_states_compared=count, accepted_TJ=len(samples),
          source_valid_TJ=sum(a['source_valid'] for a in samples), state_and_I02_structure_flags_exact=True,
          max_state_float_abs_difference=max_diff, float_tolerance=1e-8, state_phase_all_events=dict(state_phase),
          source_resets=resets, no_phase_resets=True, network_clients_constructed=0, dynamic_fits=0,
          original_quality=dict(engine.q.counts), original_processing=dict(engine.counts)))
    return samples, nodes, signals, ospec


def target_label(samples, times, origin, horizon):
    if not origin['source_valid']:
        return None, 'origin_source_invalid'
    i = bisect.bisect_left(times, origin['t'] + horizon)
    if i >= len(samples) or samples[i]['t'] > origin['t']+horizon+2:
        return None, 'no_TJ_answer'
    a = samples[i]
    if not a['source_valid']:
        return None, 'target_source_invalid'
    if a['epoch'] != origin['epoch'] or a['source_key'] != origin['source_key']:
        return None, 'source_identity_or_validity_boundary'
    return dict(ref=a['ref'], t=a['t'], value=a['current'], offset_s=a['t']-origin['t']-horizon, phase=a['phase']), None


def error_stats(errors):
    e = np.asarray(errors, float)
    if not len(e):
        return dict(n=0, MAE_C=None, RMSE_C=None, mean_error_C=None,
                    P95_abs_error_C=None, P95_underprediction_C=None, max_underprediction_C=None,
                    fraction_underprediction_gt_2C=None)
    under = np.maximum(-e, 0)
    return dict(n=len(e), MAE_C=float(abs(e).mean()), RMSE_C=float(np.sqrt(np.mean(e*e))),
                mean_error_C=float(e.mean()), P95_abs_error_C=float(np.percentile(abs(e),95)),
                P95_underprediction_C=float(np.percentile(under,95)), max_underprediction_C=float(under.max()),
                fraction_underprediction_gt_2C=float(np.mean(under > 2)))


def cohort_id(rows):
    return hashlib.sha256('\n'.join(f"{r['ref']}|{r['h']}|{r['label']['ref']}" for r in rows).encode()).hexdigest()


BRANCHES = ['AUGMENTED-KF', 'CONDITIONAL-HOLD', 'QS', 'LP30', 'LP120']


def evaluate(samples, nodes, ospec, spec, out):
    dyn = Dynamics(ospec)
    path = PhysicalPath(nodes, dyn)
    times = [a['t'] for a in samples]
    points, history = [], []
    for a in samples:
        if not a['source_valid'] or (history and (a['epoch'] != history[-1]['epoch'] or a['t']-history[-1]['t'] > 5)):
            history = []
        if a['source_valid']:
            history.append(a)
        j = bisect.bisect_left([z['t'] for z in history], a['t']-30)
        slope = ((a['current']-history[j]['current'])/(a['t']-history[j]['t'])
                 if j < len(history) and a['t']-history[j]['t'] >= 10 else None)
        for h in spec['horizons_s']:
            label, rejection = target_label(samples, times, a, h)
            row = dict(ref=a['ref'], t=a['t'], utc=a['utc'], h=h, phase=a['phase'], source_valid=a['source_valid'],
                       label=label, label_rejection=rejection, baselines={}, A_roll={}, B_HOLD={},
                       observer_phase=a['states']['AUGMENTED-KF']['phase'],
                       origin_context='confirmed_normal' if a['safety']['confirmed_normal_now'] else 'observed_abnormal_or_unknown',
                       future_contexts=None, input_cutoff_ref=a['ref'])
            if a['source_valid']:
                row['baselines']['B0'] = a['current']
                if slope is not None:
                    row['baselines']['B1'] = a['current'] + h*slope
            init, keys = [], []
            for branch in BRANCHES:
                ob = a['states'].get(branch, a['states']['AUGMENTED-KF'])
                ts = ob['Ts_C'] if branch in a['states'] else a['filters'][branch]
                if not a['source_valid'] or not ob['available'] or ts is None:
                    continue
                x = [a['current'], ts, ob['E_C']]
                u = ob['conditional_inputs_rails_W_PWM']
                row['B_HOLD'][branch] = float(dyn.step(x, u, h)[0])
                init.append(x)
                keys.append(branch)
            pieces = path.pieces(a['t'], a['t']+h)
            if pieces is not None and init:
                xs = path.propagate(init, pieces)
                row['A_roll'] = {k:float(x[0]) for k,x in zip(keys,xs)}
                row['future_contexts'] = sorted({n['context'] for _, n in pieces})
            points.append(row)
    jsonl(out/'predictions.jsonl', points)
    metrics, coverage = [], []
    for kind in ('A_roll', 'B_HOLD'):
        for h in spec['horizons_s']:
            base = [r for r in points if r['h'] == h]
            for b in BRANCHES:
                labelled = [r for r in base if r['label'] is not None]
                usable = [r for r in labelled if b in r[kind]]
                coverage.append(dict(kind=kind, h=h, branch=b, all_source_valid_TJ=sum(a['source_valid'] for a in samples),
                                     labels=len(labelled), predictions=sum(b in r[kind] for r in base), scored=len(usable),
                                     labels_rejected=dict(collections.Counter(r['label_rejection'] for r in base if r['label'] is None)),
                                     error=error_stats([r[kind][b]-r['label']['value'] for r in usable])))
            for group in (BRANCHES, BRANCHES[:2]):
                for phase in ['all'] + sorted({a['phase'] for a in samples}):
                    for qualified in ('all_available', 'KF_tracking'):
                        rs = [r for r in base if r['label'] is not None and 'B1' in r['baselines'] and
                              all(b in r[kind] for b in group) and (phase == 'all' or r['phase'] == phase) and
                              (qualified != 'KF_tracking' or r['observer_phase'] == 'tracking')]
                        metrics.append(dict(kind=kind, h=h, phase=phase, qualification=qualified, branches=group,
                           cohort_SHA256=cohort_id(rs), n=len(rs),
                           errors={b:error_stats([r[kind][b]-r['label']['value'] for r in rs]) for b in group},
                           baselines={b:error_stats([r['baselines'][b]-r['label']['value'] for r in rs]) for b in ('B0','B1')}))
    write(out/'metrics-common.json', metrics)
    write(out/'coverage-own.json', coverage)
    context_metrics = []
    for kind in ('A_roll','B_HOLD'):
        for h in spec['horizons_s']:
            base=[r for r in points if r['h']==h and r['label'] and 'B1' in r['baselines'] and all(b in r[kind] for b in BRANCHES)]
            for context in ('confirmed_normal', 'observed_abnormal_or_unknown'):
                rs=[r for r in base if r['origin_context']==context]
                context_metrics.append(dict(kind=kind,h=h,origin_context=context,n=len(rs),cohort_SHA256=cohort_id(rs),
                    errors={b:error_stats([r[kind][b]-r['label']['value'] for r in rs]) for b in BRANCHES},
                    baselines={b:error_stats([r['baselines'][b]-r['label']['value'] for r in rs]) for b in ('B0','B1')}))
    write(out/'context-metrics.json',context_metrics)
    # Fully free actual-input response after one strictly past prefix.
    first = next(a for a in samples if a['source_valid'])
    anchor = next(a for a in samples if a['source_valid'] and a['t'] >= first['t']+60)
    ob = anchor['states']['AUGMENTED-KF']
    x = np.array([ob['Tf_C'], ob['Ts_C'], ob['E_C']])
    previous = anchor['t']
    long, stop = [], None
    for a in samples:
        if a['t'] < anchor['t']:
            continue
        if a['t'] > previous:
            pieces = path.pieces(previous, a['t'])
            if pieces is None or a['epoch'] != anchor['epoch']:
                stop = dict(ref=a['ref'], t=a['t'], reason='physical_input_or_source_support_ended')
                break
            x = path.propagate(x, pieces)
        long.append(dict(ref=a['ref'], t=a['t'], utc=a['utc'], phase=a['phase'], measured_TJ_C=a['current'],
                         source_valid=a['source_valid'], Tf_C=float(x[0]), Ts_C=float(x[1]), E_C=float(x[2]),
                         initialization_ref=anchor['ref'], no_TJ_feedback_after_prefix=True))
        previous = a['t']
    jsonl(out/'A-long.jsonl', long)
    write(out/'A-long-summary.json',dict(initialization_ref=anchor['ref'], initialization_t=anchor['t'],
       first_TJ_t=first['t'], prefix_s=anchor['t']-first['t'], frozen_state_C=[ob['Tf_C'],ob['Ts_C'],ob['E_C']],
       observations_used_after_prefix_for_state_updates=0, dynamic_fits=0, resets_at_workload_boundaries=0,
       stop=stop, scored=len(long), final_free_span_s=long[-1]['t']-long[0]['t'],
       error=error_stats([r['Tf_C']-r['measured_TJ_C'] for r in long if r['source_valid']]),
       by_phase={p:error_stats([r['Tf_C']-r['measured_TJ_C'] for r in long if r['source_valid'] and r['phase']==p]) for p in sorted({r['phase'] for r in long})}))
    return points, metrics, long


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    wall=time.perf_counter();cpu=time.process_time()
    spec=read(ROOT/'spec.json')
    assert sha(ROOT/'spec.json')==read(ROOT/'design-freeze.json')['spec_sha256']
    for rel, digest in (('models/primary.json',spec['model_sha256']),('observer-spec.json',spec['observer_spec_sha256'])):
        assert sha(ROOT/'vendor/src/tto_field/research'/rel)==digest
    phases=phase_table();write(out/'phases.json',phases)
    print('Replaying frozen native / I02 / observer',flush=True)
    samples,nodes,signals,ospec=replay(out,spec,phases)
    print('Frozen state verified. Evaluating A and B',len(samples),'accepted TJ',flush=True)
    points,metrics,long=evaluate(samples,nodes,ospec,spec,out)
    from surface import surface
    surface(ROOT,out,samples,signals,long,phases,spec)
    phase_coverage=[]
    for p in ['all']+sorted({a['phase'] for a in samples}):
        aa=[a for a in samples if p=='all' or a['phase']==p]
        phase_coverage.append(dict(phase=p,accepted_TJ=len(aa),source_valid_TJ=sum(a['source_valid'] for a in aa),
             state_phases=dict(collections.Counter(a['states']['AUGMENTED-KF']['phase'] for a in aa)),
             projected=sum(a['states']['AUGMENTED-KF']['boundary_projected'] for a in aa),
             TJ_range_C=[min(a['current'] for a in aa),max(a['current'] for a in aa)]))
    write(out/'state-coverage.json',phase_coverage)
    write(out/'environment-resource.json',dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
         platform=platform.platform(),machine=platform.machine(),wall_s=time.perf_counter()-wall,
         process_cpu_s=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
         BLAS_threads=1,CUDA=False,training=False,network_clients_constructed=0))
    print('Completed frozen comparison',str(out),flush=True)


if __name__=='__main__':
    main()
