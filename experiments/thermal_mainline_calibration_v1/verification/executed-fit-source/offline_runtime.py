"""Research-process policy, distinct from the unchanged field OpenBLAS attestation."""
import os
import platform
import resource
import threading
import time
from .util import write


def initialize(out, profile):
    for key in ['OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS',
                'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:
        os.environ[key] = '1'
    import numpy as np
    import scipy
    import scipy.linalg
    from threadpoolctl import threadpool_info
    np.dot(np.eye(2), np.eye(2));scipy.linalg.expm(np.zeros((2,2)))
    names = [np.__config__.CONFIG['Build Dependencies']['blas']['name'],
             scipy.__config__.CONFIG['Build Dependencies']['blas']['name']]
    pools = threadpool_info()
    if profile == 'offline_macos_accelerate_v1':
        if platform.system() != 'Darwin' or not all('accelerate' in n.lower() for n in names):
            raise ValueError('registered offline Accelerate runtime does not match actual libraries')
        verified = False  # Never relabel this as field OpenBLAS pool attestation.
    elif profile == 'offline_openblas_v1':
        if not pools or not all('openblas' in n.lower() for n in names) or any(p['num_threads'] != 1 for p in pools):
            raise ValueError('registered OpenBLAS single-thread runtime not verified')
        verified = True
    else:
        raise ValueError('unknown registered research runtime')
    write(out/'numeric-policy.json', dict(profile=profile, numpy=np.__version__, scipy=scipy.__version__,
           pid=os.getpid(), backend_names=names, environment={k:os.environ[k] for k in os.environ if k.endswith('NUM_THREADS') or k=='VECLIB_MAXIMUM_THREADS'},
           pool_introspection=pools, numerical_pool_threads_verified=verified,
           Accelerate_thread_request=1 if profile=='offline_macos_accelerate_v1' else None,
           limitation='Accelerate worker count not introspectable; requested single-thread, serial C trajectory, CPU/RSS recorded' if not verified else None,
           field_runtime_attestation=False, scope='isolated offline training only; original cpu.3/observe policy unchanged'))
    stop = threading.Event()
    def sample():
        while True:
            use = resource.getrusage(resource.RUSAGE_SELF)
            write(out/'resource-heartbeat.tmp', dict(pid=os.getpid(), monotonic_s=time.monotonic(),
                  peak_RSS_MiB=use.ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024),
                  user_cpu_s=use.ru_utime, system_cpu_s=use.ru_stime))
            os.replace(out/'resource-heartbeat.tmp', out/'resource-heartbeat.json')
            if stop.wait(.1): break
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    return stop, thread
