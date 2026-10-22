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
