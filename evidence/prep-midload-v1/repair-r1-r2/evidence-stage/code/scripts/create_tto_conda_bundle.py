#!/usr/bin/env python3
"""Build a standalone Conda installer zip for one already-built TTO wheel."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def build(source, output, trial_site_config=None):
    source = Path(source).resolve()
    output = Path(output).resolve()
    pyproject = (source / 'pyproject.toml').read_text()
    version = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', pyproject).group(1)
    wheel = source / 'wheels' / f'tianshan_thermal_observer-{version}-py3-none-any.whl'
    if not wheel.is_file():
        raise FileNotFoundError('candidate wheel missing: ' + str(wheel))
    import tempfile
    with tempfile.TemporaryDirectory(prefix='tto-conda-bundle-', dir='/private/tmp') as tmp:
        stage = Path(tmp) / f'TTO-v1-{version}-Conda安装包'
        stage.mkdir()
        def copy(rel):
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, dst)
        for rel in ('install.sh', 'requirements-locked.txt', 'config/tto.example.json',
                    'scripts/install_tto.py', 'docs/TTO测试者使用说明.md',
                    'docs/TTO第一次测试操作卡.md', 'docs/platform-curve-v2-contract.md', 'README.md'):
            copy(rel)
        copy(Path('wheels') / wheel.name)
        trial_dir = source / 'scripts/thermal_trials'
        if trial_dir.is_dir():
            for path in sorted(trial_dir.iterdir()):
                if path.suffix in ('.py', '.json', '.md'):
                    copy(path.relative_to(source))
            for name in ('TTO中等负载测试操作卡.md', 'TTO中等负载候选安装说明.md'):
                copy(Path('docs') / name)
        if trial_site_config is not None:
            (stage / 'site').mkdir()
            shutil.copy2(trial_site_config, stage / 'site/local-midload.json')
        names = [str(path.relative_to(stage)) for path in sorted(stage.rglob('*')) if path.is_file()]
        manifest = {'installer_version': 3, 'version': version, 'environment_manager': 'conda',
                    'files': {name: sha(stage / name) for name in names}}
        manifest_path = stage / 'install-manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(str(output))
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    archive.write(path, stage.name + '/' + str(path.relative_to(stage)))
        manifest_sha = sha(manifest_path)
    print(json.dumps({'version': version, 'bundle': str(output), 'sha256': sha(output),
                      'wheel_sha256': sha(wheel), 'manifest_sha256': manifest_sha},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument('--output', required=True)
    parser.add_argument('--trial-site-config', help='本地私有测试配置，只写入候选包，不写入公共模板')
    args = parser.parse_args()
    build(args.source, args.output, args.trial_site_config)
