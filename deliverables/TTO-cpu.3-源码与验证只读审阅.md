# TTO-cpu.3-源码与验证只读审阅

本文件仅从已封存最终 release ZIP 提取现有文本，供无法解压环境只读审阅。代码块内原文不作改写；标题、身份表和对应说明为导出导航。此次没有执行候选、回放或测试，没有连接设备，也没有修改原 ZIP、源码、参数、阈值、清单或原证据。

## 1. 最终交付身份与八项运行文件变更

唯一提取源：`TTO-数值线程策略与旁录前资源检查-收尾证据包.zip`；1166222 字节；SHA-256：`dd49cbbbd87f01465b91149e2d45d048edc6e4515ee2cfd7efd7561a03e0ddae`。按包内 `SHA256.json` 逐项只读核对 284 个条目的字节数与 SHA，全部一致。完整 ZIP 继续保留；本文件不重新压缩。

| 最终文件（ZIP 内路径） | 字节数 | SHA-256 |
|---|---:|---|
| `candidate/tto_field_candidate-0.2.4+cpu.3-py3-none-any.whl` | 127193 | `a9f0394097180c952d8b7f4e1cebac65fe7f2cc612c7f7189dfac6566502c9be` |
| `candidate/cpu3.patch` | 24583 | `ca974a1d8348b1f9cad355efe05b23433b007d843e313299985a91581bce1eb4` |
| `candidate/source-identity.json` | 2758 | `299364791caa5e967e54144d3b34fb27bfb753994eef9469a5559d45e54eaa6c` |
| `source/src/tto_field/candidate-files.json` | 4915 | `dffdfb7607b52224e1be55531a23525df2e32aca02503cf76ba2affedf8de046` |

相对 cpu.2 的运行代码恰为下列 8 项；其中 2 项新增、6 项修改。打包元数据、测试和核对脚本另列，不冒充新增运行模块。

| 相对安装包路径 | 变化 | 最终 SHA-256 |
|---|---|---|
| `tto_field/__init__.py` | 修改 | `ad02c64181eea81da52a038072ec1f200a92f7255a49080e06187074bf0f574b` |
| `tto_field/cli.py` | 修改 | `827953261847e853e851c75b850a538f2b3a912d1e76dc49bc7310305f13b787` |
| `tto_field/cpu_cli.py` | 修改 | `4264c0b4a4f019c6d198d30f5b0f6b672fbac371c9cf98a6d71eef3a84842ebc` |
| `tto_field/cpu_pilot.py` | 修改 | `36861ae379d9c1a56a8ab2584aa24b23deb0a7d48dc758e6958015bbd1fc2f2f` |
| `tto_field/identity.py` | 修改 | `58850200044da1dc1417bec8ee805a3bca44813219a1523f325a6c8f92ee2ef1` |
| `tto_field/numeric_policy.py` | 新增 | `d27f383e49de5512316307250cf97ec1d619f40c7a0133e42ba0df6e0b13c27f` |
| `tto_field/receiver_resources.py` | 新增 | `cae3f2deccd16f008711dfbdabcfd53b7b4cf1a159f83752d0a5682495031781` |
| `tto_field/runtime.py` | 修改 | `82115476aa55ebecb53cde08e805b597e0534368c2072c32ba867d500ba6c281` |

以下身份文件保留完整原文。wheel 内对应源码与封存 source 文本逐字节对应；`candidate-files.json` 自身不计入其 50 项运行文件清单。

### `candidate/source-identity.json`

SHA-256：`299364791caa5e967e54144d3b34fb27bfb753994eef9469a5559d45e54eaa6c`；字节数：2758。以下为完整原文。

````json
{
  "version": "0.2.4+cpu.3",
  "files": 50,
  "changed": {
    "tto_field/__init__.py": {
      "before": "40d71affd223a7fc7a209caf8afaec266fd4b669e45e413abd317b61cc674ff6",
      "after": "ad02c64181eea81da52a038072ec1f200a92f7255a49080e06187074bf0f574b"
    },
    "tto_field/cli.py": {
      "before": "e81ca7e714568e08e841b291ba9bcbb2019f1c67a0d747dfd90ba139bd92c649",
      "after": "827953261847e853e851c75b850a538f2b3a912d1e76dc49bc7310305f13b787"
    },
    "tto_field/cpu_cli.py": {
      "before": "35be48fba52533fcda6dbddeb59175440c1a60bc54d38139985f1499c47981f9",
      "after": "4264c0b4a4f019c6d198d30f5b0f6b672fbac371c9cf98a6d71eef3a84842ebc"
    },
    "tto_field/cpu_pilot.py": {
      "before": "ce54b3e013801eeffb402d11d387cc08dcd10fd6af1d2040eeb11e681487dd45",
      "after": "36861ae379d9c1a56a8ab2584aa24b23deb0a7d48dc758e6958015bbd1fc2f2f"
    },
    "tto_field/identity.py": {
      "before": "6d88f1eb2bf0cffb8d7b903df3b68d2fcbea7106c4b7d3efd4aa3cfad2a9c982",
      "after": "58850200044da1dc1417bec8ee805a3bca44813219a1523f325a6c8f92ee2ef1"
    },
    "tto_field/numeric_policy.py": {
      "before": null,
      "after": "d27f383e49de5512316307250cf97ec1d619f40c7a0133e42ba0df6e0b13c27f"
    },
    "tto_field/receiver_resources.py": {
      "before": null,
      "after": "cae3f2deccd16f008711dfbdabcfd53b7b4cf1a159f83752d0a5682495031781"
    },
    "tto_field/runtime.py": {
      "before": "7675b328be4d5511d5152e3de06de694692e9122c28e55a0d4a12a3807fd033a",
      "after": "82115476aa55ebecb53cde08e805b597e0534368c2072c32ba867d500ba6c281"
    }
  },
  "protected_files_unchanged": [
    "tto/__init__.py",
    "tto/__main__.py",
    "tto/cli.py",
    "tto/collector.py",
    "tto/config.py",
    "tto/dataset.py",
    "tto/defaults.json",
    "tto/demo.py",
    "tto/deployment.py",
    "tto/diagnostics.py",
    "tto/engine.py",
    "tto/evaluation.py",
    "tto/features.py",
    "tto/model.py",
    "tto/platform_engine.py",
    "tto/platform_quality.py",
    "tto/profiles.py",
    "tto/quality.py",
    "tto/recorded.py",
    "tto/report.py",
    "tto/storage.py",
    "tto/training.py",
    "tto/util.py",
    "tto_field/comm_bridge.py",
    "tto_field/cpu_source.py",
    "tto_field/cpu_transport.py",
    "tto_field/plans/cpu-pilot.json",
    "tto_field/plans/execution-policy.json",
    "tto_field/plans/mix-plan.json",
    "tto_field/plans/model-profiles.json",
    "tto_field/projection.py",
    "tto_field/requester.py",
    "tto_field/research/__init__.py",
    "tto_field/research/models/primary.json",
    "tto_field/research/observer-spec.json",
    "tto_field/research/observer.py",
    "tto_field/scheduler.py",
    "tto_field/upstream_comm/__init__.py",
    "tto_field/upstream_comm/source_health.py"
  ]
}
````

### `source/src/tto_field/candidate-files.json`

SHA-256：`dffdfb7607b52224e1be55531a23525df2e32aca02503cf76ba2affedf8de046`；字节数：4915。以下为完整原文。

````json
{
  "version": "0.2.4+cpu.3",
  "files": {
    "tto/__init__.py": "672cde4b34710368c9ecba08ed361a47ef4a7c1f4ed5863a338bcde29549e700",
    "tto/__main__.py": "79ee6f134c5c5193377cf9b189cbdcc3e2095e49ba9cec310114441c15a917c4",
    "tto/cli.py": "d6adf47989226d57f798125c8f020bfdb8d1e14b357bf4f85ca82d3150747ce1",
    "tto/collector.py": "4c696d3a63cef96d255e0e6e0fd5f56754727a2647801653ed373f0aede22563",
    "tto/config.py": "5a05545f28b8b44b3e6f0e7efcf2453e01ee0726ef0bd228cc73d553e01d8e3e",
    "tto/dataset.py": "32ee485269a521b0540f6d4050eab2dac46cc93a65603086eea263349d9487ee",
    "tto/defaults.json": "4463c064f6809cf371f447cb133d30e1fdb9854b1483077c8102f0e58b67ebd1",
    "tto/demo.py": "3e1475ee0753040f35d454138c47a39879c32d315db89824e101563d56b829fb",
    "tto/deployment.py": "221b1d098d46623dc0eba5addc9804d917f8ede6cfa850cec1922c5cd177aaf7",
    "tto/diagnostics.py": "93dfcc32ca5d9fee48d14b71375705f117a81afb2b0d17b89214be3317741055",
    "tto/engine.py": "c979174d9f78fce54418ed847e9b4e57b155da07eba37c255c7037ecb27bf66c",
    "tto/evaluation.py": "e6b2fc86f32cc28dbe204519bc74c13a138b9873164318727d4187c6dad78181",
    "tto/features.py": "d6b32b3584eea3b57eb658c0d9c005b197a420062daec613f78a057bc4462fa2",
    "tto/model.py": "371a6b81ad32c87654c231dd2e326b002a3e027b7a935b67117dd7508426fe7e",
    "tto/platform_engine.py": "d1d8e48f10c731beb8a0d0b7195ab7e32553aae875ebff30a73846be88f967ea",
    "tto/platform_quality.py": "3f7e33e083251eaff8136319495ab682a7f7fdc554d0efad39fe5d990085044e",
    "tto/profiles.py": "3fb61fbe30bfce73cf7e1079c487e1ddb82b2301ed37d329e1e6da4bfc6944b4",
    "tto/quality.py": "014e67c7885d291c8bede9ad3a51fb85398b26bc71e7336b3a0f18b81aec3e56",
    "tto/recorded.py": "029679e59c68735d1ca98daf56553d6226c55e7d64597015712d972a8b7d2679",
    "tto/report.py": "59834f8fc8f226311edf8376b3a8ecce6f5ca2a48ef79bc4532d551f14e9413e",
    "tto/storage.py": "cda8d22444a0e1fe5fc2f1fa86b73cb4e3f9be4e76edb3cf265520b3285143ec",
    "tto/training.py": "c8f0d6c83587b18c8a527e9d84e222276ee1bd0edc8e69a828dd1ed33a2de773",
    "tto/util.py": "0a33bb268e7817ddd19b6ae81562c50e1fdd08a9cdb3fa08f8f2dd3fbb252f16",
    "tto_field/__init__.py": "ad02c64181eea81da52a038072ec1f200a92f7255a49080e06187074bf0f574b",
    "tto_field/cli.py": "827953261847e853e851c75b850a538f2b3a912d1e76dc49bc7310305f13b787",
    "tto_field/comm_bridge.py": "50f7297b066057323c9a46ffc8713e0a799432ffce95567db5f89b62f2fbe5d1",
    "tto_field/cpu_cli.py": "4264c0b4a4f019c6d198d30f5b0f6b672fbac371c9cf98a6d71eef3a84842ebc",
    "tto_field/cpu_interface.py": "ef5edccc09bd8c2aed21d9546934286a2fd5f05963c4b843ecbbbf969cfd6be5",
    "tto_field/cpu_pilot.py": "36861ae379d9c1a56a8ab2584aa24b23deb0a7d48dc758e6958015bbd1fc2f2f",
    "tto_field/cpu_source.py": "7f674e6913458dc73e8a677fbb46d6574812da05c5a5ba2938d126b53ca14382",
    "tto_field/cpu_transport.py": "2691b9c4040a192df6823e293aafbe211386fced0d542c6bd0fb7b550a47bfa0",
    "tto_field/gate.py": "84bad590f2d1f4f85a068eb6e1cfbaf058a7c906f974ca8316cdabfaf0176817",
    "tto_field/identity.py": "58850200044da1dc1417bec8ee805a3bca44813219a1523f325a6c8f92ee2ef1",
    "tto_field/numeric_policy.py": "d27f383e49de5512316307250cf97ec1d619f40c7a0133e42ba0df6e0b13c27f",
    "tto_field/plans/cpu-pilot.json": "addb4b2b6c4b143fe5f666742bf8072cc6003a7b2c7763da826fbf44e3f3bb88",
    "tto_field/plans/execution-policy.json": "60d56e969cb5b8b6542500af00167f65c841ef13552590d75f748c688e1279f0",
    "tto_field/plans/mix-plan.json": "1ad1f202c72121e86c8e56a1f38dc72a81f23c52de7932814798fd7c8db3e4e7",
    "tto_field/plans/model-profiles.json": "0722d79cdd95d79686c852ce322bed63826cc2d72a0b83166550c35302534e11",
    "tto_field/projection.py": "6a0e7392c1117845a36c07ae3dfe6458e76e2c84960b2fcbc6fa080f7b664b05",
    "tto_field/receiver_resources.py": "cae3f2deccd16f008711dfbdabcfd53b7b4cf1a159f83752d0a5682495031781",
    "tto_field/requester.py": "ced3134782fe5e21f123317d0da18ad567c2923c2d4592106ac97ef27c1aa670",
    "tto_field/research/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "tto_field/research/models/primary.json": "dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0",
    "tto_field/research/observer-spec.json": "2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b",
    "tto_field/research/observer.py": "599e292a0000697615e76a97596f2f48c7527bc82027bacca5aea0c0fe5d4a47",
    "tto_field/runtime.py": "82115476aa55ebecb53cde08e805b597e0534368c2072c32ba867d500ba6c281",
    "tto_field/scheduler.py": "f9c16e9a26c0d322a2df7b9105cc6823ef9c2b1ef156a2764c8076dd02229b05",
    "tto_field/support.py": "4f27123760854de2ef87b6074ee94757af61730968e14b56cfe646a99e8f9440",
    "tto_field/upstream_comm/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "tto_field/upstream_comm/source_health.py": "a64753f8dc04801701e352899235a7a2e8ad326097e2b676553181fc8c11d595"
  }
}
````

### `verification/release-source-integrity.json`

SHA-256：`641d94b5240ae07f9b5f4f338acc364f2b3ba6933e003a80d8925156f54f8dcb`；字节数：231。以下为完整原文。

````json
{
  "wheel_sha256": "a9f0394097180c952d8b7f4e1cebac65fe7f2cc612c7f7189dfac6566502c9be",
  "source_files": 50,
  "all_wheel_and_source_hashes_match": true,
  "protected_source_unchanged": true,
  "Linux310_target_verified": false
}
````

### `candidate/dependency-increment.json`

SHA-256：`e4a50203c1fba349eb2a492be41ebd4a3bd3455989e2580337fcc699c46d3d34`；字节数：425。以下为完整原文。

````json
{
  "name": "threadpoolctl",
  "version": "3.6.0",
  "wheel": "threadpoolctl-3.6.0-py3-none-any.whl",
  "bytes": 18638,
  "sha256": "43a0b8fd5a2928500110039e43a5eed8480b918967083ea48dc3ab9f13c4a7fb",
  "purpose": "same-process NumPy/SciPy native-pool introspection; no runtime reset of already-loaded libraries",
  "source": "https://pypi.org/project/threadpoolctl/3.6.0/",
  "original_dependency_versions_unchanged": true
}
````

### `candidate/dependency-reference.json`

SHA-256：`3532806aeb4c91f6f54e9c323b931f05e89c9597411893936620e53ce6b93d80`；字节数：424。以下为完整原文。

````json
{
  "accepted_archive": "TTO-CPU\u65c1\u5f55\u4e0e\u9488\u5bf9\u6027\u8865\u6d4b-\u8fd0\u884c\u51c6\u5907\u8bc1\u636e\u5305.zip",
  "accepted_archive_sha256": "bc6cf12b845d11f964253346c24b254fe2bf558eb183004a2d8b0d595c5d3693",
  "original20_dependency_wheels_preserved": true,
  "new_dependency_only": "threadpoolctl==3.6.0",
  "assembled_linux310_wheels": 22,
  "old_large_wheelhouse_not_duplicated_in_minimal_zip": true
}
````

## 2. 八项最终源码全文与完整局部补丁

### `source/src/tto_field/numeric_policy.py`

SHA-256：`d27f383e49de5512316307250cf97ec1d619f40c7a0133e42ba0df6e0b13c27f`；字节数：4686。以下为完整原文。

````python
"""Process-local numeric startup contract; no sockets or device access.

Only the pinned NumPy/SciPy OpenBLAS runtime is supported. Unknown backends or
libraries loaded before this initializer are rejected, never declared verified.
"""
import copy,json,os,platform,socket,sys,time
from datetime import datetime,timezone
from pathlib import Path

ENV_KEYS=('OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS',
          'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
_receipt=None

def _utc():return datetime.now(timezone.utc).isoformat()

def _save(path,receipt):
    if path is not None:
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')

def _pool_coverage(pools,libraries):
    # The locked wheels bundle their backends in PACKAGE/.dylibs or PACKAGE.libs.
    # A pool for just one library cannot attest the other; shared/unrecognized layouts reject.
    coverage={}
    for name,lib in libraries.items():
        root=Path(lib['module']).resolve().parent
        roots=(root,root.parent/(name+'.libs'))
        coverage[name]=[p['filepath'] for p in pools if any(Path(p['filepath']).resolve().is_relative_to(r) for r in roots)]
    return coverage

def initialize(receipt_path=None):
    global _receipt
    from . import __version__
    from threadpoolctl import threadpool_info,__version__ as threadpoolctl_version
    started=time.monotonic()
    if _receipt is not None and _receipt['pid']==os.getpid():
        r=copy.deepcopy(_receipt)
        r['checked_at_utc']=_utc();r['checked_at_mono_s']=started
        r['loaded_pools']=threadpool_info()
        r['pool_coverage']=_pool_coverage(r['loaded_pools'],r['libraries'])
        r['verified']=all(r['pool_coverage'].values()) and all(p['num_threads']==1 for p in r['loaded_pools']) and all(os.environ.get(k)=='1' for k in ENV_KEYS)
        r['error']=None if r['verified'] else 'numeric_policy_changed_after_initialization'
        _save(receipt_path,r)
        if not r['verified']:raise RuntimeError(r['error'])
        return r
    r=dict(schema='TTO-NUMERIC-THREAD-POLICY-v1',candidate_version=__version__,pid=os.getpid(),host=socket.gethostname(),
           executable=sys.executable,python=sys.version,platform=platform.platform(),started_at_utc=_utc(),started_at_mono_s=started,
           inherited_environment={k:os.environ.get(k) for k in ENV_KEYS},policy={k:'1' for k in ENV_KEYS},
           policy_scope='this candidate process numeric libraries only; not Python threads or other applications',
           modules_already_loaded=[n for n in ('numpy','scipy') if n in sys.modules],
           preloaded_versions={n:getattr(sys.modules.get(n),'__version__',None) for n in ('numpy','scipy')},threadpoolctl_version=threadpoolctl_version,verified=False,error=None)
    try:
        if r['modules_already_loaded']:raise RuntimeError('numeric_libraries_loaded_before_policy')
        for key in ENV_KEYS:os.environ[key]='1'
        r['applied_at_mono_s']=time.monotonic()
        import numpy as np
        import scipy
        import scipy.linalg as la
        # Force both pinned backends to load, without loading a thermal model.
        np.dot(np.eye(2),np.eye(2));la.expm(np.zeros((2,2)))
        r['libraries']=dict(numpy=dict(version=np.__version__,module=np.__file__,blas=np.__config__.CONFIG['Build Dependencies']['blas']),
                            scipy=dict(version=scipy.__version__,module=scipy.__file__,blas=scipy.__config__.CONFIG['Build Dependencies']['blas']))
        r['extension_modules']={n:getattr(sys.modules.get(n),'__file__',None) for n in ('numpy._core._multiarray_umath','scipy.linalg._fblas','scipy.linalg._flapack')}
        r['loaded_pools']=threadpool_info()
        r['final_environment']={k:os.environ.get(k) for k in ENV_KEYS}
        supported=all('openblas' in x['blas']['name'].lower() for x in r['libraries'].values())
        r['pool_coverage']=_pool_coverage(r['loaded_pools'],r['libraries'])
        if not supported or not all(r['pool_coverage'].values()):raise RuntimeError('numeric_backend_not_verifiable_by_candidate')
        if any(p['num_threads']!=1 for p in r['loaded_pools']):raise RuntimeError('numeric_thread_pool_is_not_single_threaded')
        r['verified']=True
    except Exception as exc:
        r['error']=str(exc);r['error_class']=type(exc).__name__;r['loaded_pools']=threadpool_info()
    r['checked_at_utc']=_utc();r['checked_at_mono_s']=time.monotonic()
    _save(receipt_path,r)
    if not r['verified']:raise RuntimeError('numeric_policy_failed:'+r['error'])
    _receipt=copy.deepcopy(r)
    return r
````

### `source/src/tto_field/receiver_resources.py`

SHA-256：`cae3f2deccd16f008711dfbdabcfd53b7b4cf1a159f83752d0a5682495031781`；字节数：1985。以下为完整原文。

````python
"""Pre-sidecar admission of the existing one-second process resource sample."""
import math
CPU_LIMIT=8.0
RSS_LIMIT=128*1024**2

def baseline_admission(sample,now):
    r=dict(evaluated_mono_s=now,resource_sample=sample,cpu_limit_single_core_percent=CPU_LIMIT,
           rss_limit_bytes=RSS_LIMIT,allowed=False,reason='baseline_receiver_resources_unavailable',
           interval_contract='latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization')
    if sample is None:return r
    vals=[sample.get(k) for k in ('interval_start_mono_s','mono_s','cpu_pct_single_core','rss_bytes')]
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in vals):return r
    start,end,cpu,rss=vals;r['sample_age_s']=now-end
    if not (start>=1 and .5<=end-start<=2 and 0<=now-end<=1.5 and cpu>=0 and rss>=0):return r
    if cpu>CPU_LIMIT or rss>RSS_LIMIT:r['reason']='baseline_receiver_resource_budget_exceeded';return r
    r.update(allowed=True,reason='baseline_receiver_resources_qualified');return r


def read_sample(now,previous):
    """Unknown resource observations revoke the sample; never reuse an older good reading."""
    import psutil
    start=previous[0] if previous else None
    try:
        process=psutil.Process();ct=process.cpu_times();total=ct.user+ct.system;rss=process.memory_info().rss
        cpu=None if previous is None else 100*(total-previous[1])/(now-start)
        if not math.isfinite(total) or rss<0 or (cpu is not None and (not math.isfinite(cpu) or cpu<0)):
            raise ValueError('invalid_process_resource_counters')
        return dict(mono_s=now,interval_start_mono_s=start,cpu_pct_single_core=cpu,rss_bytes=rss,cpu_times=ct._asdict(),resource_error=None),(now,total)
    except (psutil.Error,OSError,ValueError,ZeroDivisionError) as exc:
        return dict(mono_s=now,interval_start_mono_s=start,cpu_pct_single_core=None,rss_bytes=None,cpu_times=None,resource_error=type(exc).__name__),None
````

### `source/src/tto_field/cpu_cli.py`

SHA-256：`4264c0b4a4f019c6d198d30f5b0f6b672fbac371c9cf98a6d71eef3a84842ebc`；字节数：2626。以下为完整原文。

````python
"""Offline preview or explicitly authorized capability/pilot. No implicit upgrade or device defaults."""
import argparse,asyncio,json
from pathlib import Path
from . import __version__
from .support import digest_file

def preview(c,mode):
    from .cli import preview as original
    from .cpu_pilot import PLAN,pilot_profile
    b=original(c,'diagnose' if mode=='capability' else 'execute')
    b.update(profile_sha256=digest_file(PLAN),profile=pilot_profile(),candidate_version=__version__,capability_receipt=None,
             capability_user_decision_evidence=None,instrument={'used':False},sidecar=None)
    b['authorization']['action']='readonly-diagnostic' if mode=='capability' else 'cpu-activity-pilot'
    return b

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('verify-install').add_argument('--target',action='store_true')
    for name in ('preview','capability','execute'):
        q=sub.add_parser(name);q.add_argument('--config',type=Path,required=True)
        if name=='preview':q.add_argument('--mode',choices=('capability','execute'),default='capability')
        else:
            q.add_argument('--binding',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--allow-network',action='store_true')
    # Both installed field entry points initialize before collector/numeric imports.
    for parser in sub.choices.values():parser.add_argument('--thread-policy-output',type=Path)
    a=p.parse_args(argv)
    from .numeric_policy import initialize
    receipt=a.thread_policy_output
    if receipt is None and hasattr(a,'output'):
        receipt=a.output.with_name(a.output.name+'.startup')/'thread-policy.json'
    initialize(receipt)
    from .identity import verify
    if a.cmd=='verify-install':print(json.dumps(verify(a.target),indent=2));return 0
    verify()
    from tto.config import load_config
    c=load_config(a.config,environ={})
    if a.cmd=='preview':print(json.dumps(preview(c,a.mode),ensure_ascii=False,indent=2));return 0
    if not a.allow_network:p.error('current explicit permission and --allow-network required')
    b=json.loads(a.binding.read_text())
    if not b.get('synthetic_loopback_only'):verify(target=True)
    from .runtime import run
    result=asyncio.run(run(c,b,'diagnose' if a.cmd=='capability' else 'execute',a.output,duration=60,cpu_pilot=True))
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
````

### `source/src/tto_field/cli.py`

SHA-256：`827953261847e853e851c75b850a538f2b3a912d1e76dc49bc7310305f13b787`；字节数：3367。以下为完整原文。

````python
"""Explicit commands: offline preview, authorized read-only diagnose, or authorized fixed-anchors execute."""
import argparse,asyncio,json
from pathlib import Path
from . import __version__

def preview(config,mode):
    from tto.config import public_config
    from tto.util import digest
    from tto.storage import source_identity
    from .runtime import ROOT,profile
    from .support import digest_file
    return dict(candidate_version=__version__,mode=mode,config_sha256=digest(public_config(config)),
                collector_source_sha256=source_identity()['sha256'],observer_model_sha256=digest_file(ROOT/'research/models/primary.json'),
                observer_spec_sha256=digest_file(ROOT/'research/observer-spec.json'),old_overrides=False,command_id=None,
                expected_binding='agx_info.temperature.tj',firmware_identity=None,
                authorization=dict(action='readonly-diagnostic' if mode=='diagnose' else 'fixed-anchors',command_id=None,explicit_user_start=False,evidence=None),
                note='Preview creates no network clients and never opens credential headers. No device authorization is implied.',
                request_actor_thread='01a1331a-f937-7d91-aef0-ac4f5e50bd8a' if mode=='execute' else None,
                profile=profile() if mode=='execute' else None)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('verify-install');q.add_argument('--target',action='store_true')
    for name in ['preview','diagnose','execute']:
        q=sub.add_parser(name);q.add_argument('--config',required=True,type=Path)
        if name=='preview':q.add_argument('--mode',choices=['diagnose','execute'],default='diagnose')
        else:
            q.add_argument('--binding',required=True,type=Path);q.add_argument('--output',required=True,type=Path)
            q.add_argument('--allow-network',action='store_true')
            if name=='diagnose':q.add_argument('--duration',type=float,default=300)
    # Both installed field entry points initialize before collector/numeric imports.
    for parser in sub.choices.values():parser.add_argument('--thread-policy-output',type=Path)
    a=p.parse_args(argv)
    from .numeric_policy import initialize
    receipt=a.thread_policy_output
    if receipt is None and hasattr(a,'output'):
        receipt=a.output.with_name(a.output.name+'.startup')/'thread-policy.json'
    initialize(receipt)
    from .identity import verify
    if a.command=='verify-install':
        print(json.dumps(verify(a.target),ensure_ascii=False,indent=2));return 0
    verify()
    from tto.config import load_config
    c=load_config(a.config,environ={})
    if a.command=='preview':
        print(json.dumps(preview(c,a.mode),ensure_ascii=False,indent=2));return 0
    if not a.allow_network:p.error('Run commands require --allow-network and a current bound authorization; preview is offline.')
    from .runtime import run
    b=json.loads(a.binding.read_text())
    if not b.get('synthetic_loopback_only'):verify(target=True)
    result=asyncio.run(run(c,b,a.command,a.output,duration=getattr(a,'duration',300)))
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
````

### `source/src/tto_field/identity.py`

SHA-256：`58850200044da1dc1417bec8ee805a3bca44813219a1523f325a6c8f92ee2ef1`；字节数：1558。以下为完整原文。

````python
"""Installed source verification; checks bytes without network or credential contents."""
import importlib.metadata,json,platform,sys
from pathlib import Path
from .support import digest_file
from . import __version__

def verify(target=False):
    from .numeric_policy import initialize
    numeric=initialize()
    import tto
    root=Path(__file__).resolve().parent;packages=root.parent
    if Path(tto.__file__).resolve().parent != packages/'tto':raise ValueError('TTO import is outside the isolated candidate')
    manifest=json.loads((root/'candidate-files.json').read_text())
    for name,value in manifest['files'].items():
        if digest_file(packages/name)!=value:raise ValueError('installed candidate bytes differ: '+name)
    if tto.__version__!='0.2.4':raise ValueError('native 0.2.4 version contract changed')
    if target and (sys.version_info[:2]!=(3,10) or platform.system()!='Linux' or platform.machine()!='x86_64'):
        raise ValueError('field target is Linux x86_64 CPython3.10; use isolated target environment')
    from tto.storage import source_identity
    return dict(candidate_version=__version__,native_version=tto.__version__,native_source_identity=source_identity(),
                checked_files=len(manifest['files']),python=sys.version,platform=platform.platform(),machine=platform.machine(),
                dependencies={x:importlib.metadata.version(x) for x in ['aiohttp','python-socketio','psutil','numpy','scipy','threadpoolctl']},
                target_environment_checked=target,numeric_thread_policy=numeric)
````

### `source/src/tto_field/runtime.py`

SHA-256：`82115476aa55ebecb53cde08e805b597e0534368c2072c32ba867d500ba6c281`；字节数：25845。以下为完整原文。

````python
"""One native collector, its processed output, one observer, one scheduling/request executor.
This module contains no device defaults. Only an explicit CLI invocation with a current bound grant
constructs network clients. Diagnostic runs never instantiate Requester.
"""
import asyncio,copy,hashlib,json,os,threading,time
from pathlib import Path
from .support import Clock,Evidence,write,utc,digest_file
from .gate import readiness
from .scheduler import Scheduler,resolve_plan
from . import __version__

ROOT=Path(__file__).resolve().parent
ACTOR='01a1331a-f937-7d91-aef0-ac4f5e50bd8a'
MODEL_STATE_MAX_AGE_S=2.5


def profile():
    return resolve_plan(json.loads((ROOT/'plans/mix-plan.json').read_text()),'fixed-anchors')


def verify_grant(c,binding,mode,duration,pilot=False):
    from tto.config import public_config
    from tto.util import digest
    from tto.storage import source_identity
    a=binding['authorization']
    if binding.get('old_overrides') is not False:raise ValueError('old overrides are forbidden')
    if not binding.get('command_id') or a.get('command_id')!=binding['command_id']:raise ValueError('current command authorization missing')
    action='readonly-diagnostic' if mode=='diagnose' else ('cpu-activity-pilot' if pilot else 'fixed-anchors')
    if a.get('action')!=action or a.get('explicit_user_start') is not True or not a.get('evidence'):
        raise ValueError('explicit current-run mode authorization required')
    if binding.get('config_sha256')!=digest(public_config(c)):raise ValueError('configuration identity mismatch')
    if binding.get('collector_source_sha256')!=source_identity()['sha256']:raise ValueError('installed runtime identity mismatch')
    if binding.get('observer_model_sha256')!=digest_file(ROOT/'research/models/primary.json') or binding.get('observer_spec_sha256')!=digest_file(ROOT/'research/observer-spec.json'):
        raise ValueError('frozen observer identity mismatch')
    if binding.get('expected_binding')!='agx_info.temperature.tj':raise ValueError('unexpected control binding')
    if (c['network']['request_timeout_s'],c['tianshan']['fan_poll_interval_s'],c['tianshan']['temp_poll_interval_s'],c['features']['fan_max_age_s'])!=(2.,1.,5.,2.5):
        raise ValueError('original timeout/poll/TTL contract must be preserved')
    if binding.get('synthetic_loopback_only'):
        import ipaddress
        from urllib.parse import urlsplit
        origins=[c[k]['base_url'] for k in ('orin','tianshan')]
        if mode=='execute':origins.append(binding['inference']['base_url'])
        if not all(ipaddress.ip_address(urlsplit(u).hostname).is_loopback for u in origins):raise ValueError('synthetic mode is numeric loopback only')
    if mode=='diagnose':
        if not 0<duration<=300:raise ValueError('diagnostic record duration must be <=300s')
    else:
        if binding.get('request_actor_thread')!=ACTOR:raise ValueError('only the designated inference actor launches execute')
        m=binding['inference']
        if m.get('model')!='RM-01 VLM' and not binding.get('synthetic_loopback_only'):raise ValueError('first profile uses original resident RM-01 VLM')
        capacity=m.get('confirmed_client_slots')
        capacity_ok=(type(capacity) is int and capacity>=1) if pilot else capacity==4
        if not binding.get('synthetic_loopback_only') and (not m.get('identity_evidence') or not capacity_ok):
            raise ValueError('current model identity and client slot capacity evidence required')
        if m.get('max_tokens')!=256 or m.get('request_timeout_s')!=30:raise ValueError('request contract changed')
        if not binding.get('synthetic_loopback_only'):
            original=json.loads((ROOT/'plans/model-profiles.json').read_text())['existing-dense-27b-confirm-before-live']
            if m.get('messages')!=original['payload']['messages'] or m.get('stream') is not True or m.get('sampling',{})!=original['sampling']:
                raise ValueError('frozen inference payload changed')
        ins=binding['instrument']
        if pilot and ins.get('used') is False:return binding
        anchor=ins['clock_start'];p=Path(anchor['path'])
        if not ins.get('recording') or not ins.get('probe_fixed') or anchor.get('command_id')!=binding['command_id'] or digest_file(p)!=anchor['sha256']:
            raise ValueError('current instrument/clock evidence missing or mismatched')
        anchor['verified_file_sha256']=anchor['sha256']
        if not anchor.get('timezone') or not anchor.get('display_resolution_s') or 'uncertainty_s' not in anchor:
            raise ValueError('clock timezone/resolution/unknown error must be explicit')
    return binding


class Pipeline:
    """Called only from the native collector's single writer thread, after native processing."""
    def __init__(self,out,config,binding,mode,clock,evidence):
        self.out=out;self.config=config;self.binding=binding;self.mode=mode;self.clock=clock;self.evidence=evidence
        self.projection=self.observer=self.communication=None;self.latest=None;self.lock=threading.Lock();self.engine_id=None;self.callbacks=0;self.run_id=None;self.fan_success_times=[]
    def on_record(self,raw,processed,engine):
        from .projection import SavedStream
        from .research.observer import ThermalObserver
        try:
            if self.projection is None:
                manifests=list((self.out/'native').glob('run-*/manifest.json'))
                if len(manifests)!=1:raise ValueError('expected exactly one native collector journal')
                manifest=json.loads(manifests[0].read_text())
                if manifest['observer_run_id']!=raw['observer_run_id']:raise ValueError('native run mismatch')
                spec=json.loads((ROOT/'research/observer-spec.json').read_text())
                self.projection=SavedStream(manifest,spec,engine);self.observer=ThermalObserver(spec);self.engine_id=id(engine);self.run_id=raw['observer_run_id']
                from .comm_bridge import CommunicationBridge
                self.communication=CommunicationBridge(manifest,engine)
                self.expected=dict(run_id=self.run_id,config_sha256=manifest['config_sha256'],collector_source_sha256=manifest['source_identity']['sha256'],
                                   model_sha256=spec['model_sha256'],spec_sha256=digest_file(ROOT/'research/observer-spec.json'))
                if self.expected['collector_source_sha256']!=self.binding['collector_source_sha256']:raise ValueError('native collector source identity drift')
                write(self.out/'native-binding.json',dict(command_id=self.binding['command_id'],native_run_id=self.run_id,native_manifest=str(manifests[0].relative_to(self.out)),
                      expected_identity=self.expected,clock=self.clock.bracket(),collector_engine_instance_id=self.engine_id,
                      observer_instance_id=id(self.observer),projection_instance_id=id(self.projection),native_writer_thread_id=threading.get_ident()))
            if id(engine)!=self.engine_id or raw['observer_run_id']!=self.run_id:raise ValueError('second engine/run prohibited')
            comm=self.communication.feed(raw,processed)
            frame=self.projection.feed(raw,processed)
            before_validity={k:(v or {}).get('raw_valid',False) for k,v in frame['measurement'].items()}
            if not comm['measurement']['TJ_and_rails']['raw_valid']:
                for name in ['tj','power']:
                    if frame['measurement'][name]:frame['measurement'][name]['raw_valid']=False
                frame['new_TJ']=False
            s=self.observer.step(frame);generated=time.monotonic()
            if raw['kind']=='fan' and engine.fan and engine.fan['ref']==raw['ref']:self.fan_success_times.append(raw['mono_s'])
            env=dict(schema='TTO-FIELD-CONSUMABLE-STATE-v1',state=s,mode=self.mode,binding=self.binding,
                     native_run_id=self.run_id,expected_identity=self.expected,process_clock_domain=self.clock.domain,
                     communication=comm,native_projected_validity_before_I02=before_validity,
                     clock=dict(domain=self.clock.domain,session_origin_mono_s=self.clock.origin,observer_input_mono_s=raw['mono_s'],
                                generated_at_mono_s=generated,generated_at_utc=utc(),
                                model_consumable_until_mono_s=min(generated+MODEL_STATE_MAX_AGE_S,raw['mono_s']+MODEL_STATE_MAX_AGE_S)),
                     generation_evidence=dict(origin='actual native on_record callback after engine.process',native_ref=raw['ref'],
                                              native_engine_instance_id=id(engine),I02_shared_native_engine_instance_id=id(self.communication.view.engine),
                                              I02_processed_views=self.communication.view.process_calls,model_math_source_unchanged=True,
                                              research_snapshot_clock_label='upstream literal retained; actual clocks are in this envelope'))
            self.evidence.append('states.jsonl',env)
            with self.lock:self.latest=env
            self.callbacks+=1
        except Exception as exc:
            # Native writer already handles ValueError, preserving its raw journal on a projection failure.
            raise ValueError('field_projection_failed:'+type(exc).__name__) from exc
    def get(self):
        with self.lock:return self.latest


async def run(config,binding,mode,out,duration=300,probe_profile=None,cpu_pilot=False):
    from .numeric_policy import initialize
    numeric_policy=initialize()
    from tto.collector import collect
    from tto.storage import InstanceLock,source_identity
    from tto.config import public_config
    from tto.util import digest
    out=Path(out);binding=copy.deepcopy(binding)
    if cpu_pilot:
        from .cpu_pilot import verify_pilot_grant
        verify_pilot_grant(config,binding,mode,duration)
    else:verify_grant(config,binding,mode,duration)
    # Load numerical dependencies before constructing any network client.
    from .research.observer import ThermalObserver
    chosen=profile()
    if cpu_pilot:
        from .cpu_pilot import pilot_profile
        chosen=pilot_profile()
    if probe_profile is not None:
        if cpu_pilot:raise ValueError('pilot has no live plan override')

        # Internal integration tests only. There is no CLI plan override, and nonloopback is rejected.
        import ipaddress
        from urllib.parse import urlsplit
        origins=[config[k]['base_url'] for k in ('orin','tianshan')]+[binding['inference']['base_url']]
        if not binding.get('synthetic_loopback_only') or not all(ipaddress.ip_address(urlsplit(x).hostname).is_loopback for x in origins):
            raise ValueError('probe profile allowed only on own numeric loopback services')
        chosen=probe_profile
    clock=Clock();stop=asyncio.Event();tasks={};clients=[];scheduler=None;native_task=None
    # Same user-wide native lock still guards collector instances. This lock also covers preparation and drain.
    with InstanceLock(f'/tmp/tto-field-entry-{os.getuid()}.lock'):
        out.parent.mkdir(parents=True,exist_ok=True)
        from .scheduler import Registry
        Registry(out.parent/'.tto-command-ledger').claim(binding['command_id'],binding['command_id'])
        out.mkdir(mode=0o700)
        ev=Evidence(out);pipeline=Pipeline(out,config,binding,mode,clock,ev)
        write(out/'thread-policy.json',numeric_policy)
        stopped_reason=None;scheduler_event_cursor=0;clock_reminder_sent=False;totals={k:0. for k in ['observed_s','measurement_usable_s','model_usable_s','context_ready_s','joint_ready_s','work_paused_s','tj_usable_s','rail_usable_s','PWM_usable_s','temp_context_usable_s']}
        phase_seconds={};resource_prev=None
        previous=None;previous_gate=None;previous_work=False;last_resources=0.;protocol_records=[]
        latest_resources=None;resource_seq=0;baseline_checked=False
        def emit(name,**details):
            row=dict(event=name,mono_s=clock.now(),at_utc=utc(),command_id=binding['command_id'],native_run_id=pipeline.run_id,**details)
            ev.append('protocol.jsonl',row)
            if name=='request_end':protocol_records.append(row)
        write(out/'launch.json',dict(version=__version__,mode=mode,command_id=binding['command_id'],authorization=binding['authorization'],
              clock_start=clock.bracket(),config=public_config(config),config_sha256=digest(public_config(config)),
              collector_source_identity=source_identity(),binding=binding,profile=chosen if mode=='execute' else None,
              diagnostics_seconds=duration if mode=='diagnose' else None,control_changes=False,
              synthetic_loopback_only=binding.get('synthetic_loopback_only',False),firmware_identity=binding.get('firmware_identity')))
        if mode=='execute' and binding.get('instrument',{}).get('recording'):
            p=Path(binding['instrument']['clock_start']['path']);(out/'clock-evidence').mkdir();(out/'clock-evidence/start.original').write_bytes(p.read_bytes())
        collector_duration=duration if mode=='diagnose' else chosen['hard_limit_seconds']
        native_task=asyncio.create_task(collect(config,collector_duration,data_root=out/'native',episode=binding['command_id'],
                   deployment=dict(field_entry_version=__version__,field_command_id=binding['command_id'],field_clock_domain=clock.domain,
                                   firmware_identity=binding.get('firmware_identity')),stop_event=stop,on_record=pipeline.on_record),name='ONLY-native-collector')
        emit('native_collector_task_started',task_identity=id(native_task),collector_instances_created=1)
        sidecar=None
        if cpu_pilot:
            from .cpu_transport import Sidecar
            sidecar=Sidecar(binding.get('sidecar'),out,clock,pipeline,ev,source_duration=30 if mode=='diagnose' else 1170)
        result=None;error=None
        try:
            if mode=='execute':
                from .requester import Requester
                # One executor owns up to four per-slot sessions; no other request producer exists.
                clients=[Requester(binding['inference'],out,clock,emit) for _ in range(1 if cpu_pilot else 4)]
                for client in clients:await client.open()
                resident=await asyncio.wait_for(clients[0].check_resident_idle(),min(30.,chosen['preparation_reserve_seconds']))
                write(out/'resident-idle-check.json',resident)
            while True:
                now=clock.now();latest=pipeline.get();run_id=pipeline.run_id or 'PENDING-NATIVE-UUID'
                # Persist the existing1s process sample before the once-only baseline decision.
                if now-last_resources>=1:
                    from .receiver_resources import read_sample
                    latest_resources,resource_prev=read_sample(now,resource_prev);resource_seq+=1
                    latest_resources.update(resource_seq=resource_seq,field_log_bytes=ev.bytes,
                        native_log_bytes=sum(f.stat().st_size for f in (out/'native').rglob('*') if f.is_file()))
                    ev.append('resources.jsonl',latest_resources);last_resources=now
                    if sidecar and sidecar.process and not sidecar.closed:
                        if latest_resources['resource_error']:
                            await sidecar.halt('receiver_resource_measurement_unavailable')
                        else:await sidecar.resource(latest_resources['cpu_pct_single_core'],latest_resources['rss_bytes'])
                user_stop=(out/'STOP').exists()
                budget=duration if mode=='diagnose' else chosen['hard_limit_seconds']-chosen['cleanup_reserve_seconds']
                if sidecar and not sidecar.closed and not user_stop and now<budget:
                    if now>=30 and not baseline_checked:
                        from .receiver_resources import baseline_admission
                        admission=baseline_admission(latest_resources,now);baseline_checked=True
                        write(out/'baseline-resource-admission.json',admission)
                        sidecar.record('baseline_resource_admission',admission=admission)
                        if not admission['allowed']:await sidecar.halt(admission['reason'])
                    if not sidecar.closed:await sidecar.tick(now,latest)
                gate=readiness(latest,now,run_id,formal=True)
                if previous is not None:
                    dt=now-previous;totals['observed_s']+=dt
                    for key,layer in [('measurement_usable_s','collection_available'),('model_usable_s','model_available'),('context_ready_s','field_safety_available')]:
                        totals[key]+=dt*bool(previous_gate[layer])
                    totals['joint_ready_s']+=dt*bool(previous_gate['collection_available'] and previous_gate['model_available'] and previous_gate['field_safety_available'])
                    totals['work_paused_s']+=dt*bool(previous_work and not previous_gate['start_allowed'])
                    phase_seconds[previous_gate['observer_state']]=phase_seconds.get(previous_gate['observer_state'],0.)+dt
                    for label,key in [('tj_usable_s','tj'),('rail_usable_s','power'),('PWM_usable_s','last_successful_pwm'),('temp_context_usable_s','control_context')]:
                        totals[label]+=dt*bool(previous_gate.get('measurement_current',{}).get(key,False))
                previous=now;previous_gate=gate
                ev.append('admission.jsonl',dict(evaluated_mono_s=time.monotonic(),scheduler_mono_s=now,at_utc=utc(),command_id=binding['command_id'],native_run_id=pipeline.run_id,**gate))
                user_stop=(out/'STOP').exists()
                if mode=='diagnose':
                    if user_stop:stopped_reason='user_stop';break
                    if now>=duration:stopped_reason='diagnostic_duration';break
                    if native_task.done():stopped_reason='collector_exited';break
                else:
                    if scheduler is None and pipeline.run_id:
                        scheduler_type=Scheduler
                        if cpu_pilot:
                            from .cpu_pilot import PilotScheduler
                            scheduler_type=PilotScheduler
                        scheduler=scheduler_type(chosen,dict(max_data_unready_seconds=60,max_request_seconds=60,max_total_requests=4096),pipeline.run_id,binding['command_id'],formal=True)
                    if scheduler is not None:
                        if cpu_pilot and now>=chosen['preparation_reserve_seconds'] and sidecar.status!='running':
                            scheduler.stop('sidecar_unavailable_no_meaningful_pilot',now=now)
                        if native_task.done():scheduler.stop('collector_exited',now=now)
                        if stop.is_set():scheduler.stop('collector_or_signal_stop',now=now)
                        completed=[]
                        for ident,task in list(tasks.items()):
                            if task.done():
                                completed.append(task.result());del tasks[ident]
                        actions,gate=scheduler.tick(now,latest,completed,user_stop=user_stop)
                        previous_work=(scheduler.state=='stage' and scheduler.profile['stages'][scheduler.index]['kind']=='work' and now<scheduler.window_end)
                        for action in actions:
                            ident=action['request_id']
                            if action['kind']=='submit':
                                tasks[ident]=asyncio.create_task(clients[action['slot']].request(ident,action['timeout_s']),name='ONLY-executor-'+ident)
                            else:
                                task=tasks.pop(ident);task.cancel();await asyncio.gather(task,return_exceptions=True)
                        for event in scheduler.events[scheduler_event_cursor:]:
                            ev.append('scheduler-events.jsonl',dict(event,recorded_at_utc=utc()))
                        scheduler_event_cursor=len(scheduler.events)
                        if 0<=scheduler.index<len(scheduler.profile['stages']) and scheduler.profile['stages'][scheduler.index]['kind']=='final_recovery' and not clock_reminder_sent and now>=scheduler.window_end-120:
                            emit('instrument_clock_end_reminder',remaining_s=max(0.,scheduler.window_end-now))
                            clock_reminder_sent=True
                        if scheduler.terminal:stopped_reason=scheduler.reason;break
                    elif user_stop or native_task.done() or now>=chosen['preparation_reserve_seconds']:
                        stopped_reason='user_stop' if user_stop else 'collector_exited' if native_task.done() else 'preparation_budget_exhausted';break
                await asyncio.sleep(.1)
        except BaseException as exc:
            error=exc;stopped_reason='entry_error:'+type(exc).__name__
        finally:
            stop.set()
            if sidecar:await sidecar.close()
            for task in tasks.values():task.cancel()
            await asyncio.gather(*tasks.values(),return_exceptions=True)
            for client in clients:await client.close()
            try:
                result=await asyncio.wait_for(asyncio.shield(native_task),max(.01,min(chosen['cleanup_reserve_seconds'],chosen['hard_limit_seconds']-clock.now())) if mode=='execute' else 30.)
            except BaseException as exc:
                native_task.cancel();await asyncio.gather(native_task,return_exceptions=True)
                error=error or exc;stopped_reason='collector_cleanup_failed:'+type(exc).__name__
            if scheduler:
                for row in scheduler.events[scheduler_event_cursor:]:ev.append('scheduler-events.jsonl',dict(row,recorded_at_utc=utc()))
                recorded=set()
                for row in scheduler.requests:
                    ev.append('requests.jsonl',row);recorded.add(row['request_id'])
                for row in protocol_records:
                    if row['request_id'] not in recorded:ev.append('requests.jsonl',row)
            if not scheduler:
                # Diagnostic mode gets an explicit empty request ledger, never a Requester.
                (out/'requests.jsonl').touch(mode=0o600,exist_ok=False)
            ev.close()
            success_gaps=[b-a for a,b in zip(pipeline.fan_success_times,pipeline.fan_success_times[1:])]
            if mode=='diagnose':
                write(out/'diagnostic-precheck.json',dict(last_evaluation=previous_gate,time_coverage=totals,phase_seconds=phase_seconds,
                      current_measurement_model_context_ready=bool(previous_gate and all(previous_gate[k] for k in ['collection_available','model_available','field_safety_available'])),
                      load_authorized=False,automatic_upgrade_to_mixed=False,
                      note='Snapshot/time coverage only. New current authorization, instrument and fresh preflight remain required; not a root cause fix.'))
            write(out/'summary.json',dict(mode=mode,command_id=binding['command_id'],native_run_id=pipeline.run_id,reason=stopped_reason,
                  elapsed_s=clock.now(),time_coverage=totals,phase_seconds=phase_seconds,
                  fan_success_intervals=dict(count=len(success_gaps),max_s=max(success_gaps) if success_gaps else None,
                                             over_original_2_5s=sum(x>2.5 for x in success_gaps)),protocol_requests=len(protocol_records),
                  successful_requests=sum(r['status']=='completed' for r in protocol_records),
                  server_completion_unknown=any(r['status']!='completed' for r in protocol_records),
                  schedule_completed=bool(scheduler and scheduler.reason=='completed'),
                  workload_intent='completed_with_pauses_review_exposure' if totals['work_paused_s']>0 else 'evaluate_actual_protocol_GPU_rails_not_client_slots',
                  collector_task_identity=id(native_task),collector_engine_instance_id=pipeline.engine_id,observer_instances_created=int(pipeline.observer is not None),
                  native_callbacks=pipeline.callbacks,native_run_directories=len(list((out/'native').glob('run-*'))),
                  I02_shared_engine_instance_id=id(pipeline.communication.view.engine) if pipeline.communication else None,
                  I02_preprocessed_views=pipeline.communication.view.process_calls if pipeline.communication else 0,
                  requester_sessions_all_closed=all(client.session.closed for client in clients if client.session is not None),
                  cpu_pilot_profile=cpu_pilot,sidecar_status=sidecar.status if sidecar else None,requester_instances_created=len(clients),request_executor_instances_created=int(bool(clients)),
                  own_async_tasks_remaining=sum(not t.done() for t in [native_task,*tasks.values()]),
                  collector_summary=result[1] if result else None,clock_end=clock.bracket(),control_changes=False,
                  field_proven=False,synthetic_loopback_only=binding.get('synthetic_loopback_only',False)))
            write(out/'instrument-link.pending.json',dict(native_run_id=pipeline.run_id,command_id=binding['command_id'],
                  mode=mode,original_csv_sha256=None,end_clock_evidence=None,
                  note='Diagnostic needs no instrument. Mixed attachments use a fresh sidecar directory and keep original run index unchanged.'))
            write(out/'files.json',{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':digest_file(p)} for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'files.json'})
        if error:raise error
        return json.loads((out/'summary.json').read_text())
````

### `source/src/tto_field/cpu_pilot.py`

SHA-256：`36861ae379d9c1a56a8ab2584aa24b23deb0a7d48dc758e6958015bbd1fc2f2f`；字节数：6946。以下为完整原文。

````python
"""Count-based profile. Reuses native gate, original Requester and bounded stop semantics."""
import json
from pathlib import Path
from . import __version__
from .scheduler import Scheduler
from .gate import readiness
from .support import digest_file

PLAN=Path(__file__).with_name('plans')/'cpu-pilot.json'

def pilot_profile():
    p=json.loads(PLAN.read_text());stages=[dict(kind='background',seconds=180)]
    for wait in p['isolated_post_completion_waits_s']:
        stages.extend([dict(kind='work',seconds=30,concurrency=1),dict(kind='recovery',seconds=wait)])
    stages.extend(dict(kind='work',seconds=30,concurrency=1) for _ in range(6))
    stages.append(dict(kind='final_recovery',seconds=180))
    return dict(id='cpu-activity-pilot-v1',stages=stages,hard_limit_seconds=1200,preparation_reserve_seconds=60,
                cleanup_reserve_seconds=120,drain_per_work_max_seconds=30,nominal_worst_normal_s=1170)

def sidecar_identity(side):
    from tto.util import digest
    return digest({k:side.get(k) for k in ['transport','host','remote_python','source_script_sha256','source_config_sha256','query_target_s']})

def verify_pilot_grant(c,b,mode,duration):
    from .runtime import verify_grant
    if b.get('profile_sha256')!=digest_file(PLAN):raise ValueError('pilot plan identity mismatch')
    if b.get('cpu_pilot_verified'):raise ValueError('verified marker is internal, not a user bypass')
    if mode=='diagnose' and duration!=60:raise ValueError('capability check is one bounded 60s diagnostic')
    side=b.get('sidecar')
    if not side or side.get('query_target_s')!=.2:raise ValueError('explicit 200ms sidecar configuration required')
    if not b.get('synthetic_loopback_only'):
        import shlex
        required=['existing_control_socket','remote_python','remote_source_script','remote_source_config','remote_source_permission','command_id']
        if any(not side.get(k) for k in required) or side['command_id']!=b['command_id']:
            raise ValueError('existing Thor connection and exact source paths must be bound')
        if not side.get('source_script_sha256') or not side.get('source_config_sha256'):
            raise ValueError('source installation/configuration identity evidence missing')
        if side.get('transport')!='existing_ssh_mux' or side.get('host')!='rm01@10.10.99.98':
            raise ValueError('only existing approved Thor SSH multiplexed connection')
        # Validate before mutation; config SHA for capability is of user-visible configuration.
        if 'argv' in side:raise ValueError('arbitrary live sidecar commands are forbidden')
    verify_grant(c,b,mode,duration,pilot=True)
    if mode=='execute' and not b.get('synthetic_loopback_only'):
        # A separate, reviewable capability receipt and user decision; never inferred from a model number.
        ref=b['capability_receipt'];path=Path(ref['path'])
        if digest_file(path)!=ref['sha256']:raise ValueError('capability receipt identity mismatch')
        cap=json.loads(path.read_text())
        if cap.get('candidate_version')!=__version__ or cap.get('config_sha256')!=b['config_sha256'] or cap.get('sidecar_config_sha256')!=sidecar_identity(side):
            raise ValueError('capability identity differs from proposed pilot')
        if cap.get('qualified') is not True or cap.get('evaluation_scope') not in ('source_potential','arrival_side') or not cap.get('measured_resolution_evidence') or not cap.get('resource_check_evidence'):
            raise ValueError('capability evidence/meaning not established')
        if not b.get('capability_user_decision_evidence'):raise ValueError('separate user decision to run 12 requests required')
    b['cpu_pilot_verified']=True

class PilotScheduler(Scheduler):
    def tick(self,now,snapshot,completed=(),user_stop=False):
        if now<self.now:raise ValueError('monotonic clock moved backwards')
        self.now=float(now);actions=[];gate=readiness(snapshot,now,self.run_id,self.formal)
        ended=False
        for result in completed:
            ident=result['request_id']
            if ident not in self.pending:raise ValueError('unknown or duplicate completion')
            row=dict(self.pending.pop(ident),**result);self.requests.append(row);self.emit('request_end',result=row)
            if result['status']!='completed':self.unknown_requests.append(ident);self.stop('request_termination_unknown',now=now)
            else:ended=True
        if user_stop:self.stop('user_stop',now=now)
        if gate['explicit_stop']:self.stop('explicit_protection_or_mode_binding',now=now)
        if now>=self.profile['hard_limit_seconds']-self.profile['cleanup_reserve_seconds']:self.stop('hard_budget_cleanup_boundary',now=now)
        if self.state not in ('stopping','terminal'):
            if gate['start_allowed']:self.unready_since=None
            else:
                if self.unready_since is None:self.unready_since=now;self.emit('input_unready',layers=gate)
                if now-self.unready_since>=60:self.stop('data_or_observer_unavailable_too_long',now=now)
        if self.state=='prepare' and now>=self.profile['preparation_reserve_seconds']:
            if gate['start_allowed']:self.emit('preparation_ready',layers=gate);self.next_phase()
            else:self.stop('preparation_budget_exhausted',now=now)
        elif self.state=='stage':
            stage=self.profile['stages'][self.index]
            if stage['kind']=='work':
                if ended:self.next_phase()
                elif not self.pending and gate['start_allowed']:
                    if self.submitted>=12:self.stop('request_count_cap',now=now)
                    else:
                        self.submitted+=1;ident=f'R{self.submitted:04d}'
                        row=dict(request_id=ident,slot=0,stage_index=self.index,submit_mono_s=now,timeout_s=30,repeat_key=None)
                        self.pending[ident]=row;actions.append(dict(kind='submit',**row));self.emit('request_submit',**row)
                        self.peak=max(self.peak,len(self.pending))
            elif now>=self.window_end:self.next_phase()
        if self.state=='stopping':
            if self.pending and (now>=self.profile['hard_limit_seconds']-self.profile['cleanup_reserve_seconds'] or now-self.stopping_at>=30):
                for ident,row in list(self.pending.items()):
                    self.unknown_requests.append(ident);actions.append(dict(kind='cancel_client',request_id=ident))
                    result=dict(row,status='termination_unknown',client_end_mono_s=now,server_state='unknown',error='bounded_stop_client_only')
                    self.requests.append(result);self.emit('request_end',result=result)
                self.pending.clear();self.emit('server_completion_unconfirmed',request_ids=self.unknown_requests)
            if not self.pending:self.state='terminal';self.emit('run_end',reason=self.reason,elapsed_s=now)
        return actions,gate
````

### `source/src/tto_field/__init__.py`

SHA-256：`ad02c64181eea81da52a038072ec1f200a92f7255a49080e06187074bf0f574b`；字节数：28。以下为完整原文。

````python
__version__ = "0.2.4+cpu.3"
````

以下为封存的完整 `cpu3.patch`，包含该包实际记录的局部改动，不裁剪成仅有八个模块的片段。

### `candidate/cpu3.patch`

SHA-256：`ca974a1d8348b1f9cad355efe05b23433b007d843e313299985a91581bce1eb4`；字节数：24583。以下为完整原文。

````diff
--- cpu.2/tto_field/__init__.py
+++ cpu.3/tto_field/__init__.py
@@ -1 +1 @@
-__version__ = "0.2.4+cpu.2"
+__version__ = "0.2.4+cpu.3"
--- cpu.2/tto_field/cli.py
+++ cpu.3/tto_field/cli.py
@@ -29,7 +29,14 @@
             q.add_argument('--binding',required=True,type=Path);q.add_argument('--output',required=True,type=Path)
             q.add_argument('--allow-network',action='store_true')
             if name=='diagnose':q.add_argument('--duration',type=float,default=300)
+    # Both installed field entry points initialize before collector/numeric imports.
+    for parser in sub.choices.values():parser.add_argument('--thread-policy-output',type=Path)
     a=p.parse_args(argv)
+    from .numeric_policy import initialize
+    receipt=a.thread_policy_output
+    if receipt is None and hasattr(a,'output'):
+        receipt=a.output.with_name(a.output.name+'.startup')/'thread-policy.json'
+    initialize(receipt)
     from .identity import verify
     if a.command=='verify-install':
         print(json.dumps(verify(a.target),ensure_ascii=False,indent=2));return 0
--- cpu.2/tto_field/cpu_cli.py
+++ cpu.3/tto_field/cpu_cli.py
@@ -22,7 +22,14 @@
         if name=='preview':q.add_argument('--mode',choices=('capability','execute'),default='capability')
         else:
             q.add_argument('--binding',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--allow-network',action='store_true')
+    # Both installed field entry points initialize before collector/numeric imports.
+    for parser in sub.choices.values():parser.add_argument('--thread-policy-output',type=Path)
     a=p.parse_args(argv)
+    from .numeric_policy import initialize
+    receipt=a.thread_policy_output
+    if receipt is None and hasattr(a,'output'):
+        receipt=a.output.with_name(a.output.name+'.startup')/'thread-policy.json'
+    initialize(receipt)
     from .identity import verify
     if a.cmd=='verify-install':print(json.dumps(verify(a.target),indent=2));return 0
     verify()
--- cpu.2/tto_field/cpu_pilot.py
+++ cpu.3/tto_field/cpu_pilot.py
@@ -1,6 +1,7 @@
 """Count-based profile. Reuses native gate, original Requester and bounded stop semantics."""
 import json
 from pathlib import Path
+from . import __version__
 from .scheduler import Scheduler
 from .gate import readiness
 from .support import digest_file
@@ -44,7 +45,7 @@
         ref=b['capability_receipt'];path=Path(ref['path'])
         if digest_file(path)!=ref['sha256']:raise ValueError('capability receipt identity mismatch')
         cap=json.loads(path.read_text())
-        if cap.get('candidate_version')!='0.2.4+cpu.2' or cap.get('config_sha256')!=b['config_sha256'] or cap.get('sidecar_config_sha256')!=sidecar_identity(side):
+        if cap.get('candidate_version')!=__version__ or cap.get('config_sha256')!=b['config_sha256'] or cap.get('sidecar_config_sha256')!=sidecar_identity(side):
             raise ValueError('capability identity differs from proposed pilot')
         if cap.get('qualified') is not True or cap.get('evaluation_scope') not in ('source_potential','arrival_side') or not cap.get('measured_resolution_evidence') or not cap.get('resource_check_evidence'):
             raise ValueError('capability evidence/meaning not established')
--- cpu.2/tto_field/identity.py
+++ cpu.3/tto_field/identity.py
@@ -5,6 +5,8 @@
 from . import __version__
 
 def verify(target=False):
+    from .numeric_policy import initialize
+    numeric=initialize()
     import tto
     root=Path(__file__).resolve().parent;packages=root.parent
     if Path(tto.__file__).resolve().parent != packages/'tto':raise ValueError('TTO import is outside the isolated candidate')
@@ -17,5 +19,5 @@
     from tto.storage import source_identity
     return dict(candidate_version=__version__,native_version=tto.__version__,native_source_identity=source_identity(),
                 checked_files=len(manifest['files']),python=sys.version,platform=platform.platform(),machine=platform.machine(),
-                dependencies={x:importlib.metadata.version(x) for x in ['aiohttp','python-socketio','psutil','numpy','scipy']},
-                target_environment_checked=target)
+                dependencies={x:importlib.metadata.version(x) for x in ['aiohttp','python-socketio','psutil','numpy','scipy','threadpoolctl']},
+                target_environment_checked=target,numeric_thread_policy=numeric)
--- cpu.2/tto_field/numeric_policy.py
+++ cpu.3/tto_field/numeric_policy.py
@@ -0,0 +1,77 @@
+"""Process-local numeric startup contract; no sockets or device access.
+
+Only the pinned NumPy/SciPy OpenBLAS runtime is supported. Unknown backends or
+libraries loaded before this initializer are rejected, never declared verified.
+"""
+import copy,json,os,platform,socket,sys,time
+from datetime import datetime,timezone
+from pathlib import Path
+
+ENV_KEYS=('OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS',
+          'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
+_receipt=None
+
+def _utc():return datetime.now(timezone.utc).isoformat()
+
+def _save(path,receipt):
+    if path is not None:
+        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
+        with path.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
+
+def _pool_coverage(pools,libraries):
+    # The locked wheels bundle their backends in PACKAGE/.dylibs or PACKAGE.libs.
+    # A pool for just one library cannot attest the other; shared/unrecognized layouts reject.
+    coverage={}
+    for name,lib in libraries.items():
+        root=Path(lib['module']).resolve().parent
+        roots=(root,root.parent/(name+'.libs'))
+        coverage[name]=[p['filepath'] for p in pools if any(Path(p['filepath']).resolve().is_relative_to(r) for r in roots)]
+    return coverage
+
+def initialize(receipt_path=None):
+    global _receipt
+    from . import __version__
+    from threadpoolctl import threadpool_info,__version__ as threadpoolctl_version
+    started=time.monotonic()
+    if _receipt is not None and _receipt['pid']==os.getpid():
+        r=copy.deepcopy(_receipt)
+        r['checked_at_utc']=_utc();r['checked_at_mono_s']=started
+        r['loaded_pools']=threadpool_info()
+        r['pool_coverage']=_pool_coverage(r['loaded_pools'],r['libraries'])
+        r['verified']=all(r['pool_coverage'].values()) and all(p['num_threads']==1 for p in r['loaded_pools']) and all(os.environ.get(k)=='1' for k in ENV_KEYS)
+        r['error']=None if r['verified'] else 'numeric_policy_changed_after_initialization'
+        _save(receipt_path,r)
+        if not r['verified']:raise RuntimeError(r['error'])
+        return r
+    r=dict(schema='TTO-NUMERIC-THREAD-POLICY-v1',candidate_version=__version__,pid=os.getpid(),host=socket.gethostname(),
+           executable=sys.executable,python=sys.version,platform=platform.platform(),started_at_utc=_utc(),started_at_mono_s=started,
+           inherited_environment={k:os.environ.get(k) for k in ENV_KEYS},policy={k:'1' for k in ENV_KEYS},
+           policy_scope='this candidate process numeric libraries only; not Python threads or other applications',
+           modules_already_loaded=[n for n in ('numpy','scipy') if n in sys.modules],
+           preloaded_versions={n:getattr(sys.modules.get(n),'__version__',None) for n in ('numpy','scipy')},threadpoolctl_version=threadpoolctl_version,verified=False,error=None)
+    try:
+        if r['modules_already_loaded']:raise RuntimeError('numeric_libraries_loaded_before_policy')
+        for key in ENV_KEYS:os.environ[key]='1'
+        r['applied_at_mono_s']=time.monotonic()
+        import numpy as np
+        import scipy
+        import scipy.linalg as la
+        # Force both pinned backends to load, without loading a thermal model.
+        np.dot(np.eye(2),np.eye(2));la.expm(np.zeros((2,2)))
+        r['libraries']=dict(numpy=dict(version=np.__version__,module=np.__file__,blas=np.__config__.CONFIG['Build Dependencies']['blas']),
+                            scipy=dict(version=scipy.__version__,module=scipy.__file__,blas=scipy.__config__.CONFIG['Build Dependencies']['blas']))
+        r['extension_modules']={n:getattr(sys.modules.get(n),'__file__',None) for n in ('numpy._core._multiarray_umath','scipy.linalg._fblas','scipy.linalg._flapack')}
+        r['loaded_pools']=threadpool_info()
+        r['final_environment']={k:os.environ.get(k) for k in ENV_KEYS}
+        supported=all('openblas' in x['blas']['name'].lower() for x in r['libraries'].values())
+        r['pool_coverage']=_pool_coverage(r['loaded_pools'],r['libraries'])
+        if not supported or not all(r['pool_coverage'].values()):raise RuntimeError('numeric_backend_not_verifiable_by_candidate')
+        if any(p['num_threads']!=1 for p in r['loaded_pools']):raise RuntimeError('numeric_thread_pool_is_not_single_threaded')
+        r['verified']=True
+    except Exception as exc:
+        r['error']=str(exc);r['error_class']=type(exc).__name__;r['loaded_pools']=threadpool_info()
+    r['checked_at_utc']=_utc();r['checked_at_mono_s']=time.monotonic()
+    _save(receipt_path,r)
+    if not r['verified']:raise RuntimeError('numeric_policy_failed:'+r['error'])
+    _receipt=copy.deepcopy(r)
+    return r
--- cpu.2/tto_field/receiver_resources.py
+++ cpu.3/tto_field/receiver_resources.py
@@ -0,0 +1,30 @@
+"""Pre-sidecar admission of the existing one-second process resource sample."""
+import math
+CPU_LIMIT=8.0
+RSS_LIMIT=128*1024**2
+
+def baseline_admission(sample,now):
+    r=dict(evaluated_mono_s=now,resource_sample=sample,cpu_limit_single_core_percent=CPU_LIMIT,
+           rss_limit_bytes=RSS_LIMIT,allowed=False,reason='baseline_receiver_resources_unavailable',
+           interval_contract='latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization')
+    if sample is None:return r
+    vals=[sample.get(k) for k in ('interval_start_mono_s','mono_s','cpu_pct_single_core','rss_bytes')]
+    if any(type(v) not in (float,int) or not math.isfinite(v) for v in vals):return r
+    start,end,cpu,rss=vals;r['sample_age_s']=now-end
+    if not (start>=1 and .5<=end-start<=2 and 0<=now-end<=1.5 and cpu>=0 and rss>=0):return r
+    if cpu>CPU_LIMIT or rss>RSS_LIMIT:r['reason']='baseline_receiver_resource_budget_exceeded';return r
+    r.update(allowed=True,reason='baseline_receiver_resources_qualified');return r
+
+
+def read_sample(now,previous):
+    """Unknown resource observations revoke the sample; never reuse an older good reading."""
+    import psutil
+    start=previous[0] if previous else None
+    try:
+        process=psutil.Process();ct=process.cpu_times();total=ct.user+ct.system;rss=process.memory_info().rss
+        cpu=None if previous is None else 100*(total-previous[1])/(now-start)
+        if not math.isfinite(total) or rss<0 or (cpu is not None and (not math.isfinite(cpu) or cpu<0)):
+            raise ValueError('invalid_process_resource_counters')
+        return dict(mono_s=now,interval_start_mono_s=start,cpu_pct_single_core=cpu,rss_bytes=rss,cpu_times=ct._asdict(),resource_error=None),(now,total)
+    except (psutil.Error,OSError,ValueError,ZeroDivisionError) as exc:
+        return dict(mono_s=now,interval_start_mono_s=start,cpu_pct_single_core=None,rss_bytes=None,cpu_times=None,resource_error=type(exc).__name__),None
--- cpu.2/tto_field/runtime.py
+++ cpu.3/tto_field/runtime.py
@@ -122,6 +122,8 @@
 
 
 async def run(config,binding,mode,out,duration=300,probe_profile=None,cpu_pilot=False):
+    from .numeric_policy import initialize
+    numeric_policy=initialize()
     from tto.collector import collect
     from tto.storage import InstanceLock,source_identity
     from tto.config import public_config
@@ -155,9 +157,11 @@
         Registry(out.parent/'.tto-command-ledger').claim(binding['command_id'],binding['command_id'])
         out.mkdir(mode=0o700)
         ev=Evidence(out);pipeline=Pipeline(out,config,binding,mode,clock,ev)
+        write(out/'thread-policy.json',numeric_policy)
         stopped_reason=None;scheduler_event_cursor=0;clock_reminder_sent=False;totals={k:0. for k in ['observed_s','measurement_usable_s','model_usable_s','context_ready_s','joint_ready_s','work_paused_s','tj_usable_s','rail_usable_s','PWM_usable_s','temp_context_usable_s']}
         phase_seconds={};resource_prev=None
         previous=None;previous_gate=None;previous_work=False;last_resources=0.;protocol_records=[]
+        latest_resources=None;resource_seq=0;baseline_checked=False
         def emit(name,**details):
             row=dict(event=name,mono_s=clock.now(),at_utc=utc(),command_id=binding['command_id'],native_run_id=pipeline.run_id,**details)
             ev.append('protocol.jsonl',row)
@@ -189,7 +193,27 @@
                 write(out/'resident-idle-check.json',resident)
             while True:
                 now=clock.now();latest=pipeline.get();run_id=pipeline.run_id or 'PENDING-NATIVE-UUID'
-                if sidecar:await sidecar.tick(now,latest)
+                # Persist the existing1s process sample before the once-only baseline decision.
+                if now-last_resources>=1:
+                    from .receiver_resources import read_sample
+                    latest_resources,resource_prev=read_sample(now,resource_prev);resource_seq+=1
+                    latest_resources.update(resource_seq=resource_seq,field_log_bytes=ev.bytes,
+                        native_log_bytes=sum(f.stat().st_size for f in (out/'native').rglob('*') if f.is_file()))
+                    ev.append('resources.jsonl',latest_resources);last_resources=now
+                    if sidecar and sidecar.process and not sidecar.closed:
+                        if latest_resources['resource_error']:
+                            await sidecar.halt('receiver_resource_measurement_unavailable')
+                        else:await sidecar.resource(latest_resources['cpu_pct_single_core'],latest_resources['rss_bytes'])
+                user_stop=(out/'STOP').exists()
+                budget=duration if mode=='diagnose' else chosen['hard_limit_seconds']-chosen['cleanup_reserve_seconds']
+                if sidecar and not sidecar.closed and not user_stop and now<budget:
+                    if now>=30 and not baseline_checked:
+                        from .receiver_resources import baseline_admission
+                        admission=baseline_admission(latest_resources,now);baseline_checked=True
+                        write(out/'baseline-resource-admission.json',admission)
+                        sidecar.record('baseline_resource_admission',admission=admission)
+                        if not admission['allowed']:await sidecar.halt(admission['reason'])
+                    if not sidecar.closed:await sidecar.tick(now,latest)
                 gate=readiness(latest,now,run_id,formal=True)
                 if previous is not None:
                     dt=now-previous;totals['observed_s']+=dt
@@ -240,15 +264,6 @@
                         if scheduler.terminal:stopped_reason=scheduler.reason;break
                     elif user_stop or native_task.done() or now>=chosen['preparation_reserve_seconds']:
                         stopped_reason='user_stop' if user_stop else 'collector_exited' if native_task.done() else 'preparation_budget_exhausted';break
-                if now-last_resources>=1:
-                    import psutil
-                    p=psutil.Process();ct=p.cpu_times();cpu_total=ct.user+ct.system
-                    cpu_pct=None if resource_prev is None else 100*(cpu_total-resource_prev[1])/(now-resource_prev[0])
-                    resource_prev=(now,cpu_total)
-                    if sidecar:await sidecar.resource(cpu_pct,p.memory_info().rss)
-                    ev.append('resources.jsonl',dict(mono_s=now,rss_bytes=p.memory_info().rss,cpu_times=ct._asdict(),cpu_pct_single_core=cpu_pct,
-                                                field_log_bytes=ev.bytes,native_log_bytes=sum(f.stat().st_size for f in (out/'native').rglob('*') if f.is_file())))
-                    last_resources=now
                 await asyncio.sleep(.1)
         except BaseException as exc:
             error=exc;stopped_reason='entry_error:'+type(exc).__name__
--- cpu.2/pyproject.toml
+++ cpu.3/pyproject.toml
@@ -4,10 +4,10 @@
 
 [project]
 name = "tto-field-candidate"
-version = "0.2.4+cpu.2"
+version = "0.2.4+cpu.3"
 description = "Isolated RM-01 read-only diagnostic and fixed-anchors experiment candidate"
 requires-python = ">=3.10,<3.13"
-dependencies = ["aiohttp==3.11.18", "python-socketio==5.13.0", "psutil==7.0.0", "numpy==2.2.6", "scipy==1.15.3"]
+dependencies = ["aiohttp==3.11.18", "python-socketio==5.13.0", "psutil==7.0.0", "numpy==2.2.6", "scipy==1.15.3", "threadpoolctl==3.6.0"]
 
 [project.scripts]
 tto-field = "tto_field.cli:main"
--- cpu.2/scripts/inspect_capability.py
+++ cpu.3/scripts/inspect_capability.py
@@ -1,37 +1,35 @@
-"""Offline capability receipt from the sole native diagnostic and independent source arrivals.
-Never authorizes load. Output goes to a fresh file, preserving the run index.
-"""
+"""Offline cpu.3 receipt; a baseline rejection is an explicit failed capability, not missing success."""
 import argparse,json,statistics,hashlib
 from pathlib import Path
 from tto_field.cpu_pilot import sidecar_identity
-p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
-r=a.run;load=lambda n:json.loads((r/n).read_text());s=load('summary.json');launch=load('launch.json')
+p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=a.run
+load=lambda n:json.loads((r/n).read_text())
+def rows(n):
+    f=r/n;return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
+s=load('summary.json');launch=load('launch.json');policy=load('thread-policy.json')
 if s['mode']!='diagnose' or s['protocol_requests'] or not 59<=s['elapsed_s']<=90:raise SystemExit('not a complete no-load60s diagnostic')
-rows=[json.loads(x) for x in (r/'cpu-sidecar-arrivals.jsonl').read_text().splitlines()];sources=[x['source'] for x in rows]
-resources=[json.loads(x) for x in (r/'resources.jsonl').read_text().splitlines()]
-q=lambda xs:sorted(xs)[min(len(xs)-1,int(.95*(len(xs)-1)))] if xs else None
-periods=[b['read_start_mono_s']-a['read_start_mono_s'] for a,b in zip(sources,sources[1:])]
-read95=q([x['resources']['read_duration_s'] for x in sources]);jitter95=q([x['resources'].get('deadline_jitter_s',0) for x in sources])
-states=[json.loads(x) for x in (r/'states.jsonl').read_text().splitlines()]
-lag={'baseline':[],'sidecar':[]}
-for x in states:
-    c=x['clock'];t=c['observer_input_mono_s']-c['session_origin_mono_s']
-    lag['baseline' if t<30 else 'sidecar'].append(c['generated_at_mono_s']-c['observer_input_mono_s'])
-lag95={k:q(v) for k,v in lag.items()}
-checks=dict(native_delay_budget=all(x is not None for x in lag95.values()) and lag95['sidecar']<=.25 and lag95['sidecar']-lag95['baseline']<=.1,complete_native=s['native_run_directories']==1 and s['observer_instances_created']==1,
-            packets=len(rows)>=100,clock_identified=all(x['clock_status']=='source_identified_mapping_unknown' for x in rows),
-            cpu_measured=all(x.get('cpu',{}).get('complete_online_set') for x in sources[1:]),
-            read_budget=read95 is not None and read95<=.02,jitter_budget=jitter95 is not None and jitter95<=.1,
-            no_sidecar_trip=s.get('sidecar_status')=='native_run_ending',
-            native_fan_gap=s['fan_success_intervals']['max_s']<=2.5)
-# Qualification is software capacity only. Main-question usefulness remains an explicit review/user decision.
-receipt=dict(schema='TTO-CPU-CAPABILITY-RECEIPT-v1',candidate_version=launch['version'],config_sha256=launch['config_sha256'],
-    sidecar_config_sha256=sidecar_identity(launch['binding']['sidecar']),qualified=all(checks.values()),checks=checks,
-    evaluation_scope='arrival_side',automatic_work_authorization=False,resource_check_evidence=dict(native_callback_lag_p95_s=lag95,read_p95_s=read95,jitter_p95_s=jitter95,
-      baseline_resource_rows=[x for x in resources if x['mono_s']<30],sidecar_resource_rows=[x for x in resources if x['mono_s']>=30]),
-    measured_resolution_evidence=dict(cpu_median_read_period_s=statistics.median(periods) if periods else None,
-       GPU_independent_resolution='unknown unless actual source window/generation evidence provided',rail_independent_resolution='unknown; native coarse baseline retained',
-       exact_cross_host_source_lead='unknown; receiver receipt order is usable without zero-latency assumption'),
-    source_run_id=s['native_run_id'],files={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['launch.json','summary.json','resources.jsonl','cpu-sidecar-arrivals.jsonl']})
-with a.output.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
-print(json.dumps(dict(qualified=receipt['qualified'],checks=checks,automatic_work_authorization=False),indent=2))
+arr=rows('cpu-sidecar-arrivals.jsonl');src=[x['source'] for x in arr];resources=rows('resources.jsonl');events=rows('sidecar-events.jsonl')
+starts=[x['mono_s'] for x in events if x['event']=='started'];start=starts[0] if starts else None
+stops=[x['mono_s'] for x in events if x['event']=='stop_sidecar_only'];end=stops[0] if stops else s['elapsed_s']
+def phase(t):return 'before' if start is None or t<start else 'during' if t<end else 'after'
+q=lambda xs:sorted(xs)[int(.95*(len(xs)-1))] if xs else None
+periods=[b['read_start_mono_s']-x['read_start_mono_s'] for x,b in zip(src,src[1:])]
+read95=q([x['resources']['read_duration_s'] for x in src]);jitter95=q([x['resources'].get('deadline_jitter_s',0) for x in src]);lags={k:[] for k in ('before','during','after')}
+for x in rows('states.jsonl'):
+    c=x['clock'];t=c['observer_input_mono_s']-c['session_origin_mono_s'];lags[phase(t)].append(c['generated_at_mono_s']-c['observer_input_mono_s'])
+lag95={k:q(v) for k,v in lags.items()};baseline=load('baseline-resource-admission.json') if (r/'baseline-resource-admission.json').exists() else None
+checks=dict(thread_policy=policy['verified'] and policy['pid']==s['clock_end']['pid'],baseline_resources=bool(baseline and baseline['allowed']),
+    native_delay_budget=lag95['before'] is not None and lag95['during'] is not None and lag95['during']<=.25 and lag95['during']-lag95['before']<=.1,
+    complete_native=s['native_run_directories']==1 and s['observer_instances_created']==1,packets=len(arr)>=100,
+    clock_identified=bool(arr) and all(x['clock_status']=='source_identified_mapping_unknown' for x in arr),
+    cpu_measured=len(src)>1 and all((x.get('cpu') or {}).get('complete_online_set') for x in src[1:]),
+    read_budget=read95 is not None and read95<=.02,jitter_budget=jitter95 is not None and jitter95<=.1,
+    no_sidecar_trip=s.get('sidecar_status')=='native_run_ending',native_fan_gap=s['fan_success_intervals']['max_s'] is not None and s['fan_success_intervals']['max_s']<=2.5)
+receipt=dict(schema='TTO-CPU-CAPABILITY-RECEIPT-v2',candidate_version=launch['version'],config_sha256=launch['config_sha256'],
+    sidecar_config_sha256=sidecar_identity(launch['binding']['sidecar']),qualified=all(checks.values()),checks=checks,evaluation_scope='arrival_side',automatic_work_authorization=False,
+    actual_sidecar_interval=dict(start_mono_s=start,stop_mono_s=end if start is not None else None),baseline_admission=baseline,
+    resource_check_evidence=dict(native_callback_lag_p95_s=lag95,read_p95_s=read95,jitter_p95_s=jitter95,resources_by_actual_phase={k:[x for x in resources if phase(x['mono_s'])==k] for k in lags}),
+    measured_resolution_evidence=dict(cpu_median_read_period_s=statistics.median(periods) if periods else None,GPU_independent_resolution='unknown unless source window/generation provided',rail_independent_resolution='unknown; native coarse baseline retained',exact_cross_host_source_lead='unknown'),
+    source_run_id=s['native_run_id'],files={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['launch.json','summary.json','thread-policy.json','resources.jsonl']})
+with a.output.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
+print(json.dumps(dict(qualified=receipt['qualified'],checks=checks,actual_sidecar_interval=receipt['actual_sidecar_interval']),indent=2))
````

## 3. 相关测试源码与最终 36 项原始结果

这里只取最终 release 的 `source/` 测试代码和 `installed-release-tests.log`，不引用 development 或旧安装结果。新增的资源、入口与自建服务测试，以及修改后的 pilot/截止测试全文如下；另附未改的启动测试与公共假流依赖，以便完整阅读该 36 项回归的输入与调用链。测试中的私有锁路径、缩放时钟及确定性资源仅服务于本地隔离/分支验证，不是生产策略或现场性能结果。

### `source/pytest.ini`

SHA-256：`c809c969ec7e11b9ff37784e9c6fcc0b7c5148d168e18b05aed797e03fbd6ead`；字节数：27。以下为完整原文。

````ini
[pytest]
testpaths = tests
````

### `source/tests/conftest.py`

SHA-256：`b8b02c3a9048bbe1b4f00b12c1497b1c41793309daf220f906614e6522651fe9`；字节数：573。以下为完整原文。

````python
"""Test-only lock namespace: preserve flock semantics without colliding with unrelated local observers."""
import pytest
@pytest.fixture(autouse=True)
def private_collector_locks(tmp_path,monkeypatch):
    import tto.storage as storage
    import tto.collector as collector
    original=storage.InstanceLock
    def isolated(path=None):
        from pathlib import Path
        return original(tmp_path/('native.lock' if path is None else Path(path).name))
    monkeypatch.setattr(storage,'InstanceLock',isolated)
    monkeypatch.setattr(collector,'InstanceLock',isolated)
````

### `source/tests/test_baseline.py`

SHA-256：`0d8a0aacb5b3ebb7e04105d8a1793f1a7f5b78868c101a0ae373872fde2f7e34`；字节数：1590。以下为完整原文。

````python
import copy,json
from pathlib import Path
import pytest
from tto_field.receiver_resources import baseline_admission

def sample():return dict(interval_start_mono_s=28.5,mono_s=29.5,cpu_pct_single_core=2.,rss_bytes=80*1024**2,resource_seq=29)
@pytest.mark.parametrize('change,reason',[
 ({'cpu_pct_single_core':8.01},'baseline_receiver_resource_budget_exceeded'),
 ({'rss_bytes':128*1024**2+1},'baseline_receiver_resource_budget_exceeded'),
 ({'cpu_pct_single_core':None},'baseline_receiver_resources_unavailable'),
 ({'cpu_pct_single_core':float('nan')},'baseline_receiver_resources_unavailable'),
 ({'mono_s':28.},'baseline_receiver_resources_unavailable'),
 ({'interval_start_mono_s':0.},'baseline_receiver_resources_unavailable')])
def test_unqualified_baseline_is_not_a_sidecar_green_light(change,reason):
 x=sample();x.update(change);r=baseline_admission(x,30);assert not r['allowed'] and r['reason']==reason

def test_missing_and_exact_limits():
 assert not baseline_admission(None,30)['allowed']
 x=sample();x.update(cpu_pct_single_core=8.,rss_bytes=128*1024**2)
 assert baseline_admission(x,30)['allowed']

def test_unreadable_counter_revokes_previous_sample(monkeypatch):
 import psutil
 from tto_field.receiver_resources import read_sample
 class Denied:
  def cpu_times(self):raise psutil.AccessDenied(123)
 monkeypatch.setattr(psutil,'Process',lambda:Denied())
 row,prev=read_sample(30.,(29.,1.))
 assert prev is None and row['cpu_pct_single_core'] is None and row['rss_bytes'] is None and row['resource_error']=='AccessDenied'
 assert not baseline_admission(row,30)['allowed']
````

### `source/tests/test_resource_runtime.py`

SHA-256：`78027836cc0e19d178c0e0605b6e184c296bfb11b468f0a89f979075b8c4c012`；字节数：4465。以下为完整原文。

````python
"""Actual sole runtime/collector against owned loopback; deterministic resource counters only."""
import asyncio,collections,json,time,sys
from pathlib import Path
import pytest,psutil
from fake_source import FakeSource
from tto.config import load_config
from tto_field.cpu_cli import preview
from tto_field import runtime,receiver_resources
from tto_field.support import Clock

@pytest.mark.parametrize('scenario',['high_cpu','high_rss','unknown','normal','later_cpu'])
def test_once_only_baseline_and_native_completion(tmp_path,monkeypatch,scenario):
    async def check():
        async with FakeSource() as server:
            class FastClock(Clock):
                def __init__(self):super().__init__();self.actual_start=time.monotonic()
                def now(self):return 28+8*(time.monotonic()-self.actual_start)
            monkeypatch.setattr(runtime,'Clock',FastClock)
            real_process=psutil.Process;start=time.monotonic()
            class Process:
                def __init__(self,*a,**k):self.p=real_process(*a,**k)
                def __getattr__(self,n):return getattr(self.p,n)
                def cpu_times(self):
                    t=8*(time.monotonic()-start)
                    rate=.2 if scenario=='high_cpu' else .005
                    cpu=rate*t
                    if scenario=='later_cpu' and t>8:cpu+=.20*(t-8)
                    return self.p.cpu_times()._replace(user=cpu,system=0)
                def memory_info(self):
                    m=self.p.memory_info();return m._replace(rss=129*1024**2 if scenario=='high_rss' else 80*1024**2)
            # Unknown is represented as an absent candidate sample without emitting nonfinite JSON.
            if scenario=='unknown':
                monkeypatch.setattr(receiver_resources,'read_sample',lambda now,previous:(dict(mono_s=now,interval_start_mono_s=None,cpu_pct_single_core=None,rss_bytes=None,cpu_times=None,resource_error='TEST_RESOURCE_UNAVAILABLE'),None))
            if scenario!='unknown':monkeypatch.setattr(psutil,'Process',Process)
            # Owned CPU source subprocess, no ssh command or real device call.
            c=load_config(environ={})
            for k in ('orin','tianshan'):c[k]['base_url']=server.url
            c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC loopback')
            b=preview(c,'capability');b.update(command_id='LOCAL-'+scenario,synthetic_loopback_only=True,
                sidecar=dict(command_id='LOCAL-'+scenario,query_target_s=.2,transport='synthetic',argv=[sys.executable,str(Path(__file__).with_name('fake_sidecar.py')),'--command-id','LOCAL-'+scenario]))
            b['authorization'].update(command_id=b['command_id'],explicit_user_start=True,evidence='OWNED LOOPBACK TEST ONLY')
            # Fake source CLI has a positional command, matching its existing test-only contract.
            b['sidecar']['argv']=[sys.executable,'-c',"import sys,time,runpy; original=time.sleep; time.sleep=lambda s:original(s/8); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')",str(Path(__file__).with_name('fake_sidecar.py')),b['command_id']]
            out=tmp_path/'run';s=await runtime.run(c,b,'diagnose',out,duration=60,cpu_pilot=True)
            admission=json.loads((out/'baseline-resource-admission.json').read_text());events=[json.loads(x) for x in (out/'sidecar-events.jsonl').read_text().splitlines()]
            starts=[x for x in events if x['event']=='started'];baseline=[x for x in events if x['event']=='baseline_resource_admission']
            assert len(baseline)==1 and s['reason']=='diagnostic_duration' and s['own_async_tasks_remaining']==0
            assert s['requester_instances_created']==0 and s['native_run_directories']==1 and s['observer_instances_created']==1
            assert not server.posts and not server.model_gets
            if scenario in ('high_cpu','high_rss','unknown'):
                assert not starts and not admission['allowed'] and not (out/'cpu-sidecar-wire.jsonl').exists()
                assert s['sidecar_status'].startswith('baseline_receiver_')
            else:
                assert admission['allowed'] and len(starts)==1
                assert (out/'cpu-sidecar-wire.jsonl').exists()
                if scenario=='later_cpu':assert s['sidecar_status']=='receiver_total_resource_budget_exceeded'
            assert json.loads((out/'thread-policy.json').read_text())['verified']
    asyncio.run(check())
````

### `source/tests/test_runtime_deadline.py`

SHA-256：`fc49b60940c6ada3447ad92c68bf41d8026cff9187f011ca706cee72377ecd0b`；字节数：3119。以下为完整原文。

````python
"""Actual sole runtime checks STOP/diagnostic deadline while owned mux child never exits."""
import asyncio,json,socket,tempfile,time
from pathlib import Path
import pytest
from fake_source import FakeSource
from test_startup import Process,configuration
from tto.config import load_config
from tto_field.cpu_cli import preview
from tto_field import runtime
from tto_field.support import Clock,write

@pytest.mark.parametrize('reason',['user_stop','diagnostic_duration'])
def test_clock_loop_keeps_advancing(tmp_path,monkeypatch,reason):
    import tto_field.receiver_resources as rr
    monkeypatch.setattr(rr,'baseline_admission',lambda sample,now:dict(allowed=True,reason='UNIT-QUALIFIED-BASELINE'))
    async def check():
        async with FakeSource() as server:
            with tempfile.TemporaryDirectory(dir='/private/tmp',prefix='cpu2-loop-') as short:
                sock=socket.socket(socket.AF_UNIX);path=Path(short)/'mux';sock.bind(str(path));children=[]
                async def spawn(*argv,**kw):
                    assert argv[0]=='ssh' and '-O' in argv
                    p=Process(None);children.append(p);return p
                monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
                class OffsetClock(Clock):
                    def __init__(self):super().__init__();self.origin-=30 if reason=='user_stop' else 59.8
                monkeypatch.setattr(runtime,'Clock',OffsetClock)
                c=load_config(environ={})
                for key in ('orin','tianshan'):c[key]['base_url']=server.url
                c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC only')
                b=preview(c,'capability');b.update(command_id='FAKE-'+reason,synthetic_loopback_only=True,sidecar=configuration(path))
                b['sidecar'].update(command_id=b['command_id'],query_target_s=.2)
                b['authorization'].update(command_id=b['command_id'],explicit_user_start=True,evidence='LOCAL SIMULATED RUNTIME ONLY')
                out=tmp_path/'run'
                async def stop():await asyncio.sleep(.2);(out/'STOP').touch()
                task=asyncio.create_task(stop()) if reason=='user_stop' else None
                start=time.monotonic();result=await runtime.run(c,b,'diagnose',out,duration=60,cpu_pilot=True)
                if task:await task
                elapsed=time.monotonic()-start
                assert elapsed<3 and result['reason']==reason and result['requester_instances_created']==0
                assert children and all(p.returncode is not None for p in children)
                events=[json.loads(x) for x in (out/'sidecar-events.jsonl').read_text().splitlines()]
                assert any(x['event']=='cleanup_finished' and x['own_tasks_remaining']==x['unreaped_children']==0 for x in events)
                assert not server.posts and not server.model_gets
                write(tmp_path/'verification.json',dict(reason=reason,wall_elapsed_s=elapsed,mux_wait_never_returns=True,own_children_reaped=True,real_devices=0,real_inference=0))
                sock.close()
    asyncio.run(check())
````

### `source/tests/test_pilot.py`

SHA-256：`097ffa059c09af8e8a861840e30862d80ee8507a66fbb900e42320bcd48bdb83`；字节数：12191。以下为完整原文。

````python
import copy,json,sys
from pathlib import Path
import pytest
from tto_field.cpu_pilot import PilotScheduler,pilot_profile
import tto_field.cpu_pilot as pilot
from tto_field.cpu_source import utilization
from tto_field.cpu_interface import causal_inputs

def gate(*a,**k):return dict(start_allowed=True,explicit_stop=False)
@pytest.fixture(autouse=True)
def ready(monkeypatch):monkeypatch.setattr(pilot,'readiness',gate)

def simulation(duration=30):
    s=PilotScheduler(pilot_profile(),{},'FAKE-RUN','FAKE-COMMAND');now=0.;next_complete=None;submitted=[];ends=[]
    for _ in range(30000):
        complete=[]
        if next_complete is not None and now>=next_complete:
            complete=[dict(request_id=submitted[-1]['request_id'],status='completed',client_end_mono_s=now)];ends.append(now);next_complete=None
        actions,_=s.tick(now,None,complete)
        for a in actions:
            assert a['kind']=='submit';submitted.append(a);next_complete=now+duration
        if s.terminal:break
        # exact virtual integer seconds, no wall-clock waiting or real model
        now+=1
    return s,submitted,ends,now

def test_frozen_waits_and_full_worst_budget():
    s,requests,ends,now=simulation()
    assert len(requests)==12 and s.reason=='completed' and s.peak==1
    waits=[requests[i+1]['submit_mono_s']-ends[i] for i in range(5)]
    assert waits==[31,61,36,56,41] # >= exact frozen waits, one scheduler dispatch tick
    assert requests[6]['submit_mono_s']-ends[5]==51
    assert all(0<=requests[i+1]['submit_mono_s']-ends[i]<=1 for i in range(6,11))
    assert now==1062 and now+120==1182 and now+120<=1200
    assert pilot_profile()['nominal_worst_normal_s']==1170

def test_stop_drains_and_unknown_does_not_dispatch():
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(60,None);s.tick(240,None);a,_=s.tick(241,None);ident=a[0]['request_id']
    a,_=s.tick(242,None,user_stop=True);assert not a and s.pending
    a,_=s.tick(243,None,[dict(request_id=ident,status='completed')]);assert not a and s.terminal and s.reason=='user_stop'
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(60,None);s.tick(240,None);a,_=s.tick(241,None)
    a,_=s.tick(242,None,[dict(request_id=a[0]['request_id'],status='termination_unknown')]);assert not a and s.terminal and s.reason=='request_termination_unknown'

def test_deadline_reserves_cleanup_even_pending():
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(60,None);s.tick(240,None);s.tick(241,None)
    actions,_=s.tick(1080,None);assert s.terminal and actions[0]['kind']=='cancel_client' and s.unknown_requests
    assert s.stopping_at==1080

def test_no_60_second_warmup_rule_bypass(monkeypatch):
    monkeypatch.setattr(pilot,'readiness',lambda *a,**k:dict(start_allowed=False,explicit_stop=False))
    s=PilotScheduler(pilot_profile(),{},'R','C');s.tick(0,None);s.tick(60,None)
    assert s.terminal and s.submitted==0

def test_counter_guest_iowait_reset_and_online():
    a=dict(counters={'cpu0':[100,10,20,200,20,3,2,0,30,5]},per_core_online={'cpu0':True},read_start_mono_s=1,read_end_mono_s=1.001)
    b=copy.deepcopy(a);b.update(read_start_mono_s=1.2,read_end_mono_s=1.201);b['counters']['cpu0']=[110,10,20,210,20,3,2,0,40,5]
    r=utilization(a,b);assert r['mean_percent']==50 and r['max_percent']==50
    b['counters']['cpu0'][4]=19;assert utilization(a,b)['mean_percent'] is None
    b['per_core_online']['cpu0']=False;assert utilization(a,b)['mean_percent'] is None

def test_causality_missing_stale_unknown_clocks_not_zero():
    row=dict(field='gpu_percent',value=80,valid=True,observed_window_end_s=8,available_at_s=9,decision_generated_s=9.1,clock_domain='N305')
    rows=[row,dict(row,field='cpu_max_percent',value=90,available_at_s=11,decision_generated_s=11),dict(row,field='cpu_mean_percent',clock_domain=None),dict(row,field='vdd_gpu_W',observed_window_end_s=1)]
    x=causal_inputs(rows,10,'N305');assert x['INPUT-BASE']['gpu_percent']==row
    assert x['INPUT-CORE']['cpu_max_percent'] is None and x['INPUT-MEAN']['cpu_mean_percent'] is None and x['INPUT-BASE']['vdd_gpu_W'] is None
    x2=causal_inputs(rows+[dict(row,available_at_s=99,decision_generated_s=99)],10,'N305');assert x==x2
    assert x['deployable'] is False

def test_no_video_or_yet_dependency_and_single_thermal_history():
    p=json.loads((Path(pilot.__file__).with_name('plans')/'cpu-pilot.json').read_text())
    assert p['jtop_video_required']==p['YET_required']==False and p['single_run_and_single_thermal_history']
    assert p['existing_run_is_development']=='5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3'

def test_grants_are_specific_and_not_model_green(tmp_path):
    from tto.config import load_config
    from tto_field.cpu_cli import preview
    from tto_field.cpu_pilot import verify_pilot_grant
    c=load_config(environ={})
    for k in ('orin','tianshan'):c[k]['base_url']='http://127.0.0.1:9'
    b=preview(c,'capability');b.update(command_id='SYNTHETIC',synthetic_loopback_only=True,sidecar=dict(query_target_s=.2,argv=[]))
    b['authorization'].update(command_id='SYNTHETIC',explicit_user_start=True,evidence='LOCAL TEST')
    with pytest.raises(ValueError):verify_pilot_grant(c,copy.deepcopy(b),'diagnose',61)
    bad=copy.deepcopy(b);bad['authorization']['explicit_user_start']=False
    with pytest.raises(ValueError):verify_pilot_grant(c,bad,'diagnose',60)
    bad=copy.deepcopy(b);bad['profile_sha256']='wrong'
    with pytest.raises(ValueError):verify_pilot_grant(c,bad,'diagnose',60)
    verify_pilot_grant(c,b,'diagnose',60);assert b['cpu_pilot_verified']
    with pytest.raises(ValueError):verify_pilot_grant(c,b,'diagnose',60)

def test_source_missing_clock_or_regressed_sequence_is_preserved():
    import asyncio
    from tto_field.cpu_transport import Sidecar
    class Clock:
        domain='SYNTHETIC-RECEIVER'
        def now(self):return 31
    class Ev:
        def __init__(self):self.rows=[]
        def append(self,*a):self.rows.append(a)
    class Pipe:run_id='SYNTHETIC';fan_success_times=[]
    class Process:
        returncode=0
        def __init__(self,rows):
            self.stdout=asyncio.StreamReader()
            for row in rows:self.stdout.feed_data((json.dumps(row)+'\n').encode())
            self.stdout.feed_eof()
    row=dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host='FAKE',boot_id='FAKE',source_session='FAKE',clock=None,command_id='C'),seq=1,resources={})
    async def check(rows,expected):
        ev=Ev();s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipe(),ev);s.process=Process(rows);s.started=30
        await s.receive();assert s.status==expected;assert any(x[0]=='sidecar-events.jsonl' for x in ev.rows)
    asyncio.run(check([row],'source_invalid'))
    row['identity']['clock']='CLOCK_MONOTONIC';row['resources']=dict(elapsed_s=1,read_duration_s=.0001,rss_bytes=100,cpu_seconds=.0001)
    asyncio.run(check([row,row],'source_invalid'))

def test_stale_transport_and_budget_stop_only_sidecar():
    import asyncio
    from tto_field.cpu_transport import Sidecar
    class Clock:
        domain='SYNTHETIC'
        def now(self):return 36
    class Ev:
        def append(self,*a):pass
    class Pipe:run_id='SYNTHETIC';fan_success_times=[]
    class Process:
        returncode=None
        terminated=False
        def terminate(self):self.terminated=True
    async def test():
        s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipe(),Ev());s.started=30;s.process=Process();s.owned=[('source_start',s.process)];s.last_arrival=30;s.startup_task=asyncio.create_task(asyncio.sleep(10))
        s.status='running';s.source_started=30
        s.reader=asyncio.create_task(asyncio.sleep(10))
        await s.tick(36,None);assert s.closed and s.status=='source_stale_or_blocked' and s.process.terminated
        s.reader.cancel();await asyncio.gather(s.reader,return_exceptions=True)
        s=Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipe(),Ev());s.process=Process();s.owned=[('source_start',s.process)]
        await s.resource(9,100);assert s.closed and s.process.terminated and s.status=='receiver_total_resource_budget_exceeded'
    asyncio.run(test())

def test_existing_mux_command_and_identity_bootstrap_are_real(tmp_path,monkeypatch):
    import asyncio,socket,sys,hashlib,shlex,subprocess
    from tto_field.cpu_transport import Sidecar
    import tempfile
    short=tempfile.TemporaryDirectory(prefix='cpu-mux-',dir='/private/tmp');mux=Path(short.name)/'mux'
    sock=socket.socket(socket.AF_UNIX);sock.bind(str(mux))
    fake=tmp_path/'source.py';fake.write_text("print('SYNTHETIC BOOTSTRAP OK')\n")
    config=tmp_path/'source.json';config.write_text('{}');permit=tmp_path/'permission.json';permit.write_text('{"command_id":"C"}')
    h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    calls=[]
    class Clock:
        domain='FAKE'
        def now(self):return 30
    class Ev:
        def append(self,*a):pass
    class Pipe:run_id='FAKE';fan_success_times=[]
    class Process:
        returncode=0
        def __init__(self):
            self.stdout=asyncio.StreamReader();self.stdout.feed_eof();self.stderr=asyncio.StreamReader();self.stderr.feed_eof()
        async def wait(self):return 0
    async def spawn(*args,**kwargs):calls.append(args);return Process()
    monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
    s=Sidecar(dict(transport='existing_ssh_mux',host='rm01@10.10.99.98',existing_control_socket=str(mux),remote_python=sys.executable,
        remote_source_script=str(fake),source_script_sha256=h(fake),remote_source_config=str(config),source_config_sha256=h(config),
        remote_source_permission=str(permit),command_id='C'),tmp_path,Clock(),Pipe(),Ev())
    async def check():
        await s.tick(30,None);await s.startup_task;await asyncio.sleep(0);await s.close()
    asyncio.run(check());sock.close();short.cleanup()
    assert calls[0][:5]==('ssh','-S',str(mux),'-O','check') and 'ProxyCommand=false' in calls[1]
    remote=shlex.split(calls[1][-1]);r=subprocess.run(remote,capture_output=True,text=True,check=True);assert 'SYNTHETIC BOOTSTRAP OK' in r.stdout
    remote[4]='wrong-script-hash';r=subprocess.run(remote,capture_output=True,text=True);assert r.returncode and 'source SHA' in r.stderr

def test_original_four_slot_capacity_can_supply_one_pilot_client(tmp_path):
    from tto.config import load_config
    from tto_field.cpu_cli import preview
    from tto_field.cpu_pilot import verify_pilot_grant,sidecar_identity
    from tto_field.support import digest_file
    from tto_field.runtime import ROOT,ACTOR
    c=load_config(environ={});b=preview(c,'execute');b.update(command_id='OFFLINE-FAKE',request_actor_thread=ACTOR)
    b['authorization'].update(command_id='OFFLINE-FAKE',explicit_user_start=True,evidence='UNIT VALIDATION ONLY, NO IO')
    original=json.loads((ROOT/'plans/model-profiles.json').read_text())['existing-dense-27b-confirm-before-live']
    b['inference']=dict(model='RM-01 VLM',max_tokens=256,request_timeout_s=30,stream=True,messages=original['payload']['messages'],sampling=original['sampling'],identity_evidence='SYNTHETIC',confirmed_client_slots=4)
    side=dict(query_target_s=.2,transport='existing_ssh_mux',host='rm01@10.10.99.98',existing_control_socket='/tmp/NOT-OPENED',command_id='OFFLINE-FAKE',remote_python='/fake/python',remote_source_script='/fake/source.py',source_script_sha256='fake',remote_source_config='/fake/cfg.json',source_config_sha256='fake',remote_source_permission='/fake/grant.json')
    b['sidecar']=side
    cap=tmp_path/'cap.json';cap.write_text(json.dumps(dict(candidate_version='0.2.4+cpu.3',config_sha256=b['config_sha256'],sidecar_config_sha256=sidecar_identity(side),qualified=True,evaluation_scope='source_potential',measured_resolution_evidence='SYNTHETIC',resource_check_evidence='SYNTHETIC')))
    b['capability_receipt']=dict(path=str(cap),sha256=digest_file(cap));b['capability_user_decision_evidence']='SYNTHETIC UNIT ONLY'
    good=copy.deepcopy(b);verify_pilot_grant(c,good,'execute',60);assert good['cpu_pilot_verified'] and good['inference']['confirmed_client_slots']==4
    b['inference']['confirmed_client_slots']=0
    with pytest.raises(ValueError):verify_pilot_grant(c,b,'execute',60)
````

### `source/tests/local_cli_service.py`

SHA-256：`94415184f751e3ae12f2324a8e7f2acd18f945843c1f4a5bd811b043c9f6b448`；字节数：4000。以下为完整原文。

````python
"""One real installed CLI capability over owned numeric-loopback. No fake clocks or resource values.
Only locks are namespaced by test-sitecustomize to coexist with another local observer.
Source fixture is synthetic/proc files, not actual Thor. No model API permitted.
"""
import asyncio,json,os,sys,uuid
from pathlib import Path
from fake_source import FakeSource
from tto.config import load_config

async def main(prefix,out):
    out.mkdir(parents=True,exist_ok=False);site=out/'test-site';site.mkdir();locks=out/'private-locks';locks.mkdir()
    (site/'sitecustomize.py').write_text("import tto.storage as s\nfrom pathlib import Path\noriginal=s.InstanceLock\ndef isolated(path=None):\n return original(Path("+repr(str(locks))+ ")/('native.lock' if path is None else Path(path).name))\ns.InstanceLock=isolated\n")
    async with FakeSource() as server:
        c=load_config(environ={})
        for k in ('orin','tianshan'):c[k]['base_url']=server.url
        c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='OWNED SYNTHETIC LOOPBACK, NO FIELD')
        cfg=out/'config.json';cfg.write_text(json.dumps(c));preview=out/'preview.json';env=os.environ.copy();env['PYTHONPATH']=str(site)
        for k in ['OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='8'
        # Actual installed console script supplies preview identities; parent imports no numeric libraries.
        cmd=[str(prefix/'bin/tto-cpu-pilot'),'preview','--mode','capability','--config',str(cfg)]
        proc=await asyncio.create_subprocess_exec(*cmd,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE);data,err=await proc.communicate();assert proc.returncode==0,err.decode();preview.write_bytes(data);b=json.loads(data)
        command='SYNTHETIC-CLI-'+str(uuid.uuid4());b.update(command_id=command,synthetic_loopback_only=True)
        b['authorization'].update(command_id=command,explicit_user_start=True,evidence='LOCAL SELF-OWNED SERVICE TEST ONLY, NO REAL DEVICES')
        b['sidecar']=dict(transport='synthetic',query_target_s=.2,command_id=command,argv=[str(prefix/'bin/python'),str(Path(__file__).with_name('source_fixture.py').resolve()),str(out/'synthetic-proc'),command])
        bind=out/'binding.json';bind.write_text(json.dumps(b));run=out/'run';cmd=[str(prefix/'bin/tto-cpu-pilot'),'capability','--config',str(cfg),'--binding',str(bind),'--output',str(run),'--allow-network']
        with (out/'cli.stdout').open('wb') as stdout,(out/'cli.stderr').open('wb') as stderr:
            proc=await asyncio.create_subprocess_exec(*cmd,env=env,stdout=stdout,stderr=stderr)
            await asyncio.wait_for(proc.wait(),90)
        assert proc.returncode==0,(out/'cli.stderr').read_text();s=json.loads((run/'summary.json').read_text());pol=json.loads((run/'thread-policy.json').read_text());baseline=json.loads((run/'baseline-resource-admission.json').read_text())
        assert pol['verified'] and pol['pid']==s['clock_end']['pid']
        assert s['requester_instances_created']==s['request_executor_instances_created']==0 and s['native_run_directories']==s['observer_instances_created']==1
        assert s['reason']=='diagnostic_duration' and s['own_async_tasks_remaining']==0
        assert server.posts==server.model_gets==0
        receipt=dict(scope='ACTUAL installed CPU3 CLI, owned loopback only; NOT field',returncode=proc.returncode,pid=pol['pid'],numeric_policy_verified=True,baseline=baseline,summary=s,
                     inference_posts=server.posts,model_gets=server.model_gets,lock_namespace='TEST-ONLY sitecustomize; release locks unchanged',real_resources_and_clock=True)
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(baseline=baseline['reason'],sidecar_status=s['sidecar_status'],elapsed_s=s['elapsed_s'],pid=pol['pid']),indent=2))
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
````

### `source/scripts/verify_installed_cli.py`

SHA-256：`f6d9b554a6ce4f370f858c11bc9731d517d4ffc86241fc6d52369bc0d01da07f`；字节数：4070。以下为完整原文。

````python
"""Bounded actual installed entry subprocesses, including rejection before any socket access."""
import argparse,subprocess,os,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);exe=a.prefix/'bin/tto-cpu-pilot';other=a.prefix/'bin/tto-field';env=os.environ.copy();env.pop('PYTHONPATH',None)
keys=['OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'];receipts=[]
for name,program,multi in [('clean',exe,False),('inherited8',exe,True),('shared-field-entry',other,True)]:
 e=env.copy()
 for k in keys:
  if multi:e[k]='8'
  else:e.pop(k,None)
 path=a.output/(name+'-thread-policy.json');r=subprocess.run([str(program),'verify-install','--thread-policy-output',str(path)],env=e,capture_output=True,text=True,timeout=20)
 (a.output/(name+'.stderr')).write_text(r.stderr);(a.output/(name+'.identity.json')).write_text(r.stdout);assert r.returncode==0,(name,r.stderr)
 j=json.loads(path.read_text());v=json.loads(r.stdout);assert j['verified'] and v['numeric_thread_policy']['pid']==j['pid'];assert j['modules_already_loaded']==[] and all(x['num_threads']==1 for x in j['loaded_pools']);assert len(j['loaded_pools'])>=2
 assert j['libraries']['numpy']['version']=='2.2.6' and j['libraries']['scipy']['version']=='1.15.3'
 if multi:assert set(j['inherited_environment'].values())=={'8'}
 assert j['applied_at_mono_s']<j['checked_at_mono_s'];receipts.append(dict(scenario=name,returncode=r.returncode,pid=j['pid'],verified=True,pools=j['loaded_pools']))
# Load NumPy before actual console entry with a test-only sitecustomize; deny/log all network attempts.
site=a.output/'early-site';site.mkdir();network=a.output/'forbidden-network-attempts.txt'
(site/'sitecustomize.py').write_text("import numpy,socket\nfrom pathlib import Path\ndef blocked(*a,**k):\n Path("+repr(str(network))+ ").write_text('network attempted')\n raise RuntimeError('TEST forbids networking')\nsocket.create_connection=blocked\nsocket.socket.connect=blocked\nsocket.socket.connect_ex=blocked\n")
e=env.copy();e['PYTHONPATH']=str(site);out=a.output/'must-not-run';receipt=out.with_name(out.name+'.startup')/'thread-policy.json'
r=subprocess.run([str(exe),'capability','--config',str(a.output/'not-read-config.json'),'--binding',str(a.output/'not-read-binding.json'),'--output',str(out),'--allow-network'],env=e,capture_output=True,text=True,timeout=20)
(a.output/'preloaded-rejection.stderr').write_text(r.stderr);j=json.loads(receipt.read_text());assert r.returncode!=0 and not j['verified'] and 'numpy' in j['modules_already_loaded'];assert not network.exists() and not out.exists();receipts.append(dict(scenario='preloaded_numpy',returncode=r.returncode,verified=False,network_attempts=0,recorded_pid=j['pid']))
# A backend that cannot be introspected must fail before any client/config access.
site2=a.output/'unknown-pool-site';site2.mkdir()
(site2/'sitecustomize.py').write_text("import threadpoolctl\noriginal=threadpoolctl.threadpool_info\nthreadpoolctl.threadpool_info=lambda:original()[:1]\n")
e=env.copy();e['PYTHONPATH']=str(site2);out=a.output/'unknown-pool-run'
r=subprocess.run([str(exe),'capability','--config',str(a.output/'not-read-config.json'),'--binding',str(a.output/'not-read-binding.json'),'--output',str(out),'--allow-network'],env=e,capture_output=True,text=True,timeout=20)
(a.output/'unknown-pool.stderr').write_text(r.stderr)
j=json.loads((out.with_name(out.name+'.startup')/'thread-policy.json').read_text())
assert r.returncode!=0 and not j['verified'] and j['error']=='numeric_backend_not_verifiable_by_candidate' and not out.exists()
receipts.append(dict(scenario='unverifiable_pool',returncode=r.returncode,verified=False,run_created=False,pid=j['pid']))
(a.output/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n');print('PASS installed entries clean/inherited8/shared entry + preloaded rejection with zero network attempts')
````

### `source/scripts/replay_probe.py`

SHA-256：`b393d9c217ef61ee2359364073e1dd6288cb23453b20e201a6c54cc0f442b5f5`；字节数：3966。以下为完整原文。

````python
"""Same saved native events through actual Pipeline; pacing is for local CPU only, not field performance."""
import argparse,collections,json,sys,os,time,shutil,hashlib,math,platform
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--package-root',type=Path);p.add_argument('--candidate-policy',action='store_true');p.add_argument('--seconds',type=float,default=12);p.add_argument('--paced',action='store_true');a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False)
if a.package_root:sys.path.insert(0,str(a.package_root))
policy=None
if a.candidate_policy:
 from tto_field.numeric_policy import initialize
 policy=initialize(out/'thread-policy.json')
import numpy as np,scipy.linalg,psutil
from threadpoolctl import threadpool_info
from tto_field.runtime import Pipeline
from tto_field.support import Clock,Evidence
from tto.engine import engine_for
native=next((a.run/'native').glob('run-*'));manifest=json.loads((native/'manifest.json').read_text());cfg=manifest['config'];raw=[json.loads(x) for x in (native/'observations-0001.jsonl').read_text().splitlines()];saved=[json.loads(x)['state'] for x in (a.run/'states.jsonl').read_text().splitlines()]
first=raw[0]['mono_s'];chosen=[(i,x) for i,x in enumerate(raw) if a.seconds<=0 or x['mono_s']-first<=a.seconds]
(out/'native'/native.name).mkdir(parents=True);shutil.copy2(native/'manifest.json',out/'native'/native.name/'manifest.json')
binding=json.loads((a.run/'launch.json').read_text())['binding'];clock=Clock();ev=Evidence(out);pipe=Pipeline(out,cfg,binding,'diagnose',clock,ev);engine=engine_for(cfg,record_schema=manifest['record_schema']);proc=psutil.Process();before={t.id:t.user_time+t.system_time for t in proc.threads()};ct=proc.cpu_times();w0=time.monotonic();calls=[];maxdiff=0.;checks=0
# Compare every nested scientific/semantic field, not just Tf or one summary score.
ignore=set()
def equal(x,y,path='state'):
 global maxdiff,checks
 if isinstance(x,dict) and isinstance(y,dict):
  assert set(x)==set(y),(path,set(x)^set(y))
  for k in x:equal(x[k],y[k],path+'.'+k)
 elif isinstance(x,list) and isinstance(y,list):
  assert len(x)==len(y),path
  for i,(xx,yy) in enumerate(zip(x,y)):equal(xx,yy,path+f'[{i}]')
 elif type(x) in (int,float) and type(y) in (int,float):
  d=abs(x-y);maxdiff=max(maxdiff,d);assert d<=1e-8,(path,x,y);checks+=1
 else:assert x==y,(path,x,y)
for i,x in chosen:
 if a.paced:
  delay=x['mono_s']-first-(time.monotonic()-w0)
  if delay>0:time.sleep(delay)
 t=time.monotonic();processed=engine.process(x);pipe.on_record(x,processed,engine);calls.append(time.monotonic()-t);equal(pipe.get()['state'],saved[i])
if a.paced:
 delay=a.seconds-(time.monotonic()-w0)
 if delay>0:time.sleep(delay)
wall=time.monotonic()-w0;ct1=proc.cpu_times();cpu=ct1.user+ct1.system-ct.user-ct.system;deltas=[dict(tid=t.id,cpu_s=t.user_time+t.system_time-before.get(t.id,0)) for t in proc.threads()];ev.close()
result=dict(scope='LOCAL saved events, no network/sidecar/devices; NOT N305',events=len(chosen),numeric_fields_checked=checks,max_abs_semantic_numeric_difference=maxdiff,all_semantic_fields_equal=True,phase_validity_revocation_cold_start_included=True,
 process_cpu_s=cpu,wall_s=wall,cpu_single_core_percent=100*cpu/wall,threads=sorted(deltas,key=lambda x:-x['cpu_s']),rss_bytes=proc.memory_info().rss,
 callback_p95_s=sorted(calls)[int(.95*(len(calls)-1))],callback_max_s=max(calls),thread_pools=threadpool_info(),python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,candidate_policy=a.candidate_policy,
 candidate_version=__import__('tto_field').__version__,observer_sha256=hashlib.sha256(Path(__import__('tto_field.research.observer',fromlist=['__file__']).__file__).read_bytes()).hexdigest(),paced=a.paced)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
````

### `source/scripts/inspect_capability.py`

SHA-256：`f56119845ddacc0aadebc47bdfb8338f7df5eadce4cbd59f75e858017401edfb`；字节数：4099。以下为完整原文。

````python
"""Offline cpu.3 receipt; a baseline rejection is an explicit failed capability, not missing success."""
import argparse,json,statistics,hashlib
from pathlib import Path
from tto_field.cpu_pilot import sidecar_identity
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=a.run
load=lambda n:json.loads((r/n).read_text())
def rows(n):
    f=r/n;return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
s=load('summary.json');launch=load('launch.json');policy=load('thread-policy.json')
if s['mode']!='diagnose' or s['protocol_requests'] or not 59<=s['elapsed_s']<=90:raise SystemExit('not a complete no-load60s diagnostic')
arr=rows('cpu-sidecar-arrivals.jsonl');src=[x['source'] for x in arr];resources=rows('resources.jsonl');events=rows('sidecar-events.jsonl')
starts=[x['mono_s'] for x in events if x['event']=='started'];start=starts[0] if starts else None
stops=[x['mono_s'] for x in events if x['event']=='stop_sidecar_only'];end=stops[0] if stops else s['elapsed_s']
def phase(t):return 'before' if start is None or t<start else 'during' if t<end else 'after'
q=lambda xs:sorted(xs)[int(.95*(len(xs)-1))] if xs else None
periods=[b['read_start_mono_s']-x['read_start_mono_s'] for x,b in zip(src,src[1:])]
read95=q([x['resources']['read_duration_s'] for x in src]);jitter95=q([x['resources'].get('deadline_jitter_s',0) for x in src]);lags={k:[] for k in ('before','during','after')}
for x in rows('states.jsonl'):
    c=x['clock'];t=c['observer_input_mono_s']-c['session_origin_mono_s'];lags[phase(t)].append(c['generated_at_mono_s']-c['observer_input_mono_s'])
lag95={k:q(v) for k,v in lags.items()};baseline=load('baseline-resource-admission.json') if (r/'baseline-resource-admission.json').exists() else None
checks=dict(thread_policy=policy['verified'] and policy['pid']==s['clock_end']['pid'],baseline_resources=bool(baseline and baseline['allowed']),
    native_delay_budget=lag95['before'] is not None and lag95['during'] is not None and lag95['during']<=.25 and lag95['during']-lag95['before']<=.1,
    complete_native=s['native_run_directories']==1 and s['observer_instances_created']==1,packets=len(arr)>=100,
    clock_identified=bool(arr) and all(x['clock_status']=='source_identified_mapping_unknown' for x in arr),
    cpu_measured=len(src)>1 and all((x.get('cpu') or {}).get('complete_online_set') for x in src[1:]),
    read_budget=read95 is not None and read95<=.02,jitter_budget=jitter95 is not None and jitter95<=.1,
    no_sidecar_trip=s.get('sidecar_status')=='native_run_ending',native_fan_gap=s['fan_success_intervals']['max_s'] is not None and s['fan_success_intervals']['max_s']<=2.5)
receipt=dict(schema='TTO-CPU-CAPABILITY-RECEIPT-v2',candidate_version=launch['version'],config_sha256=launch['config_sha256'],
    sidecar_config_sha256=sidecar_identity(launch['binding']['sidecar']),qualified=all(checks.values()),checks=checks,evaluation_scope='arrival_side',automatic_work_authorization=False,
    actual_sidecar_interval=dict(start_mono_s=start,stop_mono_s=end if start is not None else None),baseline_admission=baseline,
    resource_check_evidence=dict(native_callback_lag_p95_s=lag95,read_p95_s=read95,jitter_p95_s=jitter95,resources_by_actual_phase={k:[x for x in resources if phase(x['mono_s'])==k] for k in lags}),
    measured_resolution_evidence=dict(cpu_median_read_period_s=statistics.median(periods) if periods else None,GPU_independent_resolution='unknown unless source window/generation provided',rail_independent_resolution='unknown; native coarse baseline retained',exact_cross_host_source_lead='unknown'),
    source_run_id=s['native_run_id'],files={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['launch.json','summary.json','thread-policy.json','resources.jsonl']})
with a.output.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(qualified=receipt['qualified'],checks=checks,actual_sidecar_interval=receipt['actual_sidecar_interval']),indent=2))
````

下列为复用的启动回归与公共假流/输入依赖；不是本轮新增运行文件。

### `source/tests/test_startup.py`

SHA-256：`fc5d22f93e9696d846ad37b96770bc2dd7f00a60be9444d7d9affe599819c18f`；字节数：7082。以下为完整原文。

````python
import asyncio,base64,json,socket,tempfile,time
from pathlib import Path
import pytest
from tto_field import cpu_transport as tr

class Clock:
    domain='SYNTHETIC-LOCAL'
    def now(self):return 30
class Evidence:
    def __init__(self):self.rows=[]
    def append(self,name,row):self.rows.append((name,row))
class Pipeline:run_id='SYNTHETIC-NATIVE';fan_success_times=[]
class Process:
    next_pid=1000000
    def __init__(self,code=None,lines=b'',stderr=b''):
        self.pid=Process.next_pid;Process.next_pid+=1;self.returncode=code;self.done=asyncio.Event();self.terms=0;self.kills=0
        if code is not None:self.done.set()
        self.stdout=asyncio.StreamReader();self.stdout.feed_data(lines);self.stdout.feed_eof()
        self.stderr=asyncio.StreamReader();self.stderr.feed_data(stderr);self.stderr.feed_eof()
    async def wait(self):await self.done.wait();return self.returncode
    def terminate(self):self.terms+=1;self.returncode=-15;self.done.set()
    def kill(self):self.kills+=1;self.returncode=-9;self.done.set()

def packet(seq=1):
    return dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host='SYNTHETIC',boot_id='SYNTHETIC',source_session='SYNTHETIC',clock='CLOCK_MONOTONIC',command_id='C'),seq=seq,resources=dict(elapsed_s=.2,read_duration_s=.001,rss_bytes=1000,cpu_seconds=.001))
def configuration(mux):return dict(transport='existing_ssh_mux',existing_control_socket=str(mux),host='rm01@10.10.99.98',command_id='C',remote_python='/synthetic/python',remote_source_script='/synthetic/source.py',source_script_sha256='FAKE',remote_source_config='/synthetic/cfg.json',source_config_sha256='FAKE',remote_source_permission='/synthetic/permit.json')

@pytest.mark.parametrize('scenario',['check_hangs','stop','deadline','check_fails','normal','source_fails'])
def test_bounded_startup_and_evidence(monkeypatch,scenario):
    async def check():
        with tempfile.TemporaryDirectory(dir='/private/tmp',prefix='cpu2-') as folder:
            sock=socket.socket(socket.AF_UNIX);path=Path(folder)/'mux';sock.bind(str(path))
            created=[];calls=[];ev=Evidence()
            async def spawn(*argv,**kw):
                calls.append(argv);is_check='-O' in argv
                if is_check:p=Process(5 if scenario=='check_fails' else None if scenario in ('check_hangs','stop','deadline') else 0,stderr=b'E'*5000)
                else:p=Process(7 if scenario=='source_fails' else None,lines=b'' if scenario=='source_fails' else (json.dumps(packet())+'\n').encode(),stderr=b'SOURCE-FAILED' if scenario=='source_fails' else b'')
                created.append(p);return p
            monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
            monkeypatch.setattr(tr,'CHECK_BUDGET_S',.03);monkeypatch.setattr(tr,'STARTUP_BUDGET_S',.1)
            monkeypatch.setattr(tr,'TERM_GRACE_S',.02);monkeypatch.setattr(tr,'KILL_GRACE_S',.02)
            s=tr.Sidecar(configuration(path),Path(folder),Clock(),Pipeline(),ev)
            t=time.monotonic();await s.tick(30,None);assert time.monotonic()-t<.01
            await asyncio.sleep(.005)
            if scenario in ('stop','deadline'):
                await s.halt('user_stop' if scenario=='stop' else 'diagnostic_deadline')
            else:await asyncio.sleep(.06)
            t=time.monotonic();await s.close();assert time.monotonic()-t<.2
            assert s.startup_task.done() and all(p.returncode is not None for p in created)
            if scenario=='check_hangs':assert s.status=='mux_check_timeout'
            if scenario=='stop':assert s.status=='user_stop'
            if scenario=='deadline':assert s.status=='diagnostic_deadline'
            if scenario=='check_fails':assert s.status=='existing_connection_invalid' and len(created)==1
            if scenario=='normal':
                assert any(n=='cpu-sidecar-arrivals.jsonl' for n,r in ev.rows)
                assert 'ProxyCommand=false' in calls[-1] and calls[0][3:5]==('-O','check')
            if scenario=='source_fails':assert any(r.get('returncode')==7 and r.get('child_stage')=='source_start' for n,r in ev.rows)
            stderr=[r for n,r in ev.rows if n=='sidecar-stderr.jsonl'];assert stderr and all(len(base64.b64decode(r['captured_base64']))<=4096 for r in stderr)
            assert any(r['truncated'] for r in stderr)
            assert all(p.pid>=1000000 for p in created) # own child substitutes only, no master object exists
            assert any(r.get('own_tasks_remaining')==0 for n,r in ev.rows if r.get('event')=='cleanup_finished')
            sock.close()
    asyncio.run(check())

def test_invalid_raw_bytes_are_retained_not_analyzed():
    async def check():
        ev=Evidence();s=tr.Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipeline(),ev);s.started=30
        raw=b'not-json-\xff\n';s.process=Process(0,raw)
        await s.receive()
        wire=[r for n,r in ev.rows if n=='cpu-sidecar-wire.jsonl'];assert base64.b64decode(wire[0]['raw_base64'])==raw
        assert not any(n=='cpu-sidecar-arrivals.jsonl' for n,r in ev.rows)
        reject=[r for n,r in ev.rows if r.get('event')=='source_rejected'];assert reject[0]['wire_seq']==wire[0]['wire_seq'] and reject[0]['detail']
    asyncio.run(check())

def test_legacy_helper_latest_invalid_revokes_old():
    from tto_field.cpu_interface import causal_inputs
    valid=dict(field='cpu_max_percent',value=42,valid=True,clock_domain='R',observed_window_end_s=10.,available_at_s=10.,decision_generated_s=10.)
    invalid=dict(valid,valid=False,available_at_s=10.3,decision_generated_s=10.3,error='counter_reset')
    result=causal_inputs([valid,invalid],10.5,'R')
    assert result['INPUT-CORE']['cpu_max_percent'] is None
    recovered=dict(valid,value=40,observed_window_end_s=10.6,available_at_s=10.7,decision_generated_s=10.7)
    assert causal_inputs([valid,invalid,recovered],10.8,'R')['INPUT-CORE']['cpu_max_percent']['value']==40

def test_owned_real_child_timeout_and_stderr(tmp_path,monkeypatch):
    import sys
    async def check():
        with tempfile.TemporaryDirectory(dir='/private/tmp',prefix='cpu2-child-') as folder:
            path=Path(folder)/'mux';sock=socket.socket(socket.AF_UNIX);sock.bind(str(path));original=asyncio.create_subprocess_exec
            async def own_child(*argv,**kw):
                assert argv[0]=='ssh' and '-O' in argv
                return await original(sys.executable,'-c',"import sys,time;sys.stderr.write('LOCAL SYNTHETIC MUX CHILD\\n');sys.stderr.flush();time.sleep(30)",**kw)
            monkeypatch.setattr(asyncio,'create_subprocess_exec',own_child);monkeypatch.setattr(tr,'CHECK_BUDGET_S',.1)
            ev=Evidence();s=tr.Sidecar(configuration(path),tmp_path,Clock(),Pipeline(),ev)
            await s.tick(30,None);await s.startup_task;await s.close()
            assert s.status=='mux_check_timeout' and len(s.owned)==1 and s.owned[0][1].returncode is not None
            stderr=[r for n,r in ev.rows if n=='sidecar-stderr.jsonl'];assert b'LOCAL SYNTHETIC MUX CHILD' in base64.b64decode(stderr[0]['captured_base64'])
            sock.close()
    asyncio.run(check())
````

### `source/tests/fake_sidecar.py`

SHA-256：`0540d9bd23d0ea5e1b9aafbe43c6d01cc53b476a49b4f53b9020a2f855352d3c`；字节数：742。以下为完整原文。

````python
"""Synthetic stream for own-process transport tests, no /proc or GPU access."""
import json,sys,time,socket
command=sys.argv[1];start=time.monotonic();seq=0
while time.monotonic()-start<70:
    seq+=1;t=time.monotonic()
    r=dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host=socket.gethostname(),boot_id='SYNTHETIC-BOOT',source_session='SYNTHETIC-SOURCE',clock='CLOCK_MONOTONIC',command_id=command),seq=seq,
           read_start_mono_s=t,read_end_mono_s=t+.0001,cpu=dict(mean_percent=4,max_percent=40),gpu=dict(value=0,unit='percent',source_window=None),rails=[],
           resources=dict(elapsed_s=t-start,cpu_seconds=.0001,rss_bytes=1000000,read_duration_s=.0001,deadline_jitter_s=0))
    print(json.dumps(r),flush=True);time.sleep(.2)
````

### `source/tests/fake_source.py`

SHA-256：`f6373753871dc8c97baba8463a1b46f302efb75c8b0f46e4da0065e9c8f0ad21`；字节数：4689。以下为完整原文。

````python
"""Own numeric-loopback Socket.IO + ESP status + SSE service. All values SYNTHETIC."""
import asyncio,copy,json,time,uuid
from pathlib import Path
from aiohttp import web
import socketio
from tto_field.support import utc
FIX=Path(__file__).with_name('fixtures')

class FakeSource:
    def __init__(self,scenario='normal'):
        self.scenario=scenario;self.seq=0;self.connections=set();self.posts=0;self.active=0;self.peak=0;self.status_gets=[];self.completions=0
        self.start=None;self.runner=None;self.ticker=None;self.model_gets=0;self.silent=False;self.did_disconnect=False
    def packet(self):
        p=json.loads((FIX/'orin.json').read_text());self.seq+=1
        p['telemetry_meta'].update(sample_seq=self.seq,stream_id=str(uuid.UUID(int=1)),received_at=utc(),sample_age_ms=0.,fresh=True,collector_state='running')
        p['gpu'].update(sampled_at_utc=utc(),age_at_telemetry_receive_ms=0.,device_uuid='SYNTHETIC-GPU')
        p['timestamp']=utc();p['temperature']['tj']=44.3;p['temperature']['gpu']=44.3
        return p
    def payload(self,kind):
        p=json.loads((FIX/(kind+'.json')).read_text())
        if kind=='fan':
            p['data']['fans'][0].update(mode='auto',enabled=True,guard_active=self.scenario=='guard' and self.elapsed()>=18,
                                      fault=False,temp_stale=False,successful_duty=17,duty=17,duty_valid=True,controller_gain=.82)
        else:p['data'].update(manual_mode=False,normalized_valid=True,valid=True,active_source='variable',bound_variable='agx_info.temperature.tj')
        return p
    def elapsed(self):return time.monotonic()-self.start
    async def status(self,r):
        self.status_gets.append(dict(path=r.path,at_s=self.elapsed()));kind=r.match_info['kind']
        if kind=='fan' and self.scenario=='short_gap' and 20<=self.elapsed()<26:return web.Response(status=503)
        return web.json_response(self.payload(kind))
    async def models(self,r):self.model_gets+=1;return web.json_response({'data':[{'id':'SIMULATED-MODEL','root':'SYNTHETIC-ONLY'}]})
    async def metrics(self,r):return web.Response(text=f'vllm:num_requests_running {self.active}\nvllm:num_requests_waiting 0\n')
    async def request(self,r):
        self.posts+=1;idx=self.posts;self.active+=1;self.peak=max(self.peak,self.active)
        payload=await r.json();assert payload['max_tokens']==256 and payload['stream_options']['include_usage']
        response=web.StreamResponse(headers={'Content-Type':'text/event-stream'});await response.prepare(r)
        try:
            await asyncio.sleep(.1)
            await response.write(('data: '+json.dumps({'id':f'SYNTHETIC-{idx}','choices':[{'delta':{'content':'synthetic'},'finish_reason':None}]})+'\n\n').encode())
            await asyncio.sleep(.15)
            if self.scenario=='unknown' and idx==1:return response
            await response.write(('data: '+json.dumps({'id':f'SYNTHETIC-{idx}','choices':[{'delta':{},'finish_reason':'length'}],'usage':{'completion_tokens':256,'prompt_tokens':1,'total_tokens':257}})+'\n\n').encode())
            await response.write(b'data: [DONE]\n\n');self.completions+=1;return response
        except (ConnectionResetError,RuntimeError):return response
        finally:self.active-=1
    async def tick(self):
        while True:
            if self.connections and not self.silent:await self.sio.emit('tegrastats_update',self.packet())
            if self.scenario=='disconnect' and self.elapsed()>=5 and not self.did_disconnect:
                self.did_disconnect=True
                for sid in list(self.connections):await self.sio.disconnect(sid)
            await asyncio.sleep(1.)
    async def __aenter__(self):
        app=web.Application();self.sio=socketio.AsyncServer(async_mode='aiohttp',logger=False,engineio_logger=False);self.sio.attach(app)
        @self.sio.event
        async def connect(sid,environ):self.connections.add(sid)
        @self.sio.event
        async def disconnect(sid,*args):self.connections.discard(sid)
        app.router.add_get('/api/v1/{kind}/status',self.status);app.router.add_get('/v1/models',self.models);app.router.add_get('/metrics',self.metrics);app.router.add_post('/v1/chat/completions',self.request)
        self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]);self.start=time.monotonic();self.ticker=asyncio.create_task(self.tick());return self
    async def __aexit__(self,*args):
        self.ticker.cancel();await asyncio.gather(self.ticker,return_exceptions=True);await self.sio.shutdown();await self.runner.cleanup()
````

### `source/tests/source_fixture.py`

SHA-256：`0b0a427b178032ffca6985e1aa01a82ea2a7721d24e934f93191586234619f45`；字节数：2080。以下为完整原文。

````python
"""Synthetic /proc filesystem only. Actual cpu_source.read_cpu/utilization/stream serialize all packets."""
import functools,json,sys,time,resource
from types import SimpleNamespace
from pathlib import Path
from tto_field import cpu_source as source
root=Path(sys.argv[1]);command=sys.argv[2];root.mkdir(parents=True,exist_ok=True)
for d in ['proc/sys/kernel/random','sys/devices/system/cpu']:(root/d).mkdir(parents=True,exist_ok=True)
(root/'proc/sys/kernel/random/boot_id').write_text('SYNTHETIC-PROC-BOOT-NOT-THOR')
(root/'sys/devices/system/cpu/possible').write_text('0-1')
real_path=Path
source.Path=lambda p:root/'proc/sys/kernel/random/boot_id' if str(p)=='/proc/sys/kernel/random/boot_id' else real_path(p)
read=source.read_cpu;start=time.monotonic();counts=[[100,0,0,1000,0,0,0,0,0,0],[100,0,0,1000,0,0,0,0,0,0]];reset=False

def read_fixture():
    global reset
    elapsed=time.monotonic()-start
    if elapsed>=7 and not reset:
        counts[0][:]=[0]*10;counts[1][:]=[0]*10;reset=True
    offline=9<=elapsed<11
    active=3<=elapsed<15
    for i,row in enumerate(counts):
        if i==1 and offline:continue
        busy=(10 if i==0 else 6) if active else 0
        row[0]+=busy;row[3]+=20-busy
    online='0' if offline else '0-1';(root/'sys/devices/system/cpu/online').write_text(online)
    total=[sum(x) for x in zip(*counts)]
    (root/'proc/stat').write_text('\n'.join(' '.join([name,*map(str,row)]) for name,row in [('cpu',total),('cpu0',counts[0]),('cpu1',counts[1])])+'\n')
    return read(root=str(root))
source.read_cpu=read_fixture
# cpu_source is Linux-target code: Darwin reports ru_maxrss in bytes, Linux in KiB.
# Adapt only the local synthetic backend units; keep the production64MiB limit unchanged.
if sys.platform=='darwin':
    getusage=resource.getrusage
    resource.getrusage=lambda who:SimpleNamespace(ru_maxrss=getusage(who).ru_maxrss/1024)
source.stream(dict(query_target_s=.2,nvml=False,rails=[]),dict(action='cpu-sidecar-readonly',explicit_user_start=True,evidence='SYNTHETIC FILESYSTEM, NO DEVICE OR INFERENCE',command_id=command),30)
````

### `source/tests/fixtures/fan.json`

SHA-256：`ba28640535a3a2e03e9c13fa63a23ad5ecf56b464a92576d8d5727901963fb6a`；字节数：739。以下为完整原文。

````json
{
  "code": 0,
  "data": {
    "fans": [
      {
        "auto_state": "active",
        "control_temperature": 44.3,
        "controller_gain": 0.819374918937683,
        "cooling_response": 7.599999904632568,
        "duty": 17,
        "duty_valid": true,
        "enabled": true,
        "fault": false,
        "guard_active": false,
        "guard_temperature": 44.3,
        "id": 0,
        "mode": "auto",
        "predicted_temperature": 44.3,
        "rpm": 0,
        "running": true,
        "slope_c_per_min": 0,
        "target_duty": 17,
        "temp_stale": false,
        "temperature": 44.3
      }
    ],
    "temp_source": "agx_info.temperature.tj",
    "temp_valid": true,
    "temperature": 44.29999923706055
  }
}
````

### `source/tests/fixtures/orin.json`

SHA-256：`00fbd8b3fb4192b2d4caffea0c34de4fe2e50a4ca2626ab5fdbe56d4d8695868`；字节数：2617。以下为完整原文。

````json
{
  "cpu": {
    "cores": [
      {
        "freq": 972,
        "id": 0,
        "usage": 0
      },
      {
        "freq": 972,
        "id": 1,
        "usage": 0
      },
      {
        "freq": 972,
        "id": 2,
        "usage": 1
      },
      {
        "freq": 972,
        "id": 3,
        "usage": 0
      },
      {
        "freq": 972,
        "id": 4,
        "usage": 0
      },
      {
        "freq": 972,
        "id": 5,
        "usage": 0
      },
      {
        "freq": 1620,
        "id": 6,
        "usage": 0
      },
      {
        "freq": 1620,
        "id": 7,
        "usage": 2
      },
      {
        "freq": 1134,
        "id": 8,
        "usage": 0
      },
      {
        "freq": 1134,
        "id": 9,
        "usage": 0
      },
      {
        "freq": 972,
        "id": 10,
        "usage": 0
      },
      {
        "freq": 972,
        "id": 11,
        "usage": 1
      }
    ]
  },
  "gpu": {
    "age_at_telemetry_receive_ms": 974.5415459910873,
    "device_uuid": "GPU-a7c66ad2-6dbb-0ab8-c1a2-37ba6dba3600",
    "freshness_timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "sampled_at_utc": "2026-10-17T16:30:54.294252+00:00",
    "schema_version": 1,
    "source": "nvml",
    "status": "valid",
    "utilization_pct": 0
  },
  "memory": {
    "ram": {
      "total": 125772,
      "unit": "MB",
      "used": 53554
    },
    "swap": {
      "cached": 0,
      "total": 2048,
      "unit": "MB",
      "used": 0
    }
  },
  "platform": {
    "compatible": [
      "rm01,rm01-thor",
      "nvidia,p3834-0008",
      "nvidia,tegra264"
    ],
    "family": "jetson_thor",
    "gpu_backend": "nvml",
    "identification_source": "device_tree_compatible",
    "schema_version": 1,
    "soc": "tegra264"
  },
  "power": {
    "vdd_cpu_soc_mss": {
      "average": 5953,
      "current": 5952,
      "unit": "mW"
    },
    "vdd_gpu": {
      "average": 1988,
      "current": 1984,
      "unit": "mW"
    },
    "vin_sys_5v0": {
      "average": 4353,
      "current": 4392,
      "unit": "mW"
    }
  },
  "telemetry_meta": {
    "collector_state": "running",
    "fresh": true,
    "freshness_timeout_ms": 5000,
    "received_at": "2026-10-17T16:30:55.268793Z",
    "sample_age_ms": 269.3056990101468,
    "sample_seq": 201929,
    "schema_version": 1,
    "source_sample_interval_ms": 1000,
    "stream_id": "50ea6d93-8f3a-4991-9211-43cc8129cb90",
    "time_basis": "collector_receive"
  },
  "temperature": {
    "cpu": 43.75,
    "gpu": 44.281,
    "soc012": 43.218,
    "soc345": 42.968,
    "tj": 44.281
  },
  "timestamp": "2026-10-17T16:30:55.538308Z"
}
````

### `source/tests/fixtures/temp.json`

SHA-256：`81dc059869a270227ff0893933055a8eeece09473689f364c5b6eaeca965a45b`；字节数：306。以下为完整原文。

````json
{
  "code": 0,
  "data": {
    "active_source": "variable",
    "bound_variable": "agx_info.temperature.tj",
    "initialized": true,
    "manual_mode": false,
    "preferred_source": "variable",
    "temperature_01c": 443,
    "temperature_c": 44.3,
    "timestamp_ms": 202569269,
    "valid": true
  }
}
````

以下是已经完成的最终安装候选 36 项回归原始日志。本次导出未重新执行。

### `verification/installed-release-tests.log`

SHA-256：`0d1134645849cc1a65c715b2e99d8538dafc32092ebb4b5e247dc9688a789c21`；字节数：100。以下为完整原文。

````text
....................................                                     [100%]
36 passed in 21.46s
````

## 4. 实际 CLI 同进程线程、资源准入与数值等价证据

### 4.1 实际运行进程对应

最终自建服务 CLI 的 PID 为 **53570**。下列 `launch.json` 的 `clock_start.pid`、`summary.json` 的 `clock_end.pid`、实际 run 的 `thread-policy.json` 及最终汇总 PID 对应同一进程；startup 回执也一并保留。独立 verify-install 场景的其他 PID 不作为该 run 的线程证明。环境是 macOS ARM64 / CPython 3.12.3，本地自建服务不等于 N305 现场。

### `verification/installed-cli-loopback-release/run/thread-policy.json`

SHA-256：`c905aafde35a8ad21a4131d0b38b0d89ef13ec9b13ffc009c332f02613b25bdb`；字节数：5224。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53570,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:59.453376+00:00",
  "started_at_mono_s": 951426.730366833,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": "8",
    "OPENBLAS_DEFAULT_NUM_THREADS": "8",
    "OMP_NUM_THREADS": "8",
    "MKL_NUM_THREADS": "8",
    "NUMEXPR_NUM_THREADS": "8"
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [],
  "preloaded_versions": {
    "numpy": null,
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": true,
  "error": null,
  "applied_at_mono_s": 951426.737545333,
  "libraries": {
    "numpy": {
      "version": "2.2.6",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.29",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/include",
        "lib directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/lib",
        "openblas configuration": "OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cirrus-ci-build/.openblas"
      }
    },
    "scipy": {
      "version": "1.15.3",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.28",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/include",
        "lib directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/lib",
        "openblas configuration": "OpenBLAS 0.3.28 DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/Users/runner/work/scipy/scipy"
      }
    }
  },
  "extension_modules": {
    "numpy._core._multiarray_umath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/_core/_multiarray_umath.cpython-312-darwin.so",
    "scipy.linalg._fblas": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_fblas.cpython-312-darwin.so",
    "scipy.linalg._flapack": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_flapack.cpython-312-darwin.so"
  },
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "final_environment": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  },
  "checked_at_utc": "2026-10-20T15:23:59.579280+00:00",
  "checked_at_mono_s": 951426.863227708
}
````

### `verification/installed-cli-loopback-release/run.startup/thread-policy.json`

SHA-256：`f2e00d37f848f6cd9dfc8ecca48dbdd2257a29f4d9ec2bf6c6386a8030fd1aaf`；字节数：5223。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53570,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:59.453376+00:00",
  "started_at_mono_s": 951426.730366833,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": "8",
    "OPENBLAS_DEFAULT_NUM_THREADS": "8",
    "OMP_NUM_THREADS": "8",
    "MKL_NUM_THREADS": "8",
    "NUMEXPR_NUM_THREADS": "8"
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [],
  "preloaded_versions": {
    "numpy": null,
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": true,
  "error": null,
  "applied_at_mono_s": 951426.737545333,
  "libraries": {
    "numpy": {
      "version": "2.2.6",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.29",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/include",
        "lib directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/lib",
        "openblas configuration": "OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cirrus-ci-build/.openblas"
      }
    },
    "scipy": {
      "version": "1.15.3",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.28",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/include",
        "lib directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/lib",
        "openblas configuration": "OpenBLAS 0.3.28 DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/Users/runner/work/scipy/scipy"
      }
    }
  },
  "extension_modules": {
    "numpy._core._multiarray_umath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/_core/_multiarray_umath.cpython-312-darwin.so",
    "scipy.linalg._fblas": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_fblas.cpython-312-darwin.so",
    "scipy.linalg._flapack": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_flapack.cpython-312-darwin.so"
  },
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "final_environment": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  },
  "checked_at_utc": "2026-10-20T15:23:59.570522+00:00",
  "checked_at_mono_s": 951426.85450925
}
````

### `verification/installed-cli-loopback-release/run/launch.json`

SHA-256：`0dab00d93ca9e2baaaf3608e041074ea7ecdf809481f5a782b33d6f91290bf7a`；字节数：10054。以下为完整原文。

````json
{
  "version": "0.2.4+cpu.3",
  "mode": "diagnose",
  "command_id": "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c",
  "authorization": {
    "action": "readonly-diagnostic",
    "command_id": "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c",
    "explicit_user_start": true,
    "evidence": "LOCAL SELF-OWNED SERVICE TEST ONLY, NO REAL DEVICES"
  },
  "clock_start": {
    "domain": "Massif-MacBook-Pro.local:53570:4d3505d1-c3a5-47b3-8d57-f0e4aa9bcfa9",
    "mono_before_s": 951426.8670205,
    "utc": "2026-10-20T15:23:59.583041+00:00",
    "mono_after_s": 951426.867024041,
    "utc_clock_accuracy_s": null,
    "host": "Massif-MacBook-Pro.local",
    "platform": "macOS-27.0.1-arm64-arm-64bit",
    "pid": 53570
  },
  "config": {
    "schema_version": 1,
    "mode": "observe_only",
    "orin": {
      "source_id": "orin-primary",
      "base_url": "http://127.0.0.1:55007",
      "socketio_path": "socket.io",
      "namespace": "/",
      "event": "tegrastats_update",
      "transports": [
        "websocket"
      ],
      "source_sample_interval_ms": 1000,
      "source_interval_evidence": "OWNED SYNTHETIC LOOPBACK, NO FIELD",
      "headers_file": null,
      "ca_file": null
    },
    "tianshan": {
      "source_id": "esp32-primary",
      "base_url": "http://127.0.0.1:55007",
      "fan_id": 0,
      "fan_status_path": "/api/v1/fan/status",
      "temp_status_path": "/api/v1/temp/status",
      "fan_poll_interval_s": 1.0,
      "temp_poll_interval_s": 5.0,
      "headers_file": null,
      "ca_file": null
    },
    "network": {
      "request_timeout_s": 2.0,
      "connect_timeout_s": 5.0,
      "max_inflight_esp32": 1,
      "follow_redirects": false,
      "reconnect_initial_s": 1.0,
      "reconnect_max_s": 30.0,
      "reconnect_max_attempts": 10,
      "reconnect_jitter_ratio": 0.2,
      "max_business_payload_bytes": 65536
    },
    "storage": {
      "data_root": null,
      "chunk_bytes": 67108864,
      "run_max_bytes": 2147483648,
      "min_free_bytes": 1073741824,
      "queue_max_items": 256,
      "queue_max_bytes": 8388608,
      "overwrite_existing": false
    },
    "run": {
      "default_duration_s": 1800,
      "max_duration_s": 14400,
      "doctor_duration_s": 180,
      "single_instance": true
    },
    "features": {
      "schema_version": 1,
      "time_axis": "observer_receive",
      "history_s": 180,
      "prediction_stride_s": 5,
      "fan_max_age_s": 2.5,
      "optional_train_min_availability": 0.95,
      "max_feature_columns": 64,
      "missing_optional_policy": "fallback_tj_or_baseline",
      "power_current_rails": [
        "vdd_gpu_soc",
        "vdd_cpu_cv",
        "vin_sys_5v0"
      ]
    },
    "model": {
      "schema_version": 1,
      "horizons_s": [
        15,
        45,
        90
      ],
      "primary_horizon_s": 45,
      "methods": [
        "persist",
        "trend30",
        "ridge_tj",
        "ridge_full"
      ],
      "ridge_lambda_grid": [
        0.001,
        0.01,
        0.1,
        1.0
      ],
      "train_threads": 1,
      "train_timeout_s": 600,
      "online_training": false,
      "automatic_activation": false
    },
    "resources": {
      "observer_rss_target_mib": 256,
      "observer_cpu_single_core_target_pct": 5.0,
      "predict_all_horizons_p99_target_ms": 20.0,
      "train_rss_limit_mib": 2048
    },
    "security": {
      "business_control_writes": false,
      "production_discovery": false,
      "telemetry_upload": false,
      "system_service_install": false,
      "default_live_access": false
    }
  },
  "config_sha256": "525b3bb83be7199b80fbc234a39e9be08fdd01b16763770c61aa9d25c069e76a",
  "collector_source_identity": {
    "kind": "package_source_hashes",
    "sha256": "06d17ec5205cea268d4d42eeeb87169d3ca64c91a81acd0b4bdafe2f57e49806",
    "files": {
      "__init__.py": "672cde4b34710368c9ecba08ed361a47ef4a7c1f4ed5863a338bcde29549e700",
      "__main__.py": "79ee6f134c5c5193377cf9b189cbdcc3e2095e49ba9cec310114441c15a917c4",
      "cli.py": "d6adf47989226d57f798125c8f020bfdb8d1e14b357bf4f85ca82d3150747ce1",
      "collector.py": "4c696d3a63cef96d255e0e6e0fd5f56754727a2647801653ed373f0aede22563",
      "config.py": "5a05545f28b8b44b3e6f0e7efcf2453e01ee0726ef0bd228cc73d553e01d8e3e",
      "dataset.py": "32ee485269a521b0540f6d4050eab2dac46cc93a65603086eea263349d9487ee",
      "demo.py": "3e1475ee0753040f35d454138c47a39879c32d315db89824e101563d56b829fb",
      "deployment.py": "221b1d098d46623dc0eba5addc9804d917f8ede6cfa850cec1922c5cd177aaf7",
      "diagnostics.py": "93dfcc32ca5d9fee48d14b71375705f117a81afb2b0d17b89214be3317741055",
      "engine.py": "c979174d9f78fce54418ed847e9b4e57b155da07eba37c255c7037ecb27bf66c",
      "evaluation.py": "e6b2fc86f32cc28dbe204519bc74c13a138b9873164318727d4187c6dad78181",
      "features.py": "d6b32b3584eea3b57eb658c0d9c005b197a420062daec613f78a057bc4462fa2",
      "model.py": "371a6b81ad32c87654c231dd2e326b002a3e027b7a935b67117dd7508426fe7e",
      "platform_engine.py": "d1d8e48f10c731beb8a0d0b7195ab7e32553aae875ebff30a73846be88f967ea",
      "platform_quality.py": "3f7e33e083251eaff8136319495ab682a7f7fdc554d0efad39fe5d990085044e",
      "profiles.py": "3fb61fbe30bfce73cf7e1079c487e1ddb82b2301ed37d329e1e6da4bfc6944b4",
      "quality.py": "014e67c7885d291c8bede9ad3a51fb85398b26bc71e7336b3a0f18b81aec3e56",
      "recorded.py": "029679e59c68735d1ca98daf56553d6226c55e7d64597015712d972a8b7d2679",
      "report.py": "59834f8fc8f226311edf8376b3a8ecce6f5ca2a48ef79bc4532d551f14e9413e",
      "storage.py": "cda8d22444a0e1fe5fc2f1fa86b73cb4e3f9be4e76edb3cf265520b3285143ec",
      "training.py": "c8f0d6c83587b18c8a527e9d84e222276ee1bd0edc8e69a828dd1ed33a2de773",
      "util.py": "0a33bb268e7817ddd19b6ae81562c50e1fdd08a9cdb3fa08f8f2dd3fbb252f16"
    },
    "git_head": null,
    "dirty": null,
    "git_state": "not_checked_in_installed_runtime"
  },
  "binding": {
    "candidate_version": "0.2.4+cpu.3",
    "mode": "diagnose",
    "config_sha256": "525b3bb83be7199b80fbc234a39e9be08fdd01b16763770c61aa9d25c069e76a",
    "collector_source_sha256": "06d17ec5205cea268d4d42eeeb87169d3ca64c91a81acd0b4bdafe2f57e49806",
    "observer_model_sha256": "dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0",
    "observer_spec_sha256": "2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b",
    "old_overrides": false,
    "command_id": "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c",
    "expected_binding": "agx_info.temperature.tj",
    "firmware_identity": null,
    "authorization": {
      "action": "readonly-diagnostic",
      "command_id": "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c",
      "explicit_user_start": true,
      "evidence": "LOCAL SELF-OWNED SERVICE TEST ONLY, NO REAL DEVICES"
    },
    "note": "Preview creates no network clients and never opens credential headers. No device authorization is implied.",
    "request_actor_thread": null,
    "profile": {
      "id": "cpu-activity-pilot-v1",
      "stages": [
        {
          "kind": "background",
          "seconds": 180
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "recovery",
          "seconds": 30
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "recovery",
          "seconds": 60
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "recovery",
          "seconds": 35
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "recovery",
          "seconds": 55
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "recovery",
          "seconds": 40
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "recovery",
          "seconds": 50
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "work",
          "seconds": 30,
          "concurrency": 1
        },
        {
          "kind": "final_recovery",
          "seconds": 180
        }
      ],
      "hard_limit_seconds": 1200,
      "preparation_reserve_seconds": 60,
      "cleanup_reserve_seconds": 120,
      "drain_per_work_max_seconds": 30,
      "nominal_worst_normal_s": 1170
    },
    "profile_sha256": "addb4b2b6c4b143fe5f666742bf8072cc6003a7b2c7763da826fbf44e3f3bb88",
    "capability_receipt": null,
    "capability_user_decision_evidence": null,
    "instrument": {
      "used": false
    },
    "sidecar": {
      "transport": "synthetic",
      "query_target_s": 0.2,
      "command_id": "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c",
      "argv": [
        "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
        "/Users/massif/Tianshan-thermal-observer/experiments/cpu_runtime_threads_v1/tests/source_fixture.py",
        "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/verification/installed-cli-loopback-release/synthetic-proc",
        "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c"
      ]
    },
    "synthetic_loopback_only": true,
    "cpu_pilot_verified": true
  },
  "profile": null,
  "diagnostics_seconds": 60,
  "control_changes": false,
  "synthetic_loopback_only": true,
  "firmware_identity": null
}
````

### `verification/installed-cli-loopback-release/run/summary.json`

SHA-256：`7b806d998ab3dfc20214ac425a198dbf67f5d8748c98c40c0501f62ff30dc042`；字节数：9552。以下为完整原文。

````json
{
  "mode": "diagnose",
  "command_id": "SYNTHETIC-CLI-d069b4d7-fe00-4458-8bde-16149e04916c",
  "native_run_id": "7dd5948c-785a-48aa-8a1b-787ac5491488",
  "reason": "diagnostic_duration",
  "elapsed_s": 60.08190175006166,
  "time_coverage": {
    "observed_s": 60.07236116705462,
    "measurement_usable_s": 59.36036166700069,
    "model_usable_s": 50.36227925005369,
    "context_ready_s": 54.36219950008672,
    "joint_ready_s": 50.36227925005369,
    "work_paused_s": 0.0,
    "tj_usable_s": 59.36036166700069,
    "rail_usable_s": 59.36036166700069,
    "PWM_usable_s": 59.97119675006252,
    "temp_context_usable_s": 59.97119675006252
  },
  "phase_seconds": {
    "uninitialized": 0.7119995000539348,
    "provisional": 8.998082416947,
    "tracking": 50.36227925005369
  },
  "fan_success_intervals": {
    "count": 59,
    "max_s": 1.0100928340107203,
    "over_original_2_5s": 0
  },
  "protocol_requests": 0,
  "successful_requests": 0,
  "server_completion_unknown": false,
  "schedule_completed": false,
  "workload_intent": "evaluate_actual_protocol_GPU_rails_not_client_slots",
  "collector_task_identity": 4448010688,
  "collector_engine_instance_id": 4447788816,
  "observer_instances_created": 1,
  "native_callbacks": 193,
  "native_run_directories": 1,
  "I02_shared_engine_instance_id": 4447788816,
  "I02_preprocessed_views": 193,
  "requester_sessions_all_closed": true,
  "cpu_pilot_profile": true,
  "sidecar_status": "native_run_ending",
  "requester_instances_created": 0,
  "request_executor_instances_created": 0,
  "own_async_tasks_remaining": 0,
  "collector_summary": {
    "stop_reason": "duration",
    "poll_missed": 0,
    "poll_count": 72,
    "connection_attempts": 1,
    "payload_oversize": 0,
    "orin_event_count": 60,
    "business_payload_bytes_sum": 94851,
    "business_payload_bytes_max": 1581,
    "poll_rtt_ms": [
      7.1150410221889615,
      6.8428340600803494,
      3.293125075288117,
      4.133957903832197,
      5.228750058449805,
      3.2525419956073165,
      0.6090409588068724,
      0.579125015065074,
      1.359499990940094,
      1.951916958205402,
      5.717207910493016,
      4.61412500590086,
      4.406541003845632,
      3.129333956167102,
      4.620917025022209,
      4.960374906659126,
      3.9072080980986357,
      2.404165919870138,
      4.291290999390185,
      4.400165984407067,
      4.629750037565827,
      3.951749997213483,
      4.802667070180178,
      4.7318339347839355,
      2.224957919679582,
      2.9979590326547623,
      3.861833014525473,
      4.909666022285819,
      5.191707983613014,
      5.109958001412451,
      2.1561250323429704,
      3.776332945562899,
      6.647375063039362,
      5.537040997296572,
      2.5662919506430626,
      3.5652919905260205,
      3.954000072553754,
      0.9005420142784715,
      1.825292012654245,
      4.629415925592184,
      5.0622919807210565,
      5.1558330887928605,
      3.0100831063464284,
      3.474000026471913,
      4.424917045980692,
      2.7721250662580132,
      1.2017081025987864,
      1.2310000602155924,
      2.699500066228211,
      4.009583033621311,
      6.539541995152831,
      4.181290976703167,
      10.035708080977201,
      6.421166006475687,
      4.024791996926069,
      2.223458024673164,
      1.4783749356865883,
      2.3132499773055315,
      1.447040936909616,
      2.5636249920353293,
      4.707459011115134,
      3.781791077926755,
      3.6101670702919364,
      4.200625000521541,
      3.3788749715313315,
      3.779000020585954,
      1.112625002861023,
      1.1540839914232492,
      1.7906250432133675,
      1.9072499126195908,
      1.979875029064715,
      3.145833034068346
    ],
    "prediction_ms": [
      1.898874994367361,
      3.7641249364241958,
      3.5722500178962946,
      2.1083750762045383,
      3.817375050857663,
      4.838375025428832,
      5.041958997026086,
      1.7896249191835523,
      5.257040960714221,
      3.9656670996919274,
      1.7978750402107835,
      4.0545419324189425
    ],
    "rss_mib": [
      67.921875,
      68.546875,
      68.796875,
      68.921875,
      68.953125,
      68.953125,
      69.03125,
      69.046875,
      69.078125,
      69.109375,
      69.109375,
      69.109375,
      69.15625,
      69.203125,
      69.3125,
      69.328125,
      69.34375,
      69.34375,
      69.359375,
      69.375,
      69.375,
      69.390625,
      69.40625,
      69.484375,
      69.5,
      69.5,
      69.53125,
      69.5625,
      69.578125,
      69.75,
      69.796875,
      69.828125,
      69.859375,
      69.90625,
      69.921875,
      69.921875,
      69.9375,
      69.953125,
      69.984375,
      70.0,
      70.03125,
      70.078125,
      70.09375,
      70.109375,
      70.109375,
      70.140625,
      70.140625,
      70.15625,
      70.234375,
      70.234375,
      70.265625,
      70.28125,
      70.296875,
      70.328125,
      70.375,
      70.390625,
      70.390625,
      70.421875,
      70.4375
    ],
    "cpu_pct_single_core": [
      1.962443495390859,
      2.3814197609492447,
      2.7425523229279145,
      2.3421291954038215,
      2.173023923538973,
      1.4241391021947052,
      2.0535094620167484,
      1.7897008635261051,
      2.4384130421323973,
      3.3055246889171164,
      2.2729581590225836,
      2.1400296260282268,
      2.5542858402522164,
      2.7070595933859902,
      3.220810355796815,
      2.3944862602235157,
      2.23817521162989,
      2.6136937191533205,
      2.3682919658125905,
      2.8699958444956666,
      2.7067324087327505,
      2.38783853803253,
      2.6347911557645642,
      2.240919810992868,
      3.363246013778239,
      2.7222079930222387,
      2.6192197507114825,
      2.2542174967918545,
      2.3735292311907754,
      2.611666322570831,
      2.344023579505388,
      1.7734220007215855,
      2.9811630582800412,
      2.209086352449741,
      2.7893036691325572,
      2.14091976319306,
      2.3702979329301583,
      2.6013806614536996,
      2.585230297191266,
      1.7088509121778168,
      2.9359477743539917,
      2.655952530080935,
      2.2188890759331406,
      2.2828395700822015,
      2.7215093857292088,
      2.5551322323557217,
      2.019633604482924,
      1.7636472703980155,
      2.34380611199561,
      3.1401062550296963,
      2.7266061542817615,
      2.39653588307716,
      2.050447537648892,
      2.8554442960852855,
      3.0583796137779484,
      2.351121111253704,
      2.2602916515695943,
      2.540054085785637,
      1.6756977030298552
    ],
    "elapsed_s": 60.013043166021816,
    "queue_peak_items": 2,
    "queue_peak_bytes": 1943,
    "dropped": 0,
    "quality": {
      "boundary_socketio_connecting": 1,
      "boundary_control_context_change": 1,
      "boundary_stream": 1,
      "new_samples": 60,
      "boundary_input_boundary": 1,
      "boundary_input_profile_change": 1,
      "boundary_socketio_disconnected": 1,
      "boundary_run_end": 1
    },
    "processing": {
      "fan_ok": 60,
      "temp_ok": 12,
      "origins": 12
    },
    "target_host_verified": false,
    "polling_health": {
      "contract": "TTO-POLL-INDEPENDENT-v1",
      "max_inflight_per_endpoint": 1,
      "max_total_inflight_limit": 2,
      "max_total_inflight_observed": 2,
      "end_inflight": 0,
      "legacy_config_max_inflight_esp32": 1,
      "endpoints": {
        "fan": {
          "sent": 60,
          "returned": 60,
          "http_ok": 60,
          "errors": 0,
          "skipped": 0,
          "cancelled": 0,
          "peak_inflight": 1,
          "rtt_ms": {
            "n": 60,
            "p50": 3.7803955492563546,
            "p95": 6.544933648547158,
            "min": 0.579125015065074,
            "max": 10.035708080977201
          },
          "send_interval_s": {
            "n": 59,
            "p50": 1.0012078750878572,
            "p95": 1.0020592743181624,
            "min": 1.0000975420698524,
            "max": 1.004238124936819
          },
          "return_interval_s": {
            "n": 59,
            "p50": 1.001151374890469,
            "p95": 1.0045145753538236,
            "min": 0.9968267920194194,
            "max": 1.0100925420410931
          }
        },
        "temp": {
          "sent": 12,
          "returned": 12,
          "http_ok": 12,
          "errors": 0,
          "skipped": 0,
          "cancelled": 0,
          "peak_inflight": 1,
          "rtt_ms": {
            "n": 12,
            "p50": 3.482041589450091,
            "p95": 5.668377783149479,
            "min": 0.6090409588068724,
            "max": 6.8428340600803494
          },
          "send_interval_s": {
            "n": 11,
            "p50": 5.001052709063515,
            "p95": 5.001216000004206,
            "min": 5.000181958079338,
            "max": 5.001311625004746
          },
          "return_interval_s": {
            "n": 11,
            "p50": 5.0008097919635475,
            "p95": 5.003666353994049,
            "min": 4.994818915962242,
            "max": 5.004422749974765
          }
        }
      }
    }
  },
  "clock_end": {
    "domain": "Massif-MacBook-Pro.local:53570:4d3505d1-c3a5-47b3-8d57-f0e4aa9bcfa9",
    "mono_before_s": 951486.948578541,
    "utc": "2026-10-20T15:24:59.664665+00:00",
    "mono_after_s": 951486.948585541,
    "utc_clock_accuracy_s": null,
    "host": "Massif-MacBook-Pro.local",
    "platform": "macOS-27.0.1-arm64-arm-64bit",
    "pid": 53570
  },
  "control_changes": false,
  "field_proven": false,
  "synthetic_loopback_only": true
}
````

### `verification/validation-summary-release.json`

SHA-256：`daa377d9785b98aa5229386511c4353677053cee1a38e5711a8914650544e3ab`；字节数：2157。以下为完整原文。

````json
{
  "scope": "RELEASE wheel, actual installed CLI local macOS ARM64 synthetic loopback, NOT field",
  "pid": 53570,
  "pid_matches_runtime": true,
  "elapsed_s": 60.08190175006166,
  "sidecar_start_s": 30.067727165995166,
  "sidecar_stop_s": 60.07519012503326,
  "sidecar_status": "native_run_ending",
  "resources_by_actual_phase": {
    "before": {
      "samples": 29,
      "cpu_mean_pct": 2.476151255011963,
      "cpu_max_pct": 3.299489233557254,
      "rss_max_mib": 69.578125
    },
    "during": {
      "samples": 29,
      "cpu_mean_pct": 2.4322803934638646,
      "cpu_max_pct": 3.228790685477946,
      "rss_max_mib": 70.4375
    },
    "after": {
      "samples": 0,
      "cpu_mean_pct": null,
      "cpu_max_pct": null,
      "rss_max_mib": null
    }
  },
  "requester_instances": 0,
  "native_collectors": 1,
  "estimators": 1,
  "own_async_tasks_remaining": 0,
  "wire_packets": 150,
  "states": 193,
  "pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  }
}
````

### 4.2 旁录前基线准入及分支失败

实际本地 run 的准入回执完整保留。其后各 LOCAL 分支采用确定性资源与缩放时钟，只验证拒绝/启动/停止语义，不能用于性能结论。

### `verification/installed-cli-loopback-release/run/baseline-resource-admission.json`

SHA-256：`85c15e8d727fad28bcb9632ce9142d7d6cf443108e3eba1f07e6e69b1b87e7e9`；字节数：793。以下为完整原文。

````json
{
  "evaluated_mono_s": 30.063409583061002,
  "resource_sample": {
    "mono_s": 29.652130000060424,
    "interval_start_mono_s": 28.627941166050732,
    "cpu_pct_single_core": 2.6120308200652462,
    "rss_bytes": 72957952,
    "cpu_times": {
      "user": 0.688579904,
      "system": 0.276662112,
      "children_user": 0.0,
      "children_system": 0.0
    },
    "resource_error": null,
    "resource_seq": 29,
    "field_log_bytes": 1403451,
    "native_log_bytes": 179721
  },
  "cpu_limit_single_core_percent": 8.0,
  "rss_limit_bytes": 134217728,
  "allowed": true,
  "reason": "baseline_receiver_resources_qualified",
  "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization",
  "sample_age_s": 0.411279583000578
}
````

### `verification/resource-branch-release/scope.json`

SHA-256：`56fce2068ff18c252a5a52374f03568b9f48ba2010497325a5aefb8ab0ff20be`；字节数：365。以下为完整原文。

````json
{
  "scope": "installed release branch checks; test-only scaled clock and deterministic resources, not performance",
  "source": "/private/var/folders/88/hzsgvlyj5xzghddxy9rk5_5m0000gn/T/pytest-of-massif/pytest-630",
  "cases": [
    "LOCAL-high_cpu",
    "LOCAL-high_rss",
    "LOCAL-later_cpu",
    "LOCAL-normal",
    "LOCAL-unknown"
  ],
  "suite_passed": 36
}
````

### `verification/resource-branch-release/LOCAL-high_cpu/baseline-resource-admission.json`

SHA-256：`3d55cafa5da3c28d67cb2e96e36e26906b80e082a5e881516447f733498417b7`；字节数：791。以下为完整原文。

````json
{
  "evaluated_mono_s": 30.47715567238629,
  "resource_sample": {
    "mono_s": 29.637988336384296,
    "interval_start_mono_s": 28.014210999943316,
    "cpu_pct_single_core": 20.035021142679703,
    "rss_bytes": 83886080,
    "cpu_times": {
      "user": 0.5604885326698422,
      "system": 0,
      "children_user": 0.0,
      "children_system": 0.0
    },
    "resource_error": null,
    "resource_seq": 2,
    "field_log_bytes": 28444,
    "native_log_bytes": 9357
  },
  "cpu_limit_single_core_percent": 8.0,
  "rss_limit_bytes": 134217728,
  "allowed": false,
  "reason": "baseline_receiver_resource_budget_exceeded",
  "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization",
  "sample_age_s": 0.8391673360019922
}
````

### `verification/resource-branch-release/LOCAL-high_cpu/sidecar-events.jsonl`

SHA-256：`ce7433f559bedb551cf3aef4552e745a670a9d6059e899bec4722e5a34b5b9df`；字节数：1293。以下为完整原文。

````jsonl
{"event": "baseline_resource_admission", "mono_s": 30.49207300040871, "at_utc": "2026-10-20T15:23:29.752361+00:00", "status": "baseline", "stage": "baseline", "admission": {"evaluated_mono_s": 30.47715567238629, "resource_sample": {"mono_s": 29.637988336384296, "interval_start_mono_s": 28.014210999943316, "cpu_pct_single_core": 20.035021142679703, "rss_bytes": 83886080, "cpu_times": {"user": 0.5604885326698422, "system": 0, "children_user": 0.0, "children_system": 0.0}, "resource_error": null, "resource_seq": 2, "field_log_bytes": 28444, "native_log_bytes": 9357}, "cpu_limit_single_core_percent": 8.0, "rss_limit_bytes": 134217728, "allowed": false, "reason": "baseline_receiver_resource_budget_exceeded", "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization", "sample_age_s": 0.8391673360019922}}
{"event": "stop_sidecar_only", "mono_s": 30.498437999747694, "at_utc": "2026-10-20T15:23:29.753149+00:00", "status": "baseline_receiver_resource_budget_exceeded", "stage": "baseline"}
{"event": "cleanup_finished", "mono_s": 60.212656335905194, "at_utc": "2026-10-20T15:23:33.467427+00:00", "status": "baseline_receiver_resource_budget_exceeded", "stage": "baseline", "own_tasks_remaining": 0, "unreaped_children": 0}
````

### `verification/resource-branch-release/LOCAL-high_rss/baseline-resource-admission.json`

SHA-256：`9620836152e170bafc6928fe8b549fe391cc5c8afedfa6fd93a15ddb502ce4a7`；字节数：795。以下为完整原文。

````json
{
  "evaluated_mono_s": 30.489138663746417,
  "resource_sample": {
    "mono_s": 29.644198999740183,
    "interval_start_mono_s": 28.018695999868214,
    "cpu_pct_single_core": 0.5011383135765469,
    "rss_bytes": 135266304,
    "cpu_times": {
      "user": 0.008498668321408331,
      "system": 0,
      "children_user": 0.0,
      "children_system": 0.0
    },
    "resource_error": null,
    "resource_seq": 2,
    "field_log_bytes": 28448,
    "native_log_bytes": 9364
  },
  "cpu_limit_single_core_percent": 8.0,
  "rss_limit_bytes": 134217728,
  "allowed": false,
  "reason": "baseline_receiver_resource_budget_exceeded",
  "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization",
  "sample_age_s": 0.8449396640062332
}
````

### `verification/resource-branch-release/LOCAL-high_rss/sidecar-events.jsonl`

SHA-256：`409a52f33451f3d96bf2b54947d7fa15403b92843a3d1394f91900cc5b5af507`；字节数：1297。以下为完整原文。

````jsonl
{"event": "baseline_resource_admission", "mono_s": 30.506462328135967, "at_utc": "2026-10-20T15:23:33.800747+00:00", "status": "baseline", "stage": "baseline", "admission": {"evaluated_mono_s": 30.489138663746417, "resource_sample": {"mono_s": 29.644198999740183, "interval_start_mono_s": 28.018695999868214, "cpu_pct_single_core": 0.5011383135765469, "rss_bytes": 135266304, "cpu_times": {"user": 0.008498668321408331, "system": 0, "children_user": 0.0, "children_system": 0.0}, "resource_error": null, "resource_seq": 2, "field_log_bytes": 28448, "native_log_bytes": 9364}, "cpu_limit_single_core_percent": 8.0, "rss_limit_bytes": 134217728, "allowed": false, "reason": "baseline_receiver_resource_budget_exceeded", "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization", "sample_age_s": 0.8449396640062332}}
{"event": "stop_sidecar_only", "mono_s": 30.514952999539673, "at_utc": "2026-10-20T15:23:33.801801+00:00", "status": "baseline_receiver_resource_budget_exceeded", "stage": "baseline"}
{"event": "cleanup_finished", "mono_s": 60.33956132736057, "at_utc": "2026-10-20T15:23:37.529882+00:00", "status": "baseline_receiver_resource_budget_exceeded", "stage": "baseline", "own_tasks_remaining": 0, "unreaped_children": 0}
````

### `verification/resource-branch-release/LOCAL-unknown/baseline-resource-admission.json`

SHA-256：`41e1921fbc094db9490351e54f3381c50884740bdc7cf97da1bc794590d47894`；字节数：628。以下为完整原文。

````json
{
  "evaluated_mono_s": 30.473872336558998,
  "resource_sample": {
    "mono_s": 29.64213267248124,
    "interval_start_mono_s": null,
    "cpu_pct_single_core": null,
    "rss_bytes": null,
    "cpu_times": null,
    "resource_error": "TEST_RESOURCE_UNAVAILABLE",
    "resource_seq": 2,
    "field_log_bytes": 28363,
    "native_log_bytes": 9363
  },
  "cpu_limit_single_core_percent": 8.0,
  "rss_limit_bytes": 134217728,
  "allowed": false,
  "reason": "baseline_receiver_resources_unavailable",
  "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization"
}
````

### `verification/resource-branch-release/LOCAL-unknown/sidecar-events.jsonl`

SHA-256：`366977f032eceffb84bf5e821350a1677c5337900c315c5d40862e08836c3c8f`；字节数：1156。以下为完整原文。

````jsonl
{"event": "baseline_resource_admission", "mono_s": 30.490006672218442, "at_utc": "2026-10-20T15:23:37.862402+00:00", "status": "baseline", "stage": "baseline", "admission": {"evaluated_mono_s": 30.473872336558998, "resource_sample": {"mono_s": 29.64213267248124, "interval_start_mono_s": null, "cpu_pct_single_core": null, "rss_bytes": null, "cpu_times": null, "resource_error": "TEST_RESOURCE_UNAVAILABLE", "resource_seq": 2, "field_log_bytes": 28363, "native_log_bytes": 9363}, "cpu_limit_single_core_percent": 8.0, "rss_limit_bytes": 134217728, "allowed": false, "reason": "baseline_receiver_resources_unavailable", "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization"}}
{"event": "stop_sidecar_only", "mono_s": 30.498494336381555, "at_utc": "2026-10-20T15:23:37.863457+00:00", "status": "baseline_receiver_resources_unavailable", "stage": "baseline"}
{"event": "cleanup_finished", "mono_s": 60.23674499988556, "at_utc": "2026-10-20T15:23:41.580739+00:00", "status": "baseline_receiver_resources_unavailable", "stage": "baseline", "own_tasks_remaining": 0, "unreaped_children": 0}
````

### `verification/resource-branch-release/LOCAL-normal/baseline-resource-admission.json`

SHA-256：`8b973390b494af9c78f7dce1455a9c1d3f6b589b20d38d6b3748917c063084f5`；字节数：785。以下为完整原文。

````json
{
  "evaluated_mono_s": 30.510602000169456,
  "resource_sample": {
    "mono_s": 29.647470336407423,
    "interval_start_mono_s": 28.0194423366338,
    "cpu_pct_single_core": 0.5010135970448439,
    "rss_bytes": 83886080,
    "cpu_times": {
      "user": 0.008510658321902157,
      "system": 0,
      "children_user": 0.0,
      "children_system": 0.0
    },
    "resource_error": null,
    "resource_seq": 2,
    "field_log_bytes": 28419,
    "native_log_bytes": 9356
  },
  "cpu_limit_single_core_percent": 8.0,
  "rss_limit_bytes": 134217728,
  "allowed": true,
  "reason": "baseline_receiver_resources_qualified",
  "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization",
  "sample_age_s": 0.863131663762033
}
````

### `verification/resource-branch-release/LOCAL-normal/sidecar-events.jsonl`

SHA-256：`c6e0310e6cee563bfb4da3e7622c42cf80d3dec7bab22d6d533e9bce16507193`；字节数：1767。以下为完整原文。

````jsonl
{"event": "baseline_resource_admission", "mono_s": 30.536700336262584, "at_utc": "2026-10-20T15:23:41.919409+00:00", "status": "baseline", "stage": "baseline", "admission": {"evaluated_mono_s": 30.510602000169456, "resource_sample": {"mono_s": 29.647470336407423, "interval_start_mono_s": 28.0194423366338, "cpu_pct_single_core": 0.5010135970448439, "rss_bytes": 83886080, "cpu_times": {"user": 0.008510658321902157, "system": 0, "children_user": 0.0, "children_system": 0.0}, "resource_error": null, "resource_seq": 2, "field_log_bytes": 28419, "native_log_bytes": 9356}, "cpu_limit_single_core_percent": 8.0, "rss_limit_bytes": 134217728, "allowed": true, "reason": "baseline_receiver_resources_qualified", "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization", "sample_age_s": 0.863131663762033}}
{"event": "startup_scheduled", "mono_s": 30.546200999990106, "at_utc": "2026-10-20T15:23:41.920591+00:00", "status": "starting", "stage": "baseline", "startup_budget_s": 3.0}
{"event": "started", "mono_s": 30.626862999983132, "at_utc": "2026-10-20T15:23:41.930676+00:00", "status": "running", "stage": "receive"}
{"event": "stop_sidecar_only", "mono_s": 60.0330796726048, "at_utc": "2026-10-20T15:23:45.606449+00:00", "status": "native_run_ending", "stage": "receive"}
{"event": "child_exit", "mono_s": 60.047833000309765, "at_utc": "2026-10-20T15:23:45.608294+00:00", "status": "native_run_ending", "stage": "receive", "child_stage": "source_start", "returncode": -15, "child_pid": 53523}
{"event": "cleanup_finished", "mono_s": 60.05291000008583, "at_utc": "2026-10-20T15:23:45.608929+00:00", "status": "native_run_ending", "stage": "receive", "own_tasks_remaining": 0, "unreaped_children": 0}
````

### `verification/resource-branch-release/LOCAL-later_cpu/baseline-resource-admission.json`

SHA-256：`af1d1073f1348ff933e36910ac87f011d3974cb0483c0e92c533b0a5a6cff11d`；字节数：787。以下为完整原文。

````json
{
  "evaluated_mono_s": 30.478293335996568,
  "resource_sample": {
    "mono_s": 29.64080967195332,
    "interval_start_mono_s": 28.017053000628948,
    "cpu_pct_single_core": 0.5009805437117717,
    "rss_bytes": 83886080,
    "cpu_times": {
      "user": 0.008444723323918879,
      "system": 0,
      "children_user": 0.0,
      "children_system": 0.0
    },
    "resource_error": null,
    "resource_seq": 2,
    "field_log_bytes": 28467,
    "native_log_bytes": 9370
  },
  "cpu_limit_single_core_percent": 8.0,
  "rss_limit_bytes": 134217728,
  "allowed": true,
  "reason": "baseline_receiver_resources_qualified",
  "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization",
  "sample_age_s": 0.8374836640432477
}
````

### `verification/resource-branch-release/LOCAL-later_cpu/sidecar-events.jsonl`

SHA-256：`b06933c0bd9b19f842eee37d14a7b7c798b93cf6cf75b0749dd178bd30b4ebf9`；字节数：1834。以下为完整原文。

````jsonl
{"event": "baseline_resource_admission", "mono_s": 30.500249336473644, "at_utc": "2026-10-20T15:23:45.936715+00:00", "status": "baseline", "stage": "baseline", "admission": {"evaluated_mono_s": 30.478293335996568, "resource_sample": {"mono_s": 29.64080967195332, "interval_start_mono_s": 28.017053000628948, "cpu_pct_single_core": 0.5009805437117717, "rss_bytes": 83886080, "cpu_times": {"user": 0.008444723323918879, "system": 0, "children_user": 0.0, "children_system": 0.0}, "resource_error": null, "resource_seq": 2, "field_log_bytes": 28467, "native_log_bytes": 9370}, "cpu_limit_single_core_percent": 8.0, "rss_limit_bytes": 134217728, "allowed": true, "reason": "baseline_receiver_resources_qualified", "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization", "sample_age_s": 0.8374836640432477}}
{"event": "startup_scheduled", "mono_s": 30.50857867207378, "at_utc": "2026-10-20T15:23:45.937749+00:00", "status": "starting", "stage": "baseline", "startup_budget_s": 3.0}
{"event": "started", "mono_s": 30.60390100069344, "at_utc": "2026-10-20T15:23:45.949667+00:00", "status": "running", "stage": "receive"}
{"event": "stop_sidecar_only", "mono_s": 37.89096833579242, "at_utc": "2026-10-20T15:23:46.860551+00:00", "status": "receiver_total_resource_budget_exceeded", "stage": "receive"}
{"event": "child_exit", "mono_s": 60.16751667205244, "at_utc": "2026-10-20T15:23:49.645118+00:00", "status": "receiver_total_resource_budget_exceeded", "stage": "receive", "child_stage": "source_start", "returncode": -15, "child_pid": 53544}
{"event": "cleanup_finished", "mono_s": 60.173616671934724, "at_utc": "2026-10-20T15:23:49.645880+00:00", "status": "receiver_total_resource_budget_exceeded", "stage": "receive", "own_tasks_remaining": 0, "unreaped_children": 0}
````

### 4.3 实际 CLI 核验与拒绝回执

保留干净环境、继承 8、共用入口三个核验场景，以及提前加载 NumPy、无法覆盖全部库池两个拒绝场景；这些是最终候选的本地验证，不是设备测试。

### `verification/installed-cli-release/receipt.json`

SHA-256：`996814ddfb1d8cad8f782d841c1585426f82253142ddcc15e022fda1938ab42e`；字节数：3223。以下为完整原文。

````json
[
  {
    "scenario": "clean",
    "returncode": 0,
    "pid": 53481,
    "verified": true,
    "pools": [
      {
        "user_api": "blas",
        "internal_api": "openblas",
        "num_threads": 1,
        "prefix": "libscipy_openblas",
        "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
        "version": "0.3.29",
        "threading_layer": "pthreads",
        "architecture": "neoversen1"
      },
      {
        "user_api": "blas",
        "internal_api": "openblas",
        "num_threads": 1,
        "prefix": "libscipy_openblas",
        "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
        "version": "0.3.28",
        "threading_layer": "pthreads",
        "architecture": "neoversen1"
      }
    ]
  },
  {
    "scenario": "inherited8",
    "returncode": 0,
    "pid": 53495,
    "verified": true,
    "pools": [
      {
        "user_api": "blas",
        "internal_api": "openblas",
        "num_threads": 1,
        "prefix": "libscipy_openblas",
        "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
        "version": "0.3.29",
        "threading_layer": "pthreads",
        "architecture": "neoversen1"
      },
      {
        "user_api": "blas",
        "internal_api": "openblas",
        "num_threads": 1,
        "prefix": "libscipy_openblas",
        "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
        "version": "0.3.28",
        "threading_layer": "pthreads",
        "architecture": "neoversen1"
      }
    ]
  },
  {
    "scenario": "shared-field-entry",
    "returncode": 0,
    "pid": 53498,
    "verified": true,
    "pools": [
      {
        "user_api": "blas",
        "internal_api": "openblas",
        "num_threads": 1,
        "prefix": "libscipy_openblas",
        "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
        "version": "0.3.29",
        "threading_layer": "pthreads",
        "architecture": "neoversen1"
      },
      {
        "user_api": "blas",
        "internal_api": "openblas",
        "num_threads": 1,
        "prefix": "libscipy_openblas",
        "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
        "version": "0.3.28",
        "threading_layer": "pthreads",
        "architecture": "neoversen1"
      }
    ]
  },
  {
    "scenario": "preloaded_numpy",
    "returncode": 1,
    "verified": false,
    "network_attempts": 0,
    "recorded_pid": 53501
  },
  {
    "scenario": "unverifiable_pool",
    "returncode": 1,
    "verified": false,
    "run_created": false,
    "pid": 53506
  }
]
````

### `verification/installed-cli-release/clean-thread-policy.json`

SHA-256：`b3d455f10a7b73f991d0a03c2a5ba0dbae8129e097adb62f30f23d2f2109b8f5`；字节数：5229。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53481,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:27.558315+00:00",
  "started_at_mono_s": 951394.831690625,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": null,
    "OPENBLAS_DEFAULT_NUM_THREADS": null,
    "OMP_NUM_THREADS": null,
    "MKL_NUM_THREADS": null,
    "NUMEXPR_NUM_THREADS": null
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [],
  "preloaded_versions": {
    "numpy": null,
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": true,
  "error": null,
  "applied_at_mono_s": 951394.842487958,
  "libraries": {
    "numpy": {
      "version": "2.2.6",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.29",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/include",
        "lib directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/lib",
        "openblas configuration": "OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cirrus-ci-build/.openblas"
      }
    },
    "scipy": {
      "version": "1.15.3",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.28",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/include",
        "lib directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/lib",
        "openblas configuration": "OpenBLAS 0.3.28 DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/Users/runner/work/scipy/scipy"
      }
    }
  },
  "extension_modules": {
    "numpy._core._multiarray_umath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/_core/_multiarray_umath.cpython-312-darwin.so",
    "scipy.linalg._fblas": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_fblas.cpython-312-darwin.so",
    "scipy.linalg._flapack": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_flapack.cpython-312-darwin.so"
  },
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "final_environment": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  },
  "checked_at_utc": "2026-10-20T15:23:27.686992+00:00",
  "checked_at_mono_s": 951394.971014625
}
````

### `verification/installed-cli-release/inherited8-thread-policy.json`

SHA-256：`684a204b938d19b9d951fa74711b09a84f944c1a2539853e8f10952c9bbee8e1`；字节数：5224。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53495,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:27.770276+00:00",
  "started_at_mono_s": 951395.047140291,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": "8",
    "OPENBLAS_DEFAULT_NUM_THREADS": "8",
    "OMP_NUM_THREADS": "8",
    "MKL_NUM_THREADS": "8",
    "NUMEXPR_NUM_THREADS": "8"
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [],
  "preloaded_versions": {
    "numpy": null,
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": true,
  "error": null,
  "applied_at_mono_s": 951395.054388166,
  "libraries": {
    "numpy": {
      "version": "2.2.6",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.29",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/include",
        "lib directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/lib",
        "openblas configuration": "OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cirrus-ci-build/.openblas"
      }
    },
    "scipy": {
      "version": "1.15.3",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.28",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/include",
        "lib directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/lib",
        "openblas configuration": "OpenBLAS 0.3.28 DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/Users/runner/work/scipy/scipy"
      }
    }
  },
  "extension_modules": {
    "numpy._core._multiarray_umath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/_core/_multiarray_umath.cpython-312-darwin.so",
    "scipy.linalg._fblas": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_fblas.cpython-312-darwin.so",
    "scipy.linalg._flapack": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_flapack.cpython-312-darwin.so"
  },
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "final_environment": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  },
  "checked_at_utc": "2026-10-20T15:23:27.890454+00:00",
  "checked_at_mono_s": 951395.174474916
}
````

### `verification/installed-cli-release/shared-field-entry-thread-policy.json`

SHA-256：`dcc06eedccb4591b91e9290b32e5cb52d99c241d072108e2d3b969824117ac77`；字节数：5221。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53498,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:28.536406+00:00",
  "started_at_mono_s": 951395.812222666,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": "8",
    "OPENBLAS_DEFAULT_NUM_THREADS": "8",
    "OMP_NUM_THREADS": "8",
    "MKL_NUM_THREADS": "8",
    "NUMEXPR_NUM_THREADS": "8"
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [],
  "preloaded_versions": {
    "numpy": null,
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": true,
  "error": null,
  "applied_at_mono_s": 951395.820551041,
  "libraries": {
    "numpy": {
      "version": "2.2.6",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.29",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/include",
        "lib directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/lib",
        "openblas configuration": "OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cirrus-ci-build/.openblas"
      }
    },
    "scipy": {
      "version": "1.15.3",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.28",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/include",
        "lib directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/lib",
        "openblas configuration": "OpenBLAS 0.3.28 DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/Users/runner/work/scipy/scipy"
      }
    }
  },
  "extension_modules": {
    "numpy._core._multiarray_umath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/_core/_multiarray_umath.cpython-312-darwin.so",
    "scipy.linalg._fblas": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_fblas.cpython-312-darwin.so",
    "scipy.linalg._flapack": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_flapack.cpython-312-darwin.so"
  },
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "final_environment": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  },
  "checked_at_utc": "2026-10-20T15:23:28.659175+00:00",
  "checked_at_mono_s": 951395.943195
}
````

### `verification/installed-cli-release/must-not-run.startup/thread-policy.json`

SHA-256：`5650da23c87a23cdc5d231b8abc358042aeb900db551c27e5570761823bce82c`；字节数：1784。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53501,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:28.790350+00:00",
  "started_at_mono_s": 951396.065743333,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": null,
    "OPENBLAS_DEFAULT_NUM_THREADS": null,
    "OMP_NUM_THREADS": null,
    "MKL_NUM_THREADS": null,
    "NUMEXPR_NUM_THREADS": null
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [
    "numpy"
  ],
  "preloaded_versions": {
    "numpy": "2.2.6",
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": false,
  "error": "numeric_libraries_loaded_before_policy",
  "error_class": "RuntimeError",
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 14,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "checked_at_utc": "2026-10-20T15:23:28.798278+00:00",
  "checked_at_mono_s": 951396.0822975
}
````

### `verification/installed-cli-release/preloaded-rejection.stderr`

SHA-256：`cffdd7ff515e4b19f2baa23e6c0a6f05e9f4a2e2c4bd8bdf24e5bb5ca941fde1`；字节数：816。以下为完整原文。

````text
Traceback (most recent call last):
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/tto-cpu-pilot", line 8, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/tto_field/cpu_cli.py", line 32, in main
    initialize(receipt)
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/tto_field/numeric_policy.py", line 75, in initialize
    if not r['verified']:raise RuntimeError('numeric_policy_failed:'+r['error'])
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: numeric_policy_failed:numeric_libraries_loaded_before_policy
````

### `verification/installed-cli-release/unknown-pool-run.startup/thread-policy.json`

SHA-256：`964ecfdb043009a44ca17ef2430f132ae481e1fc72038d04a7a0147476d8a4f5`；字节数：4727。以下为完整原文。

````json
{
  "schema": "TTO-NUMERIC-THREAD-POLICY-v1",
  "candidate_version": "0.2.4+cpu.3",
  "pid": 53506,
  "host": "Massif-MacBook-Pro.local",
  "executable": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/python",
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "started_at_utc": "2026-10-20T15:23:28.871605+00:00",
  "started_at_mono_s": 951396.147037791,
  "inherited_environment": {
    "OPENBLAS_NUM_THREADS": null,
    "OPENBLAS_DEFAULT_NUM_THREADS": null,
    "OMP_NUM_THREADS": null,
    "MKL_NUM_THREADS": null,
    "NUMEXPR_NUM_THREADS": null
  },
  "policy": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "policy_scope": "this candidate process numeric libraries only; not Python threads or other applications",
  "modules_already_loaded": [],
  "preloaded_versions": {
    "numpy": null,
    "scipy": null
  },
  "threadpoolctl_version": "3.6.0",
  "verified": false,
  "error": "numeric_backend_not_verifiable_by_candidate",
  "applied_at_mono_s": 951396.155749333,
  "libraries": {
    "numpy": {
      "version": "2.2.6",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.29",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/include",
        "lib directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cibw-run-uqh7mzsf/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas64/lib",
        "openblas configuration": "OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/private/var/folders/hn/b1w4xwz56_58rv5ckn7581vw0000gn/T/cirrus-ci-build/.openblas"
      }
    },
    "scipy": {
      "version": "1.15.3",
      "module": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/__init__.py",
      "blas": {
        "name": "scipy-openblas",
        "found": true,
        "version": "0.3.28",
        "detection method": "pkgconfig",
        "include directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/include",
        "lib directory": "/private/var/folders/hn/k7g0_sh57112t0xtjxcjcm5r0000gn/T/cibw-run-528_w15_/cp312-macosx_arm64/build/venv/lib/python3.12/site-packages/scipy_openblas32/lib",
        "openblas configuration": "OpenBLAS 0.3.28 DYNAMIC_ARCH NO_AFFINITY neoversen1 MAX_THREADS=64",
        "pc file directory": "/Users/runner/work/scipy/scipy"
      }
    }
  },
  "extension_modules": {
    "numpy._core._multiarray_umath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/_core/_multiarray_umath.cpython-312-darwin.so",
    "scipy.linalg._fblas": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_fblas.cpython-312-darwin.so",
    "scipy.linalg._flapack": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/linalg/_flapack.cpython-312-darwin.so"
  },
  "loaded_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "final_environment": {
    "OPENBLAS_NUM_THREADS": "1",
    "OPENBLAS_DEFAULT_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1"
  },
  "pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": []
  },
  "error_class": "RuntimeError",
  "checked_at_utc": "2026-10-20T15:23:28.993632+00:00",
  "checked_at_mono_s": 951396.277652291
}
````

### `verification/installed-cli-release/unknown-pool.stderr`

SHA-256：`f1f2baee780f0f6c7c27d04266af09aeb0c108c4abdcbb4135e035f4b922b3da`；字节数：821。以下为完整原文。

````text
Traceback (most recent call last):
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/tto-cpu-pilot", line 8, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/tto_field/cpu_cli.py", line 32, in main
    initialize(receipt)
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/tto_field/numeric_policy.py", line 75, in initialize
    if not r['verified']:raise RuntimeError('numeric_policy_failed:'+r['error'])
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: numeric_policy_failed:numeric_backend_not_verifiable_by_candidate
````

### `verification/installed-cli-release/unknown-pool-site/sitecustomize.py`

SHA-256：`c2b4b9abdd81d7ac67e899cf1bc36886f4e1f978f9cfc8025ec9613884608b6a`；字节数：112。以下为完整原文。

````python
import threadpoolctl
original=threadpoolctl.threadpool_info
threadpoolctl.threadpool_info=lambda:original()[:1]
````

### 4.4 合成能力判定与未验证目标

合成源含计数重置/核 offline 故障，因此完整能力回执 `qualified=false`、`cpu_measured=false`；没有删掉失效窗口凑通过。退出后资源样本为 0，after 均值仍为 null。Linux x86_64 / Python 3.10 目标尚未验证；本机目标检查保留预期拒绝。现场旧失败进程线程配置未保存，本地机制证据不能确认其唯一根因。

### `verification/loopback-capability-receipt-release.json`

SHA-256：`112d2f342b064f612e3216ea9e744f40106e1996d232f156f20308684b015ab6`；字节数：32511。以下为完整原文。

````json
{
  "schema": "TTO-CPU-CAPABILITY-RECEIPT-v2",
  "candidate_version": "0.2.4+cpu.3",
  "config_sha256": "525b3bb83be7199b80fbc234a39e9be08fdd01b16763770c61aa9d25c069e76a",
  "sidecar_config_sha256": "ee9ebe39df978b236077d31f393e94de4bade6019e5608e4e1338ef9e0b0b4e2",
  "qualified": false,
  "checks": {
    "thread_policy": true,
    "baseline_resources": true,
    "native_delay_budget": true,
    "complete_native": true,
    "packets": true,
    "clock_identified": true,
    "cpu_measured": false,
    "read_budget": true,
    "jitter_budget": true,
    "no_sidecar_trip": true,
    "native_fan_gap": true
  },
  "evaluation_scope": "arrival_side",
  "automatic_work_authorization": false,
  "actual_sidecar_interval": {
    "start_mono_s": 30.067727165995166,
    "stop_mono_s": 60.07519012503326
  },
  "baseline_admission": {
    "evaluated_mono_s": 30.063409583061002,
    "resource_sample": {
      "mono_s": 29.652130000060424,
      "interval_start_mono_s": 28.627941166050732,
      "cpu_pct_single_core": 2.6120308200652462,
      "rss_bytes": 72957952,
      "cpu_times": {
        "user": 0.688579904,
        "system": 0.276662112,
        "children_user": 0.0,
        "children_system": 0.0
      },
      "resource_error": null,
      "resource_seq": 29,
      "field_log_bytes": 1403451,
      "native_log_bytes": 179721
    },
    "cpu_limit_single_core_percent": 8.0,
    "rss_limit_bytes": 134217728,
    "allowed": true,
    "reason": "baseline_receiver_resources_qualified",
    "interval_contract": "latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization",
    "sample_age_s": 0.411279583000578
  },
  "resource_check_evidence": {
    "native_callback_lag_p95_s": {
      "before": 0.005161249893717468,
      "during": 0.005638708011247218,
      "after": null
    },
    "read_p95_s": 0.004907874972559512,
    "jitter_p95_s": 0.0051470056641846895,
    "resources_by_actual_phase": {
      "before": [
        {
          "mono_s": 1.0167531250044703,
          "interval_start_mono_s": null,
          "cpu_pct_single_core": null,
          "rss_bytes": 71188480,
          "cpu_times": {
            "user": 0.210024128,
            "system": 0.046072168,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 1,
          "field_log_bytes": 50235,
          "native_log_bytes": 17922
        },
        {
          "mono_s": 2.039850207976997,
          "interval_start_mono_s": 1.0167531250044703,
          "cpu_pct_single_core": 2.2378415871815,
          "rss_bytes": 71876608,
          "cpu_times": {
            "user": 0.226278464,
            "system": 0.052713124,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 2,
          "field_log_bytes": 96521,
          "native_log_bytes": 22515
        },
        {
          "mono_s": 3.061439916025847,
          "interval_start_mono_s": 2.039850207976997,
          "cpu_pct_single_core": 3.0372150145541914,
          "rss_bytes": 72138752,
          "cpu_times": {
            "user": 0.24703088,
            "system": 0.062988584,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 3,
          "field_log_bytes": 142839,
          "native_log_bytes": 27106
        },
        {
          "mono_s": 4.08182816603221,
          "interval_start_mono_s": 3.061439916025847,
          "cpu_pct_single_core": 2.69681584434438,
          "rss_bytes": 72286208,
          "cpu_times": {
            "user": 0.265799584,
            "system": 0.071737872,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 4,
          "field_log_bytes": 210647,
          "native_log_bytes": 33223
        },
        {
          "mono_s": 5.103140749968588,
          "interval_start_mono_s": 4.08182816603221,
          "cpu_pct_single_core": 1.7106324033199611,
          "rss_bytes": 72302592,
          "cpu_times": {
            "user": 0.2783024,
            "system": 0.07670596,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 5,
          "field_log_bytes": 267775,
          "native_log_bytes": 38809
        },
        {
          "mono_s": 6.119965875055641,
          "interval_start_mono_s": 5.103140749968588,
          "cpu_pct_single_core": 1.5378683722691502,
          "rss_bytes": 72384512,
          "cpu_times": {
            "user": 0.289409664,
            "system": 0.081236128,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 6,
          "field_log_bytes": 313920,
          "native_log_bytes": 47341
        },
        {
          "mono_s": 7.149019666016102,
          "interval_start_mono_s": 6.119965875055641,
          "cpu_pct_single_core": 2.136340023535723,
          "rss_bytes": 72384512,
          "cpu_times": {
            "user": 0.304656544,
            "system": 0.087973336,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 7,
          "field_log_bytes": 359919,
          "native_log_bytes": 51936
        },
        {
          "mono_s": 8.172148457961157,
          "interval_start_mono_s": 7.149019666016102,
          "cpu_pct_single_core": 2.1782078830596387,
          "rss_bytes": 72400896,
          "cpu_times": {
            "user": 0.319586336,
            "system": 0.095329416,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 8,
          "field_log_bytes": 405914,
          "native_log_bytes": 56533
        },
        {
          "mono_s": 9.19143983302638,
          "interval_start_mono_s": 8.172148457961157,
          "cpu_pct_single_core": 2.4240134474226243,
          "rss_bytes": 72450048,
          "cpu_times": {
            "user": 0.33646576,
            "system": 0.103157752,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 9,
          "field_log_bytes": 451894,
          "native_log_bytes": 61131
        },
        {
          "mono_s": 10.220700000063516,
          "interval_start_mono_s": 9.19143983302638,
          "cpu_pct_single_core": 2.908213196102437,
          "rss_bytes": 72466432,
          "cpu_times": {
            "user": 0.356245088,
            "system": 0.113311504,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 10,
          "field_log_bytes": 508197,
          "native_log_bytes": 66719
        },
        {
          "mono_s": 11.244993583066389,
          "interval_start_mono_s": 10.220700000063516,
          "cpu_pct_single_core": 2.5139503387797526,
          "rss_bytes": 72466432,
          "cpu_times": {
            "user": 0.373676448,
            "system": 0.121630376,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 11,
          "field_log_bytes": 553645,
          "native_log_bytes": 75859
        },
        {
          "mono_s": 12.261097291018814,
          "interval_start_mono_s": 11.244993583066389,
          "cpu_pct_single_core": 2.2068810323689787,
          "rss_bytes": 72482816,
          "cpu_times": {
            "user": 0.389238528,
            "system": 0.128492496,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 12,
          "field_log_bytes": 599045,
          "native_log_bytes": 80455
        },
        {
          "mono_s": 13.28360020800028,
          "interval_start_mono_s": 12.261097291018814,
          "cpu_pct_single_core": 2.5705299773219648,
          "rss_bytes": 72515584,
          "cpu_times": {
            "user": 0.406111264,
            "system": 0.137903504,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 13,
          "field_log_bytes": 644441,
          "native_log_bytes": 85048
        },
        {
          "mono_s": 14.30608858296182,
          "interval_start_mono_s": 13.28360020800028,
          "cpu_pct_single_core": 2.4357346850947503,
          "rss_bytes": 72630272,
          "cpu_times": {
            "user": 0.423139328,
            "system": 0.145780544,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 14,
          "field_log_bytes": 689854,
          "native_log_bytes": 89646
        },
        {
          "mono_s": 15.328819000045769,
          "interval_start_mono_s": 14.30608858296182,
          "cpu_pct_single_core": 3.299489233557254,
          "rss_bytes": 72695808,
          "cpu_times": {
            "user": 0.445308128,
            "system": 0.157356624,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 15,
          "field_log_bytes": 745946,
          "native_log_bytes": 95233
        },
        {
          "mono_s": 16.350082874996588,
          "interval_start_mono_s": 15.328819000045769,
          "cpu_pct_single_core": 2.2900095238487,
          "rss_bytes": 72695808,
          "cpu_times": {
            "user": 0.460689632,
            "system": 0.16536216,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 16,
          "field_log_bytes": 791378,
          "native_log_bytes": 105264
        },
        {
          "mono_s": 17.3728282910306,
          "interval_start_mono_s": 16.350082874996588,
          "cpu_pct_single_core": 2.4091938828284603,
          "rss_bytes": 72712192,
          "cpu_times": {
            "user": 0.476813088,
            "system": 0.173878624,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 17,
          "field_log_bytes": 836759,
          "native_log_bytes": 109865
        },
        {
          "mono_s": 18.397526666056365,
          "interval_start_mono_s": 17.3728282910306,
          "cpu_pct_single_core": 2.6851530821748693,
          "rss_bytes": 72712192,
          "cpu_times": {
            "user": 0.494503552,
            "system": 0.18370288,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 18,
          "field_log_bytes": 882186,
          "native_log_bytes": 114463
        },
        {
          "mono_s": 19.419018249958754,
          "interval_start_mono_s": 18.397526666056365,
          "cpu_pct_single_core": 2.3264442286653986,
          "rss_bytes": 72744960,
          "cpu_times": {
            "user": 0.509874912,
            "system": 0.192095952,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 19,
          "field_log_bytes": 927633,
          "native_log_bytes": 119065
        },
        {
          "mono_s": 20.44031095795799,
          "interval_start_mono_s": 19.419018249958754,
          "cpu_pct_single_core": 2.6057501235013127,
          "rss_bytes": 72744960,
          "cpu_times": {
            "user": 0.528164576,
            "system": 0.200418624,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 20,
          "field_log_bytes": 983732,
          "native_log_bytes": 124652
        },
        {
          "mono_s": 21.461393082980067,
          "interval_start_mono_s": 20.44031095795799,
          "cpu_pct_single_core": 2.652721395883256,
          "rss_bytes": 72761344,
          "cpu_times": {
            "user": 0.546476672,
            "system": 0.209192992,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 21,
          "field_log_bytes": 1029186,
          "native_log_bytes": 135299
        },
        {
          "mono_s": 22.482755000004545,
          "interval_start_mono_s": 21.461393082980067,
          "cpu_pct_single_core": 2.555776514171159,
          "rss_bytes": 72761344,
          "cpu_times": {
            "user": 0.56447264,
            "system": 0.217300752,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 22,
          "field_log_bytes": 1074627,
          "native_log_bytes": 139900
        },
        {
          "mono_s": 23.504479540977627,
          "interval_start_mono_s": 22.482755000004545,
          "cpu_pct_single_core": 2.6159222890491534,
          "rss_bytes": 72794112,
          "cpu_times": {
            "user": 0.58248928,
            "system": 0.226011632,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 23,
          "field_log_bytes": 1120075,
          "native_log_bytes": 144502
        },
        {
          "mono_s": 24.531443165964447,
          "interval_start_mono_s": 23.504479540977627,
          "cpu_pct_single_core": 2.295799327878107,
          "rss_bytes": 72859648,
          "cpu_times": {
            "user": 0.599162688,
            "system": 0.232915248,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 24,
          "field_log_bytes": 1165531,
          "native_log_bytes": 149100
        },
        {
          "mono_s": 25.556537666008808,
          "interval_start_mono_s": 24.531443165964447,
          "cpu_pct_single_core": 3.079558421065944,
          "rss_bytes": 72876032,
          "cpu_times": {
            "user": 0.620052608,
            "system": 0.243593712,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 25,
          "field_log_bytes": 1221636,
          "native_log_bytes": 154686
        },
        {
          "mono_s": 26.579653957975097,
          "interval_start_mono_s": 25.556537666008808,
          "cpu_pct_single_core": 2.8237071608426554,
          "rss_bytes": 72908800,
          "cpu_times": {
            "user": 0.638942464,
            "system": 0.253593664,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 26,
          "field_log_bytes": 1267106,
          "native_log_bytes": 165920
        },
        {
          "mono_s": 27.60531841602642,
          "interval_start_mono_s": 26.579653957975097,
          "cpu_pct_single_core": 2.4476917185662925,
          "rss_bytes": 72925184,
          "cpu_times": {
            "user": 0.655414144,
            "system": 0.262227088,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 27,
          "field_log_bytes": 1312565,
          "native_log_bytes": 170521
        },
        {
          "mono_s": 28.627941166050732,
          "interval_start_mono_s": 27.60531841602642,
          "cpu_pct_single_core": 2.0387436128821035,
          "rss_bytes": 72957952,
          "cpu_times": {
            "user": 0.670444672,
            "system": 0.268045216,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 28,
          "field_log_bytes": 1358030,
          "native_log_bytes": 175122
        },
        {
          "mono_s": 29.652130000060424,
          "interval_start_mono_s": 28.627941166050732,
          "cpu_pct_single_core": 2.6120308200652462,
          "rss_bytes": 72957952,
          "cpu_times": {
            "user": 0.688579904,
            "system": 0.276662112,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 29,
          "field_log_bytes": 1403451,
          "native_log_bytes": 179721
        }
      ],
      "during": [
        {
          "mono_s": 30.672063625068404,
          "interval_start_mono_s": 29.652130000060424,
          "cpu_pct_single_core": 1.844044704365236,
          "rss_bytes": 73170944,
          "cpu_times": {
            "user": 0.699444928,
            "system": 0.28460512,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 30,
          "field_log_bytes": 1485302,
          "native_log_bytes": 185312
        },
        {
          "mono_s": 31.696750957984477,
          "interval_start_mono_s": 30.672063625068404,
          "cpu_pct_single_core": 2.4965836092847646,
          "rss_bytes": 73187328,
          "cpu_times": {
            "user": 0.71674144,
            "system": 0.292890784,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 31,
          "field_log_bytes": 1575422,
          "native_log_bytes": 197221
        },
        {
          "mono_s": 32.713647832977585,
          "interval_start_mono_s": 31.696750957984477,
          "cpu_pct_single_core": 3.0738818034239674,
          "rss_bytes": 73252864,
          "cpu_times": {
            "user": 0.737769984,
            "system": 0.303120448,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 32,
          "field_log_bytes": 1676122,
          "native_log_bytes": 204908
        },
        {
          "mono_s": 33.73144983302336,
          "interval_start_mono_s": 32.713647832977585,
          "cpu_pct_single_core": 2.4680823970546464,
          "rss_bytes": 73302016,
          "cpu_times": {
            "user": 0.754389504,
            "system": 0.31162112,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 33,
          "field_log_bytes": 1775117,
          "native_log_bytes": 209509
        },
        {
          "mono_s": 34.74998504098039,
          "interval_start_mono_s": 33.73144983302336,
          "cpu_pct_single_core": 2.292167007837472,
          "rss_bytes": 73318400,
          "cpu_times": {
            "user": 0.770411648,
            "system": 0.318945504,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 34,
          "field_log_bytes": 1865182,
          "native_log_bytes": 214115
        },
        {
          "mono_s": 35.76980808295775,
          "interval_start_mono_s": 34.74998504098039,
          "cpu_pct_single_core": 2.574294452996187,
          "rss_bytes": 73318400,
          "cpu_times": {
            "user": 0.789809152,
            "system": 0.325801248,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 35,
          "field_log_bytes": 1965922,
          "native_log_bytes": 227676
        },
        {
          "mono_s": 36.79051145806443,
          "interval_start_mono_s": 35.76980808295775,
          "cpu_pct_single_core": 2.527859966888348,
          "rss_bytes": 73334784,
          "cpu_times": {
            "user": 0.808301568,
            "system": 0.333110784,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 36,
          "field_log_bytes": 2056086,
          "native_log_bytes": 232278
        },
        {
          "mono_s": 37.80962287506554,
          "interval_start_mono_s": 36.79051145806443,
          "cpu_pct_single_core": 2.2299551963487954,
          "rss_bytes": 73351168,
          "cpu_times": {
            "user": 0.82444512,
            "system": 0.33969296,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 37,
          "field_log_bytes": 2146081,
          "native_log_bytes": 236881
        },
        {
          "mono_s": 38.834826249978505,
          "interval_start_mono_s": 37.80962287506554,
          "cpu_pct_single_core": 2.5473314504272944,
          "rss_bytes": 73383936,
          "cpu_times": {
            "user": 0.84125248,
            "system": 0.349000928,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 38,
          "field_log_bytes": 2235782,
          "native_log_bytes": 241483
        },
        {
          "mono_s": 39.85188312502578,
          "interval_start_mono_s": 38.834826249978505,
          "cpu_pct_single_core": 1.474563750360862,
          "rss_bytes": 73383936,
          "cpu_times": {
            "user": 0.851939008,
            "system": 0.353311552,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 39,
          "field_log_bytes": 2325804,
          "native_log_bytes": 246082
        },
        {
          "mono_s": 40.870130333001725,
          "interval_start_mono_s": 39.85188312502578,
          "cpu_pct_single_core": 2.9443977616787276,
          "rss_bytes": 73433088,
          "cpu_times": {
            "user": 0.872889216,
            "system": 0.362342592,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 40,
          "field_log_bytes": 2426618,
          "native_log_bytes": 260226
        },
        {
          "mono_s": 41.89303691603709,
          "interval_start_mono_s": 40.870130333001725,
          "cpu_pct_single_core": 2.852883780785207,
          "rss_bytes": 73482240,
          "cpu_times": {
            "user": 0.89188352,
            "system": 0.372530624,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 41,
          "field_log_bytes": 2516687,
          "native_log_bytes": 264831
        },
        {
          "mono_s": 42.91245104104746,
          "interval_start_mono_s": 41.89303691603709,
          "cpu_pct_single_core": 2.110595828734581,
          "rss_bytes": 73482240,
          "cpu_times": {
            "user": 0.907011648,
            "system": 0.378918208,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 42,
          "field_log_bytes": 2606743,
          "native_log_bytes": 269436
        },
        {
          "mono_s": 43.93670454097446,
          "interval_start_mono_s": 42.91245104104746,
          "cpu_pct_single_core": 2.40237089761018,
          "rss_bytes": 73515008,
          "cpu_times": {
            "user": 0.923839488,
            "system": 0.386696736,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 43,
          "field_log_bytes": 2705570,
          "native_log_bytes": 274035
        },
        {
          "mono_s": 44.95901212503668,
          "interval_start_mono_s": 43.93670454097446,
          "cpu_pct_single_core": 2.5812035840667256,
          "rss_bytes": 73515008,
          "cpu_times": {
            "user": 0.941825408,
            "system": 0.395098656,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 44,
          "field_log_bytes": 2795473,
          "native_log_bytes": 278629
        },
        {
          "mono_s": 45.98150087497197,
          "interval_start_mono_s": 44.95901212503668,
          "cpu_pct_single_core": 2.858556243464758,
          "rss_bytes": 73547776,
          "cpu_times": {
            "user": 0.963662656,
            "system": 0.402489824,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 45,
          "field_log_bytes": 2895994,
          "native_log_bytes": 293688
        },
        {
          "mono_s": 47.00617625005543,
          "interval_start_mono_s": 45.98150087497197,
          "cpu_pct_single_core": 1.597961695787434,
          "rss_bytes": 73547776,
          "cpu_times": {
            "user": 0.975723904,
            "system": 0.406802496,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 46,
          "field_log_bytes": 2986036,
          "native_log_bytes": 298286
        },
        {
          "mono_s": 48.026710291043855,
          "interval_start_mono_s": 47.00617625005543,
          "cpu_pct_single_core": 1.8146890996466243,
          "rss_bytes": 73564160,
          "cpu_times": {
            "user": 0.989056576,
            "system": 0.411989344,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 47,
          "field_log_bytes": 3075962,
          "native_log_bytes": 302888
        },
        {
          "mono_s": 49.049954000045545,
          "interval_start_mono_s": 48.026710291043855,
          "cpu_pct_single_core": 2.248363688690116,
          "rss_bytes": 73646080,
          "cpu_times": {
            "user": 1.004275904,
            "system": 0.419776256,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 48,
          "field_log_bytes": 3165956,
          "native_log_bytes": 307494
        },
        {
          "mono_s": 50.07340650004335,
          "interval_start_mono_s": 49.049954000045545,
          "cpu_pct_single_core": 3.0223190622003844,
          "rss_bytes": 73646080,
          "cpu_times": {
            "user": 1.024909568,
            "system": 0.430074592,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 49,
          "field_log_bytes": 3255985,
          "native_log_bytes": 313086
        },
        {
          "mono_s": 51.096146999974735,
          "interval_start_mono_s": 50.07340650004335,
          "cpu_pct_single_core": 2.7397166731815,
          "rss_bytes": 73678848,
          "cpu_times": {
            "user": 1.044161152,
            "system": 0.4388432,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 50,
          "field_log_bytes": 3356683,
          "native_log_bytes": 327764
        },
        {
          "mono_s": 52.11706758302171,
          "interval_start_mono_s": 51.096146999974735,
          "cpu_pct_single_core": 2.323481022314596,
          "rss_bytes": 73695232,
          "cpu_times": {
            "user": 1.060299776,
            "system": 0.446425472,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 51,
          "field_log_bytes": 3446806,
          "native_log_bytes": 332369
        },
        {
          "mono_s": 53.13988916599192,
          "interval_start_mono_s": 52.11706758302171,
          "cpu_pct_single_core": 3.228790685477946,
          "rss_bytes": 73744384,
          "cpu_times": {
            "user": 1.082873216,
            "system": 0.4568768,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 52,
          "field_log_bytes": 3567113,
          "native_log_bytes": 338491
        },
        {
          "mono_s": 54.159392833011225,
          "interval_start_mono_s": 53.13988916599192,
          "cpu_pct_single_core": 2.758393217183712,
          "rss_bytes": 73777152,
          "cpu_times": {
            "user": 1.102080384,
            "system": 0.465791552,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 53,
          "field_log_bytes": 3657130,
          "native_log_bytes": 343097
        },
        {
          "mono_s": 55.17851125006564,
          "interval_start_mono_s": 54.159392833011225,
          "cpu_pct_single_core": 2.466181709544941,
          "rss_bytes": 73793536,
          "cpu_times": {
            "user": 1.119570816,
            "system": 0.473434432,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 54,
          "field_log_bytes": 3757852,
          "native_log_bytes": 348696
        },
        {
          "mono_s": 56.198343666037545,
          "interval_start_mono_s": 55.17851125006564,
          "cpu_pct_single_core": 2.4143762851992316,
          "rss_bytes": 73809920,
          "cpu_times": {
            "user": 1.137885184,
            "system": 0.479742656,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 55,
          "field_log_bytes": 3847949,
          "native_log_bytes": 363970
        },
        {
          "mono_s": 57.21956333296839,
          "interval_start_mono_s": 56.198343666037545,
          "cpu_pct_single_core": 2.301618031959793,
          "rss_bytes": 73809920,
          "cpu_times": {
            "user": 1.154542848,
            "system": 0.486589568,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 56,
          "field_log_bytes": 3937964,
          "native_log_bytes": 368571
        },
        {
          "mono_s": 58.24071412498597,
          "interval_start_mono_s": 57.21956333296839,
          "cpu_pct_single_core": 2.530315424713008,
          "rss_bytes": 73859072,
          "cpu_times": {
            "user": 1.171530496,
            "system": 0.495440256,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 57,
          "field_log_bytes": 4028024,
          "native_log_bytes": 373176
        },
        {
          "mono_s": 59.26008191599976,
          "interval_start_mono_s": 58.24071412498597,
          "cpu_pct_single_core": 1.811152379225041,
          "rss_bytes": 73859072,
          "cpu_times": {
            "user": 1.184892672,
            "system": 0.500540384,
            "children_user": 0.0,
            "children_system": 0.0
          },
          "resource_error": null,
          "resource_seq": 58,
          "field_log_bytes": 4118141,
          "native_log_bytes": 377775
        }
      ],
      "after": []
    }
  },
  "measured_resolution_evidence": {
    "cpu_median_read_period_s": 0.20000616693869233,
    "GPU_independent_resolution": "unknown unless source window/generation provided",
    "rail_independent_resolution": "unknown; native coarse baseline retained",
    "exact_cross_host_source_lead": "unknown"
  },
  "source_run_id": "7dd5948c-785a-48aa-8a1b-787ac5491488",
  "files": {
    "launch.json": "0dab00d93ca9e2baaaf3608e041074ea7ecdf809481f5a782b33d6f91290bf7a",
    "summary.json": "7b806d998ab3dfc20214ac425a198dbf67f5d8748c98c40c0501f62ff30dc042",
    "thread-policy.json": "c905aafde35a8ad21a4131d0b38b0d89ef13ec9b13ffc009c332f02613b25bdb",
    "resources.jsonl": "66499e7dfe28e693546722efba20e78bfa44af673594a0f376c78e33a22961d2"
  }
}
````

### `verification/target-release-boundary.json`

SHA-256：`23a551e8ab1afecfe8cd5c3f1c2790d9acc553abf5943209e37980765df004ef`；字节数：130。以下为完整原文。

````json
{
  "expected_local_macOS_rejection": true,
  "Linux310_target_verified": false,
  "exit": 1,
  "version_guard_unchanged": true
}
````

### `verification/target-release-boundary.stderr`

SHA-256：`783c4ebdd4722253b8abdda9b08c1b7016c435004e32e5c3c19446afcf47aba3`；字节数：879。以下为完整原文。

````text
Traceback (most recent call last):
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/bin/tto-cpu-pilot", line 8, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/tto_field/cpu_cli.py", line 34, in main
    if a.cmd=='verify-install':print(json.dumps(verify(a.target),indent=2));return 0
                                                ^^^^^^^^^^^^^^^^
  File "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/tto_field/identity.py", line 18, in verify
    raise ValueError('field target is Linux x86_64 CPython3.10; use isolated target environment')
ValueError: field target is Linux x86_64 CPython3.10; use isolated target environment
````

### 4.5 193 条数值等价结果

以下为封存结果：193 条事件、11054 个数值字段，最大绝对差 `3.836930773104541e-13`，全部语义一致。紧循环约 100% CPU 只用于数学等价，不是实时性能指标；没有重新拟合、重新打分或改变旧成绩。独立解包复验的既有回执一并保留，本次没有再运行。

### `verification/replay-full193-release/result.json`

SHA-256：`4695da593e819e70f84d6926d68ccac784a7aa36acf7211acc491358d0c11570`；字节数：1808。以下为完整原文。

````json
{
  "scope": "LOCAL saved events, no network/sidecar/devices; NOT N305",
  "events": 193,
  "numeric_fields_checked": 11054,
  "max_abs_semantic_numeric_difference": 3.836930773104541e-13,
  "all_semantic_fields_equal": true,
  "phase_validity_revocation_cold_start_included": true,
  "process_cpu_s": 0.06242603999999998,
  "wall_s": 0.06242225004825741,
  "cpu_single_core_percent": 100.0060714756992,
  "threads": [
    {
      "tid": 1,
      "cpu_s": 0.062471000000000027
    }
  ],
  "rss_bytes": 78774272,
  "callback_p95_s": 0.00041204190347343683,
  "callback_max_s": 0.0016581249656155705,
  "thread_pools": [
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib",
      "version": "0.3.29",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    },
    {
      "user_api": "blas",
      "internal_api": "openblas",
      "num_threads": 1,
      "prefix": "libscipy_openblas",
      "filepath": "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib",
      "version": "0.3.28",
      "threading_layer": "pthreads",
      "architecture": "neoversen1"
    }
  ],
  "python": "3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]",
  "platform": "macOS-27.0.1-arm64-arm-64bit",
  "numpy": "2.2.6",
  "scipy": "1.15.3",
  "candidate_policy": true,
  "candidate_version": "0.2.4+cpu.3",
  "observer_sha256": "599e292a0000697615e76a97596f2f48c7527bc82027bacca5aea0c0fe5d4a47",
  "paced": false
}
````

### `verification/independent-release-package-replay.json`

SHA-256：`b504392a31a473660422fb7f99801ca0443686713b0c23bdcee50a4325fc9b71`；字节数：970。以下为完整原文。

````json
{
  "scope": "independently extracted final release payload, installed same exact wheel, existing pinned local dependencies",
  "wheel_sha256": "a9f0394097180c952d8b7f4e1cebac65fe7f2cc612c7f7189dfac6566502c9be",
  "replay_script_sha256": "b393d9c217ef61ee2359364073e1dd6288cb23453b20e201a6c54cc0f442b5f5",
  "result_sha256": "8d08cda593760fb1e98d64d880840cf5402ed5829ae70dbc575f47c92fb1cf64",
  "events": 193,
  "numeric_fields_checked": 11054,
  "max_abs_difference": 3.836930773104541e-13,
  "all_semantics_equal": true,
  "numeric_policy_pool_coverage": {
    "numpy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/numpy/.dylibs/libscipy_openblas64_.dylib"
    ],
    "scipy": [
      "/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/local-env/lib/python3.12/site-packages/scipy/.dylibs/libscipy_openblas.dylib"
    ]
  },
  "devices": 0,
  "requests": 0
}
````

### 4.6 原报告对早期失败的说明（原文）

来源：`TTO-数值线程策略与旁录前资源检查-收尾报告.md`，SHA-256：`15da19af63d3a9b44899d17ec0854033b52b4a3627208039a5e2dd019ba56054`。只保留该说明，不混入开发副本源码或成绩。

早期失败日志保留：隔离测试环境缺依赖、通用锁冲突、沙箱拒绝自身逐线程取证、测试中读到旧安装副本和缩放假流不匹配；最终对固定wheel安装副本重新验证。没有把这些失败藏成现场结果或通过放宽预算解决。首轮本地CLI与最终CLI验证分别存放，交付结论只引用最终identity/SHA和installed release suite。

