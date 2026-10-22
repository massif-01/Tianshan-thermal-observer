"""Install this candidate into a NEW isolated Linux x86_64 CPython3.10 directory. Never alters old TTO.
This script is for future separately authorized installation, or an owned disposable target container.
"""
import argparse,json,platform,subprocess,sys,venv,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--wheelhouse',type=Path,required=True);a=p.parse_args()
if sys.version_info[:2]!=(3,10) or platform.system()!='Linux' or platform.machine()!='x86_64':raise SystemExit('Target installer requires Linux x86_64 CPython3.10')
if a.prefix.exists():raise SystemExit('Refusing existing prefix; old installation is preserved')
manifest=json.loads((a.wheelhouse/'SHA256.json').read_text())
for name,expected in manifest.items():
 b=(a.wheelhouse/name).read_bytes()
 if hashlib.sha256(b).hexdigest()!=expected:raise SystemExit('Wheel identity mismatch: '+name)
wheels=list(a.wheelhouse.glob('tto_field_candidate-*.whl'))
if len(wheels)!=1:raise SystemExit('Exactly one candidate wheel required')
venv.EnvBuilder(with_pip=True).create(a.prefix)
python=a.prefix/'bin/python'
subprocess.run([str(python),'-I','-m','pip','install','--no-index','--find-links',str(a.wheelhouse),str(wheels[0])],check=True)
verified=subprocess.run([str(python),'-I','-m','tto_field.cli','verify-install','--target'],check=True,capture_output=True,text=True)
(a.prefix/'installation-identity.json').write_text(verified.stdout)
print(verified.stdout)
print('Installed in independent directory; no collection, inference, system service or control changes were started.')
