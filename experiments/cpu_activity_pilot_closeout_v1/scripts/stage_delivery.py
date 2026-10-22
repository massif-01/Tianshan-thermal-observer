"""Assemble only this closeout and the model-owned adapter, not historical archives/dependencies."""
from pathlib import Path
import shutil,hashlib,json
ROOT=Path('/Users/massif/Tianshan-thermal-observer');S=ROOT/'experiments/cpu_activity_pilot_closeout_v1';E=ROOT/'evidence/cpu-pilot-closeout-20261020';M=ROOT/'experiments/thermal_cpu_activity_bridge_v1'
D=Path('/private/tmp/tto-cpu2-closeout-delivery-20261020');D.mkdir(exist_ok=False)
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache','build','dist','*.egg-info','*current')
shutil.copytree(S,D/'source',ignore=ignore)
shutil.copytree(E,D/'field-evidence',ignore=shutil.ignore_patterns('candidate','*current','__pycache__','*.pyc'))
shutil.copytree(E/'candidate',D/'candidate',ignore=shutil.ignore_patterns('wheelhouse'))
shutil.copytree(M,D/'model-adapter',ignore=shutil.ignore_patterns('results','delivery','handoff','__pycache__','.pytest_cache','*.pyc','protected-before.json'))
for name in ['final-v2','joint-final-v2']:
 shutil.copytree(M/'results'/name,D/'model-adapter/results'/name,ignore=ignore)
shutil.copy2(ROOT/'deliverables/TTO-CPU旁录与分析衔接-收尾报告.md',D/'TTO-CPU旁录与分析衔接-收尾报告.md')
shutil.copy2(S/'docs/操作卡.md',D/'操作卡.md')
freeze=json.loads((D/'model-adapter/interface-freeze.json').read_text())
for name,digest in freeze['files'].items():assert hashlib.sha256((D/'model-adapter'/name).read_bytes()).hexdigest()==digest,name
print(D)
