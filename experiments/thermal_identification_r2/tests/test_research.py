import copy
import json
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.linalg import expm

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/v1'))
from common import read,balanced_weights
from greybox import build_kernel,propagate,matrices,FitProblem
from initialize import estimate,rolling_state
from data_views import target_label,interval_context,index_evidence,cohort_id
from research import seal_valid,old_identity
from fitting import solve_bound
from scoring import evaluate


@pytest.fixture(scope='session',autouse=True)
def kernel(tmp_path_factory): build_kernel(tmp_path_factory.mktemp('kernel'))


def synthetic(n=181):
    p=[.18,.006,.002,.004,.09,.03];ts=np.arange(n,dtype=float)
    u=np.column_stack([5+20*((ts//17)%2),6+8*((ts//31)%2),.15+.6*((ts//43)%2)])
    y=propagate('G2',p,24,np.diff(ts),u[:-1],[48,55])[:,0]
    rows=[dict(t=float(t),mono_s=float(t),ref=str(i),timeline_index=i,values=dict(tj=y[i]),run='M',macro='work',duration=1 if i<n-1 else 0,
               utc=str(i),phase='M20',regime='midload',wall=float(t)) for i,t in enumerate(ts)]
    return dict(id='M-00',run='M',rows=rows,timeline=[dict(t=float(t),inputs=u[i].tolist()) for i,t in enumerate(ts)],
                span_s=float(n-1),eligible_for_fit=True),p


@pytest.mark.parametrize('model,p',[('G1',[.3,.2,.1,.04]),('G2',[.18,.006,.002,.004,.09,.03]),('G2',[4,1,1,1,5,5])])
def test_exact_cpu_propagation(model,p):
    for dt in (.000001,.7,90):
        u=[25,17,.73];A,f=matrices(model,p,24,u);n=len(A);M=np.zeros((n+1,n+1));M[:n,:n]=A;M[:n,-1]=f
        exact=(expm(M*dt)@np.r_[[48,55][:n],1])[:n]
        np.testing.assert_allclose(propagate(model,p,24,[dt],[u],[48,55])[-1,:n],exact,rtol=1e-10,atol=1e-9)


def test_prefix_and_rolling_state_do_not_read_future_TJ():
    s,p=synthetic();a=estimate('G2',p,s,60,60,E=None,E_fallback=24);r=rolling_state('G2',p,24,s,100)
    for row in s['rows'][101:]:row['values']['tj']+=50
    assert rolling_state('G2',p,24,s,100)==r
    for row in s['rows'][61:]:row['values']['tj']+=50
    assert estimate('G2',p,s,60,60,E=None,E_fallback=24)==a


def test_A24_binding_is_removed_from_solver_variables(tmp_path):
    s,p=synthetic(91);spec=read(ROOT/'handoff/references/greybox-v1-spec.json');problem=FitProblem('G2',[s],spec)
    seed={'id':'synthetic-not-real-matrix','G2':dict(zip(problem.dynamic,p))}
    result=solve_bound(problem,seed,tmp_path/'synthetic.json',{'E_M':24})
    assert result['parameters']['E_M']==24
    assert 'E_M' not in result['optimized_parameter_names']
    assert result['free_parameter_count']==len(problem.names)-1
    assert set(result['parameters'])==set(problem.names)


def fake_evidence():
    samples=[dict(t=float(i),ref=str(i),target_valid=True,source_epoch=0,source_identity='same',values=dict(tj=40+i/10)) for i in range(61)]
    nodes=[dict(t=float(i),ref=str(i),complete=True,valid_until=i+1,observed_abnormal_or_changed=False,context_known=True) for i in range(61)]
    return index_evidence(dict(samples=samples,nodes=nodes))


def test_future_aux_gap_keeps_label_and_marks_gap():
    e=fake_evidence();e['nodes'][20]['complete']=False
    label,reason=target_label(e,e['samples'][0],45)
    assert label['ref']=='45' and reason is None
    assert interval_context(e,0,45)==dict(complete=False,control_context='aux_observation_gap',reasons=['20:input_or_aux_context_gap'])
    assert interval_context(e,0,15)['complete']


def test_abnormal_unknown_recovery_and_source_isolation():
    e=fake_evidence();e['nodes'][20]['complete']=False;e['nodes'][20]['observed_abnormal_or_changed']=True
    assert interval_context(e,0,45)['control_context']=='observed_abnormal_or_changed'
    assert interval_context(e,21,45)['control_context']=='confirmed_normal'
    e['nodes'][20]['observed_abnormal_or_changed']=False;e['nodes'][20]['context_known']=False
    assert interval_context(e,0,45)['control_context']=='unclassified_gap'
    e['samples'][45]['source_epoch']=1
    assert target_label(e,e['samples'][0],45)[1]=='source_identity_or_validity_boundary'


def test_horizons_and_common_identity_are_independent():
    e=fake_evidence();o=e['samples'][0]
    assert target_label(e,o,45)[0] is not None
    assert target_label(e,o,90)[0] is None
    r=dict(ref='a',h=45,label={'ref':'b'});assert cohort_id([r])!=cohort_id([dict(r,h=90)])


def test_balanced_weights_preserve_background_and_runs():
    rows=[dict(run=r,macro=m,duration=d) for r in ['L','M'] for m in ['work','background','recovery'] for d in [1,100]]
    w=balanced_weights(rows);assert abs(w.sum()-1)<1e-15
    for run in ['L','M']:
        for macro in ['work','background','recovery']:assert abs(sum(v for v,r in zip(w,rows) if r['run']==run and r['macro']==macro)-1/6)<1e-15


def test_registration_M_identity_no_phase_resets_and_expiry():
    r=ROOT/'runs/main';e=read(r/'registered/evidence-M.json');coverage=read(r/'coverage-M.json');ambient=read(r/'ambient-addendum.json')
    assert e['run_id']==ambient['run_id']=='637f114b-563b-4c35-8062-a7588a89ce1c'
    assert ambient['ambient_temperature_C']==24 and e['override_used_for_qualification'] is False
    assert all(e['source_matches_manifest'].values())
    assert len(coverage['segments'])==2
    assert {'M20','M60','M180'}<=set(coverage['segments'][0]['phases'])
    samples={s['ref']:s for s in e['samples']}
    for n in e['nodes']:
        if n['power_ref']:assert n['source_until']==samples[n['power_ref']]['source_valid_until']
    assert set(read(r/'experiment-spec.json')['stage3']['ambient_diagnostic']['fixed_E'])=={'M'}


def test_old_artifacts_match_predeclared_index():
    actual=old_identity();index=read(ROOT/'handoff/references/frozen-old-model-index.json')
    assert len(actual)==9
    assert actual=={m['member']:m['sha256'] for m in index['models']}


def test_ambient_nulls_and_phase_order_are_preserved():
    raw=[json.loads(x) for x in (ROOT/'cache/M-trial/events.jsonl').read_text().splitlines()]
    ambient=[r for r in raw if r['event']=='ambient_snapshot']
    assert len(ambient)==14 and all(r['record']['temperature_c'] is None for r in ambient)
    out=ROOT/'runs/main';seal_valid(out)
    s2=read(out/'stage2-frozen-evaluation.json');s3=read(out/'stage3-started.json');directions=read(out/'directions-frozen.json')
    assert s2['completed_at']<s3['started_at']<directions['frozen_at']
    assert all(read(out/'evaluation'/eid/'evaluation-identity.json')['evaluated_at']>directions['frozen_at'] for eid in ('D-LM','D-SM'))


@pytest.mark.parametrize('eid,runs',[('D-LM',{'L','M'}),('D-SM',{'S','M'}),('D-LSM',{'L','S','M'})])
def test_refit_identity_ridge_scaling_and_horizon_training(eid,runs):
    out=ROOT/'runs/main';spec=read(out/'experiment-spec.json');examples=read(out/'registered/examples.json')
    index={r['ref']:r for r in examples};ridge=read(out/'fits'/f'{eid}-ridge.json')
    for model in ('G1','G2'):
        artifact=read(out/'fits'/f'{eid}-{model}/model.json')
        assert set(artifact['fit_runs'])==runs and artifact['deployable'] is False
        if model=='G2':assert {k for k in artifact['parameters'] if k.startswith('Ts_M')}=={'Ts_M-00','Ts_M-01'}
    for method,heads in ridge['methods'].items():
        assert heads['45']['n']>heads['90']['n']
        for h,head in heads.items():
            rows=[index[r] for r in head['training_refs']];assert set(r['run'] for r in rows)<=runs
            assert len(head['columns'])==(9 if method=='R_TJ' else 15)
            assert head['lambda_'] in [.01,.1,1,10]
            w=balanced_weights(rows);X=np.array([r[method] for r in rows]);mean=np.average(X,axis=0,weights=w)
            np.testing.assert_allclose(mean,head['mean'],rtol=1e-12,atol=1e-12)
            assert abs(head['alpha']-head['lambda_']*w.sum())<1e-12


def test_all_real_starts_and_A24_freedom_are_accounted_for():
    out=ROOT/'runs/main';attempts=list((out/'fits').glob('*/N*.json'));assert len(attempts)==42
    for f in attempts:
        a=read(f);assert a['actual_residual_calls']<=1500
        if 'A24' in str(f):assert a['parameters']['E_M']==24 and 'E_M' not in a['optimized_parameter_names']
    free=read(out/'fits/D-LSM-G2/model.json');bound=read(out/'fits/D-LSM-G2-A24/model.json')
    assert free['parameter_count']==bound['parameter_count']+1
    assert bound['extra_offset_or_heat_input'] is False


def test_stage3_cannot_start_before_stage2_seal(tmp_path):
    with pytest.raises(FileNotFoundError):seal_valid(tmp_path)


def test_future_inputs_affect_A_but_not_B_and_labels_only_future_TJ(tmp_path):
    s,p=synthetic();g1=dict(model='G1',dynamic=dict(zip(['k0','k1','b_g','b_c'],[.03,.08,.08,.03])),parameters={'E_X':24},P10_fit=[2,6],input_min=[0,0],input_max=[40,30],u_range=[0,1])
    g2=dict(g1,model='G2',dynamic=dict(zip(['a','c','d0','d1','b_g','b_c'],p)))
    head=dict(mean=[0]*9,scale=[1]*9,coef=[0]*9,intercept=0,min=[-100]*9,max=[100]*9)
    ridge={'methods':{'R_TJ':{str(h):head for h in (15,45,90)},'R_IO':{}}}
    a=s['rows'][80];row={k:a[k] for k in ('run','ref','utc','wall','macro','phase','regime','duration')}
    row.update(segment=s['id'],t=80.,current=a['values']['tj'],R_TJ=np.zeros(9),R_IO=None,slope=.1,ready=True,strict_i=80,source_valid=True,
               labels={str(h):dict(value=s['rows'][80+h]['values']['tj'],ref=str(80+h),t=80+h) for h in (15,45,90)},
               label_rejections={str(h):None for h in (15,45,90)},contexts={str(h):'confirmed_normal' for h in (15,45,90)},
               A_eligible={str(h):True for h in (15,45,90)},strict_labels={str(h):True for h in (15,45,90)})
    before,_=evaluate('test',['M'],{'G1':g1,'G2':g2},ridge,{'segments':[s]},[row],tmp_path/'before')
    changed=copy.deepcopy(s)
    for n in changed['timeline'][81:]:n['inputs'][0]+=10
    for a in changed['rows'][81:]:a['values']['tj']+=20;a['phase']='future_task_ends_early'
    changed_row=copy.deepcopy(row)
    for l in changed_row['labels'].values():l['value']+=20
    after,_=evaluate('test',['M'],{'G1':g1,'G2':g2},ridge,{'segments':[changed]},[changed_row],tmp_path/'after')
    for a,b in zip(before,after):
        assert a['B']==b['B']
        assert a['A']!=b['A']
        assert b['label']['value']==a['label']['value']+20
