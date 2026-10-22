"""Post-freeze diagnostics only: no extra fits or score-driven search."""
import os
import sys
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/v1'))
import numpy as np
from common import read,write,balanced_weights,sha
from greybox import FitProblem,build_kernel,matrices
from scoring import metrics,load_jsonl,jsonl
from research import seal_valid


def correlation(X):
    std=np.std(X,axis=0); active=std>1e-12;matrix=np.zeros((X.shape[1],X.shape[1]));np.fill_diagonal(matrix,1)
    if active.sum()>1:matrix[np.ix_(active,active)]=np.corrcoef(X[:,active],rowvar=False)
    Z=(X-X.mean(axis=0))/np.where(active,std,1)
    sv=np.linalg.svd(Z,compute_uv=False)
    return dict(n=len(X),mean=X.mean(axis=0),std=std,correlation=matrix,singular_values=sv,rank=int(np.linalg.matrix_rank(Z)),
                condition=float(sv[0]/sv[-1]) if sv[-1]>1e-12 else None)


def fit_diagnostics(out,data,spec):
    summaries=[];reconstruction=[]
    for model_file in sorted((out/'fits').glob('*/model.json')):
        artifact=read(model_file);m=artifact['model'];ss=[s for s in data['segments'] if s['run'] in artifact['fit_runs']]
        problem=FitProblem(m,ss,spec);x=np.array(artifact['x']);p=x[:problem.nd]
        trials=[read(f) for f in sorted(model_file.parent.glob('N*.json'))]
        predictions=problem.responses(x);res=problem.residual(x);J=problem.objective(x)
        assert abs(J-artifact['J'])<1e-8
        for g,pred in zip(problem.groups,predictions):
            for r,yhat in zip(g['segment']['rows'],pred):
                reconstruction.append(dict(candidate=model_file.parent.name,run=r['run'],segment=g['segment']['id'],ref=r['ref'],t=r['t'],
                                           macro=r['macro'],phase=r['phase'],regime=r['regime'],duration=r['duration'],h=0,
                                           label={'value':r['values']['tj'],'ref':r['ref']},A={m:float(yhat)}))
        free=[i for i,n in enumerate(problem.names) if n not in artifact.get('fixed_parameters',{})]
        sensitivities=[];jac=[];near=[a for a in trials if a['finite'] and a['J']<=min(t['J'] for t in trials if t['finite'])*1.05]
        scales=np.array([max(abs(v),.01 if n in ('b_g','b_c') else .001) if i<problem.nd else 20 for i,(n,v) in enumerate(zip(problem.names,x))])
        for i in free:
            step=1e-4*scales[i];left=x.copy();right=x.copy();left[i]=max(problem.lo[i],x[i]-step);right[i]=min(problem.hi[i],x[i]+step)
            jac.append((problem.residual(right)-problem.residual(left))/(right[i]-left[i])*scales[i])
            low=x.copy();high=x.copy();low[i]=max(problem.lo[i],x[i]-.01*scales[i]);high[i]=min(problem.hi[i],x[i]+.01*scales[i])
            sensitivities.append(dict(parameter=problem.names[i],scale=scales[i],J_minus=problem.objective(low),J_plus=problem.objective(high),
                                      response_RMS_change_minus=float(np.sqrt(np.mean((problem.residual(low)-res)**2))),
                                      response_RMS_change_plus=float(np.sqrt(np.mean((problem.residual(high)-res)**2)))))
        weighted=np.array(jac).T*np.sqrt(problem.weights[:,None]);singular=np.linalg.svd(weighted,compute_uv=False)
        decay={}
        for run in artifact['fit_runs']:
            input_rows=[r for r in problem.rows if r['run']==run];u=np.median([[r['values']['vdd_gpu'],r['values']['vdd_cpu_soc_mss'],r['values']['duty']/100] for r in input_rows],axis=0)
            A,f=matrices(m,p,artifact['parameters'][f'E_{run}'],u);eig=np.linalg.eigvals(A);rates=-eig.real
            gain=-np.linalg.solve(A,np.eye(len(A))[:,0])[:,None]*(p[2:] if m=='G1' else p[4:])
            decay[run]=dict(median_input=u,time_scales_s=sorted((1/rates).tolist()),steady_reported_TJ_gain_C_per_W=gain[0],
                            evidence='algebraic local diagnosis only; subsecond poles not identifiable by 1Hz data')
        autocorrelation={}
        for run in artifact['fit_runs']:
            pairs=[]
            for g,pred in zip(problem.groups,predictions):
                if g['segment']['run']!=run:continue
                er=pred-g['y']
                pairs += [(a,b) for a,b in zip(er,er[1:])]
            ac=float(np.corrcoef(np.array(pairs).T)[0,1]) if pairs and np.std(np.array(pairs),axis=0).min()>1e-12 else None
            autocorrelation[run]=dict(adjacent_sample_residual_correlation=ac,pairs=len(pairs),not_a_p_value=True)
        summaries.append(dict(candidate=model_file.parent.name,model=m,artifact_sha=sha(model_file),parameters=artifact['parameters'],J=J,
                              dynamic_count=problem.nd,boundary_free_count=len(problem.runs)-len(artifact.get('fixed_parameters',{})),
                              slow_initial_count=len(problem.groups) if m=='G2' else 0,total_free_count=len(free),fixed_parameters=artifact.get('fixed_parameters',{}),
                              attempts=[{k:a[k] for k in ('seed','J','converged','status','actual_residual_calls','seconds','boundary_parameters')} for a in trials],
                              selected_seed=artifact['selected_seed'],near_optimal_seeds=[a['seed'] for a in near],
                              near_optimal_dynamic_ranges={n:[min(a['parameters'][n] for a in near),max(a['parameters'][n] for a in near)] for n in problem.dynamic},
                              scaled_weighted_jacobian_singular_values=singular,scaled_weighted_condition=float(singular[0]/singular[-1]) if singular[-1]>1e-14 else None,
                              sensitivity_1percent_scale=sensitivities,local_time_scales_and_gains=decay,residual_autocorrelation=autocorrelation))
    write(out/'diagnostics/fit-diagnostics.json',summaries);jsonl(out/'diagnostics/fitted-state-reconstruction.jsonl',reconstruction)
    recon_metrics=[]
    for a in summaries:
        rows=[r for r in reconstruction if r['candidate']==a['candidate']]
        for field in ('all','run','macro','phase'):
            for value in ['all'] if field=='all' else sorted({r[field] for r in rows}):
                group=rows if field=='all' else [r for r in rows if r[field]==value]
                recon_metrics.append(dict(candidate=a['candidate'],scope=field,value=value,metrics=metrics(group,a['model'],'A'),
                                         role='training_fitted_initial_states_not_fair_old_new_evaluation'))
    write(out/'diagnostics/fitted-state-metrics.json',recon_metrics)


def events_for_run(run):
    if run['run']=='M':return [dict(id=p['id'],start=p['start'],end=p['end'],actual_s=p['actual_s'],kind='actual_block') for p in run['phases'] if p['macro']=='work']
    if run['run']=='S':return [dict(q,kind='request_not_independent_episode') for q in run['requests']]
    return [dict(id=p['id'],start=p['start'],end=p['end'],kind='work_phase') for p in run['phases'] if p['macro']=='work']


def event_diagnostics(data,out):
    evaluations=list((out/'old-models-on-M').iterdir())+[p for p in (out/'evaluation').iterdir() if p.is_dir()]
    results=[];wall_by_ref={a['ref']:a['wall'] for a in data['accepted']}
    for dest in evaluations:
        long=load_jsonl(dest/'A-long.jsonl');preds=load_jsonl(dest/'predictions.jsonl');models=sorted({m for r in long for m in r['A']})
        for row in long:row['wall']=wall_by_ref[row['ref']]
        for run in data['runs']:
            if not any(r['run']==run['run'] for r in long):continue
            samples=[a for a in data['accepted'] if a['run']==run['run'] and a['target_valid']];events=events_for_run(run)
            for j,event in enumerate(events):
                start=event['start'];end=event['end'];peak_end=end+5 if run['run']=='S' else end
                during=[a for a in samples if start<=a['wall']<end]
                actual=[a for a in samples if start<=a['wall']<peak_end]
                pre=[a for a in samples if start-30<=a['wall']<start];before=[a for a in samples if a['wall']<start]
                rows=[r for r in long if r['run']==run['run'] and r['ref'] in {a['ref'] for a in actual}]
                peaks={}
                for m in models:
                    common=[r for r in rows if m in r['A']]
                    if common:
                        ap=max(common,key=lambda r:r['label']['value']);mp=max(common,key=lambda r:r['A'][m])
                        peaks[m]=dict(n=len(common),actual_peak=ap['label']['value'],model_peak=mp['A'][m],peak_error=mp['A'][m]-ap['label']['value'],
                                      peak_time_offset_s=mp['t']-ap['t'],at_observed_peak_error=ap['A'][m]-ap['label']['value'],metrics=metrics(common,m,'A'),refs=[r['ref'] for r in common],
                                      coverage=len(common)/len(actual),omitted_actual_peak=max(a['values']['tj'] for a in actual) if len(common)<len(actual) else None)
                cooldown=[]
                for lo,hi in [(0,5),(5,15),(15,45),(45,90),(90,300)]:
                    rows=[r for r in long if r['run']==run['run'] and end+lo<=r['wall']<end+hi]
                    actual_window=[a for a in samples if end+lo<=a['wall']<end+hi]
                    cooldown.append(dict(window_s=[lo,hi],source_TJ_n=len(actual_window),common_A_n=len(rows),
                                         mean_actual_TJ=float(np.mean([a['values']['tj'] for a in actual_window])) if actual_window else None,
                                         other_task_overlaps=any(k!=j and q['start']<end+hi and q['end']>end+lo for k,q in enumerate(events)),
                                         metrics={m:metrics(rows,m,'A') for m in models} if rows else {}))
                b_window=[r for r in preds if r['run']==run['run'] and r['h']==45 and start<=r['wall']<end and r['label'] and all(m in r['B'] for m in ('B0','B1','G2-HOLD','G2-RELAX30'))]
                ref=float(np.median([a['values']['tj'] for a in pre])) if pre else None
                area=0. if ref is not None else None
                if ref is not None:
                    for a,b in zip(samples,samples[1:]):
                        left=max(start,a['wall']);right=min(end,b['wall'])
                        if right>left and a['source_epoch']==b['source_epoch'] and b['t']-a['t']<=5:
                            area+=max(0,a['values']['tj']-ref)*(right-left)
                results.append(dict(evaluation=str(dest.relative_to(out)),run=run['run'],event=event,
                                    start_TJ=before[-1]['values']['tj'] if before else None,actual_peak=max(a['values']['tj'] for a in actual) if actual else None,
                                    actual_n=len(actual),peak_window=[start,peak_end],peak_semantics='submit to client end+5s' if run['run']=='S' else 'actual full work block/phase',
                                    peak_window_other_task_overlaps=any(k!=j and q['start']<peak_end and q['end']>start for k,q in enumerate(events)),
                                    during_actual_peak=max(a['values']['tj'] for a in during) if during else None,during_actual_n=len(during),
                                    A_peak=peaks,cooldown=cooldown,pre30_median_TJ=ref,positive_rise_area_C_s=area,
                                    temperature_area_is_not_energy=True,B45_work_common_n=len(b_window),
                                    B45_work_metrics={m:metrics(b_window,m) for m in ('B0','B1','G2-HOLD','G2-RELAX30')} if b_window else {}))
    write(out/'diagnostics/event-metrics.json',results)


def raw_temperature_diagnostics(out):
    diagnostics=[]
    for label in ('L','S','M'):
        e=read(out/'registered'/f'evidence-{label}.json');accepted={s['ref'] for s in e['samples']};cache=ROOT/'cache'
        base=cache/'M-trial/collection' if label=='M' else cache/('L-seven-conditions-original' if label=='L' else 'S-shortqa-original-complete')
        run=next(base.glob('run-*')); zones={};diff=[];nvml=[]
        for r in map(__import__('json').loads,(run/'observations-0001.jsonl').read_text().splitlines()):
            if r['ref'] not in accepted:continue
            temp=r['payload']['temperature'];tj=temp['tj'];z={k:v for k,v in temp.items() if k!='tj' and isinstance(v,(float,int))}
            for k,v in z.items():zones.setdefault(k,[]).append(tj-v)
            if z:diff.append(tj-max(z.values()))
        diagnostics.append(dict(run=label,zones_TJ_minus={k:dict(n=len(v),mean=float(np.mean(v)),min=float(min(v)),max=float(max(v))) for k,v in zones.items()},
                                TJ_minus_max_zone=dict(mean=float(np.mean(diff)),max_abs=float(max(abs(x) for x in diff)),n=len(diff)) if diff else None,
                                TTP_measured=False,latent_state_not_measured_heat_capacity=True))
    write(out/'diagnostics/hotspot-approximation.json',diagnostics)


def source_supplement(out):
    old=read(ROOT/'cache/greybox-v1-evidence/runs/main/data.json')
    write(out/'source-identity-supplement.json',dict(source='unaltered v1 run identity evidence',runs=[dict(run=r['run'],run_id=r['run_id'],
          private_original_hashes=r['private_run_hashes'],share_archive_run_hashes=r['share_run_hashes']) for r in old['runs']],
          reason='retain private originals vs share archive distinction; neither is overwritten'))


def main(out):
    seal_valid(out); assert (out/'stage3-complete.json').exists(); (out/'diagnostics').mkdir(exist_ok=False)
    build_kernel(out/'build');data=read(out/'registered/data.json');spec=read(out/'experiment-spec.json')
    collinearity=[]
    for run in ('L','S','M'):
        rows=[a for a in data['accepted'] if a['run']==run and a['target_valid'] and a['research_segment']]
        for macro in ['all','work','recovery','background']:
            group=rows if macro=='all' else [a for a in rows if a['macro']==macro]
            if len(group)>3:
                X=np.array([[a['values']['vdd_gpu'],a['values']['vdd_cpu_soc_mss'],a['values']['duty']/100] for a in group])
                collinearity.append(dict(run=run,macro=macro,columns=['GPU_W','CPU_SOC_MSS_W','successful_PWM_fraction'],**correlation(X)))
    write(out/'diagnostics/input-collinearity.json',collinearity)
    fit_diagnostics(out,data,spec);event_diagnostics(data,out);raw_temperature_diagnostics(out)
    source_supplement(out)
    print('Diagnostics complete; no additional real-data fitting',flush=True)


if __name__=='__main__':main(ROOT/'runs/main')
