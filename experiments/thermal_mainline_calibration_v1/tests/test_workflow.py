import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'baseline'))
sys.path.insert(0, str(ROOT/'tool/legacy'))
from tool.util import read, write, sha, load_bundle, validate_roles, load_job, create_bundle, parent_actual_fit_runs
from tool import registry
from g2_runtime import Predictor
import greybox
from initialize import rolling_state

BASE = ROOT/'baseline/frozen-model-manifest.json'
GEN = ROOT/'runs/generate/model-bundle/model-manifest.json'
CAL = ROOT/'runs/calibrate/model-bundle/model-manifest.json'
DEVICE = 'RM01-reference-LSM'
CONFIG = 'RM01-original-development-config-unverified-revision'


@pytest.fixture(scope='module')
def dataset():
    return read(ROOT/'inputs/dataset.json')


@pytest.fixture(scope='module')
def kernel(tmp_path_factory):
    greybox.build_kernel(tmp_path_factory.mktemp('kernel'))


def test_bundle_tampering_rejected(tmp_path):
    dest = tmp_path/'bundle';shutil.copytree(GEN.parent, dest)
    p = dest/'g2_runtime/frozen/primary.json'
    model = read(p);model['dynamic']['a'] *= 2;write(p, model)
    with pytest.raises(ValueError, match='checksum'):
        load_bundle(dest/'model-manifest.json')


def test_whole_run_seen_data_and_device_separation(dataset):
    for train, val, seen, device in [(['L'],['L'],True,DEVICE),(['L'],['S'],False,DEVICE),(['L'],['S'],True,'OTHER')]:
        with pytest.raises(ValueError):
            validate_roles(dataset,train,val,device_id=device,thermal_config_id=CONFIG,all_seen=seen)
    duplicate = copy.deepcopy(dataset)
    duplicate['runs'][1]['run_id'] = duplicate['runs'][0]['run_id']
    with pytest.raises(ValueError, match='duplicate run'):
        validate_roles(duplicate,['L'],['S'],device_id=DEVICE,thermal_config_id=CONFIG,all_seen=True)


def test_registry_manual_switch_only_new_sessions_and_rollback(tmp_path):
    root = tmp_path/'registry'
    registry.register(root,BASE,device_id=DEVICE,thermal_config_id=CONFIG)
    registry.register(root,GEN)
    assert registry.load(root)['selected_for_next_session'] == 'G2-FROZEN-RM01-v1'
    first = registry.open_session(root,'offline-session1')
    with pytest.raises(ValueError, match='confirm'):
        registry.select(root,'G2-GEN-L-20261021-v1',confirm=False,reason='not confirmed')
    registry.select(root,'G2-GEN-L-20261021-v1',confirm=True,reason='offline software test only')
    assert registry.open_session(root,'offline-session1') == first
    second = registry.open_session(root,'offline-session2')
    assert second['model_id'] == 'G2-GEN-L-20261021-v1'
    registry.select(root,'G2-FROZEN-RM01-v1',confirm=True,reason='offline rollback verification',action='rollback')
    assert registry.open_session(root,'offline-session2') == second
    assert registry.open_session(root,'offline-session3')['model_id'] == 'G2-FROZEN-RM01-v1'
    assert registry.load(root)['frozen_reference_model_id'] == 'G2-FROZEN-RM01-v1'
    with pytest.raises(ValueError, match='another device'):
        registry.register(root,CAL,device_id='OTHER',thermal_config_id=CONFIG)


def test_registry_cannot_replace_existing_model_id(tmp_path):
    root = tmp_path/'registry';registry.register(root,BASE,device_id=DEVICE,thermal_config_id=CONFIG)
    registry.register(root,GEN)
    other = tmp_path/'different';shutil.copytree(GEN.parent,other)
    obj = read(other/'model-manifest.json');obj['changed_metadata'] = True;write(other/'model-manifest.json',obj)
    with pytest.raises(ValueError, match='different bytes'):
        registry.register(root,other/'model-manifest.json')


def test_activation_requires_retained_frozen_rollback(tmp_path):
    root=tmp_path/'candidate-only'
    registry.register(root,GEN,device_id=DEVICE,thermal_config_id=CONFIG)
    with pytest.raises(ValueError,match='original frozen reference'):
        registry.select(root,'G2-GEN-L-20261021-v1',confirm=True,reason='offline test')


def test_inherited_C_kernel_matches_frozen_observer(kernel):
    p = Predictor();order=['a','c','d0','d1','b_g','b_c']
    theta=[p.model['dynamic'][k] for k in order]
    for h in [15,45,90]:
        for u in [[1.984,5.952,.17],[26.532,17.827,.66]]:
            expected=p.engine.mean_step([48.,43.,35.],u,h)
            got=greybox.propagate('G2',theta,35.,[h],[u],[48.,43.])[-1]
            assert np.max(abs(got-expected[:2])) < 1e-8


def test_actual_six_starts_and_parent_seed_training_only():
    parent=read(GEN.parent/'g2_runtime/frozen/primary.json')
    cal_spec=read(ROOT/'runs/calibrate/experiment-spec.json')
    assert cal_spec['initializations'][0] == dict(id='PARENT',G2=parent['dynamic'])
    for label in ['generate','calibrate']:
        result=read(ROOT/f'runs/{label}/result.json')
        attempts=[read(p) for p in (ROOT/f'runs/{label}/fits/G2').glob('N*.json')]
        if label=='calibrate': attempts += [read(ROOT/'runs/calibrate/fits/G2/PARENT.json')]
        assert len(attempts)==6 and all(x['actual_residual_calls']<=1500 for x in attempts)
        good=[a for a in attempts if a['finite'] and a['converged']]
        selected=min(good,key=lambda a:a['J'])
        assert selected['seed']==result['selected_seed']
        assert read(ROOT/f'runs/{label}/freeze-before-fit.json')['validation_not_used_for_initialization_or_selection']
        job=read(ROOT/f'runs/{label}/job-frozen.json')
        assert not set(job['train_runs']) & set(job['validation_runs'])
        for name,digest in job['fit_execution_code_sha256'].items():
            assert sha(ROOT/'verification/executed-fit-source'/name)==digest


def test_calibration_rejects_same_actual_process_under_new_alias(dataset,tmp_path):
    data=copy.deepcopy(dataset)
    data['runs'][0]['run']='renamed-L'
    path=tmp_path/'renamed-data.json';write(path,data)
    job=read(ROOT/'config/calibrate.json')
    job.update(dataset=str(path),dataset_sha256=sha(path),solver_spec=str(ROOT/'config/solver-spec.json'),train_runs=['renamed-L'])
    request=tmp_path/'job.json';write(request,job)
    with pytest.raises(ValueError,match='additional actual runs'):
        load_job(request,'calibrate',GEN)


def test_new_bundles_retain_actual_UUID_lineage(tmp_path):
    job=read(ROOT/'runs/generate/job-frozen.json')
    model=read(ROOT/'runs/generate/fits/G2/model.json')
    manifest=create_bundle(model,job,tmp_path/'bundle',parent_id=job['parent_model_id'],fit_report=read(ROOT/'runs/generate/result.json'))
    assert parent_actual_fit_runs(manifest)=={'929742d7-6f4d-4d80-b53e-4436d45ac12c'}
    assert manifest['validation_actual_run_ids']==['d2a7593a-e68a-4b6f-9d4d-875fafa73c02']
    unknown=dict(manifest);unknown.pop('parameter_fit_actual_run_ids');unknown['training_dataset_sha256']='unknown'
    with pytest.raises(ValueError,match='lineage unknown'):
        parent_actual_fit_runs(unknown)


def test_past60_state_invariant_to_future_temperatures_and_inputs(dataset,kernel):
    s=next(s for s in dataset['segments'] if s['run']=='S' and s['span_s']>100)
    i=next(i for i,r in enumerate(s['rows']) if r['t']-s['rows'][0]['t']>=70)
    cutoff=s['rows'][i]['t'];p=read(BASE.parent/'g2_runtime/frozen/primary.json')
    theta=[p['dynamic'][k] for k in ['a','c','d0','d1','b_g','b_c']]
    a,_=rolling_state('G2',theta,35.,s,i)
    changed=copy.deepcopy(s)
    for row in changed['rows']:
        if row['t']>cutoff:row['values']['tj']=999
    for n in changed['timeline']:
        if n['t']>cutoff:n['inputs']=[999,999,1.]
    b,_=rolling_state('G2',theta,35.,changed,i)
    assert np.max(abs(np.array(a)-b))<1e-8


def test_labels_independent_by_horizon_and_same_process(dataset):
    ids={r['run']:r['run_id'] for r in dataset['runs']}
    assert any(r['labels']['45'] and not r['labels']['90'] for r in dataset['examples'])
    for row in dataset['examples']:
        for h,lab in row['labels'].items():
            if lab:
                assert lab['ref'].startswith(ids[row['run']]+'/')
                assert row['t']+int(h)<=lab['t']<=row['t']+int(h)+2


def test_stationary_data_returns_insufficient_without_fitting(tmp_path):
    data=dict(schema='TTO-G2-MODELING-DATA-v1',runs=[dict(run=n,run_id=n,device_id=DEVICE,thermal_config_id=CONFIG,role='synthetic_software_fixture') for n in ['T','V']],
              segments=[dict(id='T-00',run='T',eligible_for_fit=True,rows=[dict(values=dict(tj=45.,vdd_gpu=2.,vdd_cpu_soc_mss=6.,duty=20))]*2)],examples=[],all_seen_development=True)
    data_path=tmp_path/'data.json';write(data_path,data)
    job=read(ROOT/'config/generate.json');job.update(dataset=str(data_path),dataset_sha256=sha(data_path),solver_spec=str(ROOT/'config/solver-spec.json'),
          train_runs=['T'],validation_runs=['V'],data_role='synthetic software fixture',model_id='G2-SYNTHETIC-INSUFFICIENT')
    path=tmp_path/'job.json';write(path,job)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run([sys.executable,'-m','tool','generate','--job',str(path),'--parent',str(BASE),'--output',str(tmp_path/'out')],cwd=ROOT,env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    result=read(tmp_path/'out/result.json')
    assert result['status']=='insufficient_excitation' and result['new_theta_fit'] is False
    assert not (tmp_path/'out/model-bundle').exists()
