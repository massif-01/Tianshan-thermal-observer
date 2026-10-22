"""Past-only affine boundary / state estimation with fixed dynamic parameters."""
import numpy as np
from scipy.optimize import lsq_linear
from greybox import propagate


def path_between(segment,start,end):
    """Nominal end time; only actual left-held input events strictly before end."""
    times=np.array([n['t'] for n in segment['timeline']])
    lo=np.searchsorted(times,start,side='right')-1
    hi=np.searchsorted(times,end,side='left')
    mids=times[lo+1:hi]
    edges=np.r_[start,mids,end]
    inputs=np.array([n['inputs'] for n in segment['timeline'][lo:hi]],float).reshape(-1,3)
    return np.diff(edges),inputs


def estimate(model,p,segment,end,window,E=None,E_fallback=None):
    """All observed TJ used is in [end-window,end], inclusively."""
    rows=segment['rows']
    chosen=[a for a in rows if end-window-1e-9<=a['mono_s']<=end+1e-9]
    assert chosen and chosen[-1]['mono_s']<=end+1e-9
    start=chosen[0]['mono_s']
    dt,u=path_between(segment,start,end)
    times=np.r_[start,start+np.cumsum(dt)]
    idx=np.array([np.argmin(abs(times-r['mono_s'])) for r in chosen])
    y=np.array([a['values']['tj'] for a in chosen]);y0=y[0]
    z=propagate(model,p,0 if E is None else E,dt,u,[y0,0])
    columns=[];names=[]
    zero=u.copy();zero[:,:2]=0
    if E is None:
        columns.append(propagate(model,p,1,dt,zero,[0,0])[:,0]);names.append('E')
    if model=='G2':
        columns.append(propagate(model,p,0,dt,zero,[0,1])[:,0]);names.append('Ts')
    X=np.array(columns).T[idx] if columns else np.empty((len(chosen),0))
    norms=np.linalg.norm(X,axis=0)
    singular=np.linalg.svd(X/np.where(norms>0,norms,1),compute_uv=False)
    ratio=float(singular[-1]/singular[0]) if len(singular) and singular[0]>0 else 0
    weak=E is None and model=='G2' and ratio<1e-6
    if weak:
        result=estimate(model,p,segment,end,window,E=E_fallback)
        result.update(weak_prefix_calibration=True,original_singular_ratio=ratio,original_singular_values=singular.tolist())
        return result
    lower=[-10 if n=='E' else -20 for n in names];upper=[60 if n=='E' else 120 for n in names]
    fit=lsq_linear(X,y-z[idx,0],bounds=(lower,upper),tol=1e-12) if names else None
    values=dict(zip(names,fit.x)) if fit else {}
    Er=values.get('E',E);ts=values.get('Ts',0.)
    states=propagate(model,p,Er,dt,u,[y0,ts])
    return dict(E=float(Er),Ts_initial=float(ts),state=states[-1].tolist(),start=start,end=end,
                first_ref=chosen[0]['ref'],last_ref=chosen[-1]['ref'],n=len(chosen),rank=int(np.linalg.matrix_rank(X)) if names else 0,
                normalized_singular_values=singular.tolist(),singular_ratio=ratio,condition=1/ratio if ratio>0 else None,
                weak_prefix_calibration=False,rmse=float(np.sqrt(np.mean((states[idx,0]-y)**2))),
                bounds_hit=[n for n,v,l,h in zip(names,fit.x if fit else [],lower,upper) if min(v-l,h-v)<1e-5])


def rolling_state(model,p,E,segment,index,window=60):
    row=segment['rows'][index];t=row['mono_s']
    if model=='G1':
        return [row['values']['tj'],0.],dict(start=t,end=t,first_ref=row['ref'],last_ref=row['ref'],n=1)
    result=estimate(model,p,segment,t,window,E=E)
    state=result['state'].copy();state[0]=row['values']['tj']
    return state,result
