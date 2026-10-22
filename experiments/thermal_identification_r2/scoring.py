"""Uniform past-prefix replay of old and new artifacts; all horizons independent."""
from pathlib import Path
import json
import numpy as np
from common import write, read, sha, stamp, balanced_weights
from greybox import propagate, forecast, arrays
from initialize import estimate, rolling_state, path_between
from ridge_reference import predict
from data_views import cohort_id

METHODS=['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']


def jsonl(path, rows):
    def cast(x): return x.tolist() if isinstance(x,np.ndarray) else x.item() if isinstance(x,np.generic) else str(x)
    with Path(path).open('x') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False,default=cast,allow_nan=False)+'\n')


def load_jsonl(path): return [json.loads(line) for line in Path(path).open()]


def metrics(rows, method, mode='B'):
    e=np.array([r[mode][method]-r['label']['value'] for r in rows]); dt=np.array([r['duration'] for r in rows])
    w=dt/dt.sum() if dt.sum() else np.ones(len(e))/len(e)
    return dict(n=len(e),seconds=float(dt.sum()),mae=float(w@abs(e)),balanced_mae=float(balanced_weights(rows)@abs(e)),
                point_mae=float(np.mean(abs(e))),rmse=float(np.sqrt(w@(e*e))),p95_abs=float(np.percentile(abs(e),95)),bias=float(w@e),
                underprediction_p95=float(np.percentile(np.maximum(-e,0),95)),underprediction_max=float(max(0,-e.min())))


def tables(rows, mode, methods, layer):
    result=[]
    for h in (15,45,90):
        allrows=[r for r in rows if r['h']==h and r['label'] is not None and all(m in r[mode] for m in methods)]
        for context in ['all','confirmed_normal','aux_observation_gap','observed_abnormal_or_changed','unclassified_gap','strict_legacy']:
            base=[r for r in allrows if context=='all' or context=='strict_legacy' and r['strict_label'] or r['control_context']==context]
            scopes=[('all','all',base)]
            for field in ('run','macro','regime','phase'):
                scopes += [(field,val,[r for r in base if r[field]==val]) for val in sorted({r[field] for r in base})]
            for field,val,cohort in scopes:
                if cohort: result.append(dict(mode=mode,layer=layer,h=h,context=context,scope=field,value=val,cohort_id=cohort_id(cohort),
                                               metrics={m:metrics(cohort,m,mode) for m in methods}))
    return result


def model_context(artifact, segments, fixed_E=None):
    m=artifact['model']; p=np.array(list(artifact['dynamic'].values())); boundary={}; calibrations={}; responses={}
    fallback=float(np.median([v for k,v in artifact['parameters'].items() if k.startswith('E_')]))
    for segment in segments:
        if segment['span_s']<60: continue
        run=segment['run']; end=segment['rows'][0]['t']+60
        given=(fixed_E or {}).get(run,boundary.get(run))
        ev=estimate(m,p,segment,end,60,E=given,E_fallback=fallback)
        E=ev['E']; boundary[run]=E; calibrations[segment['id']]=ev
        g=arrays(segment)
        states=propagate(m,p,E,g['dt'],g['u'],[g['y'][0],ev['Ts_initial']])
        responses[segment['id']]=states[g['index'],0]
    return p,boundary,calibrations,responses


def evaluate(label, runs, artifacts, ridge, data, examples, dest, fixed_E=None):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=False)
    segments=[s for s in data['segments'] if s['run'] in runs]; smap={s['id']:s for s in segments}
    contexts={m:model_context(a,segments,fixed_E if m=='G2' else None) for m,a in artifacts.items()}
    write(dest/'calibrations.json',{m:c[2] for m,c in contexts.items()})
    longs=[]
    for s in segments:
        for i,r in enumerate(s['rows']):
            if r['t']-s['rows'][0]['t']<60: continue
            long={k:r[k] for k in ('ref','utc','run','macro','phase','regime','duration')}
            long.update(t=r['t'],h=0,segment=s['id'],label=dict(value=r['values']['tj'],ref=r['ref']),
                        A={m:c[3][s['id']][i] for m,c in contexts.items()},control_context='confirmed_normal',strict_label=True)
            longs.append(long)
    jsonl(dest/'A-long.jsonl',longs)
    longtables=[]
    for field in ('all','run','macro','regime','phase','segment'):
        for val in ['all'] if field=='all' else sorted({r[field] for r in longs}):
            cohort=longs if field=='all' else [r for r in longs if r[field]==val]
            if cohort: longtables.append(dict(scope=field,value=val,cohort_id=cohort_id(cohort),metrics={m:metrics(cohort,m,'A') for m in artifacts}))
    write(dest/'A-long-metrics.json',longtables)
    predictions=[]; states=[]
    for row in examples:
        if row['run'] not in runs: continue
        segment=smap.get(row['segment']); local={}
        if row['ready'] and segment:
            for m,a in artifacts.items():
                p,boundary,_,_=contexts[m]; E=boundary[row['run']]
                state,ev=rolling_state(m,p,E,segment,row['strict_i'],window=60)
                local[m]=(state,E,p)
                states.append(dict(ref=row['ref'],segment=segment['id'],model=m,E=E,state=state,evidence=ev,window_s=60,
                                   parameter_learning=False,input_cutoff=row['t']))
        current_inputs=np.array(segment['timeline'][segment['rows'][row['strict_i']]['timeline_index']]['inputs']) if local else None
        for h in (15,45,90):
            B={}; A={}; unavailable={}; outside={}
            if row['source_valid']: B['B0']=row['current']
            if row['source_valid'] and row['slope'] is not None: B['B1']=row['current']+h*row['slope']
            for name in ('R_TJ','R_IO'):
                if row[name] is not None:
                    head=ridge['methods'][name][str(h)]; vector=np.array(row[name]); B[name]=predict(head,vector,row['current'])
                    outside[name]=bool(np.any((vector<head['min'])|(vector>head['max'])))
            for m,a in artifacts.items():
                if m not in local: continue
                state,E,p=local[m]
                for scenario in ('HOLD','RELAX30'):
                    B[f'{m}-{scenario}']=forecast(m,p,E,state,current_inputs,h,scenario,a['P10_fit'])
                    outside[f'{m}-{scenario}']=bool(np.any((current_inputs[:2]<a['input_min'])|(current_inputs[:2]>a['input_max'])) or not a['u_range'][0]<=current_inputs[2]<=a['u_range'][1])
                # A path must extend through the nominal future end in the same strict segment.
                if row['A_eligible'][str(h)] and row['t']+h<=segment['rows'][-1]['t']:
                    dt,inputs=path_between(segment,row['t'],row['t']+h)
                    A[m]=float(propagate(m,p,E,dt,inputs,state)[-1,0])
            for m in METHODS:
                if m not in B: unavailable[m]='past_method_inputs_or_source_unavailable'
            rec={k:row[k] for k in ('ref','utc','run','segment','t','wall','macro','phase','regime','duration','current')}
            rec.update(h=h,label=row['labels'][str(h)],label_rejection=row['label_rejections'][str(h)],B=B,A=A,unavailable=unavailable,
                       control_context=row['contexts'][str(h)],strict_label=row['strict_labels'][str(h)],
                       future_inputs_complete=row['A_eligible'][str(h)],input_available_cutoff=row['t'],
                       actual_input_end=row['t']+h if A else None,outside_fit_input_range=outside)
            predictions.append(rec)
    jsonl(dest/'predictions.jsonl',predictions); jsonl(dest/'states.jsonl',states)
    scores=[]
    for layer,methods in [('baselines',METHODS[:2]),('plus_TJ',METHODS[:3]),('plus_IO',METHODS[:4]),('all_methods',METHODS)]:
        scores+=tables(predictions,'B',methods,layer)
    for m in METHODS[2:]: scores+=tables(predictions,'B',['B0','B1',m],m+'_pair')
    write(dest/'B-metrics.json',scores)
    write(dest/'A-roll-metrics.json',tables(predictions,'A',list(artifacts),'known_input_only'))
    coverage=[]
    for run in runs:
        for h in (15,45,90):
            rows=[r for r in predictions if r['run']==run and r['h']==h]
            for m in METHODS:
                emit=[r for r in rows if m in r['B']]; score=[r for r in emit if r['label']]
                coverage.append(dict(run=run,h=h,method=m,accepted_denominator=len(rows),emitted=len(emit),scored=len(score),
                                     coverage=len(score)/len(rows),strict_legacy_scored=sum(r['strict_label'] for r in score),
                                     contexts={c:sum(r['control_context']==c for r in score) for c in ('confirmed_normal','aux_observation_gap','observed_abnormal_or_changed','unclassified_gap')},
                                     outside_fit_domain=sum(r['outside_fit_input_range'].get(m,False) for r in emit)))
    write(dest/'coverage.json',coverage)
    write(dest/'evaluation-identity.json',dict(label=label,runs=runs,evaluated_at=stamp(),initialization='uniform_past60_prefix_then_fixed_E; rolling60_state',
                                              A_long='no_TJ_feedback_after_prefix',B='no_future_inputs_or_task_end',deployable=False))
    print('evaluated',label,'A-long',len(longs),'B rows',len(predictions),flush=True)
    return predictions,longs


def paired(old_dir,new_dir,dest):
    out={}
    for filename,mode,methods in [('predictions.jsonl','B',METHODS),('predictions.jsonl','A',['G1','G2']),('A-long.jsonl','A',['G1','G2'])]:
        old=load_jsonl(Path(old_dir)/filename); new=load_jsonl(Path(new_dir)/filename)
        index={(r['ref'],r['h'],r['label']['ref']):r for r in old if r['label']}
        combined=[]
        for r in new:
            if not r['label']: continue
            a=index.get((r['ref'],r['h'],r['label']['ref']))
            if not a: continue
            x=dict(r); x[mode]={**{f'old:{m}':a[mode][m] for m in methods if m in a[mode]},**{f'new:{m}':r[mode][m] for m in methods if m in r[mode]}}
            combined.append(x)
        key='A-long' if filename=='A-long.jsonl' else mode
        names=[prefix+m for prefix in ('old:','new:') for m in methods]
        if key=='A-long':
            summaries=[]
            for field in ('all','run','macro','regime','phase'):
                for val in ['all'] if field=='all' else sorted({r[field] for r in combined}):
                    group=combined if field=='all' else [r for r in combined if r[field]==val]
                    cohort=[r for r in group if all(m in r[mode] for m in names)]
                    if cohort: summaries.append(dict(scope=field,value=val,cohort_id=cohort_id(cohort),metrics={m:metrics(cohort,m,mode) for m in names}))
        else: summaries=tables(combined,mode,names,'old_new_common')
        out[key]=summaries
    write(dest,out)
    return out
