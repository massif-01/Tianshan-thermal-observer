"""Limited algorithm and real-file replay checks, not a product/device test suite."""
from pathlib import Path
import copy
import json
import sys
import numpy as np
import pytest
from scipy.linalg import expm

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vendor'))
from core import qs, lp_step, filters_at_origins, shape, reversal_count, BRANCHES
from prepare import read, jsonlines, digest
from greybox import build_kernel, propagate, matrices, forecast
from initialize import rolling_state, path_between


@pytest.fixture(scope='session')
def real():
    build_kernel(ROOT / 'build/tests')
    data = read(ROOT / 'sources/registered/data.json')
    model = read(ROOT / 'sources/models/primary.json')
    p = [model['dynamic'][k] for k in ['a','c','d0','d1','b_g','b_c']]
    states = jsonlines(ROOT / 'results/states-causal60.jsonl')
    return data, model, p, states


def test_irregular_left_hold_and_qs():
    assert lp_step(10, 20, 0, 30) == 10
    assert lp_step(10, 20, 13, 30) == pytest.approx(20-10*np.exp(-13/30))
    p = [.1,.02,.003,.004,.03,.05]
    q = qs(50,24,.4,p)
    assert p[1]*(50-q)+(p[2]+p[3]*.4)*(24-q) == pytest.approx(0,abs=1e-14)
    segment = dict(rows=[dict(ref=str(t),mono_s=t,values={'tj':40+t}) for t in [0.,1.5,8.]],
                   timeline=[dict(t=t,inputs=[2,6,.2]) for t in [0.,1.5,2.7,8.]])
    a=filters_at_origins(segment,24,p)
    assert a['1.5']['STATE-LP30']==a['0.0']['STATE-QS']
    assert a['8.0']['STATE-LP30']==pytest.approx(lp_step(a['0.0']['STATE-QS'],a['1.5']['STATE-QS'],6.5,30))
    mutated=copy.deepcopy(segment)
    mutated['rows'][-1]['values']['tj']=120
    mutated['timeline'][-1]['inputs']=[50,25,1.]
    mutated['future_request_end']=999
    b=filters_at_origins(mutated,24,p)
    assert a['0.0']==b['0.0'] and a['1.5']==b['1.5']


def test_demand_fixed_limits_amplitude_and_hysteresis():
    first=shape(45,45,0,0)
    assert first['z_output']==0
    assert shape(.2,0,0,1)['deadband']
    assert shape(45.199,45,0,1)['deadband']
    rising=shape(65,45,0,1.7)
    assert rising['z_raw']==2 and rising['z_target']==1
    assert rising['z_output']==pytest.approx(1.7/30)
    falling=shape(44,45,1,3.2)
    assert falling['z_raw']<0 and falling['z_target']==0
    assert falling['z_output']==pytest.approx(1-3.2/120)
    # Gradual falls smaller than 0.02 per step must still count as a reversal.
    vals=list(np.linspace(0,.3,101))+list(np.linspace(.3,.1,101))+list(np.linspace(.1,.4,101))
    assert reversal_count(vals)==2
    assert reversal_count([0,0,0,0])==0
    assert len({json.dumps(shape(48,43,.2,1.03),sort_keys=True) for _ in BRANCHES})==1


def test_exact_cpu_propagation_against_expm(real):
    _,_,p,_=real
    E=34.9
    dts=np.array([.01,1.7,7.93,30.4])
    inputs=np.array([[2,6,.18],[30,16,.4],[4,7,.2],[10,9,.3]])
    out=propagate('G2',p,E,dts,inputs,[46,42])
    z=np.array([46.,42.,1.])
    for i,(d,u) in enumerate(zip(dts,inputs)):
        A,f=matrices('G2',p,E,u)
        M=np.zeros((3,3));M[:2,:2]=A;M[:2,2]=f
        z=expm(M*d)@z
        assert np.max(abs(out[i+1]-z[:2]))<1e-10


def test_real_past60_state_does_not_read_future(real):
    data,model,p,states=real
    for run in ['L','S','M']:
        chosen=[s for s in states if s['model']=='primary' and s['run']==run][90]
        seg=next(s for s in data['segments'] if s['id']==chosen['segment'])
        idx=next(i for i,r in enumerate(seg['rows']) if r['ref']==chosen['ref'])
        before,_=rolling_state('G2',p,chosen['E'],seg,idx)
        mut=copy.deepcopy(seg)
        for r in mut['rows'][idx+1:]:r['values']['tj']=119.
        for n in mut['timeline']:
            if n['t']>chosen['t']:n['inputs']=[99,88,1.]
        mut['future_requests']=[dict(start=chosen['t']+1,end=chosen['t']+2)]
        after,_=rolling_state('G2',p,chosen['E'],mut,idx)
        assert before==after
        assert before[0]==chosen['Tf']
        assert before[1]==pytest.approx(chosen['Ts'],abs=1e-10)
        fa=filters_at_origins(seg,chosen['E'],p)[chosen['ref']]
        fb=filters_at_origins(mut,chosen['E'],p)[chosen['ref']]
        assert fa==fb
        demand_a={b:shape(v,40,.2,1.1) for b,v in fa.items()}
        demand_b={b:shape(v,40,.2,1.1) for b,v in fb.items()}
        assert demand_a==demand_b
        assert forecast('G2',p,chosen['E'],before,np.array(chosen['current_inputs']),45,'HOLD',model['P10_fit'])==forecast(
            'G2',p,chosen['E'],after,np.array(chosen['current_inputs']),45,'HOLD',model['P10_fit'])
        # A-roll is explicitly allowed to use changed future input (but no future TJ).
        if seg['rows'][-1]['mono_s']>chosen['t']+45:
            dt1,u1=path_between(seg,chosen['t'],chosen['t']+45)
            dt2,u2=path_between(mut,chosen['t'],chosen['t']+45)
            assert abs(propagate('G2',p,chosen['E'],dt1,u1,before)[-1,0]-
                       propagate('G2',p,chosen['E'],dt2,u2,after)[-1,0])>1


def test_two_dimensional_export_and_anchor_not_forecast(real):
    _,_,_,states=real
    long=jsonlines(ROOT/'results/states-A-long.jsonl')
    checks=read(ROOT/'results/replay-checks.json')
    assert all(c['max_abs_Tf_replay_error_C']<=1e-10 for c in checks)
    assert all(r['Tf']==r['sealed_Tf'] for r in long)
    assert sum(abs(r['Tf']-r['Ts'])>.5 for r in long)>.8*len(long)
    assert all(s['Tf_is_observation_anchor'] and not s['parameter_learning'] for s in states)
    assert all(s['evidence']['end']<=s['t']+1e-9 for s in states)
    assert all(s['state_truth_available'] is False for s in states+long)


def test_model_and_original_members_hash_unchanged():
    inv=read(ROOT/'source-inventory.json')
    for item in inv:
        if item['kind']=='member':
            assert digest((ROOT/item['copied_to']).read_bytes())==item['sha256']
    freeze=read(ROOT/'stage1-freeze.json')
    assert digest((ROOT/'slowstate-spec.json').read_bytes())==freeze['spec_sha256']
    for name,sha in freeze['models'].items():
        assert digest((ROOT/f'sources/models/{name}.json').read_bytes())==sha


def test_same_cohort_and_independent_horizons():
    points=jsonlines(ROOT/'results/four-branch-predictions.jsonl')
    check=read(ROOT/'results/ablation-replay-check.json')
    assert check['A_roll_max_replay_error_C']<=1e-10 and check['B_HOLD_max_replay_error_C']<=1e-10
    partial=0
    byref={}
    for row in points:
        byref.setdefault(row['ref'],{})[row['h']]=row
        for kind in ['A_roll','B_HOLD']:
            assert not row[kind] or set(row[kind])==set(BRANCHES)
    for rows in byref.values():
        if rows[45]['label'] is not None and rows[90]['label'] is None:
            partial+=1
    assert partial>0
    metrics=read(ROOT/'results/temperature-metrics.json')
    assert all(len({m['n'] for m in r['metrics'].values()})==1 for r in metrics)
    assert all(r['n']==r['metrics']['STATE-G2']['n'] for r in metrics)


def test_M_work_blocks_keep_slow_state_and_qualification(real):
    data,_,_,states=real
    model_states=[r for r in states if r['model']=='primary' and r['run']=='M']
    run=next(r for r in data['runs'] if r['run']=='M')
    for phase in [p for p in run['phases'] if p['macro']=='work']:
        a=[r for r in model_states if phase['start']-5<=r['wall']<=phase['start']+5]
        assert len(a)>=8 and {r['segment'] for r in a}=={'M-00'}
        assert all(r['t']-r['evidence']['start']>58 for r in a)
    assert {r['segment'] for r in model_states}=={'M-00','M-01'}


def test_fast_risk_is_immediate_and_demand_never_extended():
    ledger=jsonlines(ROOT/'results/fast-status-and-demand-ledger.jsonl')
    rows={r['ref']:r for r in jsonlines(ROOT/'results/normal-demand-origins.jsonl')}
    bad=[r for r in ledger if r['fast_status']['observed_abnormal_or_changed'] or r['fast_status']['temp_stale'] is True]
    assert bad
    assert all(r['normal_extra_demand_index'] is None and not r['ordinary_available'] for r in bad)
    assert all(r['normal_extra_demand_index'] is None for r in ledger if r['event']=='known_input_expiry')
    for r in ledger:
        if r['ordinary_available']:
            d=rows[r['shape_ref']]
            assert d['t']<=r['t'] and d['source_epoch']==r['fast_status']['source_epoch']
            assert r['t']<r['current_input_valid_until']
            assert set(r['normal_extra_demand_index'])==set(BRANCHES)


def test_expiry_keeps_fast_TJ_and_tail_bins_do_not_overcount():
    ledger=jsonlines(ROOT/'results/fast-status-and-demand-ledger.jsonl')
    expiry=[r for r in ledger if r['event']=='known_input_expiry']
    assert expiry
    kept=[r for r in expiry if r['measured_TJ_valid']]
    assert kept and all(r['measured_TJ'] is not None and r['normal_extra_demand_index'] is None for r in kept)
    tails=read(ROOT/'results/post-task-tail-metrics.json')
    for row in tails:
        if row['status']=='unavailable_at_end':
            assert row['branches'] is None
            continue
        for label,value in row['bins'].items():
            lo,hi=map(float,label[:-1].split('-'))
            assert value['available_seconds']<=hi-lo+1e-7


def test_sensitivity_is_frozen_and_not_a_Ts_accuracy_claim():
    rows=read(ROOT/'results/frozen-model-state-sensitivity.json')
    assert all(r['no_per_segment_recentring'] for r in rows)
    assert all(r['Tf_difference'] is None for r in rows if r['mode']=='causal60')
    init=read(ROOT/'results/prefix-and-unit-initialization-sensitivity.json')
    assert all(r['no_refit'] and r['prefix_is_not_equilibrium'] for r in init)
    assert read(ROOT/'results/resources.json')['optimization_runs']==0


def test_signal_scale_not_an_actuator_and_gaps_not_joined():
    rows=jsonlines(ROOT/'results/normal-demand-origins.jsonl')
    previous={}
    for r in rows:
        for b,v in r['branches'].items():
            assert 0<=v['z_output']<=1
            assert v['z_target']==max(0,min(1,v['z_raw']))
            assert -v['dt_s']/120-1e-12<=v['change']<=v['dt_s']/30+1e-12
        if r['segment'] not in previous:
            assert all(v['z_output']==0 and v['dt_s']==0 for v in r['branches'].values())
        previous[r['segment']]=r
        assert not r['deployable'] and r['reference_is_not_equilibrium']
    metrics=read(ROOT/'results/demand-signal-metrics.json')
    assert all(m['branches'][b]['z_output']['amplitude'] is not None for m in metrics for b in BRANCHES
               if m['branches'][b]['available_seconds']>0)
