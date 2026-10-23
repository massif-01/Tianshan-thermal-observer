"""Constrained thermal candidates with exact CPU propagation and bounded fitting."""
import ctypes
import os
import subprocess
import time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from scipy.optimize import least_squares
from common import write, balanced_weights, stamp, sha

LIB = None


def build_kernel(build_dir):
    global LIB
    build_dir=Path(build_dir);build_dir.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).with_name('propagate.c')
    binary=build_dir/'propagate.so'
    cmd=[os.environ.get('CC','cc'),'-O2','-fPIC','-shared',str(source),'-o',str(binary),'-lm']
    result=subprocess.run(cmd,capture_output=True,text=True,check=True)
    write(build_dir/'compiler.json',dict(command=cmd,stdout=result.stdout,stderr=result.stderr,source_sha256=sha(source)))
    LIB=ctypes.CDLL(str(binary.resolve()))
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
    LIB.trajectory.argtypes=[ctypes.c_int,ctypes.c_size_t,ptr,ctypes.c_double,ptr,ptr,ptr,ptr]
    LIB.trajectory.restype=None


def propagate(model,p,E,dt,inputs,initial):
    p,dt,inputs,initial=[np.ascontiguousarray(x,dtype=np.float64) for x in (p,dt,inputs,initial)]
    assert len(initial)==2 and inputs.shape==(len(dt),3)
    out=np.empty((len(dt)+1,2),dtype=np.float64)
    LIB.trajectory(int(model[-1]),len(dt),p,float(E),dt,inputs,initial,out)
    return out


def matrices(model,p,E,u):
    pg,pc,duty=u
    if model=='G1':
        k=p[0]+p[1]*duty
        return np.array([[-k]]),np.array([k*E+p[2]*pg+p[3]*pc])
    a,c,d0,d1,bg,bc=p;d=d0+d1*duty
    return np.array([[-a,a],[c,-c-d]]),np.array([bg*pg+bc*pc,d*E])


def forecast(model,p,E,state,current,h,scenario,floors):
    if scenario=='HOLD':
        return propagate(model,p,E,[h],[current],state)[-1,0]
    # Augment with the *known hypothetical* exponential power deviation state.
    floor=np.minimum(current[:2],floors)
    A,f=matrices(model,p,E,[*floor,current[2]])
    n=len(A);M=np.zeros((n+2,n+2));M[:n,:n]=A;M[:n,-1]=f
    b=p[2:] if model=='G1' else p[4:]
    M[0,n]=np.dot(b,np.asarray(current[:2])-floor);M[n,n]=-1/30
    return (expm(M*h)@np.r_[state[:n],1.,1.])[0]


def arrays(segment):
    t=np.array([n['t'] for n in segment['timeline']])
    return dict(dt=np.diff(t),u=np.array([n['inputs'] for n in segment['timeline'][:-1]],dtype=float).reshape(-1,3),
                index=np.array([a['timeline_index'] for a in segment['rows']],dtype=int),
                y=np.array([a['values']['tj'] for a in segment['rows']]),segment=segment)


def huber_loss(weights):
    def loss(z):
        z=np.asarray(z);root=np.sqrt(np.maximum(z,1.));mask=z<=1
        return np.array([np.where(mask,z,2*root-1),np.where(mask,1,1/root),np.where(mask,0,-0.5/(root**3))])*weights
    return loss


class FitProblem:
    def __init__(self,model,segments,spec):
        self.model,self.spec=model,spec
        self.groups=[arrays(s) for s in segments if s['eligible_for_fit']]
        self.runs=sorted({g['segment']['run'] for g in self.groups})
        self.dynamic=spec['models'][model]['dynamic_parameters']
        self.names=self.dynamic+[f'E_{r}' for r in self.runs]+([f'Ts_{g["segment"]["id"]}' for g in self.groups] if model=='G2' else [])
        bounds=[spec['models'][model]['bounds'][n] for n in self.dynamic]+[[-10,60]]*len(self.runs)+([[-20,120]]*len(self.groups) if model=='G2' else [])
        self.lo,self.hi=np.array(bounds).T
        self.rows=[a for g in self.groups for a in g['segment']['rows']]
        self.weights=balanced_weights(self.rows)
        self.nd=len(self.dynamic)

    def initial(self,seed):
        values=[seed[self.model][k] for k in self.dynamic]
        values += [np.clip(next(g['y'][0] for g in self.groups if g['segment']['run']==r)-15,-10,60) for r in self.runs]
        if self.model=='G2': values += [np.clip(g['y'][0]-2,-20,120) for g in self.groups]
        return np.array(values)

    def responses(self,x):
        out=[]
        for j,g in enumerate(self.groups):
            E=x[self.nd+self.runs.index(g['segment']['run'])]
            ts=x[self.nd+len(self.runs)+j] if self.model=='G2' else 0
            z=propagate(self.model,x[:self.nd],E,g['dt'],g['u'],[g['y'][0],ts])
            out.append(z[g['index'],0])
        return out

    def residual(self,x):
        return np.concatenate([v-g['y'] for v,g in zip(self.responses(x),self.groups)])

    def objective(self,x):
        e=self.residual(x)/.3
        return float(np.dot(self.weights,np.where(np.abs(e)<=1,e*e,2*np.abs(e)-1)))


def solve(problem,x0,seed_id,out,max_nfev=300,max_calls=1500,fixed_d1=False):
    start=time.perf_counter();calls=0;best=(float('inf'),x0.copy());trace=[]
    free=np.arange(len(x0))
    if fixed_d1: free=np.delete(free,3);x0=x0.copy();x0[3]=0
    def unpack(z):
        x=x0.copy();x[free]=z;return x
    def residual(z):
        nonlocal calls,best
        if calls>=max_calls: raise RuntimeError('actual_residual_call_budget')
        calls+=1;x=unpack(z);r=problem.residual(x)/.3
        J=float(np.dot(problem.weights,np.where(abs(r)<=1,r*r,2*abs(r)-1)))
        if np.isfinite(J) and J<best[0]:best=(J,x.copy())
        trace.append(dict(call=calls,J=J if np.isfinite(J) else None))
        return r
    def jacobian(z):
        # Finite differences only for nonlinear dynamics. Nuisance columns are
        # exact homogeneous/affine sensitivities, not 56 perturbed full fits.
        x=unpack(z);base=residual(z);J=np.zeros((len(base),len(x)))
        for k in range(problem.nd):
            if k not in free: continue
            step=np.sqrt(np.finfo(float).eps)*max(abs(x[k]),.01)
            if x[k]+step>problem.hi[k]: step=-step
            zp=z.copy();zp[list(free).index(k)]+=step
            J[:,k]=(residual(zp)-base)/step
        pos=0
        for j,g in enumerate(problem.groups):
            n=len(g['y']);zero=g['u'].copy();zero[:,:2]=0
            eb=propagate(problem.model,x[:problem.nd],1,g['dt'],zero,[0,0])[g['index'],0]/.3
            J[pos:pos+n,problem.nd+problem.runs.index(g['segment']['run'])]=eb
            if problem.model=='G2':
                sb=propagate('G2',x[:problem.nd],0,g['dt'],zero,[0,1])[g['index'],0]/.3
                J[pos:pos+n,problem.nd+len(problem.runs)+j]=sb
            pos+=n
        return J[:,free]
    try:
        result=least_squares(residual,x0[free],jac=jacobian,bounds=(problem.lo[free],problem.hi[free]),method='trf',x_scale='jac',
                             loss=huber_loss(problem.weights),max_nfev=max_nfev,ftol=1e-8,xtol=1e-8,gtol=1e-8)
        x=unpack(result.x);status=int(result.status);message=result.message;nfev=result.nfev;optimality=float(result.optimality)
        J=float(np.dot(problem.weights,np.where(abs(result.fun)<=1,result.fun**2,2*abs(result.fun)-1)))
    except RuntimeError as e:
        x=best[1];J=best[0];status=0;message=str(e);nfev=None;optimality=None
    entry=dict(seed=seed_id,initial=x0,parameters=dict(zip(problem.names,x)),x=x,J=J,finite=bool(np.isfinite(x).all() and np.isfinite(J)),
               converged=status>0,status=status,message=message,nfev=nfev,actual_residual_calls=calls,optimality=optimality,
               seconds=time.perf_counter()-start,finished_at=stamp(),
               boundary_parameters=[name for name,v,lo,hi in zip(problem.names,x,problem.lo,problem.hi) if min(v-lo,hi-v)<1e-4*(hi-lo)],trace=trace)
    write(out,entry)
    print(problem.model,seed_id,'J',round(J,6),'status',status,'calls',calls,'seconds',round(entry['seconds'],2),flush=True)
    return entry


def fit(model,segments,spec,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    problem=FitProblem(model,segments,spec)
    trials=[solve(problem,problem.initial(seed),seed['id'],out/f'{seed["id"]}.json',spec['fit']['max_nfev'],spec['fit']['max_actual_residual_calls_per_seed']) for seed in spec['initializations']]
    good=[v for v in trials if v['converged'] and v['finite']]
    selected=min(good if good else [v for v in trials if v['finite']],key=lambda v:v['J'])
    rows=problem.rows;P=np.array([[r['values']['vdd_gpu'],r['values']['vdd_cpu_soc_mss']] for r in rows])
    artifact=dict(schema='TTO-GREYBOX-EXPERIMENT-v1',deployable=False,model=model,
                  fit_runs=problem.runs,selected_seed=selected['seed'],converged=selected['converged'],selection='training_objective_only',
                  dynamic={k:selected['parameters'][k] for k in problem.dynamic},parameters=selected['parameters'],x=selected['x'],
                  J=selected['J'],P10_fit=np.percentile(P,10,axis=0),input_min=P.min(axis=0),input_max=P.max(axis=0),
                  u_range=[min(r['values']['duty']/100 for r in rows),max(r['values']['duty']/100 for r in rows)],
                  frozen_at=stamp(),parameter_count=len(problem.names),spec_sha256=sha(Path(out).parents[1]/'experiment-spec.json'))
    write(out/'model.json',artifact)
    return artifact,problem,trials
