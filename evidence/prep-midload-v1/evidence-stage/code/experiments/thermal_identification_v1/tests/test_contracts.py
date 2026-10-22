import copy
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from test_numeric import synthetic,kernel
from greybox import forecast,propagate,FitProblem
from initialize import rolling_state,path_between
from ridge_reference import features,label_index,fit_one,predict
from common import read,balanced_weights


def test_future_temperature_input_and_request_end_causal_counterexample():
    p=np.array([.18,.006,.002,.004,.09,.03]);segment=synthetic('G2',p);i=150;now=150.
    state,evidence=rolling_state('G2',p,25,segment,i)
    u=np.array(segment['timeline'][i]['inputs']);before=forecast('G2',p,25,state,u,45,'HOLD',[2,6])
    feature_before=features(segment,i)
    dt,inputs=path_between(segment,now,now+45);response_before=propagate('G2',p,25,dt,inputs,state)[-1,0]
    changed=copy.deepcopy(segment);changed['future_request_end']=152
    for row in changed['rows'][i+1:]:row['values']['tj']+=50
    for node in changed['timeline'][i+1:]:node['inputs'][0]+=25
    state2,evidence2=rolling_state('G2',p,25,changed,i)
    assert state==state2 and evidence==evidence2
    assert forecast('G2',p,25,state2,u,45,'HOLD',[2,6])==before
    np.testing.assert_equal(features(changed,i),feature_before)
    dt,inputs=path_between(changed,now,now+45);assert abs(propagate('G2',p,25,dt,inputs,state2)[-1,0]-response_before)>1


def test_horizons_are_independent_and_no_early_or_cross_segment_label():
    t=np.array([0.,15.2,45.6,59.])
    assert label_index(t,0,45)==2 and label_index(t,0,90) is None
    assert label_index(t[:2],0,45) is None
    assert label_index(np.array([0.,44.9,48.]),0,45) is None


def test_ridge_normalization_penalty_and_unpenalized_intercept():
    rows=[]
    for i in range(25):
        x=np.array([i*.1,np.sin(i)])
        rows.append(dict(run='L' if i<10 else 'S',macro='work' if i%2 else 'background',duration=1.+i*.02,segment=str(i//5),
                         current=40.,R_TJ=x,labels={'45':dict(value=41.+x@[.3,.9])}))
    lam=.1;model=fit_one(rows,'R_TJ',45,lam);w=balanced_weights(rows)
    X=np.array([r['R_TJ'] for r in rows]);X=(X-model['mean'])/model['scale'];y=np.array([r['labels']['45']['value']-40 for r in rows])
    A=np.column_stack([np.ones(len(rows)),X]);reg=np.diag([0,lam*w.sum(),lam*w.sum()])
    ref=np.linalg.solve(A.T@(w[:,None]*A)+reg,A.T@(w*y))
    np.testing.assert_allclose(np.r_[model['intercept'],model['coef']],ref,atol=1e-11)
    assert abs(sum(w)-1)<1e-12


def test_real_quality_timeline_never_bridges_ttl_or_restores_rejected_points():
    root=Path(os.environ.get('TTO_RESEARCH_RUN',Path(__file__).parents[1]/'runs/main'));data=read(root/'data.json')
    assert [r['accepted'] for r in data['runs']]==[2529,1610]
    assert [len(r['rejections']) for r in data['runs']]==[21,4]
    assert len({r['episode'] for r in data['runs']})==2
    for s in data['segments']:
        for a,b in zip(s['timeline'],s['timeline'][1:]):
            assert a['good'] and a['valid_until']>=b['t']-1e-9
            assert a['segment']==s['source_segment']
        assert all(r['control_eligible'] and not r['isolation'] for r in s['rows'])
    assert any(s['span_s']<60 and s['eligible_for_fit'] for s in data['segments'])
    assert any(s['source_segment']>5 and s['span_s']>180 for s in data['segments'])


def test_nuisance_affine_sensitivities_match_full_parameter_difference():
    spec=read(Path(__file__).parents[1]/'experiment-spec.json');p=[.18,.006,.002,.004,.09,.03]
    s=synthetic('G2',p,n=130);problem=FitProblem('G2',[s],spec);x=np.r_[p,25.,55.];base=problem.residual(x);g=problem.groups[0]
    u=g['u'].copy();u[:,:2]=0
    for k,E,init in [(6,1,[0,0]),(7,0,[0,1])]:
        changed=x.copy();changed[k]+=1
        expected=propagate('G2',p,E,g['dt'],u,init)[g['index'],0]
        np.testing.assert_allclose(problem.residual(changed)-base,expected,atol=1e-11)


def test_constant_power_has_distinct_indistinguishable_heat_coefficients():
    p=np.array([.18,.006,.002,.004,.09,.03]);q=p.copy();q[4]+=.03;q[5]-=.01
    u=np.tile([2,6,.2],(300,1));dt=np.ones(300)
    a=propagate('G2',p,25,dt,u,[48,55]);b=propagate('G2',q,25,dt,u,[48,55])
    assert not np.array_equal(p,q)
    np.testing.assert_allclose(a,b,atol=1e-12)
