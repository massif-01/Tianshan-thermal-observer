"""Reuse accepted cpu.1 dependency bytes in a fresh wheelhouse; replace only the candidate."""
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--accepted-wheelhouse',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('new directory required')
old=json.loads((a.accepted_wheelhouse/'SHA256.json').read_text());a.output.mkdir(parents=True)
for name,sha in old.items():
 data=(a.accepted_wheelhouse/name).read_bytes()
 if hashlib.sha256(data).hexdigest()!=sha:raise SystemExit('accepted wheel identity mismatch: '+name)
 if not name.startswith('tto_field_candidate-'):shutil.copy2(a.accepted_wheelhouse/name,a.output/name)
shutil.copy2(a.candidate,a.output/a.candidate.name)
(a.output/'SHA256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.glob('*.whl')},indent=2)+'\n')
print('copied existing dependencies; exactly one new candidate, no upgrades')
