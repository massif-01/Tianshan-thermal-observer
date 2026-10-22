#!/usr/bin/env python3
"""Minimal TTO-only review bundle; monitor artifacts belong to its own chat."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def package(a):
    root=Path(__file__).resolve().parent.parent;ev=root/'evidence/platform-curve-v2'
    stage=Path(a.stage).resolve();stage.mkdir(parents=True,exist_ok=False)
    def copy(src,rel):
        dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir():shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.egg-info','.pytest_cache'))
        else:shutil.copy2(src,dst)
    for name in ('src','tests','config','templates'):copy(root/name,Path(name))
    names=('reproduce_offline.py','verify_r1_r4.py','verify_r3b.py','verify_r3b_saved.py','verify_signals.py','benchmark_offline.py','check_install_identity.py','install_tto.py','verify_install.py','verify_platform_upgrade.py','package_platform_evidence.py','create_tto_conda_bundle.py')
    for name in names:copy(root/'scripts'/name,Path('scripts')/name)
    docs=('TTO测试者使用说明.md','TTO第一次测试操作卡.md','platform-curve-v2-contract.md','contracts.md','CLI使用卡.md','R1-R4-repair-contract.md','R3b-report-eligibility.md')
    for name in docs:copy(root/'docs'/name,Path('docs')/name)
    copy(root/'docs/plans/TTO-Orin-Thor-CURVE最终执行方案-20261012.md',Path('docs/plans/TTO-Orin-Thor-CURVE最终执行方案-20261012.md'))
    for name in ('README.md','pyproject.toml','requirements-locked.txt','install.sh','install-manifest.json',a.report):copy(root/name,Path(name))
    wheel=Path(a.wheel).resolve();copy(wheel,Path('wheels')/wheel.name)
    copy(Path(a.installer).resolve(),Path('installer')/Path(a.installer).name)
    old_installer=root/'evidence/conda-installer-v1/final-package/TTO-v1-0.1.2-conda-install'
    copy(old_installer,Path('baseline/TTO-v1-0.1.2-conda-install'))
    copy(root/'wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl',Path('baseline/wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl'))
    # Authoring source starts at the preserved HEAD. Only changed necessary
    # files get baseline copies; existing private/unrelated history is excluded.
    candidates=[p.relative_to(stage) for p in stage.rglob('*') if p.is_file() and p.suffix in ('.py','.md','.toml','.json','.jsonl','.sh','.txt') and p.parts[len(stage.parts)] in ('src','tests','scripts','docs')]
    candidates += [Path(n) for n in ('README.md','pyproject.toml','requirements-locked.txt','install.sh','install-manifest.json')]
    head=json.loads((ev/'before/tto-identity.json').read_text())['head']
    patches=[];changed=[]
    for rel in sorted(set(candidates)):
        actual=root/rel
        if not actual.is_file():continue
        r=subprocess.run(['git','show',head+':'+str(rel)],cwd=root,capture_output=True)
        old=r.stdout if r.returncode==0 else b''
        new=actual.read_bytes()
        # Frozen producer fixtures are evidence assets. Copy their exact bytes
        # during roundtrip instead of normalizing no-newline JSON through patch.
        if str(rel).startswith('tests/fixtures/platform-v2/producer/'):
            if old==new:continue
            changed.append({'path':str(rel),'before_sha256':hashlib.sha256(old).hexdigest() if r.returncode==0 else None,'after_sha256':hashlib.sha256(new).hexdigest(),'copy_mode':'verbatim'})
            if r.returncode==0:
                p=stage/'baseline/tree'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(old)
            continue
        if old==new:continue
        try:oldtext,newtext=old.decode(),new.decode()
        except UnicodeError:continue
        fromfile='a/'+str(rel) if r.returncode==0 else '/dev/null'
        tofile='b/'+str(rel)
        if (old and not old.endswith(b'\n')) or not new.endswith(b'\n'):
            # difflib represents the last line without its terminator, while
            # patch requires the standard marker on each affected file side.
            before_lines=oldtext.splitlines();after_lines=newtext.splitlines()
            old_start=1 if before_lines else 0;new_start=1 if after_lines else 0
            diff=[f'--- {fromfile}\n',f'+++ {tofile}\n',
                  f'@@ -{old_start},{len(before_lines)} +{new_start},{len(after_lines)} @@\n']
            for line in before_lines:diff.append('-'+line+'\n')
            if old and not old.endswith(b'\n'):diff.append('\\ No newline at end of file\n')
            for line in after_lines:diff.append('+'+line+'\n')
            if not new.endswith(b'\n'):diff.append('\\ No newline at end of file\n')
        else:
            diff=list(difflib.unified_diff(oldtext.splitlines(True),newtext.splitlines(True),fromfile=fromfile,tofile=tofile))
        patches.extend(diff)
        # A last context line can retain no terminator when the compared file
        # has none; separate the next file's header to keep the patch replayable.
        if diff and not diff[-1].endswith('\n'):
            patches[-1]+='\n'
        changed.append({'path':str(rel),'before_sha256':hashlib.sha256(old).hexdigest() if r.returncode==0 else None,'after_sha256':hashlib.sha256(new).hexdigest()})
        if r.returncode==0:
            p=stage/'baseline/tree'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(old)
    patch=stage/'incremental.patch';patch.write_text(''.join(patches))
    (stage/'changes.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2))
    with tempfile.TemporaryDirectory(prefix='tto-v2-patch-',dir='/private/tmp') as tmp:
        tree=Path(tmp)/'tree';shutil.copytree(stage/'baseline/tree',tree)
        for item in changed:(tree/item['path']).parent.mkdir(parents=True,exist_ok=True)
        r=subprocess.run(['patch','-p1','--batch','-i',str(patch)],cwd=tree,capture_output=True,text=True)
        (stage/'patch-roundtrip.log').write_text(r.stdout+r.stderr)
        assert r.returncode==0
        for item in changed:
            if item.get('copy_mode')=='verbatim':shutil.copy2(stage/item['path'],tree/item['path'])
            assert sha(tree/item['path'])==item['after_sha256'],item['path']
    for name in ('tto-identity.json','tto-status.bin','tto-diff.patch','tto-tests.log','tto-junit.xml','legacy-production-gaps.json'):
        p=ev/'before'/name
        if p.is_file():copy(p,Path('before')/name)
    verification=Path(a.verification).resolve()
    assert json.loads((verification/'verification.json').read_text())['passed']
    # Keep focused report results and logs rather than all duplicate synthetic
    # run/dataset copies. Fixtures and entry points can recreate those records.
    for p in verification.iterdir():
        if p.is_file():copy(p,Path('verified')/p.name)
    for rel in ('signals/result.json','repair-probes/findings.json','r3b-probes/findings.json','demo/evaluation/evaluation.json','demo/collection-report'):
        p=verification/rel
        if p.exists():copy(p,Path('verified')/rel)
    for rel in ('r3b-probes/normal-report','r3b-probes/conflict-report','r3b-probes/conflict_then_recovery-report'):
        p=verification/rel
        if p.exists():copy(p,Path('verified')/rel)
    for p in sorted(ev.glob('*')):
        if p.is_file() and p.suffix in ('.log','.xml','.json') and not p.name.startswith('rm-'):
            copy(p,Path('logs')/p.name)
    copy(Path(a.upgrade).resolve()/'findings.json',Path('installation/upgrade-findings.json'))
    for p in Path(a.upgrade).resolve().glob('*.log'):copy(p,Path('installation/upgrade')/p.name)
    copy(Path(a.install_checks).resolve()/'findings.json',Path('installation/installer-findings.json'))
    for p in Path(a.install_checks).resolve().glob('*.log'):copy(p,Path('installation/installer')/p.name)
    if a.repair_evidence:
        repair=Path(a.repair_evidence).resolve();before=repair/'before'
        identity=json.loads((before/'identity.json').read_text())
        copy(before/'identity.json',Path('review-repair/before/identity.json'))
        copy(before/'new-regression-failures.log',Path('review-repair/before/new-regression-failures.log'))
        copy(before/'independent-review-probes',Path('review-repair/before/independent-review-probes'))
        copy(repair/'intermediate-0.2.1/historical-regression-failure.json',Path('review-repair/intermediate-0.2.1/historical-regression-failure.json'))
        copy(repair/'final-historical-report',Path('review-repair/final-historical-report'))
        copy(root/'wheels/tianshan_thermal_observer-0.2.0-py3-none-any.whl',Path('baseline/wheels/tianshan_thermal_observer-0.2.0-py3-none-any.whl'))
        for p in repair.iterdir():
            if p.is_file() and p.suffix in ('.log','.json','.xml'):copy(p,Path('review-repair')/p.name)
        # This patch is only the finite repair relative to the saved dirty tree.
        # incremental.patch separately reconstructs the whole candidate from HEAD.
        repair_patch=[];repair_changes=[]
        new_files={'tests/test_review_repair.py'} | {str(p.relative_to(root)) for p in (root/'tests/fixtures/review-repair').rglob('*') if p.is_file()}
        for rel in sorted(set(identity['files']) | new_files):
            current=stage/rel
            if not current.is_file():continue
            previous=before/rel
            old=previous.read_bytes() if previous.is_file() else b''
            new=current.read_bytes()
            if old==new:continue
            assert not old or old.endswith(b'\n'),rel
            assert new.endswith(b'\n'),rel
            repair_patch.extend(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile='a/'+rel if previous.is_file() else '/dev/null',tofile='b/'+rel))
            repair_changes.append({'path':rel,'before_sha256':hashlib.sha256(old).hexdigest() if previous.is_file() else None,'after_sha256':hashlib.sha256(new).hexdigest()})
            if previous.is_file():copy(previous,Path('review-repair/baseline/tree')/rel)
        patch_path=stage/'review-repair/repair.patch';patch_path.write_text(''.join(repair_patch))
        (stage/'review-repair/repair-changes.json').write_text(json.dumps(repair_changes,ensure_ascii=False,indent=2)+'\n')
        with tempfile.TemporaryDirectory(prefix='tto-repair-patch-',dir='/private/tmp') as tmp:
            tree=Path(tmp)/'tree';shutil.copytree(stage/'review-repair/baseline/tree',tree)
            for item in repair_changes:(tree/item['path']).parent.mkdir(parents=True,exist_ok=True)
            r=subprocess.run(['patch','-p1','--batch','-i',str(patch_path)],cwd=tree,capture_output=True,text=True)
            (stage/'review-repair/patch-roundtrip.log').write_text(r.stdout+r.stderr)
            assert r.returncode==0
            for item in repair_changes:assert sha(tree/item['path'])==item['after_sha256'],item['path']
    (stage/'REPRODUCE.md').write_text('''# TTO独立离线复核

所有训练/协议夹具为合成；本包只交付TTO候选，服务由WS会话独立交付。先准备Python3.10隔离环境和requirements-locked.txt，安装wheels中的候选（非editable），运行pip check与scripts/check_install_identity.py。

‘python scripts/reproduce_offline.py --output /新的验证目录’运行原88项与新增回归、离线doctor、schema2模拟训练评估、历史R1-R4/R3b（正常510、冲突510排除、恢复306有效）、真实loopback协议及自身进程退出。它不访问真实设备。新合同监控服务producer 1.1.1 fixture以冻结manifest逐项核验，并由TTO Quality、Engine、Journal及正式report入口消费；16个JSON资产逐字节保留。

独立Conda安装验证需出厂Conda、匹配系统/架构的离线依赖wheelhouse和Conda本机缓存。运行verify_install.py可核对安装器。verify_platform_upgrade.py可使用baseline/TTO-v1-0.1.2-conda-install和本目录installer里的新包，在全新临时前缀重现旧配置/旧模型/旧记录升级，不对现有用户目录执行。

incremental.patch与baseline/tree可在新目录重放；patch-roundtrip.log已核对全部修改后SHA。before保存起点与旧缺口复现，退出0代表旧缺口复现成功，不代表修复通过。logs保留失败与修正后的日志。verified是最终安装候选的结果；中间包/历史服务包不能作为最终候选。

SHA256SUMS不含自身。不运行live doctor、不连接设备、不部署/重启、不调风扇、不使用CUDA、不提交或推送。
''')
    if a.repair_evidence:
        with (stage/'REPRODUCE.md').open('a') as f:
            f.write('\n本轮有限返修位于review-repair/：repair.patch相对修复前未提交工作树，baseline/tree及repair-changes.json提供逐文件SHA和往返记录。tests/test_review_repair.py包含新记录与0.2.0已保存评分的恢复引用回归；固定历史夹具纯合成，132历史、54排除、78恢复有效只作为该夹具断言。权威最终结果以verified/、review-repair/final-*及本轮报告为准；logs/中的早期成功是历史结果，不是新候选身份。0.2.0 wheel只用于复现旧缺口。\n')
    files=sorted(p for p in stage.rglob('*') if p.is_file())
    (stage/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(stage))+'\n' for p in files))
    out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stage.rglob('*')):
            if p.is_file():z.write(p,stage.name+'/'+str(p.relative_to(stage)))
    print(json.dumps({'zip':str(out),'sha256':sha(out),'files':len(files),'changed_files':len(changed)},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('stage','output','wheel','installer','report','verification','upgrade','install-checks'):p.add_argument('--'+name,required=True)
    p.add_argument('--repair-evidence')
    package(p.parse_args())
