"""Reuse exact accepted Linux310 dependency bytes; one observe candidate, no downloads."""
import argparse,json,hashlib,shutil,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--accepted-wheelhouse',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('fresh wheelhouse required')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((a.accepted_wheelhouse/'SHA256.json').read_text())
expected=json.loads((Path(__file__).resolve().parents[1]/'docs/dependency-lock.json').read_text())
if {n:h for n,h in m.items() if not n.startswith('tto_field_candidate-')}!=expected:raise SystemExit('not the frozen21 dependency identities')
with zipfile.ZipFile(a.candidate) as z:
 if json.loads(z.read('tto_field/candidate-files.json'))['version']!='0.2.4+observe.4':raise SystemExit('observe.4 candidate required')
if len(m)!=22:raise SystemExit('exact cpu.3 wheelhouse of22 expected')
for name,h in m.items():
 if sha(a.accepted_wheelhouse/name)!=h:raise SystemExit('dependency identity mismatch:'+name)
a.output.mkdir()
for name in m:
 if not name.startswith('tto_field_candidate-'):shutil.copy2(a.accepted_wheelhouse/name,a.output/name)
shutil.copy2(a.candidate,a.output/a.candidate.name)
(a.output/'SHA256.json').write_text(json.dumps({f.name:sha(f) for f in sorted(a.output.glob('*.whl'))},indent=2)+'\n')
print('one observe.4 candidate +21 unchanged locked dependencies')
