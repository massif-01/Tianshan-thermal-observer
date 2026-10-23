"""Finite regressions for the new offline evaluator; upstream algorithms remain frozen."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_study import Dynamics,PhysicalPath,target_label,read,ROOT
import numpy as np
from scipy.integrate import solve_ivp


def test_affine_propagation_matches_independent_solver():
    spec=read(ROOT/'vendor/src/tto_field/research/observer-spec.json')
    dyn=Dynamics(spec);p=dyn.p;u=[12.,21.,.35];x=[61.,47.,33.]
    def rhs(_,z):
        return [p['a']*(z[1]-z[0])+p['b_g']*u[0]+p['b_c']*u[1],
                p['c']*(z[0]-z[1])-(p['d0']+p['d1']*u[2])*(z[1]-z[2]),0]
    truth=solve_ivp(rhs,[0,90],x,rtol=1e-11,atol=1e-12).y[:,-1]
    assert np.max(abs(dyn.step(x,u,90)-truth))<1e-8


def test_future_label_horizons_independent_and_no_nearest_before():
    def row(t):return dict(t=t,source_valid=True,epoch=1,source_key=['a','b'],ref=str(t),current=40+t,phase='x')
    ss=[row(t) for t in (0,14.9,15.8,45.4)];times=[a['t'] for a in ss]
    label,_=target_label(ss,times,ss[0],15)
    assert label['ref']=='15.8'
    assert target_label(ss,times,ss[0],45)[0]['ref']=='45.4'
    assert target_label(ss,times,ss[0],90)[0] is None
    ss[3]['epoch']=2
    assert target_label(ss,times,ss[0],45)[1]=='source_identity_or_validity_boundary'


def test_actual_path_never_fills_gap_with_fresh_recovery():
    dyn=Dynamics(read(ROOT/'vendor/src/tto_field/research/observer-spec.json'))
    nodes=[dict(t=0.,until=2.5,u=[2.,3.,.2],epoch=1),dict(t=4.,until=10.,u=[99.,99.,1.],epoch=1),dict(t=6.,until=12.,u=[2.,3.,.2],epoch=1)]
    path=PhysicalPath(nodes,dyn)
    assert path.pieces(0,6) is None
    assert path.pieces(4,6) is not None
    nodes[1]['until']=6.;nodes[1]['epoch']=2
    assert path.pieces(0,4.5) is None


def test_known_path_matrix_and_single_branch_match():
    dyn=Dynamics(read(ROOT/'vendor/src/tto_field/research/observer-spec.json'))
    nodes=[dict(t=0.,until=3.,u=[2.,3.,.2],epoch=1),dict(t=1.,until=4.,u=[12.,5.,.4],epoch=1),dict(t=2.,until=5.,u=[2.,3.,.2],epoch=1)]
    path=PhysicalPath(nodes,dyn);pieces=path.pieces(0,2)
    a=[50.,43.,35.];b=[60.,46.,32.]
    allx=path.propagate([a,b],pieces)
    assert np.max(abs(allx[0]-path.propagate(a,pieces)))<1e-12
    assert np.max(abs(allx[1]-path.propagate(b,pieces)))<1e-12


def test_first_invalid_label_is_not_skipped_for_a_later_better_answer():
    ss=[dict(t=t,source_valid=valid,epoch=1,source_key=['a','b'],ref=str(t),current=40.,phase='x')
        for t,valid in ((0,True),(45.1,False),(45.9,True))]
    assert target_label(ss,[a['t'] for a in ss],ss[0],45)==(None,'target_source_invalid')


def test_actual_csv_keeps_equal_adjacent_samples_and_original_dates():
    import csv
    from run_study import lines
    raw=list(csv.DictReader((ROOT/'inputs/instrument/imported/original-csv/26071081-20261019173740.csv').read_text().splitlines()[30:]))
    normalized=list(lines(ROOT/'inputs/instrument/imported/normalized/records.jsonl'))
    assert len(raw)==len(normalized)==2984
    assert sum(a['CH1']==b['CH1'] for a,b in zip(raw,raw[1:]))==1119
    assert [float(a['CH1']) for a in raw]==[a['temperature_c'] for a in normalized]
    assert normalized[0]['measured_at_raw']=='2026-10-19T17:37:40'
    assert all(a['time_uncertainty_s'] is None and not a['model_input'] for a in normalized)
