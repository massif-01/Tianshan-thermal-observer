"""Bundle the bounded local preparation, inputs and replay evidence."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile
import psutil

root=Path(__file__).resolve().parents[1];c=root/'candidate';stage=root/'evidence-stage'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def copy(p,rel):
    dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
def tree(source,dest,exclude=()):
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if p.is_file() and not any(x in rel.parts for x in exclude):copy(p,Path(dest)/rel)

assert not stage.exists();stage.mkdir()
for rel in ('README.md','LICENSE','pyproject.toml','requirements-locked.txt','install.sh','install-manifest.json','.gitignore','config/tto.example.json'):
    if (c/rel).is_file():copy(c/rel,Path('code')/rel)
for directory in ('src/tto','tests','experiments'):
    tree(c/directory,Path('code')/directory,exclude=('__pycache__','.pytest_cache'))
for rel in ('scripts/install_tto.py','scripts/create_tto_conda_bundle.py','docs/TTO测试者使用说明.md','docs/TTO第一次测试操作卡.md','docs/platform-curve-v2-contract.md','docs/TTO中等负载测试操作卡.md','docs/TTO中等负载候选安装说明.md'):
    copy(c/rel,Path('code')/rel)
tree(c/'scripts/thermal_trials','code/scripts/thermal_trials',exclude=('__pycache__','.pytest_cache'))
tree(c/'docs/research/greybox-id-v1','code/docs/research/greybox-id-v1')
copy(c/'wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl','code/wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl')
for name in ('README.md','01-软件修改与测试准备实施方案.md','02-给Codex的指令.txt','04-离线验收清单.md','SHA256.json'):
    copy(root/'handoff'/name,Path('handoff')/name)
tree(root/'handoff/templates','handoff/templates')
for name in ('input-index.json','L-seven-conditions-original.zip','S-shortqa-original-complete.zip'):
    copy(root/'handoff/inputs'/name,Path('handoff/inputs')/name)
for rel in ('SHA256.json','experiment-spec.json','TTO-首轮灰箱实际辨识与对照实验报告.md','runs/main/data.json'):
    copy(root/'frozen-greybox'/rel,Path('frozen-greybox')/rel)
tree(root/'frozen-greybox/runs/main/fits','frozen-greybox/runs/main/fits')
tree(root/'frozen-greybox/runs/main/evaluation','frozen-greybox/runs/main/evaluation')
for p in sorted((root/'results').rglob('*')):
    rel=p.relative_to(root/'results')
    if p.is_file() and 'input-cache' not in rel.parts and 'availability-v2-attempt01' not in rel.parts:
        copy(p,Path('results')/rel)
attempt=root/'results/availability-v2-attempt01'
write(stage/'results/failed-coverage-attempt-index.json',{str(p.relative_to(attempt)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(attempt.rglob('*')) if p.is_file() and 'input-cache' not in p.relative_to(attempt).parts})
tree(root/'logs','logs')
tree(root/'tools','tools',exclude=('__pycache__',))
tree(root/'site','site')
copy(root/'deliverables/TTO-v1-0.2.3-中等负载准备-Conda安装候选.zip','installation/TTO-v1-0.2.3-中等负载准备-Conda安装候选.zip')
for name in ('original-files.json','original-worktree-status.txt','baseline.json','source-zip.json'):
    copy(root/name,Path('preservation')/name)
report=root/'TTO-软件修改与中等负载测试准备报告.md';copy(report,report.name)
for name in ('test-installed-core-final','test-installed-tools'):
    tree(root/name,Path('loopback-evidence')/name,exclude=('__pycache__',))
usage=psutil.disk_usage(root)
environment=dict(python=sys.version,platform=platform.platform(),machine=platform.machine(),cpu_logical=psutil.cpu_count(),
    cpu_physical=psutil.cpu_count(logical=False),memory_total_MiB=psutil.virtual_memory().total/1048576,disk_free_GiB=usage.free/1073741824,
    CUDA_used=False,network_scope='owned loopback only; dependencies and Conda from existing local caches',
    source_build_python='CPython3.10.18',conda_installed_python='3.10.22',target_N305_executed=False,
    commands=['python -m build --no-isolation --wheel --outdir wheels',
        'pip install --no-index --find-links=<existing macOS CP310 cache> -r requirements-locked.txt',
        'pip install --no-index --no-deps <0.2.3 wheel>',
        'python -I tools/archive_and_identity.py',
        'python -m pytest -q tests/test_polling_schedule.py tests/test_network.py tests/test_failures.py tests/test_config_storage.py tests/test_quality.py',
        'python -m pytest -q scripts/thermal_trials/tests experiments/thermal_identification_prep_v2/tests',
        'python experiments/thermal_identification_prep_v2/coverage_audit.py --handoff ../handoff --frozen ../frozen-greybox --output ../results/availability-v2',
        'python scripts/create_tto_conda_bundle.py --output ../deliverables/TTO-v1-0.2.3-中等负载准备-Conda安装候选.zip --trial-site-config ../site/local-midload.json',
        'CONDA_REGISTER_ENVS=false CONDA_OFFLINE=true CONDA_CHANNELS=conda-forge (existing cache) sh install.sh --prefix <fresh local test prefix> --offline --offline-wheelhouse <existing macOS CP310 cache>',
        'python tools/protect_and_patch.py'],
    production_source_modified=['collector.py','__init__.py'],training_executed=False)
write(stage/'results/environment.json',environment);write(root/'results/environment.json',environment)
readme='''# TTO 软件修改与中等负载测试准备证据

`TTO-PREP-MIDLOAD-v1.0`，本地0.2.3候选，交独立复审。现场部署/实测、新训练、Git提交/推送/PR均未执行。完整结论见同层报告。

- `code/`：基线与此次修改的可重跑源码、研究索引、模型副本、runner、操作卡、现有依赖锁及新wheel。临时环境、Git对象和无关旧产物不进入包。
- `results/midload-prep-v1.patch`：针对a27ddb6f41c887fd9f08d4120f98d97eed31f4d0的源码patch。新wheel单独在code/wheels中，先复制到相应wheels路径再用安装manifest；patch已实际apply-check并逐文件对照。
- `installation/`：新Conda候选，含runner及本地目标配置。私有site配置不在公共patch，包只交本地复审，不自动公开。
- `results/`：冻结规则、逐点新资格、共同集合/误差、覆盖、事件诊断、图及安装身份；`loopback-evidence/`含最终自建服务测试原日志。
- `handoff/inputs/`：L/S完整分享归档和输入索引；`frozen-greybox/`含原spec、data、参数/尝试、已保存评价以及原SHA总表。复核所需原文件逐字相同。原完整灰箱ZIP仍按d2039aaf…索引保留，不递归塞进包。
- `preservation/`：原工作树身份、起点状态及4289个原文件SHA；`logs/`保留失败和最终通过日志。失败覆盖尝试本地仍保存，本包记录其SHA索引，不重复大体积逐点派生内容。

## 先验证包

解压后在本目录执行 `python tools/verify_delivery.py`，只读SHA，不连接任何接口。

## 独立离线复核

在新的CPython3.10环境安装当前锁和0.2.3 wheel；依赖须使用匹配本机平台的已有缓存，本包不提供通用依赖wheelhouse：

```sh
python -m venv .review-env
.review-env/bin/python -m pip install --no-index --find-links /path/to/existing-platform-wheelhouse -r code/requirements-locked.txt
.review-env/bin/python -m pip install --no-index --no-deps code/wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl
.review-env/bin/python -I -m tto doctor --config code/config/tto.example.json
.review-env/bin/python code/scripts/thermal_trials/run_midload.py --plan --trial-config site/local-midload.json
cd code
../.review-env/bin/python -m pytest -q tests/test_polling_schedule.py tests/test_network.py tests/test_failures.py tests/test_config_storage.py tests/test_quality.py
../.review-env/bin/python -m pytest -q scripts/thermal_trials/tests experiments/thermal_identification_prep_v2/tests
../.review-env/bin/python experiments/thermal_identification_prep_v2/coverage_audit.py --handoff ../handoff --frozen ../frozen-greybox --output ../review-availability-v2
```

两组pytest分开运行，避免旧测试的同名conftest导入方式冲突。只重算已保存预测的资格/误差，输出用新的目录；不执行首轮run_experiment、拟合测试或模型搜索。`--live`需未来明确授权，当前复审只用默认plan/dry-run。N305命令与停止/回退见code/docs/TTO中等负载测试操作卡.md，真实地址来源未作现场验证。
'''
(stage/'README.md').write_text(readme)
manifest={str(p.relative_to(stage)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(stage.rglob('*')) if p.is_file()}
write(stage/'SHA256.json',manifest)
output=root/'deliverables/TTO-软件修改与中等负载测试准备证据包.zip'
with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(stage.rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to(stage)),compress_type=zipfile.ZIP_STORED if p.suffix in ('.zip','.whl') else zipfile.ZIP_DEFLATED)
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    for p,d in manifest.items():assert hashlib.sha256(z.read(p)).hexdigest()==d['sha256'],p
    assert z.read(report.name)==report.read_bytes()
receipt=dict(evidence=str(output),bytes=output.stat().st_size,sha256=sha(output),CRC='passed',manifest_files=len(manifest),all_manifest_hashes_verified=True,
     report=str(report),report_sha256=sha(report),report_bytes_identical_in_archive=True)
write(root/'deliverables/delivery-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
