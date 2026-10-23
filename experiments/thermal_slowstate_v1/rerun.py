"""One local-only entry: prepare -> CPU research -> limited tests -> four figures -> readback."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).absolute().parent


def supports(exe,modules):
    if not Path(exe).exists():return False
    code='import '+','.join(modules)
    return subprocess.run([str(exe),'-c',code],capture_output=True).returncode==0


def choose(explicit,modules,candidates):
    if explicit:
        path=Path(explicit).absolute()  # Keep venv symlink identity; do not resolve().
        if supports(path,modules):return path
        raise SystemExit(f'{path} lacks required local modules {modules}')
    for exe in candidates:
        if supports(exe,modules):return Path(exe).absolute()
    raise SystemExit('No suitable existing local Python. See README; this entry never installs packages or uses the network.')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input-dir',type=Path,required=True,help='Directory containing the two original named R2 ZIPs')
    ap.add_argument('--python',type=Path)
    ap.add_argument('--plot-python',type=Path)
    args=ap.parse_args()
    repo_python=Path('/Users/massif/Tianshan-thermal-observer/.venv310/bin/python')
    runtime=choose(args.python,['numpy','scipy','pytest'],[Path(sys.executable),repo_python])
    plot=choose(args.plot_python,['numpy','matplotlib'],[runtime,Path('/private/tmp/tto-analysis-20261013-env/bin/python')])
    env=os.environ.copy()
    for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:env[k]='1'
    env['MPLCONFIGDIR']=str(ROOT/'build/mpl-cache')
    logs=ROOT/'replay-logs';logs.mkdir(exist_ok=True)
    stages=[('prepare',[runtime,ROOT/'prepare.py','--input-dir',args.input_dir.absolute()]),
            ('compute',[runtime,ROOT/'run_study.py']),
            ('tests',[runtime,'-m','pytest','-q',ROOT/'tests']),
            ('plots',[plot,ROOT/'plots.py']),
            ('readback',[runtime,ROOT/'verify_results.py']),
            ('report',[runtime,ROOT/'make_report.py'])]
    receipt=[]
    for label,cmd in stages:
        started=time.perf_counter()
        print(label,flush=True)
        with (logs/(label+'.log')).open('w') as f:
            result=subprocess.run([str(c) for c in cmd],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        receipt.append(dict(stage=label,exit_code=result.returncode,wall_seconds=time.perf_counter()-started))
        (logs/'receipt.json').write_text(json.dumps(dict(runtime=str(runtime),plot_runtime=str(plot),stages=receipt),indent=2)+'\n')
        if result.returncode:raise SystemExit(f'{label} failed; see {logs/(label+".log")}')
    print('Replay complete. Original inputs/models unchanged. No fitting, network or device actions.',flush=True)


if __name__=='__main__':main()
