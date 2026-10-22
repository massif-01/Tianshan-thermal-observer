"""Finite contracts: exact frozen kernel, causal initialization, gaps, real identity and no false comparison."""
from pathlib import Path
import copy,json,sys,os
import numpy as np
import pytest
from scipy.linalg import expm
ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor'))
from common import read,sha
import greybox
from initialize import estimate
from trajectories import qualified_support
from refprep.clocks import align_time

@pytest.fixture(scope='module',autouse=True)
def kernel(tmp_path_factory):greybox.build_kernel(tmp_path_factory.mktemp('kernel'))

@pytest.mark.parametrize('name',['primary','old_LS','A24'])
def test_frozen_kernel_matches_independent_affine_exponential(name):
    model=read(ROOT/'models'/(name+'.json'));p=[model['dynamic'][k] for k in ['a','c','d0','d1','b_g','b_c']]
    state=np.array([46.,42.]);u=np.array([12.,9.,.2]);E=35.
    for dt in [1e-4,1.,60.,300.]:
        A,f=greybox.matrices('G2',p,E,u);M=np.zeros((3,3));M[:2,:2]=A;M[:2,2]=f
        expected=(expm(M*dt)@np.r_[state,1.])[:2]
        actual=greybox.propagate('G2',p,E,[dt],[u],state)[-1]
        assert np.max(abs(actual-expected))<1e-10
    assert not model['deployable']


def test_original_prefix_estimation_is_past_only_not_external_state_correction():
    m=read(ROOT/'models/primary.json');p=[m['dynamic'][k] for k in ['a','c','d0','d1','b_g','b_c']]
    times=np.arange(121,dtype=float);u=np.array([[8+3*(i%3),7,.2] for i in range(120)],float)
    states=greybox.propagate('G2',p,35.,np.ones(120),u,[46.,42.])
    rows=[dict(mono_s=float(t),ref='SYNTHETIC-TEST-'+str(i),values=dict(tj=float(states[i,0]))) for i,t in enumerate(times)]
    segment=dict(rows=rows,timeline=[dict(t=float(t),inputs=u[min(i,119)].tolist()) for i,t in enumerate(times)])
    first=estimate('G2',p,segment,60,60,E=None,E_fallback=35)
    changed=copy.deepcopy(segment)
    for row in changed['rows']:
        if row['mono_s']>60:row['values']['tj']+=100
    second=estimate('G2',p,changed,60,60,E=None,E_fallback=35)
    assert first==second and abs(first['E']-35)<1e-7 and abs(first['Ts_initial']-42)<1e-7
    assert first['end']==60 and first['last_ref']=='SYNTHETIC-TEST-60'


def test_support_does_not_bridge_an_abnormal_or_expired_input():
    def n(t,good,expiry):return dict(t=t,complete=good,valid_until=expiry,source_epoch=1,segment=1,ref=str(t))
    nodes=[n(0,True,2),n(1,False,3),n(1.5,True,2),n(3,True,4),n(4,False,4)]
    intervals=qualified_support(nodes)
    assert [(x['start'],x['end']) for x in intervals]==[(0,1),(1.5,2),(3,4)]


def test_unknown_clock_precision_never_becomes_a_photo_offset():
    session=dict(run_id='new',time=dict(clock_domain='instrument_local_datetime',timezone=None,sync_anchors=[]))
    rec=dict(run_id='new',clock_domain='instrument_local_datetime',measured_at_raw='2026-10-18T00:34:04',time_uncertainty_s=None)
    assert align_time(rec,session)['interval_utc_s'] is None
    rec['temperature_c']=999
    assert align_time(rec,session)['status']=='unaligned_clock'
    assert read(ROOT/'spec.json')['clock']['offset_sensitivity_s']==[-30,-10,-5,0,5,10,30]
    assert read(ROOT/'spec.json')['ambient_C'] is None


def test_actual_dataset_has_no_eligible_prefix_and_keeps_independent_horizon_answers():
    path=Path(os.environ.get('TTO_YET_TEST_DATA_PATH',str(ROOT/'data.json')))
    if not path.exists():pytest.skip('real data is supplied to the standalone run output')
    d=read(path)
    assert d['run_id']=='1ae9a7d7-bec7-4e45-a9d6-4415b4a8dece'
    assert len(d['samples'])==1843 and len(d['segments'])==352
    assert max(s['span_s'] for s in d['segments'])<60
    assert not d['execution_policy_used_for_model_qualification']
    assert all(not n['complete'] for n in d['nodes'] if n['observed_abnormal_or_changed'])
    assert any(x['labels']['45'] is not None and x['labels']['90'] is None for x in d['examples'])
    result=path.parent/'results'
    if (result/'comparison-summary.json').exists():
        summary=read(result/'comparison-summary.json')
        assert summary['actual_surface_records']==2027 and summary['actual_CSV_mapping_verified']
        assert summary['strict_model_states']=={'primary':0,'old_LS':0,'A24':0}
        assert summary['strict_clock_qualified_points']==0
        assert summary['frozen_model_initialization_attempts']==1056
        assert all(v=={} for v in read(result/'calibrations.json').values())


def test_frozen_identities_still_exact():
    expected=read(ROOT/'source-identity.json')
    for name,h in expected['frozen_models'].items():assert sha(ROOT/'models'/name)==h
    for name,h in expected['vendor_files'].items():assert sha(ROOT/name)==h
