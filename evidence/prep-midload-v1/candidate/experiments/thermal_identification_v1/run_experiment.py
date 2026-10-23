"""Reproducible offline entry point. Every fresh run requires a new output path."""
import os
for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[variable]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
import importlib.metadata
import platform
import resource
import shutil
import sys
import time
from pathlib import Path
from threadpoolctl import threadpool_limits,threadpool_info
from common import read,write,sha,stamp
from data_adapter import extract_inputs,prepare
from greybox import build_kernel,fit,FitProblem,solve
from ridge_reference import examples,fit_ridges


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--spec',type=Path,default=Path(__file__).with_name('experiment-spec.json'))
    parser.add_argument('--input-index',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stage',choices=['all','directions','finish'],default='all')
    args=parser.parse_args();out=args.output.resolve();start=time.perf_counter()
    if args.stage!='finish':
        out.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(args.spec,out/'experiment-spec.json')
        cache=extract_inputs(args.input_index,out);data=prepare(cache,out)
        write(out/'freeze.json',dict(frozen_at=stamp(),files={p:sha(out/p) for p in ['experiment-spec.json','data.json','coverage.json','roles.json','source-archives.json']},
                                     source_files={p.name:sha(p) for p in Path(__file__).parent.glob('*') if p.suffix in ('.py','.c')},note='before first real-data numerical fit'))
        write(out/'environment.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),machine=platform.machine(),
              dependencies={p:importlib.metadata.version(p) for p in ['numpy','scipy','scikit-learn','threadpoolctl','pytest']},
              threadpools=threadpool_info(),CUDA=False,device_access=False,N305_benchmark=False))
    else:
        data=read(out/'data.json')
        frozen=read(out/'freeze.json')
        assert all(sha(out/p)==h for p,h in frozen['files'].items())
        assert (out/'directions-frozen.json').exists()
        assert not (out/'evaluation').exists(), 'Never overwrite an existing evaluation'
    spec=read(out/'experiment-spec.json');build_kernel(out/'kernel')
    with threadpool_limits(limits=1):
        rows=examples(data)
        if args.stage!='finish':
            bench=FitProblem('G2',[s for s in data['segments'] if s['run']=='L'],spec)
            t=time.perf_counter();bench.residual(bench.initial(spec['initializations'][0]))
            write(out/'residual-timing.json',dict(seconds=time.perf_counter()-t,n_samples=len(bench.rows),parameters=len(bench.names)))
            for eid,run in [('F-LS','L'),('F-SL','S')]:
                selected=[s for s in data['segments'] if s['run']==run]
                for model in ('G1','G2'):
                    fit(model,selected,spec,out/'fits'/f'{eid}-{model}')
                fit_ridges(rows,[run],spec,out/'fits'/f'{eid}-ridge.json')
            files=list((out/'fits').rglob('model.json'))+list((out/'fits').glob('*ridge.json'))
            write(out/'directions-frozen.json',dict(frozen_at=stamp(),files={str(p.relative_to(out)):sha(p) for p in files},no_target_candidate_scores_computed=True))
        if args.stage in ('all','finish'):
            from evaluation import evaluate_experiment
            from diagnostics import run_diagnostics
            (out/'evaluation').mkdir()
            for eid,target in [('F-LS',['S']),('F-SL',['L'])]:evaluate_experiment(eid,target,data,rows,out)
            for model in ('G1','G2'):fit(model,data['segments'],spec,out/'fits'/f'F-POOL-{model}')
            fit_ridges(rows,['L','S'],spec,out/'fits'/'F-POOL-ridge.json')
            pool=read(out/'fits/F-POOL-G2/model.json');problem=FitProblem('G2',data['segments'],spec)
            solve(problem,__import__('numpy').array(pool['x']),'nested-d1-zero',out/'fits/nested-d1-zero.json',fixed_d1=True)
            evaluate_experiment('F-POOL',['L','S'],data,rows,out)
            run_diagnostics(data,rows,spec,out)
            write(out/'status.json',dict(implementation='complete',numeric_fit='complete',response_evaluation='complete',causal_forecast='complete_development_replay',target_validation='not_performed',control_authorization='none',deployable=False))
        write(out/f'resource-{args.stage}.json',dict(wall_s=time.perf_counter()-start,ru_maxrss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                rss_unit='bytes' if sys.platform=='darwin' else 'KiB',thread_limit=1,finished_at=stamp()))


if __name__=='__main__':main()
