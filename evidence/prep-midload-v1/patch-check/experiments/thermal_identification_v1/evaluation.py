"""Separate known-input response A from strictly past-only forecast B."""
import hashlib
import json
from pathlib import Path
import numpy as np
from common import read,write,balanced_weights,stamp,sha
from greybox import propagate,forecast,arrays
from initialize import estimate,rolling_state,path_between
from ridge_reference import predict


def jsonl(path,rows):
    from common import write as _write
    def cast(x):
        return x.tolist() if isinstance(x,np.ndarray) else x.item() if isinstance(x,np.generic) else str(x)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('x') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,default=cast,allow_nan=False)+'\n')


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).open()]


def metrics(rows,method,mode='B'):
    e=np.array([r[mode][method]-r['label']['value'] for r in rows]);dt=np.array([r['duration'] for r in rows])
    w=dt/dt.sum() if dt.sum()>0 else np.ones(len(e))/len(e)
    return dict(n=len(e),seconds=float(dt.sum()),mae=float(w@abs(e)),balanced_mae=float(balanced_weights(rows)@abs(e)),
                point_mae=float(np.mean(abs(e))),rmse=float(np.sqrt(w@(e*e))),p95_abs=float(np.percentile(abs(e),95)),
                bias=float(w@e),underprediction_p95=float(np.percentile(np.maximum(-e,0),95)),underprediction_max=float(max(0,-e.min())))


def cohort_id(rows):
    return hashlib.sha256('\n'.join(f"{r['ref']}|{r['h']}|{r['label']['ref']}" for r in rows).encode()).hexdigest()


def table(rows,mode,methods,layer):
    out=[]
    for h in (15,45,90):
        common=[r for r in rows if r['h']==h and r['label'] is not None and all(m in r[mode] for m in methods)]
        scopes=[('all','all',common)]
        for field in ('run','macro','phase','regime'):
            for val in sorted({r[field] for r in common}):scopes.append((field,val,[r for r in common if r[field]==val]))
        for field,val,cohort in scopes:
            if not cohort:continue
            out.append(dict(mode=mode,layer=layer,h=h,scope=field,value=val,cohort_id=cohort_id(cohort),
                            metrics={m:metrics(cohort,m,mode) for m in methods}))
    return out


def model_context(artifact,segments,pool=False):
    model=artifact['model'];p=np.array(list(artifact['dynamic'].values()))
    fallback=np.median([v for k,v in artifact['parameters'].items() if k.startswith('E_')])
    boundary={};calibrations={};responses={}
    for segment in segments:
        if segment['span_s']<60:continue
        run=segment['run'];end=segment['rows'][0]['mono_s']+60
        if pool:
            E=artifact['parameters'][f'E_{run}'];ts=artifact['parameters'].get(f'Ts_{segment["id"]}',0)
            g=arrays(segment);states=propagate(model,p,E,g['dt'],g['u'],[g['y'][0],ts]);response=states[g['index'],0]
            calibration=dict(E=E,Ts_initial=ts,training_joint_initial=True,start=segment['rows'][0]['mono_s'],end=end,
                             evidence_end=segment['rows'][-1]['mono_s'],note='in-sample nuisance fitted on whole training segment')
        else:
            calibration=estimate(model,p,segment,end,60,E=boundary.get(run),E_fallback=fallback)
            E=calibration['E'];ts=calibration['Ts_initial'];g=arrays(segment)
            states=propagate(model,p,E,g['dt'],g['u'],[g['y'][0],ts]);response=states[g['index'],0]
        boundary[run]=E;calibrations[segment['id']]=calibration;responses[segment['id']]=response
    return p,boundary,calibrations,responses


def evaluate_experiment(eid,target_runs,data,examples,out):
    out=Path(out);dest=out/'evaluation'/eid;dest.mkdir()
    artifacts={name:read(out/'fits'/f'{eid}-{name}'/'model.json') for name in ('G1','G2')}
    ridge=read(out/'fits'/f'{eid}-ridge.json')
    segments=[s for s in data['segments'] if s['run'] in target_runs];smap={s['id']:s for s in segments}
    contexts={m:model_context(a,segments,pool=eid=='F-POOL') for m,a in artifacts.items()}
    write(dest/'calibrations.json',{m:c[2] for m,c in contexts.items()})
    longs=[]
    for segment in segments:
        for i,r in enumerate(segment['rows']):
            if r['mono_s']-segment['rows'][0]['mono_s']<60:continue
            pred={m:c[3][segment['id']][i] for m,c in contexts.items()}
            longs.append(dict(ref=r['ref'],utc=r['utc'],run=r['run'],segment=segment['id'],t=r['mono_s'],macro=r['macro'],phase=r['phase'],regime=r['regime'],duration=r['duration'],
                              label=dict(value=r['values']['tj'],ref=r['ref']),A=pred))
    jsonl(dest/'A-long.jsonl',longs)
    longtable=[]
    for segment in segments:
        cohort=[r for r in longs if r['segment']==segment['id']]
        if not cohort:continue
        longtable.append(dict(segment=segment['id'],run=segment['run'],n=len(cohort),seconds=cohort[-1]['t']-cohort[0]['t'],first_ref=cohort[0]['ref'],last_ref=cohort[-1]['ref'],
                              metrics={m:metrics(cohort,m,'A') for m in artifacts},
                              peak_error={m:float(max(r['A'][m] for r in cohort)-max(r['label']['value'] for r in cohort)) for m in artifacts},
                              tail_bias={m:float(np.mean([r['A'][m]-r['label']['value'] for r in cohort if r['t']>=cohort[-1]['t']-60])) for m in artifacts}))
    longsummary={m:metrics(longs,m,'A') for m in artifacts}
    write(dest/'A-long-metrics.json',dict(summary=longsummary,segments=longtable))
    predictions=[];states=[];sensitivity=[]
    end_by_run={run:max(a['mono_s'] for a in data['accepted'] if a['run']==run) for run in target_runs}
    for row in examples:
        if row['run'] not in target_runs:continue
        segment=smap[row['segment']];current=segment['rows'][row['i']];ready=row['t']>=segment['rows'][0]['mono_s']+60
        local={};old180={}
        for m,artifact in artifacts.items():
            if not ready:continue
            p,boundary,_,_=contexts[m];E=boundary[row['run']]
            state,ev=rolling_state(m,p,E,segment,row['i'])
            local[m]=(state,E,p)
            states.append(dict(ref=row['ref'],segment=row['segment'],model=m,E=E,state=state,evidence=ev,window=60,dynamic_model_sha256=sha(out/'fits'/f'{eid}-{m}/model.json')))
            if m=='G2' and eid!='F-POOL' and row['t']>=segment['rows'][0]['mono_s']+180:
                s180,e180=rolling_state(m,p,E,segment,row['i'],window=180);old180[m]=s180
                states.append(dict(ref=row['ref'],segment=row['segment'],model=m,E=E,state=s180,evidence=e180,window=180))
        u=np.array([current['values']['vdd_gpu'],current['values']['vdd_cpu_soc_mss'],current['values']['duty']/100])
        for h in (15,45,90):
            label=row['labels'].get(str(h));B={'B0':row['current']};A={};outside={}
            unavailable={}
            if row['slope'] is not None:B['B1']=row['current']+h*row['slope']
            else:unavailable['B1']='history_under_10s'
            for name in ('R_TJ','R_IO'):
                if row[name] is not None:
                    head=ridge['methods'][name][str(h)];B[name]=predict(head,row[name],row['current'])
                    outside[name]=bool(np.any((row[name]<head['min'])|(row[name]>head['max'])))
                else:unavailable[name]='history_under_60s'
            for m,artifact in artifacts.items():
                if m not in local:
                    for scenario in ('HOLD','RELAX30'):unavailable[f'{m}-{scenario}']='history_under_60s'
                    continue
                state,E,p=local[m]
                for scenario in ('HOLD','RELAX30'):
                    B[f'{m}-{scenario}']=forecast(m,p,E,state,u,h,scenario,artifact['P10_fit'])
                    outside[f'{m}-{scenario}']=bool(np.any((u[:2]<artifact['input_min'])|(u[:2]>artifact['input_max'])) or u[2]<artifact['u_range'][0] or u[2]>artifact['u_range'][1])
                if label is not None:
                    dt,inputs=path_between(segment,row['t'],row['t']+h)
                    A[m]=float(propagate(m,p,E,dt,inputs,state)[-1,0])
                    if m in old180:
                        s180=old180[m]
                        sensitivity.append(dict(ref=row['ref'],h=h,run=row['run'],macro=row['macro'],duration=row['duration'],label=label,
                                                A60=A[m],A180=float(propagate(m,p,E,dt,inputs,s180)[-1,0]),
                                                HOLD60=B[f'{m}-HOLD'],HOLD180=forecast(m,p,E,s180,u,h,'HOLD',artifact['P10_fit']),
                                                RELAX3060=B[f'{m}-RELAX30'],RELAX30180=forecast(m,p,E,s180,u,h,'RELAX30',artifact['P10_fit'])))
            record={k:row[k] for k in ('ref','utc','run','segment','t','wall','macro','phase','regime','duration')}
            record.update(h=h,label=label,current=row['current'],B=B,A=A,outside_fit_input_range=outside,unavailable=unavailable,
                          label_status='scored' if label else 'run_end' if row['t']+h>end_by_run[row['run']] else 'cross_quality_or_input_interval',
                          input_available_cutoff=row['t'],power_ref=current['ref'],fan_ref=segment['timeline'][current['timeline_index']]['fan_ref'],
                          actual_input_end=row['t']+h if A else None)
            if h==45 and ready and current['fan_observation']['predicted_temperature'] is not None:
                record['firmware_diagnostic']=dict(value=current['fan_observation']['predicted_temperature'],fan_ref=record['fan_ref'],age_s=current['fan_return_age_s'])
            predictions.append(record)
    jsonl(dest/'predictions.jsonl',predictions);jsonl(dest/'states.jsonl',states)
    jsonl(dest/'state-sensitivity-180.jsonl',sensitivity)
    methods=['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']
    scores=[]
    for layer,ms in [('baselines',methods[:2]),('plus_TJ',methods[:3]),('plus_IO',methods[:4]),('all_methods',methods)]:scores+=table(predictions,'B',ms,layer)
    scores+=table(predictions,'B',['B0','G2-HOLD'],'G2_B0_pair')
    write(dest/'B-metrics.json',scores)
    write(dest/'A-roll-metrics.json',table(predictions,'A',['G1','G2'],'known_input_only'))
    coverage=[]
    for h in (15,45,90):
        for run in target_runs:
            cohort=[r for r in predictions if r['h']==h and r['run']==run]
            total=sum(r['run']==run for r in data['accepted'])
            for m in methods:
                emitted=[r for r in cohort if m in r['B']];scored=[r for r in emitted if r['label'] is not None]
                coverage.append(dict(run=run,h=h,method=m,all_accepted_denominator=total,quality_or_current_input_rejected=total-len(cohort),
                                     emitted=len(emitted),scored=len(scored),warming_up=sum(m in r['unavailable'] for r in cohort),
                                     cross_boundary=sum(r['label_status']=='cross_quality_or_input_interval' for r in emitted),
                                     no_future_at_end=sum(r['label_status']=='run_end' for r in emitted),outside_fit_domain=sum(r['outside_fit_input_range'].get(m,False) for r in emitted)))
    write(dest/'method-coverage.json',coverage)
    request_table=[]
    for run in data['runs']:
        if run['run'] not in target_runs:continue
        reqs=run['requests']
        for j,q in enumerate(reqs):
            windows=[('pre15',q['start']-15,q['start']),('during',q['start'],q['end']),('post0_15',q['end'],q['end']+15),('post15_45',q['end']+15,q['end']+45),('post45_90',q['end']+45,q['end']+90)]
            for window,a,b in windows:
                for h in (15,45,90):
                    emitted=[r for r in predictions if r['run']==run['run'] and r['h']==h and a<=r['wall']<b]
                    shared=[r for r in emitted if r['label'] is not None and all(m in r['B'] for m in methods)]
                    request_table.append(dict(request=q['id'],stage=q['stage'],window=window,h=h,start=a,end=b,
                                              next_request_overlap=j+1<len(reqs) and reqs[j+1]['start']<b,
                                              any_other_request_overlap=any(k!=j and v['start']<b and v['end']>a for k,v in enumerate(reqs)),
                                              raw_accepted=sum(a<=r['wall']<b for r in data['accepted'] if r['run']==run['run']),
                                              normal_origins=len(emitted),shared_n=len(shared),cohort_id=cohort_id(shared),
                                              metrics={m:metrics(shared,m) for m in methods} if shared else {}))
    write(dest/'request-windows.json',request_table)
    write(dest/'evaluation-identity.json',dict(evaluated_at=stamp(),directions_freeze_sha256=sha(out/'directions-frozen.json'),
          model_sha256={m:sha(out/'fits'/f'{eid}-{m}/model.json') for m in artifacts},
          interpretation='in_sample_only' if eid=='F-POOL' else 'reverse_time_stress' if eid=='F-SL' else 'development_cross_workload',
          A='recorded_future_inputs_no_future_TJ_feedback',B='only_arrived_measurements_fixed_future_scenarios',control='none'))
    print('evaluated',eid,'A-long',len(longs),'forecast rows',len(predictions),flush=True)
