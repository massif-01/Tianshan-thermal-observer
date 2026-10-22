"""Reuses all accepted cpu.1 dependency bytes; adds only cpu.3 and pinned threadpoolctl3.6.0."""
import argparse,json,hashlib,shutil,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--accepted-wheelhouse',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--threadpool-wheel',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('fresh wheelhouse required')
manifest=json.loads((a.accepted_wheelhouse/'SHA256.json').read_text());h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
lock=json.loads((Path(__file__).parents[1]/'docs/dependency-increment.json').read_text())
if h(a.threadpool_wheel)!=lock['sha256']:raise SystemExit('threadpoolctl wheel SHA mismatch')
with zipfile.ZipFile(a.candidate) as z:
 if json.loads(z.read('tto_field/candidate-files.json'))['version']!='0.2.4+cpu.3':raise SystemExit('cpu.3 wheel required')
a.output.mkdir(parents=True)
for name,sha in manifest.items():
 f=a.accepted_wheelhouse/name
 if h(f)!=sha:raise SystemExit('accepted wheel SHA mismatch: '+name)
 if not name.startswith('tto_field_candidate-'):shutil.copy2(f,a.output/name)
for f in [a.candidate,a.threadpool_wheel]:shutil.copy2(f,a.output/f.name)
(a.output/'SHA256.json').write_text(json.dumps({f.name:h(f) for f in sorted(a.output.glob('*.whl'))},indent=2)+'\n');print('only cpu.3 candidate +21 locked dependencies, no upgrades')
