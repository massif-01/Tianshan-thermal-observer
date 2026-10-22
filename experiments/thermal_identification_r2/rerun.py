"""Explicit independent rerun in a new directory; never overwrite author outputs."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--handoff',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True)
parser.add_argument('--plot-python',type=Path)
args=parser.parse_args();dest=args.destination.resolve();dest.mkdir(parents=True,exist_ok=False)
for file in [*root.glob('*.py'),root/'README-R2.md',root/'protected-before.json']:
    shutil.copy2(file,dest/file.name)
for name in ('vendor','tests'):shutil.copytree(root/name,dest/name,ignore=shutil.ignore_patterns('__pycache__'))
def run(script,*arguments,python=None):subprocess.run([str(python or sys.executable),str(dest/script),*arguments],cwd=dest,check=True)
run('bootstrap.py','--handoff',str(args.handoff.resolve()))
run('research.py','register')
run('monitor_stage.py','frozen');run('monitor_stage.py','refit')
run('diagnose.py');run('readback.py','--skip-workspace-integrity')
with (dest/'runs/main/final-tests.log').open('w') as log:
    subprocess.run([sys.executable,'-m','pytest','-q',str(dest/'tests')],cwd=dest,stdout=log,stderr=subprocess.STDOUT,check=True)
if args.plot_python:run('plots.py',python=args.plot_python.absolute())
run('make_report.py')
print('Completed independent fixed-matrix rerun:',dest)
