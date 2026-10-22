#!/usr/bin/env python3
"""Build a synthetic-only review package from explicitly selected deliverables."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True); a = p.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = Path(a.output).resolve()
    simulation = json.loads((root/'evidence/simulation/SIMULATION-ONLY.json').read_text())
    if simulation.get('simulated') is not True:
        raise ValueError('package allows fixed synthetic evidence only')
    out = output.parent
    out.mkdir(parents=True, exist_ok=True)
    selected = ['src', 'tests', 'scripts', 'config/tto.example.json', 'templates/deployment-record.example.json', 'wheels', 'requirements-locked.txt', 'pyproject.toml', '.gitignore', 'README.md', 'PROGRESS.md', 'TTO-v1-实施与验证报告.md', 'docs/TTO-PLAN-v1.0.md', 'docs/contracts.md', 'docs/CLI使用卡.md', 'evidence/final', 'evidence/simulation', 'evidence/reference-identities.json', 'evidence/wheel-build.txt', 'evidence/independent-wheel-install.txt', 'evidence/final-candidate-replay.txt', 'evidence/linux-wheel-resolution.txt', 'evidence/browser-snapshot.txt', 'evidence/browser-requests-final.txt', 'evidence/browser-console.txt', 'output/playwright']
    failures = ['phase-b-first-setup-failure.txt','phase-b-first-regression.txt','demo-first.txt','signals-first.txt','python310-lock-collision.txt','final-tests-python310-v3.txt','browser-open-first.txt','browser-open.txt']
    with tempfile.TemporaryDirectory(prefix='tto-package-') as tmp:
        base = Path(tmp)/'TTO-v1'; base.mkdir()
        for item in selected:
            src, dst = root/item, base/item
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache','*.egg-info'))
            else:
                shutil.copy2(src, dst)
        (base/'evidence/failures').mkdir()
        for name in failures:
            shutil.copy2(root/'evidence'/name, base/'evidence/failures'/name)
        (base/'evidence/failures/README.md').write_text('这些是旧失败/过程日志，不是最终验收。正式候选身份与61项独立重跑见evidence/final；模拟数据不是实机收益。\n')
        files = {str(f.relative_to(base)): sha(f) for f in sorted(base.rglob('*')) if f.is_file()}
        manifest = {'artifact':'TTO-v1-implementation-evidence','schema_version':1,'real_device_data_included':False,'fixed_simulation_included':True,'test_count':61,'dependencies':'pinned requirements; prepare via local wheelhouse or package download, verification itself is offline','replay':'python scripts/reproduce_offline.py --output NEW_DIRECTORY (non-editable installed wheel required)','files':files}
        (base/'bundle-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        (base/'checksums.sha256').write_text(''.join(f'{hash_}  {name}\n' for name,hash_ in files.items()))
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for f in sorted(base.rglob('*')):
                if f.is_file():
                    archive.write(f,str(f.relative_to(base.parent)))
    print(json.dumps({'output':str(output),'sha256':sha(output),'bytes':output.stat().st_size},ensure_ascii=False))


if __name__ == '__main__':
    main()
