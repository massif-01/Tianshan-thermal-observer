"""TTO-ID-R2-v1.0 sequential offline research CLI. No network or device entry points."""
import argparse
import os
import sys
from pathlib import Path
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[name]='1'
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor/v1'))
import hashlib
import shutil
import subprocess
import platform
import time
import numpy as np
import scipy
import sklearn
import psutil
from common import read,write,sha,stamp
import greybox
from data_views import index_evidence,strict_segments,make_examples
from scoring import evaluate,paired
from fitting import fit_A24,ridge_fit


def code_identity():
    core=[ROOT/n for n in ('research.py','replay_run.py','data_views.py','scoring.py','fitting.py')]
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted([*core,*ROOT.glob('vendor/**/*.py'),*ROOT.glob('vendor/**/*.c')])}


def old_identity():
    index=read(ROOT/'handoff/references/frozen-old-model-index.json')
    return {m['member']:sha(ROOT/'cache/greybox-v1-evidence'/m['member']) for m in index['models']}


def file_inventory(root): return {str(p.relative_to(root)):sha(p) for p in sorted(Path(root).rglob('*')) if p.is_file()}


def seal_valid(out):
    sealed=read(out/'stage2-frozen-evaluation.json')
    assert read(out/'stage2-complete.json')['seal_sha256']==sha(out/'stage2-frozen-evaluation.json')
    assert sealed['old_models']==old_identity()
    assert sealed['predictions_and_metrics']==file_inventory(out/'old-models-on-M')
    assert sealed['experiment_spec']==sha(out/'experiment-spec.json')
    assert sealed['registration']==sha(out/'stage1-frozen-registration.json')
    for f,h in read(out/'stage1-frozen-registration.json')['registered_files'].items(): assert sha(out/f)==h,f
    assert read(out/'stage1-frozen-registration.json')['computation_code']==code_identity()
    return sealed


def load_data(out):
    data=read(out/'registered/data.json'); examples=read(out/'registered/examples.json'); return data,examples


def old_models(label):
    code={'L-fit':'F-LS','S-fit':'F-SL','LS-fit':'F-POOL'}[label]; base=ROOT/'cache/greybox-v1-evidence/runs/main/fits'
    return {m:read(base/f'{code}-{m}/model.json') for m in ('G1','G2')},read(base/f'{code}-ridge.json')


def register(out):
    out.mkdir(parents=True,exist_ok=False); (out/'registered').mkdir()
    verified=subprocess.run([sys.executable,str(ROOT/'handoff/scripts/verify_handoff.py')],capture_output=True,text=True,check=True)
    (out/'handoff-verification.log').write_text(verified.stdout)
    template=read(ROOT/'handoff/templates/experiment-spec.json'); oldspec=read(ROOT/'handoff/references/greybox-v1-spec.json')
    assert template['stage3']['initializations']==oldspec['initializations']
    spec=dict(template,status='preregistered_before_old_M_scores',frozen_at=stamp(),models=oldspec['models'],fit=oldspec['fit'],ridge=oldspec['ridge'],initializations=oldspec['initializations'])
    spec['fit']['main_fits_max']=42
    spec['implementation_decisions']=dict(source_expiry='accepted_measurement_anchor_not_later_rejected_message',
        processors={'LS':'archived v1 validated processor; accepted values verified exactly','M':'22 manifest-SHA-matching source files'},
        labels='first same-source accepted TJ >=nominal h and <=h+2s; independent per horizon',
        ridge_training='current strict-segment origins; own TJ/IO past eligibility; legal future TJ labels need no future auxiliaries; whole strict-segment grouped CV',
        state='60s past only, first qualifying prefix calibrates E once/run; rank<1e-6 fallback median training E; later true breaks reinitialize state only',
        fair_joint_comparison='past prefix E calibration also for training runs; full-fit nuisance reconstruction reported separately',
        current_input='latest actual event power and successful PWM; no gain or 5V sum; unchanged TTL',
        context_unknown='unclassified_gap if unknown context; observed changes/flags never normal',
        M_phases='UTC join to actual phase markers; no reset at work/cooldown boundary')
    write(out/'experiment-spec.json',spec)
    evidence={}; segments=[]; coverage={}; examples=[]
    for label in ('L','S','M'):
        f=out/'registered'/f'evidence-{label}.json'
        process=subprocess.run([sys.executable,str(ROOT/'replay_run.py'),label,str(ROOT/'cache'),str(f)],capture_output=True,text=True,check=True)
        print(process.stdout.strip(),flush=True)
        (out/'registered'/f'replay-{label}.log').write_text(process.stdout+process.stderr)
        e=index_evidence(read(f)); assert e['run_id']==spec['run_ids'][label]
        if label=='M': assert all(e['source_matches_manifest'].values())
        ss,coverage[label]=strict_segments(e); evidence[label]=e; segments+=ss; examples+=make_examples(e,ss)
        write(out/'registered'/f'data-{label}.json',dict(segments=ss,samples=e['samples']))
    data=dict(segments=segments,accepted=[s for e in evidence.values() for s in e['samples']],runs=[{k:v for k,v in e.items() if k not in ('samples','nodes') and not k.startswith('_')} for e in evidence.values()])
    write(out/'registered/data.json',data); write(out/'registered/examples.json',examples)
    write(out/'registered/coverage.json',coverage); write(out/'coverage-M.json',coverage['M'])
    ambient=read(ROOT/'handoff/metadata/M-ambient-user-confirmed.json'); assert ambient['run_id']==spec['run_ids']['M'] and ambient['ambient_temperature_C']==24
    write(out/'ambient-addendum.json',ambient)
    write(out/'data-roles.json',dict(runs=spec['run_ids'],all_development=True,episodes=3,M_blocks_are_one_episode=True,stage2=spec['stage2'],stage3=spec['stage3']))
    source=dict(handoff=read(ROOT/'handoff/inputs/input-index.json'),old_models=read(ROOT/'handoff/references/frozen-old-model-index.json'),
                private_vs_share=read(ROOT/'cache/greybox-v1-evidence/runs/main/source-archives.json') if (ROOT/'cache/greybox-v1-evidence/runs/main/source-archives.json').exists() else read(ROOT/'cache/previous-exploration-evidence/results/private-original-run-index-verification.json'),
                M_outer=sha(ROOT/'handoff/inputs/M-midload-original.zip'),M_inner=sha(ROOT/'cache/M-midload-original/trial-result.zip'),
                data_processors={r:e['source_hashes'] for r,e in evidence.items()},processor_manifest_match={r:e['source_matches_manifest'] for r,e in evidence.items()})
    write(out/'source-inventory.json',source)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,
             cpu_count=os.cpu_count(),blas_threads=1,CUDA_used=False,device_access=False,git_commit_push_pr=False)
    write(out/'environment.json',env)
    protected=[*out.glob('*.json'),*out.glob('registered/*')]
    write(out/'stage1-frozen-registration.json',dict(completed_at=stamp(),old_models=old_identity(),computation_code=code_identity(),
                                                   registered_files={str(p.relative_to(out)):sha(p) for p in protected if p.is_file()}))
    print('REGISTERED / spec frozen',sha(out/'experiment-spec.json'), 'M strict segments',coverage['M']['segments'],flush=True)


def frozen(out):
    assert not (out/'stage2-frozen-evaluation.json').exists()
    stage1=read(out/'stage1-frozen-registration.json'); assert stage1['old_models']==old_identity(); assert stage1['computation_code']==code_identity()
    for f,h in stage1['registered_files'].items(): assert sha(out/f)==h
    data,examples=load_data(out); greybox.build_kernel(out/'build'); (out/'old-models-on-M').mkdir()
    for label in ('L-fit','S-fit','LS-fit'):
        artifacts,ridge=old_models(label); evaluate(label,['M'],artifacts,ridge,data,examples,out/'old-models-on-M'/label)
    seal=dict(completed_at=stamp(),old_models=old_identity(),experiment_spec=sha(out/'experiment-spec.json'),registration=sha(out/'stage1-frozen-registration.json'),
              predictions_and_metrics=file_inventory(out/'old-models-on-M'),training_performed=False)
    write(out/'stage2-frozen-evaluation.json',seal)
    write(out/'stage2-complete.json',dict(completed_at=stamp(),seal_sha256=sha(out/'stage2-frozen-evaluation.json')))
    print('SEALED STAGE2',sha(out/'stage2-frozen-evaluation.json'),flush=True)


def fit_combo(eid,runs,data,examples,spec,out):
    segments=[s for s in data['segments'] if s['run'] in runs]
    artifacts={m:greybox.fit(m,segments,spec,out/'fits'/f'{eid}-{m}')[0] for m in ('G1','G2')}
    ridge=ridge_fit(examples,runs,spec,out/'fits'/f'{eid}-ridge.json')
    return artifacts,ridge


def refit(out):
    seal_valid(out); assert not (out/'stage3-started.json').exists()
    write(out/'stage3-started.json',dict(started_at=stamp(),stage2_seal_sha256=sha(out/'stage2-frozen-evaluation.json')))
    data,examples=load_data(out); spec=read(out/'experiment-spec.json'); greybox.build_kernel(out/'build'); (out/'fits').mkdir(); (out/'evaluation').mkdir()
    directions={}
    for eid,runs in [('D-LM',['L','M']),('D-SM',['S','M'])]: directions[eid]=fit_combo(eid,runs,data,examples,spec,out)
    write(out/'directions-frozen.json',dict(frozen_at=stamp(),fits=file_inventory(out/'fits'),target_scores_not_computed=True))
    for eid,target,old in [('D-LM','S','L-fit'),('D-SM','L','S-fit')]:
        artifacts,ridge=directions[eid]; oa,orr=old_models(old)
        evaluate(eid,[target],artifacts,ridge,data,examples,out/'evaluation'/eid)
        evaluate(old,[target],oa,orr,data,examples,out/'evaluation'/f'{old}-on-{target}')
        paired(out/'evaluation'/f'{old}-on-{target}',out/'evaluation'/eid,out/'evaluation'/f'{eid}-paired.json')
    artifacts,ridge=fit_combo('D-LSM',['L','S','M'],data,examples,spec,out)
    oa,orr=old_models('LS-fit')
    evaluate('D-LSM',['L','S','M'],artifacts,ridge,data,examples,out/'evaluation/D-LSM')
    evaluate('LS-fit',['L','S','M'],oa,orr,data,examples,out/'evaluation/LS-fit-on-LSM')
    paired(out/'evaluation/LS-fit-on-LSM',out/'evaluation/D-LSM',out/'evaluation/D-LSM-paired.json')
    a24=fit_A24(data['segments'],spec,out/'fits/D-LSM-G2-A24')
    evaluate('D-LSM-G2-A24',['L','S','M'],{'G2':a24},ridge,data,examples,out/'evaluation/D-LSM-G2-A24',fixed_E={'M':24.})
    write(out/'stage3-complete.json',dict(completed_at=stamp(),stage2_unchanged=seal_valid(out)['completed_at'],fits=file_inventory(out/'fits'),
                                        nonlinear_attempts=42,directions_freeze_sha256=sha(out/'directions-frozen.json'),models_deployable=False))
    print('REFIT COMPLETED: 36 main + 6 A24 attempts',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('stage',choices=['register','frozen','refit','all']); parser.add_argument('--out',type=Path,default=ROOT/'runs/main'); args=parser.parse_args()
    started=time.perf_counter()
    for stage in ['register','frozen','refit'] if args.stage=='all' else [args.stage]: globals()[stage](args.out.resolve())
    write(args.out/'last-stage-resource.json',dict(stage=args.stage,elapsed_s=time.perf_counter()-started,peak_rss_current_MiB=psutil.Process().memory_info().rss/2**20,finished_at=stamp()))
