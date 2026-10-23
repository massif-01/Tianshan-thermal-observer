"""Same-cohort development comparison using accepted R2 initialization/scoring."""
import copy
from pathlib import Path
import sys
import time
from .util import ROOT, read, write, sha, load_bundle, legacy_identity
from .offline_runtime import initialize


def compare(plan_path, output):
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    data_path = (plan_path.parent/plan['dataset']).resolve()
    if sha(data_path) != plan['dataset_sha256']:
        raise ValueError('comparison dataset changed')
    out = Path(output).resolve();out.mkdir(parents=True, exist_ok=False)
    stop, thread = initialize(out, plan['runtime_profile'])
    import numpy as np
    sys.path.insert(0, str(ROOT/'tool/legacy'))
    from greybox import build_kernel, propagate, forecast
    from initialize import rolling_state, path_between
    from scoring import model_context, tables, metrics, jsonl
    from data_views import cohort_id
    from slow_core import filters_at_origins
    legacy_identity()
    data = read(data_path)
    run_meta = {r['run']:r for r in data['runs']}
    if not plan['all_data_seen'] and any(run_meta[r]['role']=='seen_development' for r in plan['runs']):
        raise ValueError('old development data cannot be called new confirmation')
    models, manifests = {}, {}
    for item in plan['models']:
        path = (plan_path.parent/item['manifest']).resolve()
        manifest, model, _ = load_bundle(path)
        if manifest['model_id'] != item['model_id']:
            raise ValueError('comparison model identity mismatch')
        models[item['model_id']] = model
        manifests[item['model_id']] = dict(path=str(path), sha256=sha(path))
    frozen = dict(plan, plan_source_sha256=sha(plan_path), models_frozen=manifests, dataset_sha256=sha(data_path),
                  no_further_model_search=True, legacy_sources=legacy_identity(), all_results_development=True)
    write(out/'comparison-frozen-before-score.json', frozen)
    started = time.monotonic()
    build_kernel(out/'build')
    segments = [s for s in data['segments'] if s['run'] in plan['runs']]
    smap = {s['id']:s for s in segments}
    contexts = {name:model_context(model, segments) for name, model in models.items()}
    write(out/'past-prefix-calibrations.json', {name:c[2] for name,c in contexts.items()})
    baseline = plan['models'][0]['model_id']
    lp = {}
    bp, be, _, _ = contexts[baseline]
    for s in segments:
        if s['id'] in contexts[baseline][3]:
            lp.update(filters_at_origins(s, be[s['run']], bp))
    longs = []
    for s in segments:
        if s['id'] not in contexts[baseline][3]: continue
        for i,r in enumerate(s['rows']):
            if r['t']-s['rows'][0]['t'] < 60: continue
            item = {k:r[k] for k in ('ref','utc','run','macro','phase','regime','duration')}
            item.update(t=r['t'], h=0, segment=s['id'], label=dict(value=r['values']['tj'],ref=r['ref']),
                        A={name:c[3][s['id']][i] for name,c in contexts.items()}, control_context='confirmed_normal', strict_label=True)
            longs.append(item)
    jsonl(out/'A-long-points.jsonl', longs)
    long_scores = []
    for scope in ['all','run','macro','phase','regime']:
        for value in ['all'] if scope=='all' else sorted({r[scope] for r in longs}):
            group = longs if scope=='all' else [r for r in longs if r[scope]==value]
            if group:
                long_scores.append(dict(scope=scope,value=value,cohort_id=cohort_id(group),metrics={n:metrics(group,n,'A') for n in models}))
    write(out/'A-long-metrics.json', long_scores)
    points, states = [], []
    for row in data['examples']:
        if row['run'] not in plan['runs']: continue
        segment = smap.get(row['segment'])
        local = {}
        if row['ready'] and segment:
            for name, model in models.items():
                p, boundary, _, _ = contexts[name]
                state, ev = rolling_state('G2', p, boundary[row['run']], segment, row['strict_i'], window=60)
                local[name] = (state,boundary[row['run']],p)
                states.append(dict(ref=row['ref'], model_id=name, state=state, E=boundary[row['run']],
                                   evidence=ev, input_cutoff=row['t'], parameter_learning=False))
        u = np.array(segment['timeline'][segment['rows'][row['strict_i']]['timeline_index']]['inputs']) if local else None
        for h in (15,45,90):
            B, A, missing, outside = {}, {}, {}, {}
            if row['source_valid']:
                B['B0'] = row['current']
                if row['slope'] is not None: B['B1'] = row['current']+h*row['slope']
            for name, model in models.items():
                if name not in local:
                    missing[name] = 'original_quality_or_past60_prefix_unavailable'
                    continue
                state, E, p = local[name]
                for scenario in ('HOLD','RELAX30'):
                    B[name+':'+scenario] = forecast('G2',p,E,state,u,h,scenario,model['P10_fit'])
                outside[name] = bool(np.any((u[:2]<model['input_min'])|(u[:2]>model['input_max'])) or not model['u_range'][0]<=u[2]<=model['u_range'][1])
                if row['A_eligible'][str(h)] and row['t']+h <= segment['rows'][-1]['t']:
                    dt, inputs = path_between(segment,row['t'],row['t']+h)
                    A[name] = float(propagate('G2',p,E,dt,inputs,state)[-1,0])
            if baseline in local and row['ref'] in lp:
                _, E, p = local[baseline]
                for key in ['STATE-LP30','STATE-LP120']:
                    name = 'baseline-'+key.removeprefix('STATE-')
                    state = [row['current'],lp[row['ref']][key]]
                    B[name] = forecast('G2',p,E,state,u,h,'HOLD',models[baseline]['P10_fit'])
                    if row['A_eligible'][str(h)] and row['t']+h <= segment['rows'][-1]['t']:
                        dt, inputs = path_between(segment,row['t'],row['t']+h)
                        A[name] = float(propagate('G2',p,E,dt,inputs,state)[-1,0])
            point = {k:row[k] for k in ('ref','utc','run','segment','t','wall','macro','phase','regime','duration','current')}
            point.update(h=h,label=row['labels'][str(h)],label_rejection=row['label_rejections'][str(h)],
                         B=B,A=A,unavailable=missing,outside_fit_input_range=outside,
                         control_context=row['contexts'][str(h)],strict_label=row['strict_labels'][str(h)],
                         input_available_cutoff=row['t'],actual_future_inputs_used_in_B=False,
                         time_contract='LEGACY-R2-PAST60-REPLAY-v1',publication_mode='replay')
            points.append(point)
    jsonl(out/'predictions.jsonl',points);jsonl(out/'states.jsonl',states)
    hold = ['B0','B1']+[n+':HOLD' for n in models]+['baseline-LP30','baseline-LP120']
    relax = ['B0','B1']+[n+':RELAX30' for n in models]
    b_scores = tables(points,'B',hold,'all_HOLD_common')+tables(points,'B',relax,'all_RELAX30_common')
    a_scores = tables(points,'A',list(models)+['baseline-LP30','baseline-LP120'],'known_input_only')
    write(out/'B-metrics.json',b_scores);write(out/'A-roll-metrics.json',a_scores)
    coverage = []
    for run in plan['runs']:
        for h in (15,45,90):
            rows = [r for r in points if r['run']==run and r['h']==h]
            for mode,names in [('B',hold+[n+':RELAX30' for n in models]),('A',list(models)+['baseline-LP30','baseline-LP120'])]:
                for name in names:
                    scored = [r for r in rows if name in r[mode] and r['label']]
                    coverage.append(dict(run=run,h=h,mode=mode,method=name,accepted_TJ_denominator=len(rows),
                        valid_labels=sum(r['label'] is not None for r in rows),emitted=sum(name in r[mode] for r in rows),
                        scored=len(scored),cohort_id=cohort_id(scored),
                        all_available_metrics=metrics(scored,name,mode) if scored else None,
                        missing_reasons=dict(__import__('collections').Counter(r['label_rejection'] or 'method_unavailable' for r in rows if not r['label'] or name not in r[mode]))))
    write(out/'coverage.json',coverage)
    main = next((r for r in b_scores if r['h']==45 and r['scope']=='all' and r['context']=='all' and r['layer']=='all_HOLD_common'),None)
    decisions = {}
    for name in models:
        if name == baseline: continue
        if not main:
            decisions[name] = dict(decision='insufficient_common_samples',automatic_activation=False)
            continue
        old, new = main['metrics'][baseline+':HOLD'],main['metrics'][name+':HOLD']
        better = new['point_mae'] < old['point_mae']
        decisions[name] = dict(decision='development_average_better_requires_future_confirmation' if better else 'not_better_on_development',
            comparison_cohort=main['cohort_id'],same_points=old['n'],baseline_point_MAE=old['point_mae'],candidate_point_MAE=new['point_mae'],
            max_under_delta=new['underprediction_max']-old['underprediction_max'],p95_abs_delta=new['p95_abs']-old['p95_abs'],
            future_confirmation_available=False,recommended_for_automatic_activation=False,requires_manual_observation_decision=True,
            automatic_activation=False,control_permission=False)
    write(out/'decisions.json',dict(current_baseline=baseline,role=plan['role'],candidates=decisions,
                                   old_official_scores_unchanged=True,all_scenarios_reported=True))
    stop.set();thread.join(timeout=1)
    write(out/'resources.json',dict(elapsed_s=time.monotonic()-started,last_self_usage=read(out/'resource-heartbeat.json'),
                                   new_fits=0,device_access=False,network_clients=0,CUDA_used=False))
    print('Comparison completed:',len(points),'rows; all development; frozen baseline not activated/replaced.')
