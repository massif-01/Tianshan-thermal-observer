"""Independent table recomputation, artifact replay and immutable-source audit."""
import sys
import os
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/v1'))
import numpy as np
from common import read,write,sha
from greybox import build_kernel,forecast,propagate
from initialize import rolling_state,path_between
from ridge_reference import predict
from research import seal_valid,old_models
from scoring import load_jsonl
from data_views import cohort_id


def independent_weights(rows):
    weight=np.zeros(len(rows));runs={r['run'] for r in rows if r['duration']>0}
    for run in runs:
        macros={r['macro'] for r in rows if r['run']==run and r['duration']>0}
        for macro in macros:
            idx=[i for i,r in enumerate(rows) if r['run']==run and r['macro']==macro];dt=np.array([rows[i]['duration'] for i in idx])
            weight[idx]=dt/dt.sum()/len(runs)/len(macros)
    return weight


def verify_metrics(table,rows,mode):
    methods=list(table['metrics']);context=table.get('context','all');field=table['scope'];value=table['value']
    cohort=[r for r in rows if r['label'] and (not table.get('h') or r['h']==table['h']) and
            all(m in r[mode] for m in methods) and
            (context=='all' or context=='strict_legacy' and r['strict_label'] or r['control_context']==context) and
            (field=='all' or r[field]==value)]
    assert table['cohort_id']==cohort_id(cohort)
    dt=np.array([r['duration'] for r in cohort]);weight=dt/dt.sum() if dt.sum() else np.ones(len(cohort))/len(cohort)
    balanced=independent_weights(cohort)
    for m,recorded in table['metrics'].items():
        err=np.array([r[mode][m]-r['label']['value'] for r in cohort]);under=np.maximum(-err,0)
        expected=dict(n=len(cohort),seconds=dt.sum(),mae=weight@abs(err),balanced_mae=balanced@abs(err),point_mae=np.mean(abs(err)),
                      rmse=np.sqrt(weight@(err**2)),p95_abs=np.percentile(abs(err),95),bias=weight@err,underprediction_p95=np.percentile(under,95),underprediction_max=under.max())
        for key,v in expected.items():assert abs(v-recorded[key])<1e-9,(m,key,v,recorded[key])


def artifacts_for(dest,out):
    if dest.parent.name=='old-models-on-M':return old_models(dest.name)
    if dest.name.endswith('-on-LSM'):return old_models('LS-fit')
    if dest.name.endswith('-on-L'):return old_models('S-fit')
    if dest.name.endswith('-on-S'):return old_models('L-fit')
    if dest.name=='D-LSM-G2-A24':return {'G2':read(out/'fits/D-LSM-G2-A24/model.json')},read(out/'fits/D-LSM-ridge.json')
    return {m:read(out/'fits'/f'{dest.name}-{m}/model.json') for m in ('G1','G2')},read(out/'fits'/f'{dest.name}-ridge.json')


def main(out,skip_workspace=False):
    seal_valid(out);before=read(ROOT/'protected-before.json')
    mismatches=[] if skip_workspace else [name for name,h in before.items() if not (ROOT.parents[1]/name).is_file() or sha(ROOT.parents[1]/name)!=h]
    assert not mismatches,mismatches
    stage2=read(out/'stage2-frozen-evaluation.json');stage3=read(out/'stage3-started.json');directions=read(out/'directions-frozen.json')
    assert stage2['completed_at']<stage3['started_at']<directions['frozen_at']
    attempts=[read(p) for p in (out/'fits').glob('*/N*.json')];assert len(attempts)==42
    assert all(a['finished_at']>stage3['started_at'] and a['actual_residual_calls']<=1500 for a in attempts)
    for eid in ('D-LM','D-SM'):assert read(out/'evaluation'/eid/'evaluation-identity.json')['evaluated_at']>directions['frozen_at']
    build_kernel(out/'build');data=read(out/'registered/data.json');ss={s['id']:s for s in data['segments']};examples={r['ref']:r for r in read(out/'registered/examples.json')}
    table_count=0;sample_count=0;max_error=0
    paths=[*list((out/'old-models-on-M').iterdir()),*[p for p in (out/'evaluation').iterdir() if p.is_dir()]]
    for dest in paths:
        rows=load_jsonl(dest/'predictions.jsonl');long=load_jsonl(dest/'A-long.jsonl')
        for filename,mode,source in [('B-metrics.json','B',rows),('A-roll-metrics.json','A',rows),('A-long-metrics.json','A',long)]:
            for table in read(dest/filename):verify_metrics(table,source,mode);table_count+=1
        artifacts,ridge=artifacts_for(dest,out);cal=read(dest/'calibrations.json')
        for row in rows[::137]:
            ex=examples[row['ref']];segment=ss.get(ex['segment'])
            for method in ('R_TJ','R_IO'):
                if method in row['B']:
                    got=predict(ridge['methods'][method][str(row['h'])],np.array(ex[method]),ex['current'])
                    max_error=max(max_error,abs(got-row['B'][method]));sample_count+=1
            if not segment or not ex['ready']:continue
            u=segment['timeline'][segment['rows'][ex['strict_i']]['timeline_index']]['inputs']
            for m,artifact in artifacts.items():
                p=np.array(list(artifact['dynamic'].values()));E=cal[m][segment['id']]['E'];state,ev=rolling_state(m,p,E,segment,ex['strict_i'],60)
                for scenario in ('HOLD','RELAX30'):
                    got=forecast(m,p,E,state,u,row['h'],scenario,artifact['P10_fit']);max_error=max(max_error,abs(got-row['B'][f'{m}-{scenario}']));sample_count+=1
                if m in row['A']:
                    dt,inputs=path_between(segment,row['t'],row['t']+row['h']);got=propagate(m,p,E,dt,inputs,state)[-1,0]
                    max_error=max(max_error,abs(got-row['A'][m]));sample_count+=1
    assert max_error<1e-10
    # Paired tables are independently assembled from matching origin/horizon/label triples.
    for eid,oldpath in [('D-LM','L-fit-on-S'),('D-SM','S-fit-on-L'),('D-LSM','LS-fit-on-LSM')]:
        paired=read(out/'evaluation'/f'{eid}-paired.json')
        for key,filename,mode in [('B','predictions.jsonl','B'),('A','predictions.jsonl','A'),('A-long','A-long.jsonl','A')]:
            old=load_jsonl(out/'evaluation'/oldpath/filename);new=load_jsonl(out/'evaluation'/eid/filename)
            lookup={(r['ref'],r['h'],r['label']['ref']):r for r in old if r['label']};combined=[]
            for row in new:
                if not row['label']:continue
                a=lookup.get((row['ref'],row['h'],row['label']['ref']))
                if a:
                    x=dict(row);x[mode]={**{'old:'+k:v for k,v in a[mode].items()},**{'new:'+k:v for k,v in row[mode].items()}};combined.append(x)
            for table in paired[key]:verify_metrics(table,combined,mode);table_count+=1
    receipt=dict(status='passed',protected_files_verified=0 if skip_workspace else len(before),workspace_integrity='producer_receipt_only' if skip_workspace else 'verified_locally',original_models_verified=9,stage_order_verified=True,real_fit_attempts=42,
                 converged_attempts=sum(a['converged'] for a in attempts),metric_tables_recomputed=table_count,
                 model_JSON_roundtrip_prediction_checks=sample_count,max_prediction_difference_C=max_error,control_authorization='none',deployed='not_performed')
    write(out/'readback-verification.json',receipt);print(receipt,flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--skip-workspace-integrity',action='store_true',help='For independent artifact replay when the original dirty author workspace is not present.')
    main(ROOT/'runs/main',parser.parse_args().skip_workspace_integrity)
