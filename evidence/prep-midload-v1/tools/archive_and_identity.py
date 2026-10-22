"""Local bookkeeping only; never fit, connect or change the original workspace."""
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'candidate'
F=ROOT/'frozen-greybox'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def main():
    index=C/'docs/research/greybox-id-v1';index.mkdir(parents=True,exist_ok=True)
    hashes=json.loads((F/'SHA256.json').read_text())
    models=[]
    for p in sorted((F/'runs/main/fits').glob('*/model.json')):
        target=index/'models'/f'{p.parent.name}.json';target.parent.mkdir(exist_ok=True)
        shutil.copy2(p,target);assert target.read_bytes()==p.read_bytes()
        assert json.loads(p.read_text())['deployable'] is False
        models.append(dict(original=str(p.relative_to(F)),copy=str(target.relative_to(C)),sha256=sha(p),copy_identical=True,deployable=False))
    data=json.loads((F/'runs/main/data.json').read_text())
    source=[{k:r[k] for k in ('run','run_id','episode','accepted','share_run_hashes','private_run_hashes')} for r in data['runs']]
    inputs=json.loads((ROOT/'handoff/inputs/input-index.json').read_text())
    selected={k:v for k,v in hashes.items() if k.startswith(('runs/main/fits/','runs/main/evaluation/')) or k in ('experiment-spec.json','runs/main/data.json','TTO-首轮灰箱实际辨识与对照实验报告.md')}
    write(index/'evidence-index.json',dict(execution_id='TTO-GREYBOX-ID-v1.0',data_role='previously_observed_development_data',deployable=False,
         original_archive=dict(local_path='../handoff/references/greybox-v1-evidence.zip',sha256=sha(ROOT/'handoff/references/greybox-v1-evidence.zip')),
         archive_manifest_sha256=sha(F/'SHA256.json'),input_archives=inputs,source_identities=source,models=models,frozen_outputs=selected,
         refitted_this_round=False,old_split_or_test_used_changed=False,preservation='Original workspace and extracted frozen evidence kept in place; this index is a derivative.'))
    readme='''# 首轮灰箱研究索引

接受的是首轮实际离线研究交付，模型仍 `deployable=false`；本轮不训练、不选参、不改变初值或未来输入情景。

- 研究代码和原冻结spec：`../../../experiments/thermal_identification_v1/`。
- 六个G1/G2参数的逐字副本：`models/`；模型身份和全部旧拟合/评价SHA：`evidence-index.json`。
- 原证据ZIP SHA：`d2039aafbc778a35ad223a7f6f9cac378e570a1ed67f8e9cf4962da8385ef546`。本地仍位于准备目录的 `handoff/references/greybox-v1-evidence.zip`，其解出内容在同层 `frozen-greybox/`；旧原工作树证据、数据、split与test-used均原位保留。
- L/S分享归档及此前探索输入身份见索引；私有原件SHA与分享SHA分别保存，尤其S的manifest不相同，不能替换身份。
- 旧报告、成功/失败成绩、36个主尝试及其他原诊断均按原SHA引用，未覆盖。新A/B覆盖见 `../../../experiments/thermal_identification_prep_v2/` 和本次证据包 `results/availability-v2/`。

L→S是开发期跨任务检查，S→L是反向工况压力检查，合并资料是表达能力与残差研究；它们均不是新未来留出验证，也没有控制收益结论。两轮只有两个热过程，不把18个请求当18个独立episode。
'''
    (index/'README.md').write_text(readme)
    rootread=C/'README.md'
    suffix='\n## 本地研究与测试准备\n\n首轮冻结灰箱研究的代码、模型副本和来源SHA见 [研究索引](docs/research/greybox-id-v1/README.md)。新A/B资格仅写独立研究结果，见 [准备研究](experiments/thermal_identification_prep_v2/README.md)。0.2.3中等负载候选的 [操作卡](docs/TTO中等负载测试操作卡.md) 默认离线预览；现场未执行，须先独立复审。\n'
    if suffix not in rootread.read_text():rootread.write_text(rootread.read_text()+suffix)
    import tto
    wheel=C/'wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl'
    installed=Path(tto.__file__).resolve().parent;files={}
    assert 'site-packages' in installed.parts and Path(sys.prefix) in installed.parents
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.startswith('tto/') and not name.endswith('/'):
                rel=name[4:];assert z.read(name)==(C/'src/tto'/rel).read_bytes()==(installed/rel).read_bytes(),rel
                files[rel]=sha(installed/rel)
    deps={}
    for line in (C/'requirements-locked.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            name,value=line.split('==');actual=metadata.version(name);assert actual==value,(name,actual,value);deps[name]=actual
    assert tto.__version__==metadata.version('tianshan-thermal-observer')=='0.2.3'
    write(ROOT/'results/clean-install-identity.json',dict(version=tto.__version__,python=sys.version,platform=platform.platform(),machine=platform.machine(),
        prefix=sys.prefix,import_path=str(installed),non_editable=True,source_wheel_installed_identical=True,files=files,dependencies=deps,
        wheel_sha256=sha(wheel),dependency_lock_sha256=sha(C/'requirements-locked.txt'),CUDA_used=False,target_N305_installation=False))
    manifest=dict(installer_version=3,version='0.2.3',environment_manager='conda',files={p:sha(C/p) for p in ('install.sh','requirements-locked.txt','config/tto.example.json','scripts/install_tto.py','wheels/'+wheel.name)})
    write(C/'install-manifest.json',manifest)
    print(json.dumps({'models_copied':len(models),'tto_files_verified':len(files),'installed':tto.__version__,'lock_unchanged':True}))

if __name__=='__main__':main()
