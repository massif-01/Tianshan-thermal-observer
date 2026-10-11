#!/usr/bin/env python3
"""Package only the R3b source, synthetic evidence and new candidate identities."""
import argparse
import difflib
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def build(output):
    root=Path(__file__).resolve().parent.parent; evidence=root/'evidence/r3b-v1'
    verified=evidence/'installed-verification'
    assert json.loads((verified/'verification.json').read_text())['passed']
    assert '88 passed' in (verified/'tests.txt').read_text()
    stage=evidence/'package/TTO-v1-R3b';stage.mkdir(parents=True,exist_ok=False)
    ignored=shutil.ignore_patterns('__pycache__','*.egg-info','.pytest_cache')
    def copy(src,dst):
        dst=stage/dst;dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir():shutil.copytree(src,dst,ignore=ignored)
        else:shutil.copy2(src,dst)
    for name in ('src','tests','config','templates') :copy(root/name,Path(name))
    for name in ('contracts.md','CLI使用卡.md','R1-R4-repair-contract.md','R3b-report-eligibility.md'):copy(root/'docs'/name,Path('docs')/name)
    script_names=('reproduce_offline.py','verify_r1_r4.py','verify_r3b.py','verify_r3b_saved.py','verify_signals.py','benchmark_offline.py','check_install_identity.py','package_r3b_evidence.py')
    for name in script_names:copy(root/'scripts'/name,Path('scripts')/name)
    for name in ('README.md','pyproject.toml','requirements-locked.txt','TTO-v1-R3b收尾与验证报告.md'):copy(root/name,Path(name))
    wheel=root/'wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl';copy(wheel,Path('wheels')/wheel.name)
    old=root/'wheels/tianshan_thermal_observer-0.1.1-py3-none-any.whl';copy(old,Path('baseline/wheels')/old.name)
    for name in ('identity.json','git-status.txt','reproduction.log'):copy(evidence/'before'/name,Path('before')/name)
    copy(evidence/'before/reproduction',Path('before/reproduction'))
    review=evidence/'review-original/TTO-v1-R1-R4-second-review'
    for name in ('README.md','TTO-v1-R1-R4返修独立复审.md','scripts/check_shadow_quality.py','results/shadow-quality/findings.json'):
        copy(review/name,Path('review-original')/name)
    copy(review/'fixtures',Path('review-original/fixtures'))
    copy(evidence/'after/installed-same-records',Path('after/same-records'))
    copy(verified/'r3b-probes',Path('after/r3b-probes'))
    for directory,names in [('development',('focused.log','focused.xml','full.log','full.xml','build.log','dependency-install.log')),('after',('identity.json','pip-check.log','wheel-install.log','installed-same-records.log','installed-replay.log','scope-invariants.json'))]:
        for name in names:copy(evidence/directory/name,Path('logs')/directory/name)
    for p in verified.iterdir():
        if p.is_file():copy(p,Path('logs/installed')/p.name)
    for name in ('signals/result.json','repair-probes/findings.json','demo/evaluation/evaluation.json'):
        p=verified/name
        if p.is_file():copy(p,Path('logs/installed')/name)
    candidates=[]
    for directory in ('src','tests','scripts','docs','config','templates'):
        candidates += [p.relative_to(root) for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not any(x.endswith('.egg-info') for x in p.parts)]
    candidates += [Path(p) for p in ('README.md','PROGRESS.md','pyproject.toml','requirements-locked.txt')]
    patches=[];changed=[]
    for rel in sorted(candidates):
        before=evidence/'before'/rel;after=root/rel
        oldtext=before.read_text() if before.exists() else ''
        newtext=after.read_text()
        if oldtext==newtext:continue
        patches.extend(difflib.unified_diff(oldtext.splitlines(keepends=True),newtext.splitlines(keepends=True),fromfile='a/'+str(rel) if before.exists() else '/dev/null',tofile='b/'+str(rel)))
        changed.append({'path':str(rel),'before_sha256':hashlib.sha256(before.read_bytes()).hexdigest() if before.exists() else None,'after_sha256':hashlib.sha256(after.read_bytes()).hexdigest()})
        if before.exists():copy(before,Path('baseline/tree')/rel)
        # Necessary newly added packaging scripts are available for a full patch round trip.
        if not (stage/rel).exists():copy(after,rel)
    (stage/'incremental.patch').write_text(''.join(patches))
    (stage/'changes.json').write_text(json.dumps(changed,indent=2))
    (stage/'REPRODUCE.md').write_text('''# R3b离线独立重跑

全部数据/模型为合成。baseline/wheels/0.1.1仅用于旧缺陷复现，新候选为wheels/0.1.2。不要覆盖已有工作树，不部署。

在新的Python 3.10隔离环境准备requirements-locked.txt全部依赖，非editable安装：

```sh
python -m pip install -r requirements-locked.txt
python -m pip install --no-index --no-deps wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl
python -m pip check
python scripts/check_install_identity.py --source . --wheel wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl --output /tmp/tto-r3b-identity-NEW.json
python scripts/reproduce_offline.py --output /tmp/tto-r3b-verification-NEW
python scripts/verify_r3b_saved.py --runs-root before/reproduction --output /tmp/tto-r3b-same-records-NEW
```

完整入口运行88项（原81+新增7）、离线doctor、模拟训练/时间留出评估、实际Engine/Journal模拟记录/正式报告、真实loopback协议与自身测试进程退出。仅允许测试创建的loopback端点，不运行doctor --live。也可单独运行verify_r3b.py。输出路径必须不存在。依赖准备可能访问包索引；验证不访问设备。

旧缺陷独立复现必须使用另一个隔离环境安装baseline/wheels/0.1.1，然后执行review-original/scripts/check_shadow_quality.py。该原脚本退出0表示复现旧缺陷，不能作为修复通过。原脚本未改；新verify_r3b.py是单独注明的修复断言适配版。

before/reproduction保留修复前生产路径产生的原日志与旧报告；after/same-records是同一批原日志的新报告及哈希不变核对。after/r3b-probes是新安装候选通过Engine/Journal/正式report的正常、冲突、恢复、倒退报告与记录。logs包含第一次新增测试的失败及后续通过记录，不能混用为候选成绩。

SHA256SUMS逐文件清单不包含自身。源码patch起点见before/identity.json，baseline/tree只保存修改前必要文件；新文件以/dev/null标记。必要源码全量位于src，未包含历史大包、凭据或实机记录。
''')
    files=sorted(p for p in stage.rglob('*') if p.is_file())
    (stage/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(stage))+'\n' for p in files))
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stage.rglob('*')):
            if p.is_file():z.write(p,Path(stage.name)/p.relative_to(stage))
    print(json.dumps({'zip':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'changed_files':len(changed)},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();build(a.output)
