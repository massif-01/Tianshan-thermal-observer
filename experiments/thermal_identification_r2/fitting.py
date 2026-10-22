"""Inherited six-start solver; one registered E_M=24 binding diagnostic."""
import time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from common import write, stamp, sha
from greybox import FitProblem, propagate, huber_loss, fit
from ridge_reference import fit_ridges


def solve_bound(problem, seed, out, fixed):
    x0=problem.initial(seed)
    for name,value in fixed.items(): x0[problem.names.index(name)]=value
    free=np.array([i for i,n in enumerate(problem.names) if n not in fixed]); start=time.perf_counter(); calls=0; trace=[]; best=(float('inf'),x0.copy())
    def unpack(z):
        x=x0.copy(); x[free]=z; return x
    def residual(z):
        nonlocal calls,best
        if calls>=1500: raise RuntimeError('actual_residual_call_budget')
        calls+=1; x=unpack(z); r=problem.residual(x)/.3
        J=float(problem.weights@np.where(abs(r)<=1,r*r,2*abs(r)-1))
        if np.isfinite(J) and J<best[0]: best=(J,x.copy())
        trace.append(dict(call=calls,J=J if np.isfinite(J) else None)); return r
    def jacobian(z):
        x=unpack(z); base=residual(z); J=np.zeros((len(base),len(x)))
        for k in range(problem.nd):
            step=np.sqrt(np.finfo(float).eps)*max(abs(x[k]),.01)
            if x[k]+step>problem.hi[k]: step=-step
            zp=z.copy(); zp[list(free).index(k)]+=step; J[:,k]=(residual(zp)-base)/step
        pos=0
        for j,g in enumerate(problem.groups):
            n=len(g['y']); zero=g['u'].copy(); zero[:,:2]=0
            J[pos:pos+n,problem.nd+problem.runs.index(g['segment']['run'])]=propagate('G2',x[:problem.nd],1,g['dt'],zero,[0,0])[g['index'],0]/.3
            J[pos:pos+n,problem.nd+len(problem.runs)+j]=propagate('G2',x[:problem.nd],0,g['dt'],zero,[0,1])[g['index'],0]/.3
            pos+=n
        return J[:,free]
    try:
        r=least_squares(residual,x0[free],jac=jacobian,bounds=(problem.lo[free],problem.hi[free]),method='trf',x_scale='jac',
                        loss=huber_loss(problem.weights),max_nfev=300,ftol=1e-8,xtol=1e-8,gtol=1e-8)
        x=unpack(r.x); status=int(r.status); message=r.message; nfev=r.nfev; optimality=float(r.optimality)
        J=float(problem.weights@np.where(abs(r.fun)<=1,r.fun*r.fun,2*abs(r.fun)-1))
    except RuntimeError as exc:
        x=best[1]; J=best[0]; status=0; message=str(exc); nfev=None; optimality=None
    entry=dict(seed=seed['id'],initial=x0,parameters=dict(zip(problem.names,x)),x=x,J=J,finite=bool(np.isfinite(x).all() and np.isfinite(J)),
               converged=status>0,status=status,message=message,nfev=nfev,actual_residual_calls=calls,optimality=optimality,
               seconds=time.perf_counter()-start,finished_at=stamp(),fixed_parameters=fixed,
               optimized_parameter_names=[problem.names[i] for i in free],free_parameter_count=len(free),
               boundary_parameters=[n for n,v,lo,hi in zip(problem.names,x,problem.lo,problem.hi) if n not in fixed and min(v-lo,hi-v)<1e-4*(hi-lo)],trace=trace)
    write(out,entry); print('G2-A24',seed['id'],'J',round(J,6),'status',status,'calls',calls,flush=True); return entry


def fit_A24(segments,spec,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False); problem=FitProblem('G2',segments,spec)
    attempts=[solve_bound(problem,s,out/f"{s['id']}.json",{'E_M':24.}) for s in spec['initializations']]
    good=[a for a in attempts if a['finite'] and a['converged']]
    best=min(good or [a for a in attempts if a['finite']],key=lambda a:a['J']); P=np.array([[r['values']['vdd_gpu'],r['values']['vdd_cpu_soc_mss']] for r in problem.rows])
    artifact=dict(schema='TTO-GREYBOX-EXPERIMENT-v1',deployable=False,model='G2',fit_runs=problem.runs,
                  selected_seed=best['seed'],converged=best['converged'],selection='training_objective_only',dynamic={k:best['parameters'][k] for k in problem.dynamic},
                  parameters=best['parameters'],x=best['x'],J=best['J'],P10_fit=np.percentile(P,10,axis=0),input_min=P.min(axis=0),input_max=P.max(axis=0),
                  u_range=[min(r['values']['duty']/100 for r in problem.rows),max(r['values']['duty']/100 for r in problem.rows)],
                  fixed_parameters={'E_M':24.},parameter_count=len(problem.names)-1,stored_parameter_count=len(problem.names),
                  diagnostic_only=True,extra_offset_or_heat_input=False,frozen_at=stamp(),spec_sha256=sha(out.parents[1]/'experiment-spec.json'))
    write(out/'model.json',artifact); return artifact


def ridge_fit(examples,runs,spec,out):
    # Keep inherited whole strict-segment CV; labels are independently admitted under AVAIL-v2.
    training=[dict(r,labels={h:v for h,v in r['labels'].items() if v is not None}) for r in examples if r['run'] in runs and r['segment'] is not None]
    result=fit_ridges(training,runs,spec,out)
    for methods in result['methods'].values():
        for h,head in methods.items():
            head['fold_composition']={g:dict(runs=sorted({r['run'] for r in training if r['segment']==g}),
                                            macro_n={m:sum(r['segment']==g and r['macro']==m for r in training) for m in ('work','recovery','background')})
                                       for g in head['groups']}
    write(out,result); return result
