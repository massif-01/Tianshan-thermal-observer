"""Package only this preparation, not historical experiment trees."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path('/Users/massif/Tianshan-thermal-observer');S=ROOT/'experiments/cpu_activity_pilot_v1';E=ROOT/'evidence/cpu-activity-pilot-prep-20261019'
D=ROOT/'deliverables';staging=Path('/private/tmp/tto-cpu-pilot-delivery-20261019')
if staging.exists():raise SystemExit('fresh staging required')
staging.mkdir()
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache','build','dist','*.egg-info')
shutil.copytree(S,staging/'source',ignore=ignore)
for name in ('candidate','checks','inputs'):shutil.copytree(E/name,staging/name,ignore=ignore)
shutil.copy2(D/'TTO-CPU旁录与针对性补测-运行准备报告.md',staging/'TTO-CPU旁录与针对性补测-运行准备报告.md')
shutil.copy2(S/'docs/一页操作卡.md',staging/'一页操作卡.md')
files={str(p.relative_to(staging)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(staging.rglob('*')) if p.is_file()}
(staging/'SHA256.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')
output=D/'TTO-CPU旁录与针对性补测-运行准备证据包.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(staging.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(staging)))
print(json.dumps(dict(zip=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),indexed_files=len(files)),ensure_ascii=False,indent=2))
