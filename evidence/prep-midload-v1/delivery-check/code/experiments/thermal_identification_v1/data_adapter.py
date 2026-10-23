"""Replay the preserved quality processor; never invoke collectors or live I/O."""
import bisect
import collections
import copy
import csv
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
from common import read, write, sha, seconds, stamp


def extract_inputs(index_path, output):
    index_path = Path(index_path).resolve()
    base = index_path.parent.parent
    dest = Path(output)/'input-cache'
    checks = []
    for entry in read(index_path)['archives']:
        src = base/entry['path']
        assert src.stat().st_size == entry['bytes'] and sha(src) == entry['sha256']
        target = dest/src.stem
        with zipfile.ZipFile(src) as z:
            assert z.testzip() is None
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(target)
        manifest = target/('archive-file-hashes.json' if src.stem.startswith('L-') else 'SHA256.json')
        hashes = read(manifest)
        for name, value in hashes.items():
            expected = value['sha256'] if isinstance(value, dict) else value
            assert sha(target/name) == expected, name
        checks.append(dict(entry, verified_entries=len(hashes)))
    write(Path(output)/'source-archives.json', checks)
    return dest


def phase_metadata(root, label):
    if label == 'L':
        phases = []
        with (root/'analysis/phase-summary.csv').open() as f:
            for p in csv.DictReader(f):
                phases.append(dict(id=p['phase'], label=p['label'], start=seconds(p['start']), end=seconds(p['end']),
                                   macro='work' if p['phase'] in ('2','4','5a','5b') else 'recovery' if p['phase'] in ('3','I1','I2','6') else 'background',
                                   boundary_precision='manual_seconds' if p['phase'] in ('1','2','3') else 'client_event_milliseconds'))
        return phases, []
    phases = [dict(id=p['phase'], start=seconds(p['start_utc']), end=seconds(p['end_utc'])) for p in read(root/'normalized-phases.json')]
    # Read only metadata into derived evidence: request text is never a feature.
    reqs = [dict(id=p['request_id'], stage=p['stage'], start=seconds(p['submit_utc']), end=seconds(p['end_utc']),
                 client_submit_mono_s=p['submit_mono_s'], client_end_mono_s=p['end_mono_s'],
                 end_semantics=p['end_semantics']) for p in read(root/'normalized-requests.json')]
    return phases, reqs


def classify(wall, label, phases, reqs):
    phase = next((p for p in phases if p['start'] <= wall < p['end']), None)
    if label == 'L':
        if phase is None:
            return 'background', 'unlabelled', 'background'
        regime = ('model_loading' if phase['id']=='2' else 'long_rise' if phase['macro']=='work' and wall-phase['start']<60 else 'long_sustained' if phase['macro']=='work' else 'cooldown' if phase['macro']=='recovery' else 'idle')
        return phase['macro'], phase['id'], regime
    for j, q in enumerate(reqs):
        stop = min(q['end']+30, reqs[j+1]['start'] if j+1<len(reqs) else float('inf'))
        if q['start'] <= wall < stop:
            return 'work', q['stage'], 'continuous_short' if q['stage']=='continuous' else 'isolated_pulse'
    # Labelled inter-request gaps and explicit post-task cooldowns are recovery.
    recovery = phase is not None and phase['id'] in ('resident-baseline','sparse','between-groups','continuous','final-cooldown')
    return ('recovery' if recovery else 'background', phase['id'] if phase else 'unlabelled', 'cooldown' if recovery else 'idle')


def prepare(cache, out):
    cache, out = Path(cache), Path(out)
    reference = cache/'previous-exploration-evidence/sources/tto-reference/src'
    sys.path.insert(0, str(reference))
    from tto.config import load_config, merge, validate
    from tto.engine import engine_for
    from tto.dataset import replay
    records, segments, evidence = [], [], []
    for label, sub, old in [('L','L-seven-conditions-original','seven-conditions'),('S','S-shortqa-original-complete','short-qa')]:
        root = cache/sub
        run = next(root.glob('run-*'))
        m = read(run/'manifest.json')
        index = read(run/'files.json')
        assert all(sha(run/k)==v for k,v in index.items())
        replayed = replay(run)
        assert not replayed['platform_state']['mixed_profiles']
        assert not replayed['platform_state']['evidence_issues']
        invalids = {v['segment'] for v in replayed['quality_eligibility']['isolations']}
        c = load_config(environ={})
        saved = copy.deepcopy(m['config'])
        for section in ('orin','tianshan'):
            saved[section]['headers_file'] = saved[section]['ca_file'] = None
        merge(c,saved); validate(c)
        engine = engine_for(c,record_schema=2)
        originals = [json.loads(line) for line in (cache/'previous-exploration-evidence/model-exploration'/old/'accepted-timeseries.jsonl').open()]
        lookup = {a['ref']:a for a in originals}
        phases, reqs = phase_metadata(root,label)
        nodes, accepted, latest = [], [], None
        for line in (run/'observations-0001.jsonl').open():
            raw = json.loads(line)
            result = engine.process(raw)
            t = raw['mono_s']; q = result['quality']
            if q and q['accepted']:
                s = engine.features.history[-1]
                a = lookup[raw['ref']]
                assert a['values']==s['values'] and a['segment']==s['segment'] and a['control_eligible']==s['control_eligible']
                assert a['mono_s']==t and a['utc']==raw['received_at_utc'] and a['sample_seq']==raw['payload']['telemetry_meta']['sample_seq']
                for field in ('vdd_gpu','vdd_cpu_soc_mss','vin_sys_5v0'):
                    assert s['values'][field] == raw['payload']['power'][field]['current']/1000
                assert s['values']['tj']==raw['payload']['temperature']['tj']
                latest = copy.deepcopy(a)
                latest.update(run=label, wall=seconds(a['utc']), source_age_ms=q['age_lower_bound_ms'],
                              source_received_at=raw['payload']['telemetry_meta']['received_at'], source_timestamp=raw['payload']['timestamp'],
                              source_valid_until=t+(raw['payload']['telemetry_meta']['freshness_timeout_ms']-q['age_lower_bound_ms'])/1000,
                              contract_eligible=q['period_known'] and engine.profile_id is not None,
                              isolation=latest['segment'] in invalids, node_index=len(nodes))
                latest['macro'],latest['phase'],latest['regime']=classify(latest['wall'],label,phases,reqs)
                accepted.append(latest)
            scope, ctrl, reasons = engine.control_qualification(t)
            deadline = min(engine.fan['t']+2.5 if engine.fan else t, engine.temp['t']+7.5 if engine.temp else t,
                           engine.q.anchor_t+(engine.q.timeout_ms-engine.q.anchor_age)/1000 if latest else t)
            good = bool(latest and ctrl and latest['contract_eligible'] and not engine.q.blocked and not engine.q.quarantined and
                        latest['segment']==engine.q.segment and latest['segment'] not in invalids)
            inputs = [latest['values']['vdd_gpu'],latest['values']['vdd_cpu_soc_mss'],engine.fan['data']['successful_duty']/100] if good else None
            if good:
                assert np.isfinite(inputs).all() and 0 <= inputs[2] <= 1
            nodes.append(dict(t=t, valid_until=deadline, good=good, segment=engine.q.segment, inputs=inputs,
                              trigger_ref=raw['ref'], power_ref=latest['ref'] if latest else None,
                              fan_ref=engine.fan['ref'] if engine.fan else None,
                              temp_ref=engine.temp['ref'] if engine.temp else None,
                              fan_age_s=t-engine.fan['t'] if engine.fan else None,
                              source_age_ms=(t-engine.q.anchor_t)*1000+engine.q.anchor_age if latest else None,
                              reasons=reasons))
        assert len(accepted)==len(originals)
        groups, group, rejected, interval_rejections = [], [], [], []
        for a in accepted:
            node = nodes[a['node_index']]
            good = node['good'] and node['valid_until'] > a['mono_s']
            if not good:
                if group: groups.append(group);group=[]
                rejected.append(dict(ref=a['ref'],segment=a['segment'],reasons=node['reasons'],isolation=a['isolation']))
                a['research_segment']=None
                continue
            if group:
                prev=group[-1]
                used=nodes[prev['node_index']:a['node_index']+1]
                bad=[dict(ref=x['trigger_ref'],reason='qualification_or_segment' if not x['good'] or x['segment']!=prev['segment'] else 'TTL_expires_inside_interval',from_t=x['t'],to_t=y['t'],valid_until=x['valid_until'])
                     for x,y in zip(used,used[1:]) if y['t']>x['t'] and (not x['good'] or x['segment']!=prev['segment'] or x['valid_until']<y['t']-1e-9)]
                if bad or a['segment']!=prev['segment']:
                    interval_rejections.append(dict(from_ref=prev['ref'],to_ref=a['ref'],details=bad,segment_change=a['segment']!=prev['segment']))
                    groups.append(group);group=[]
            group.append(a)
        if group:groups.append(group)
        for j,g in enumerate(groups):
            sid=f'{label}-{j:02d}'
            event_nodes=nodes[g[0]['node_index']:g[-1]['node_index']+1]
            # Include real arrival updates, but remove zero-duration duplicate times.
            timeline=[]
            for n in event_nodes:
                if timeline and n['t']==timeline[-1]['t']: timeline[-1]=n
                else: timeline.append(n)
            ts=[n['t'] for n in timeline]
            for i,a in enumerate(g):
                a['research_segment']=sid
                a['duration']=g[i+1]['mono_s']-a['mono_s'] if i+1<len(g) else 0.0
                a['timeline_index']=bisect.bisect_left(ts,a['mono_s'])
            segments.append(dict(id=sid,run=label,source_segment=g[0]['segment'],rows=g,timeline=timeline,
                                 span_s=g[-1]['mono_s']-g[0]['mono_s'],eligible_for_fit=len(g)>1))
        records+=accepted
        evidence.append(dict(run=label,run_id=m['observer_run_id'],episode=m['episode'],accepted=len(accepted),
                             accepted_match_all_fields=True,share_run_hashes=index,
                             private_run_hashes=read(root/'original-run-file-hashes.json') if (root/'original-run-file-hashes.json').exists() else read(cache/'previous-exploration-evidence/results/private-original-run-index-verification.json'),
                             quality_counts=replayed['quality'],isolations=replayed['quality_eligibility']['isolations'],
                             rejections=rejected,interval_rejections=interval_rejections,phases=phases,requests=reqs,
                             duration_s=seconds(m['ended_at_utc'])-seconds(m['started_at_utc']) if m.get('ended_at_utc') else accepted[-1]['mono_s']-accepted[0]['mono_s']))
    data=dict(usage='previously_observed_development_only',segments=segments,accepted=records,runs=evidence)
    write(out/'data.json',data)
    coverage=[]
    for s in segments:
        row=dict(id=s['id'],run=s['run'],source_segment=s['source_segment'],start=s['rows'][0]['utc'],end=s['rows'][-1]['utc'],span_s=s['span_s'],n=len(s['rows']),
                 first_ref=s['rows'][0]['ref'],last_ref=s['rows'][-1]['ref'],fit=s['eligible_for_fit'],
                 evaluation_warmup_s=60,eligible_after_60=sum(a['mono_s']>=s['rows'][0]['mono_s']+60 for a in s['rows']),
                 macro_seconds={m:sum(a['duration'] for a in s['rows'] if a['macro']==m) for m in ('work','recovery','background')})
        coverage.append(row)
    write(out/'coverage.json',coverage)
    write(out/'roles.json',dict(frozen_at=stamp(),runs={r['run']:r['run_id'] for r in evidence},
          F_LS=dict(fit=['L'],target=['S']),F_SL=dict(fit=['S'],target=['L']),F_POOL=dict(fit=['L','S'],target=['L','S']),
          segments=coverage,continuous_groups_are_not_independent_episodes=True))
    return data
