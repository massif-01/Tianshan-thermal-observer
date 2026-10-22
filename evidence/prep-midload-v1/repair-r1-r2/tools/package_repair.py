"""Small repair evidence; no old datasets or fitting jobs are duplicated."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

r=Path(__file__).resolve().parents[1];c=r.parent/'candidate';s=r/'evidence-stage'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def copy(p,n):
    q=s/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def tree(p,n):
    for f in sorted(p.rglob('*')):
        rel=f.relative_to(p)
        if f.is_file() and not any(x in rel.parts for x in ('__pycache__','.pytest_cache','.git')):copy(f,Path(n)/rel)
assert not s.exists();s.mkdir()
for rel in ('README.md','pyproject.toml','install-manifest.json','requirements-locked.txt','install.sh','LICENSE','config/tto.example.json','scripts/install_tto.py','scripts/create_tto_conda_bundle.py',
            'docs/TTO中等负载测试操作卡.md','docs/TTO中等负载候选安装说明.md','docs/TTO测试者使用说明.md','docs/TTO第一次测试操作卡.md','docs/platform-curve-v2-contract.md'):
    if (c/rel).is_file():copy(c/rel,Path('code')/rel)
for rel in ('src/tto','tests','scripts/thermal_trials','experiments/thermal_identification_prep_v2','docs/research/greybox-id-v1'):
    tree(c/rel,Path('code')/rel)
for ver in ('0.2.3','0.2.4'):
    name=f'tianshan_thermal_observer-{ver}-py3-none-any.whl';copy(c/'wheels'/name,Path('wheels')/name)
copy(c/'wheels/tianshan_thermal_observer-0.2.4-py3-none-any.whl','code/wheels/tianshan_thermal_observer-0.2.4-py3-none-any.whl')
for rel in ('scripts','results','legacy-022-source'):
    tree(r/'original-reproduction'/rel,Path('original-reproduction')/rel)
before=r/'original-reproduction/candidate/code'
for rel in ('src/tto','tests','scripts/thermal_trials'):
    tree(before/rel,Path('original-reproduction/candidate/code')/rel)
for rel in json.loads((r/'results/repair-identity-and-preservation.json').read_text())['changed_previous_source_files']:
    copy(before/rel,Path('original-reproduction/candidate/code')/rel)
tree(r/'review','review');tree(r/'results','results');tree(r/'tools','tools')
for p in (r/'logs').iterdir():
    if p.is_file() and p.name!='package-evidence.log':copy(p,Path('logs')/p.name)
tree(r/'test-delivery','test-evidence/tools')
copy(r/'conda-install/installation.json','results/installation.json')
copy(r/'review-integrity.json','results/review-integrity.json');copy(r/'before-code-sha256.json','preservation/before-code-sha256.json')
copy(r.parent/'frozen-greybox/SHA256.json','preservation/frozen-greybox-SHA256.json')
copy(r.parent/'baseline.json','preservation/candidate-baseline.json')
bundle=r/'deliverables/TTO-v1-0.2.4-R1-R2返修-Conda安装候选.zip';copy(bundle,Path('installation')/bundle.name)
report=r/'TTO-中等负载测试准备-R1-R2返修报告.md';copy(report,report.name)
(s/'results/environment.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),machine=platform.machine(),
    network='owned loopback only; existing local dependency caches',CUDA_used=False,model_fitting_executed=False,field_executed=False,
    clean_venv='CPython3.10.18',clean_conda='CPython3.10.22'),indent=2)+'\n')
(s/'README.md').write_text('''# R1/R2有限返修证据

版本0.2.4，待独立复审。只修runner的源准入与安装入口；原轮询、A/B规则、模型及旧成绩不变。本包不授权部署或真实负载。先读同层修复报告，操作卡在code/docs。

`results/R1-R2-against-0.2.3.patch`是针对此前已交0.2.3源码的增量patch，14条路径；已有完整0.2.3代码副本时从其根目录执行 `git apply --check` 再apply。新wheel独立放在wheels/及code/wheels，旧wheel保留用于原反例。`code/`可直接读/重跑相关测试；未重复携带L/S原档和19MB旧交付。其SHA与冻结研究/输出保护在results/repair-identity-and-preservation.json和preservation/。

## 校验

```sh
python tools/verify_evidence.py
```

## 复跑新验证

需要已有Conda及匹配当前平台Python3.10的依赖缓存；Conda缓存也需具备Python/pip。下例在包根运行，缓存目录是复审者自己的已有目录，不会下载：

```sh
unzip -n installation/TTO-v1-0.2.4-R1-R2返修-Conda安装候选.zip -d installer
sh installer/TTO-v1-0.2.4-Conda安装包/install.sh --prefix "$PWD/review-install" --offline --offline-wheelhouse /path/to/existing-platform-wheelhouse
export TTO_MIDLOAD_INSTALLED_PREFIX="$PWD/review-install"
export TTO_MIDLOAD_LEGACY_SOURCE="$PWD/original-reproduction/legacy-022-source"
PYTHONPATH="$TTO_MIDLOAD_LEGACY_SOURCE" "$TTO_MIDLOAD_INSTALLED_PREFIX/tto-midload" --plan
PYTHONPATH="$TTO_MIDLOAD_LEGACY_SOURCE" "$TTO_MIDLOAD_INSTALLED_PREFIX/tto-midload" --dry-run
"$TTO_MIDLOAD_INSTALLED_PREFIX/conda-env/bin/python" -I -m pytest -q code/tests/test_polling_schedule.py code/tests/test_network.py code/tests/test_failures.py code/tests/test_config_storage.py code/tests/test_quality.py
"$TTO_MIDLOAD_INSTALLED_PREFIX/conda-env/bin/python" -I -m pytest -q code/scripts/thermal_trials/tests code/experiments/thermal_identification_prep_v2/tests
```

两组pytest分开。R2测试会调用安装生成的同一个tto-midload入口，并只创建自己的loopback服务；真实默认背景阶段数秒后由测试停止，不向site配置的真实目标连接。R1使用生产Engine和调度器、合成源与请求替身。不能把替身请求数称为真实负载。

## 原反例

原独立复审完整文件在review/。本机重现的原脚本、旧健康/入口、真实旧0.2.2源和结果在original-reproduction/。三个原脚本返回0表示确认原0.2.3有问题，不是新候选通过标准。若需重现，先在另一独立环境非editable安装wheels/内的0.2.3及已有依赖，再运行该目录scripts/check_health_source.py、check_readiness_to_request.py、check_runner_import.py；不要运行旧版--live或研究拟合脚本。新修复标准由新交叉测试反向断言。

logs/保留原反例、测试和安装日志，包括夹具失败/收尾尝试；最终以core.log（50项）与delivery-tools.log（37项）及对应XML为准。test-evidence/tools含正常、拒收、恢复、旧PYTHONPATH下的安装入口及实际loopback停止/归档记录。未执行目标机部署、真实推理、模型训练、Git发布。
''')
manifest={str(p.relative_to(s)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(s.rglob('*')) if p.is_file()}
(s/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
out=r/'deliverables/TTO-中等负载测试准备-R1-R2返修证据包.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(s.rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to(s)))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(n)).hexdigest()==d['sha256'] for n,d in manifest.items())
    assert z.read(report.name)==report.read_bytes()
receipt=dict(evidence=str(out),bytes=out.stat().st_size,sha256=sha(out),manifest_files=len(manifest),CRC='passed',all_hashes_verified=True,
    report=str(report),report_sha256=sha(report),report_in_archive_identical=True)
(r/'deliverables/delivery-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))
