"""Offline candidate build/staging. Preserve Sonnet sources and all sealed rc3 artifacts."""
import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='1.0.0rc5'
STAGE=ROOT/'candidate-rc5'
ACTIVE_TOOLS=('build_history_candidate.py','install.py','verify_final_archive.py',
    'history_source.py','history_service.py','history_view.html','history_view.js',
    'history_allocation.py','history_resource_monitor.py','audit_history_equivalence.py',
    'browser_history_checks.js','browser_history_D_regression.js')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    wheel=ROOT/f'dist/tto_web_ui-{VERSION}-py3-none-any.whl'
    if STAGE.exists() or wheel.exists():
        raise SystemExit('candidate stage or wheel already exists; preserve the sealed artifacts')
    old=ROOT/'dist/tto_web_ui-1.0.0rc3-py3-none-any.whl'
    assert sha(old)=='5f4c9fe5f28e8ab892c83b1309f8b91ad8d6e828489f116f17c4f67c8a35b910'
    with zipfile.ZipFile(old) as z:
        for n in z.namelist():
            if n.startswith('tto_web/static/'):assert (ROOT/'src'/n).read_bytes()==z.read(n), 'static frontend differs; preserve and resolve ownership before packaging'
    packages={str(p.relative_to(base)):sha(p) for base in (ROOT/'src',ROOT/'vendor') for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json','.js','.css','.html','.md') and p.name!='web-candidate-files.json'}
    manifest=dict(version=VERSION,baseline='0.2.4+closeout.2; historical identity retained separately',frozen_model_sha256=sha(ROOT/'vendor/tto_field/research/models/primary.json'),frontend='sealed rc3 static assets; Sonnet redesign not included',files=packages)
    (ROOT/'src/tto_web/web-candidate-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if (ROOT/'build').exists():shutil.rmtree(ROOT/'build')
    subprocess.run([sys.executable,'-m','build','--wheel','--no-isolation'],cwd=ROOT,check=True)
    wheel=ROOT/f'dist/tto_web_ui-{VERSION}-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as z:
        assert {n for n in z.namelist() if '.dist-info/' not in n}==set(packages)|{'tto_web/web-candidate-files.json'}
        for n,digest in packages.items():assert hashlib.sha256(z.read(n)).hexdigest()==digest
    STAGE.mkdir()
    for name in ('src','vendor','config','tests','requirements'):
        shutil.copytree(ROOT/name,STAGE/name,ignore=shutil.ignore_patterns('__pycache__'))
    # Ship active reproduction/installation tools; historical rc1/rc2/rc3 tools
    # remain in their sealed releases rather than becoming alternate rc5 entrypoints.
    (STAGE/'tools').mkdir()
    for name in ACTIVE_TOOLS:shutil.copy2(ROOT/'tools'/name,STAGE/'tools'/name)
    for name in ('pyproject.toml','requirements.runtime.lock','baseline-identities.json','TTO-WebUI-模型状态历史序列-实施与验收方案-v1.0.md'):
        shutil.copy2(ROOT/name,STAGE/name)
    (STAGE/'wheelhouse').mkdir()
    for p in (ROOT/'wheelhouse').glob('*.whl'):
        if not p.name.startswith('tto_web_ui-'):shutil.copy2(p,STAGE/'wheelhouse'/p.name)
    shutil.copy2(wheel,STAGE/'wheelhouse'/wheel.name)
    identities={str(p.relative_to(STAGE)):sha(p) for d in ('src','vendor','config','tools','tests','requirements','wheelhouse') for p in (STAGE/d).rglob('*') if p.is_file()}
    for name in ('pyproject.toml','requirements.runtime.lock','baseline-identities.json'):identities[name]=sha(STAGE/name)
    (STAGE/'candidate-identities.json').write_text(json.dumps(identities,indent=2)+'\n')
    receipt=dict(version=VERSION,wheel=wheel.name,wheel_bytes=wheel.stat().st_size,wheel_sha256=sha(wheel),package_files=len(packages),installer_files=len(identities),static_from_rc3=True,no_frontend_build=True,offline=True)
    (ROOT/'evidence/self-review-rc5/build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
