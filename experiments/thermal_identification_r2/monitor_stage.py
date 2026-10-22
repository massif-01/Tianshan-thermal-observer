"""CPU-only subprocess resource receipt; does not alter the research computation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import resource

root=Path(__file__).resolve().parent; stage=sys.argv[1]; out=root/'runs/main'
start=time.perf_counter()
with (out/f'{stage}.log').open('x') as log:
    p=subprocess.Popen([sys.executable,str(root/'research.py'),stage],stdout=log,stderr=subprocess.STDOUT)
    p.wait()
r=resource.getrusage(resource.RUSAGE_CHILDREN)
receipt=dict(stage=stage,exit_code=p.returncode,elapsed_s=time.perf_counter()-start,child_peak_RSS_MiB=r.ru_maxrss/(2**20 if sys.platform=='darwin' else 1024),
             CPU_seconds=r.ru_utime+r.ru_stime,resource_method='getrusage_children_no_system_process_enumeration',CUDA_used=False,device_access=False,BLAS_threads=1)
(out/f'{stage}-resources.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt));sys.exit(p.returncode)
