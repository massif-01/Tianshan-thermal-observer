"""Build a fresh offline observe/Web bundle; keep their Python environments separate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'work/webui-v1'
BACKEND = ROOT / 'experiments/mainline_observe_v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args, cwd=ROOT):
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or Path(str(output) + '.zip').exists():
        raise SystemExit('fresh output and ZIP required; preserve existing candidates')
    version = tomllib.loads((WEB / 'pyproject.toml').read_text())['project']['version']
    backend_version = tomllib.loads((BACKEND / 'pyproject.toml').read_text())['project']['version']
    sealed = json.loads((WEB / 'candidate-identities.json').read_text())
    dependencies = [p for p in (WEB / 'wheelhouse').glob('*.whl') if not p.name.startswith('tto_web_ui-')]
    for dependency in dependencies:
        if sha(dependency) != sealed['wheelhouse/' + dependency.name]:
            raise SystemExit('Web dependency identity mismatch: ' + dependency.name)
    run('npm', 'run', 'build', cwd=WEB / 'frontend')
    packages = {str(p.relative_to(base)): sha(p)
                for base in (WEB / 'src', WEB / 'vendor') for p in sorted(base.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts
                and p.suffix in ('.py', '.json', '.js', '.css', '.html', '.md')
                and p.name != 'web-candidate-files.json'}
    manifest = dict(version=version, baseline='observe.5 committed ledger + main frontend time labels',
                    frozen_model_sha256=sha(WEB / 'vendor/tto_field/research/models/primary.json'),
                    frontend='rc7: backend forecast IDs and expiry; fixed target/issued time', files=packages)
    (WEB / 'src/tto_web/web-candidate-files.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Build in a disposable source tree so setuptools cannot retain old static assets.
    output.mkdir(parents=True)
    build = output / '.web-build'
    build.mkdir()
    for name in ('src', 'vendor'):
        shutil.copytree(WEB / name, build / name, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(WEB / 'pyproject.toml', build / 'pyproject.toml')
    run(sys.executable, '-m', 'build', '--wheel', '--no-isolation', cwd=build)
    wheel = next((build / 'dist').glob('*.whl'))
    with zipfile.ZipFile(wheel) as archive:
        actual = {n for n in archive.namelist() if '.dist-info/' not in n}
        assert actual == set(packages) | {'tto_web/web-candidate-files.json'}
        for name, digest in packages.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
    web = output / 'web'
    (web / 'wheelhouse').mkdir(parents=True)
    shutil.copy2(wheel, web / 'wheelhouse' / wheel.name)
    shutil.rmtree(build)
    # Both supported wheel platforms are already frozen locally; no dependency download.
    for dependency in dependencies:
        shutil.copy2(dependency, web / 'wheelhouse' / dependency.name)
    (web / 'tools').mkdir()
    shutil.copy2(WEB / 'tools/install.py', web / 'tools/install.py')
    shutil.copytree(WEB / 'config', web / 'config')
    shutil.copy2(WEB / 'requirements.runtime.lock', web / 'requirements.runtime.lock')
    identities = {str(p.relative_to(web)): sha(p) for p in sorted(web.rglob('*')) if p.is_file()}
    (web / 'candidate-identities.json').write_text(json.dumps(identities, indent=2) + '\n')
    run(sys.executable, BACKEND / 'scripts/build_wheel.py')
    backend = output / 'backend'
    backend.mkdir()
    run(sys.executable, BACKEND / 'scripts/assemble_wheelhouse.py',
        '--accepted-wheelhouse', ROOT / 'evidence/cpu-runtime-threads-20261020/target-wheelhouse-release',
        '--candidate', BACKEND / f'dist/tto_field_candidate-{backend_version}-py3-none-any.whl',
        '--output', backend / 'wheelhouse')
    shutil.copy2(BACKEND / 'scripts/install_candidate.py', backend / 'install_candidate.py')
    shutil.copy2(ROOT / 'tools/install_unified_candidate.py', output / 'install.py')
    shutil.copy2(ROOT / 'docs/统一候选安装与短测.md', output / 'README.md')
    receipt = dict(backend_version=backend_version, web_version=version,
                   git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   source_tree_may_include_uncommitted_changes=True,
                   web_manifest_sha256=sha(WEB / 'src/tto_web/web-candidate-files.json'),
                   backend_manifest_sha256=sha(BACKEND / 'src/tto_field/candidate-files.json'))
    (output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    identities = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'SHA256.json').write_text(json.dumps(identities, indent=2) + '\n')
    shutil.make_archive(str(output), 'zip', output.parent, output.name)
    print(json.dumps(dict(bundle=str(output), zip_sha256=sha(Path(str(output) + '.zip')))))


if __name__ == '__main__':
    main()
