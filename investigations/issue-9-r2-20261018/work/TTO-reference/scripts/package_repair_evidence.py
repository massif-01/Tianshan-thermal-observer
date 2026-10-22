#!/usr/bin/env python3
"""New repair candidate only; original candidate stays historical."""
import argparse, hashlib, json, shutil, tempfile, zipfile
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent;output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    identity=json.loads((root/'evidence/repair-v1/delivery/identity.json').read_text());wheel=root/'wheels'/identity['wheel']
    assert digest(wheel)==identity['wheel_sha256']
    for name,h in identity['files'].items():assert digest(root/'src/tto'/name)==h,name
    with tempfile.TemporaryDirectory(prefix='tto-repair-package-') as tmp:
        base=Path(tmp)/'TTO-v1-R1-R4';base.mkdir()
        def copy(name):
            src=root/name;dst=base/name;dst.parent.mkdir(parents=True,exist_ok=True)
            if src.is_dir():shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache','*.egg-info'))
            else:shutil.copy2(src,dst)
        for name in ('src','tests','config/tto.example.json','templates/deployment-record.example.json','pyproject.toml','requirements-locked.txt','.gitignore','README.md','PROGRESS.md','TTO-v1-R1-R4返修与验证报告.md'):copy(Path(name))
        for name in ('reproduce_offline.py','verify_signals.py','benchmark_offline.py','verify_r1_r4.py','package_repair_evidence.py'):copy(Path('scripts')/name)
        for name in ('contracts.md','CLI使用卡.md','R1-R4-repair-contract.md','TTO-PLAN-v1.0.md'):copy(Path('docs')/name)
        copy(wheel.relative_to(root));copy(Path('evidence/repair-v1/delivery'))
        for name in ('identity.json','files-sha256.json','git-status.txt','tracked.diff','model-probes.json','model-probes.log','ws-redirect.json','ws-redirect.stderr','original61-tests.txt','junit-original61.xml','r4-failing-tests.txt'):copy(Path('evidence/repair-v1/before')/name)
        for name in ('wheel-build-release.txt','install-release.txt','clean-dependencies.txt','release-replay.txt','r4-protocol-tests.txt','r1-model-tests.txt','r1-r2-tests-first.txt','full-tests-first.txt','markdown-render-check.json','markdown-format-before.txt','markdown-format-after.txt'):copy(Path('evidence/repair-v1/after')/name)
        review=Path('evidence/repair-v1/review-original')
        for name in ('TTO-v1-R1-R4有限修复-Codex执行指令.md','TTO-v1-全链路独立复审.md'):copy(review/name)
        for name in ('README.md','scripts','results'):copy(review/'TTO-v1-review'/name)
        for name in ('shadow-final.png','layered-final.png'):copy(Path('output/playwright/repair')/name)
        for manifest in (base/'evidence/repair-v1/delivery').rglob('manifest.json'):assert json.loads(manifest.read_text()).get('simulated') is True
        files={str(p.relative_to(base)):digest(p) for p in sorted(base.rglob('*')) if p.is_file()}
        m={'schema_version':1,'repair_contract':'TTO-REPAIR-v1.0','version':identity['version'],'wheel_sha256':identity['wheel_sha256'],'test_count':81,'real_data_included':False,'original_candidate_binary_included':False,'replay':'python scripts/reproduce_offline.py --output NEW_DIRECTORY after non-editable wheel/dependency installation','files':files}
        (base/'bundle-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');(base/'checksums.sha256').write_text(''.join(h+'  '+name+'\n' for name,h in files.items()))
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in sorted(base.rglob('*')):
                if p.is_file():z.write(p,str(p.relative_to(base.parent)))
    print(json.dumps({'output':str(output),'sha256':digest(output),'bytes':output.stat().st_size},ensure_ascii=False))
if __name__=='__main__':main()
