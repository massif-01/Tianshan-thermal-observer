import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from scipy.linalg import expm
from greybox import build_kernel,propagate,matrices,forecast,huber_loss,FitProblem,solve
from initialize import estimate
from common import read


@pytest.fixture(scope='session',autouse=True)
def kernel(tmp_path_factory):
    build_kernel(tmp_path_factory.mktemp('kernel'))


def synthetic(model,p,E=25.,n=401,excited=True):
    t=np.arange(n,dtype=float)
    u=np.column_stack([5+20*((t//17)%2),6+8*((t//31)%2),.15+.6*((t//43)%2)]) if excited else np.tile([2,6,.2],(n,1))
    y=propagate(model,p,E,np.diff(t),u[:-1],[48,55])[:,0]
    rows=[dict(mono_s=float(v),timeline_index=i,values=dict(tj=y[i]),ref=str(i),run='X',macro='work',duration=1 if i<n-1 else 0) for i,v in enumerate(t)]
    timeline=[dict(t=float(v),inputs=u[i].tolist()) for i,v in enumerate(t)]
    return dict(id='X-0',run='X',rows=rows,timeline=timeline,eligible_for_fit=True,span_s=float(n-1))


def test_exact_propagation_and_affine_shift():
    rng=np.random.default_rng(423)
    params=[[.4,.2,.1,.05],[1,.02,.001,.02,.08,.04],[.0001,.000001,.0001,0,.01,.02],[4,1,1,1,5,5]]
    for p in params:
        model='G1' if len(p)==4 else 'G2'
        for dt in [1e-9,1e-5,.1,1.37,90.]:
            u=rng.uniform([0,0,0],[60,30,1]);A,f=matrices(model,p,31,u);n=len(A)
            M=np.zeros((n+1,n+1));M[:n,:n]=A;M[:n,-1]=f
            x=[54,63];ref=(expm(M*dt)@np.r_[x[:n],1])[:n]
            got=propagate(model,p,31,[dt],[u],x)[-1,:n]
            np.testing.assert_allclose(got,ref,rtol=1e-10,atol=1e-9)
            shifted=propagate(model,p,43,[dt],[u],np.array(x)+12)[-1,:n]
            np.testing.assert_allclose(shifted,got+12,atol=1e-9)


def test_huber_weight_does_not_move_celsius_knee():
    z=np.array([.5,2.,.5,2.])**2
    w=np.array([1.,1.,.01,.01]);rho=huber_loss(w)(z)
    np.testing.assert_allclose(rho[:,2:]/.01,rho[:,:2])
    np.testing.assert_allclose(rho[0,:2],[.25,3])


def test_hot_slow_initial_and_past_only():
    p=np.array([.18,.006,.002,.004,.09,.03]);s=synthetic('G2',p)
    r=estimate('G2',p,s,60,60,E=None,E_fallback=25)
    np.testing.assert_allclose([r['E'],r['Ts_initial']],[25,55],atol=1e-6)
    for row in s['rows'][61:]:row['values']['tj']+=100
    r2=estimate('G2',p,s,60,60,E=None,E_fallback=25)
    assert r==r2


def test_g1_later_segment_has_fixed_boundary_and_no_fit_columns():
    p=np.array([.03,.08,.08,.03]);s=synthetic('G1',p)
    r=estimate('G1',p,s,60,60,E=25)
    assert r['E']==25 and r['rank']==0 and r['rmse']<1e-10


def test_relax_analytic_step_halving():
    p=np.array([.18,.006,.002,.004,.09,.03]);state=[52,50];current=np.array([25,15,.4]);floor=[2,6]
    exact=forecast('G2',p,25,state,current,90,'RELAX30',floor)
    errors=[]
    for step in [.1,.05]:
        t=np.arange(0,90,step);power=np.minimum(current[:2],floor)+(current[:2]-np.minimum(current[:2],floor))*np.exp(-(t[:,None]+step/2)/30)
        u=np.column_stack([power,np.full(len(t),current[2])])
        got=propagate('G2',p,25,np.full(len(t),step),u,state)[-1,0];errors.append(abs(got-exact))
    assert errors[1]<errors[0]/3 and errors[1]<1e-5


def test_excited_synthetic_fits_response_and_weak_excitation_rank(tmp_path):
    spec=read(Path(__file__).parents[1]/'experiment-spec.json')
    for model,p in [('G1',[.03,.08,.08,.03]),('G2',[.18,.006,.002,.004,.09,.03])]:
        s=synthetic(model,p,n=501);problem=FitProblem(model,[s],spec)
        # A verification fit, deliberately offset from truth; never real-data seed selection.
        x=np.r_[np.array(p)*1.15,27,53] if model=='G2' else np.r_[np.array(p)*1.15,27]
        r=solve(problem,x,'synthetic',tmp_path/f'{model}.json',max_calls=1500)
        assert r['converged'] and np.sqrt(np.mean(problem.residual(r['x'])**2))<1e-4
    weak=synthetic('G2',p,excited=False);u=np.array([n['inputs'] for n in weak['timeline']])
    assert np.linalg.matrix_rank(u-u.mean(axis=0),tol=1e-10)==0
