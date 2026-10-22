"""Seal new identities and build offline artifacts; never re-label original field identity."""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    packages={}
    for base in (ROOT/'src',ROOT/'vendor'):
        for p in base.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json','.js','.css','.html') and p.name!='web-candidate-files.json':
                packages[str(p.relative_to(base))]=sha(p)
    model=ROOT/'vendor/tto_field/research/models/primary.json'
    identity=dict(version='1.0.0rc1',baseline='0.2.4+closeout.2; historical identity retained separately',frozen_model_sha256=sha(model),files=packages)
    (ROOT/'src/tto_web/web-candidate-files.json').write_text(json.dumps(identity,indent=2)+'\n')
    # Setuptools otherwise retains assets from earlier local frontend builds.
    if (ROOT/'build').exists():shutil.rmtree(ROOT/'build')
    subprocess.run([sys.executable,'-m','build','--wheel','--no-isolation'],cwd=ROOT,check=True)
    for wheel in (ROOT/'dist').glob('*.whl'):
        with zipfile.ZipFile(wheel) as z:
            actual={name for name in z.namelist() if '.dist-info/' not in name}
            expected=set(packages)|{'tto_web/web-candidate-files.json'}
            if actual!=expected:raise ValueError('wheel contains missing or unsealed files: '+str(actual^expected))
    wheelhouse=ROOT/'wheelhouse';wheelhouse.mkdir(exist_ok=True)
    for p in (ROOT/'dist').glob('*.whl'):shutil.copy2(p,wheelhouse/p.name)
    original=ROOT.parents[1]/'evidence/cpu-pilot-closeout-20261020/candidate/wheelhouse'
    for p in original.glob('*.whl'):
        if not p.name.startswith('tto_field_candidate'):shutil.copy2(p,wheelhouse/p.name)
    subprocess.run([sys.executable,'-m','pip','--cache-dir','/private/tmp/tto-web-pip-cache','download','--only-binary=:all:','-r',str(ROOT/'requirements.runtime.lock'),'-d',str(wheelhouse)],check=True)
    identity_files=[p for base in (wheelhouse,ROOT/'src',ROOT/'vendor',ROOT/'config',ROOT/'tools',ROOT/'frontend/src',ROOT/'requirements/contracts') for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    identity_files += [ROOT/'pyproject.toml',ROOT/'requirements.runtime.lock',ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json',ROOT/'baseline-identities.json']
    identities={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(identity_files))}
    (ROOT/'candidate-identities.json').write_text(json.dumps(identities,indent=2)+'\n')
    (ROOT/'evidence/build-receipt.json').write_text(json.dumps(dict(candidate_files=len(identities),wheel_files=len(list(wheelhouse.glob('*.whl'))),identity_files=len(packages),static_gzip_bytes=sum(__import__('gzip').compress(p.read_bytes()).__len__() for p in (ROOT/'src/tto_web/static').rglob('*') if p.is_file()),frozen_model_sha256=sha(model),model_spec_sha256=sha(ROOT/'vendor/tto_field/research/observer-spec.json')),indent=2)+'\n')

if __name__=='__main__':main()
