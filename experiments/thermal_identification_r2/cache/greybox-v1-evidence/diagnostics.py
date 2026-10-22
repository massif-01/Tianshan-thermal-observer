"""Pre-registered numerical, state, input, hotspot and residual diagnostics."""
import copy
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from common import read,write,balanced_weights
from greybox import FitProblem,propagate,matrices,forecast
from initialize import rolling_state
from evaluation import load_jsonl,model_context,jsonl


def corr(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    keep=np.isfinite(x)&np.isfinite(y);x=x[keep];y=y[keep]
    return float(np.corrcoef(x,y)[0,1]) if len(x)>2 and np.std(x)>1e-10 and np.std(y)>1e-10 else None


def spectrum(M):
    U,s,V=np.linalg.svd(M,full_matrices=False)
    return dict(singular_values=s,condition=float(s[0]/s[-1]) if len(s) and s[-1]>0 else None,
                numerical_rank=int(sum(s>s[0]*1e-10)) if len(s) and s[0] else 0,
                weakest_vectors=V[-min(3,len(V)):])


def parameter_diagnostic(eid,model,data,spec,out):
    artifact=read(out/'fits'/f'{eid}-{model}/model.json')
    seg=[s for s in data['segments'] if s['run'] in artifact['fit_runs']]
    problem=FitProblem(model,seg,spec);x=np.array(artifact['x']);base=problem.residual(x);columns=[]
    scales=np.r_[np.maximum(abs(x[:problem.nd]),[.001]*(problem.nd-2)+[.01,.01]),np.full(len(x)-problem.nd,20.)]
    for i in range(len(x)):
        h=1e-5*scales[i]
        if x[i]+h>problem.hi[i]:h=-h
        v=x.copy();v[i]+=h;columns.append((problem.residual(v)-base)/h)
    J=np.array(columns).T*np.sqrt(problem.weights)[:,None]*scales[None,:]
    nuisance=J[:,problem.nd:];u,s,_=np.linalg.svd(nuisance,full_matrices=False)
    rank=sum(s>s[0]*1e-10) if len(s) and s[0] else 0
    D=J[:,:problem.nd];projected=D-u[:,:rank]@(u[:,:rank].T@D)
    p=np.array(list(artifact['dynamic'].values()));times=[];numeric=[]
    for duty in sorted(set([0.,1.,*artifact['u_range'],np.mean(artifact['u_range'])])):
        A,f=matrices(model,p,artifact['parameters'][f'E_{artifact["fit_runs"][0]}'],[15,8,duty]);eigen=np.linalg.eigvals(A).real
        times.append(dict(u=duty,eigenvalues=eigen,time_constants_s=-1/eigen,all_stable=bool(np.all(eigen<0))))
        for dt in [1e-8,.003,1.003,2.49,90.]:
            n=len(A);aug=np.zeros((n+1,n+1));aug[:n,:n]=A;aug[:n,-1]=f
            E=artifact['parameters'][f'E_{artifact["fit_runs"][0]}'];initial=[48,55]
            actual=propagate(model,p,E,[dt],[[15,8,duty]],initial)[-1,:n]
            reference=(expm(aug*dt)@np.r_[initial[:n],1])[:n]
            numeric.append(float(np.max(abs(actual-reference))))
    attempts=[read(out/'fits'/f'{eid}-{model}/{seed["id"]}.json') for seed in spec['initializations']]
    return dict(experiment=eid,model=model,parameter_names=problem.names,scale=scales,
                weighted_raw_residual_full=spectrum(J),projected_dynamic=spectrum(projected),nuisance_rank=int(rank),
                singular_value_interpretation='numerical sensitivity only; no physical confidence interval',time_constants=times,
                expm_max_abs_difference=max(numeric),
                attempts=[{k:a[k] for k in ['seed','parameters','J','converged','status','actual_residual_calls','nfev','seconds','boundary_parameters']} for a in attempts])


def run_diagnostics(data,examples,spec,out):
    out=Path(out);dest=out/'diagnostics';dest.mkdir()
    rows={r['ref']:r for r in data['accepted']}
    input_info=[];hotspots=[]
    for run in ('L','S'):
        valid=[r for r in data['accepted'] if r['run']==run and r.get('research_segment')]
        names=['vdd_gpu','vdd_cpu_soc_mss','vin_sys_5v0','duty'];X=np.array([[r['values'][n] for n in names] for r in valid]);Z=(X-X.mean(axis=0))/X.std(axis=0)
        input_info.append(dict(run=run,n=len(valid),columns=names,min=X.min(axis=0),max=X.max(axis=0),std=X.std(axis=0),correlation=np.corrcoef(X.T),standardized_spectrum=spectrum(Z)))
        zones=[k for k in valid[0]['values'] if k.startswith('temp_')]
        last=None
        for r in valid:
            temps=[r['values'][k] for k in zones];mx=max(temps);dominant='|'.join(k for k,v in zip(zones,temps) if v==mx)
            switch=last is not None and last[0]==r['research_segment'] and last[1]!=dominant
            hotspots.append(dict(ref=r['ref'],run=run,segment=r['research_segment'],tj_minus_zone_max=r['values']['tj']-mx,dominant=dominant,switch=switch))
            last=(r['research_segment'],dominant)
    write(dest/'input-information.json',input_info);jsonl(dest/'hotspots.jsonl',hotspots);hs={r['ref']:r for r in hotspots}
    write(dest/'hotspot-summary.json',[dict(run=run,n=sum(r['run']==run for r in hotspots),switches=sum(r['switch'] for r in hotspots if r['run']==run),
          max_abs_TJ_minus_zone_max=max(abs(r['tj_minus_zone_max']) for r in hotspots if r['run']==run),
          dominant_counts={k:sum(r['run']==run and r['dominant']==k for r in hotspots) for k in sorted({r['dominant'] for r in hotspots if r['run']==run})}) for run in ('L','S')])
    parameters=[];residuals=[];initials=[];input_assumption=[];offset_sensitivity=[];firmware=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        predictions=load_jsonl(out/'evaluation'/eid/'predictions.jsonl');longs=load_jsonl(out/'evaluation'/eid/'A-long.jsonl')
        for model in ('G1','G2'):
            parameters.append(parameter_diagnostic(eid,model,data,spec,out))
            error=np.array([r['A'][model]-r['label']['value'] for r in longs]);assoc={}
            for field in ['vin_sys_5v0','gain','temp_cpu','temp_gpu','temp_soc012','temp_soc345','duty','vdd_gpu','vdd_cpu_soc_mss']:
                assoc[field]=corr(error,[rows[r['ref']]['values'].get(field,np.nan) for r in longs])
            ac={}
            for lag in (1,5,15,45,90):
                a=[];b=[]
                for sid in sorted({r['segment'] for r in longs}):
                    group=[r for r in longs if r['segment']==sid];t=np.array([r['t'] for r in group]);e=np.array([r['A'][model]-r['label']['value'] for r in group])
                    for i in range(len(group)):
                        j=np.searchsorted(t,t[i]+lag)
                        if j<len(t) and t[j]-t[i]-lag<=2:a.append(e[i]);b.append(e[j])
                ac[str(lag)]=dict(n_pairs=len(a),correlation=corr(a,b))
            byhot={}
            for hot in sorted({hs[r['ref']]['dominant'] for r in longs}):
                e=[v for v,r in zip(error,longs) if hs[r['ref']]['dominant']==hot];byhot[hot]=dict(n=len(e),mae=float(np.mean(np.abs(e))),bias=float(np.mean(e)))
            switch_error=[v for v,r in zip(error,longs) if hs[r['ref']]['switch']]
            bad=sorted(zip(error,longs),key=lambda x:abs(x[0]),reverse=True)[:20]
            residuals.append(dict(experiment=eid,model=model,correlations=assoc,autocorrelation=ac,by_hotspot=byhot,
                                  hotspot_switch_error=dict(n=len(switch_error),mae=float(np.mean(np.abs(switch_error))) if switch_error else None),
                                  largest_errors=[dict(ref=r['ref'],utc=r['utc'],run=r['run'],regime=r['regime'],error_C=float(e),truth=r['label']['value'],prediction=r['A'][model]) for e,r in bad]))
        sens=load_jsonl(out/'evaluation'/eid/'state-sensitivity-180.jsonl')
        for h in (15,45,90):
            cohort=[r for r in sens if r['h']==h]
            for mode in ('A','HOLD','RELAX30'):
                if not cohort:continue
                w=balanced_weights(cohort);err={v:np.array([r[f'{mode}{v}']-r['label']['value'] for r in cohort]) for v in (60,180)}
                initials.append(dict(experiment=eid,h=h,mode=mode,n=len(cohort),mae60=float(np.mean(abs(err[60]))),mae180=float(np.mean(abs(err[180]))),balanced_mae60=float(w@abs(err[60])),balanced_mae180=float(w@abs(err[180])),prediction_change_p95=float(np.percentile(abs(err[60]-err[180]),95))))
        for h in (15,45,90):
            for model in ('G1','G2'):
                cohort=[r for r in predictions if r['h']==h and r['label'] and model in r['A'] and f'{model}-HOLD' in r['B']]
                for regime in ['all']+sorted({r['regime'] for r in cohort}):
                    c=cohort if regime=='all' else [r for r in cohort if r['regime']==regime]
                    if not c:continue
                    input_assumption.append(dict(experiment=eid,h=h,model=model,regime=regime,n=len(c),
                         known_input_mae=float(np.mean([abs(r['A'][model]-r['label']['value']) for r in c])),
                         hold_mae=float(np.mean([abs(r['B'][f'{model}-HOLD']-r['label']['value']) for r in c])),
                         relax30_mae=float(np.mean([abs(r['B'][f'{model}-RELAX30']-r['label']['value']) for r in c]))))
            labeled=[r for r in predictions if r['h']==h and r['label']]
            for bucket in ('offset_le_0.5','offset_gt_0.5'):
                c=[r for r in labeled if (r['label']['offset_s']<=.5)==(bucket=='offset_le_0.5') and 'G2-HOLD' in r['B']]
                offset_sensitivity.append(dict(experiment=eid,h=h,bucket=bucket,n=len(c),max_offset_s=max([r['label']['offset_s'] for r in c],default=None),
                      B0_mae=float(np.mean([abs(r['B']['B0']-r['label']['value']) for r in c])) if c else None,
                      G2_HOLD_mae=float(np.mean([abs(r['B']['G2-HOLD']-r['label']['value']) for r in c])) if c else None))
        c=[r for r in predictions if r['h']==45 and r['label'] and 'firmware_diagnostic' in r]
        firmware.append(dict(experiment=eid,n=len(c),firmware_mae=float(np.mean([abs(r['firmware_diagnostic']['value']-r['label']['value']) for r in c])),B0_same_origins_mae=float(np.mean([abs(r['B']['B0']-r['label']['value']) for r in c])),note='as-of firmware number, different fan timestamp, not control efficacy'))
    write(dest/'parameters.json',parameters);write(dest/'residuals.json',residuals);write(dest/'state-sensitivity.json',initials)
    write(dest/'known-vs-assumed-inputs.json',input_assumption);write(dest/'label-offset-sensitivity.json',offset_sensitivity);write(dest/'firmware-reference.json',firmware)
    nested=read(out/'fits/nested-d1-zero.json');pool=read(out/'fits/F-POOL-G2/model.json')
    write(dest/'nested-fan.json',dict(main_J=pool['J'],d1_zero_J=nested['J'],relative_increase=(nested['J']-pool['J'])/pool['J'],
                                   converged=nested['converged'],main_d1=pool['dynamic']['d1'],interpretation='closed-loop observational identifiability diagnostic; no causal fan claim'))
    near=[]
    for eid,target in [('F-LS','S'),('F-SL','L')]:
        target_segments=[s for s in data['segments'] if s['run']==target];smap={s['id']:s for s in target_segments}
        scored=[r for r in load_jsonl(out/'evaluation'/eid/'predictions.jsonl') if r['h']==45 and r['label'] and 'G2-HOLD' in r['B']]
        for model in ('G1','G2'):
            best=read(out/'fits'/f'{eid}-{model}/model.json')
            for seed in spec['initializations']:
                trial=read(out/'fits'/f'{eid}-{model}/{seed["id"]}.json')
                if not trial['finite'] or trial['J']>best['J']*1.05:continue
                alternative=copy.deepcopy(best);alternative['parameters']=trial['parameters'];alternative['dynamic']={k:trial['parameters'][k] for k in best['dynamic']}
                p,boundaries,cal,responses=model_context(alternative,target_segments)
                changes=[];errors=[];points=[]
                byref={r['ref']:r for s in target_segments for r in s['rows']}
                for r in scored:
                    seg=smap[r['segment']];a=byref[r['ref']];i=next(i for i,x in enumerate(seg['rows']) if x['ref']==r['ref'])
                    state,_=rolling_state(model,p,boundaries[target],seg,i);u=[a['values']['vdd_gpu'],a['values']['vdd_cpu_soc_mss'],a['values']['duty']/100]
                    pred=forecast(model,p,boundaries[target],state,u,45,'HOLD',best['P10_fit']);delta=pred-r['B'][f'{model}-HOLD']
                    changes.append(delta);errors.append(pred-r['label']['value']);points.append(dict(ref=r['ref'],prediction=pred,delta_from_selected=delta))
                jsonl(dest/f'near-{eid}-{model}-{seed["id"]}.jsonl',points)
                rel={k:abs(alternative['dynamic'][k]-v)/max(abs(v),.001) for k,v in best['dynamic'].items()}
                near.append(dict(experiment=eid,model=model,seed=seed['id'],J=trial['J'],converged=trial['converged'],relative_dynamic_differences=rel,
                                 n=len(changes),HOLD45_prediction_change_p95=float(np.percentile(abs(np.array(changes)),95)),HOLD45_prediction_change_max=float(max(abs(np.array(changes)))),HOLD45_mae=float(np.mean(abs(np.array(errors))))))
    write(dest/'near-optimal-solutions.json',near)
    print('diagnostics complete',flush=True)
