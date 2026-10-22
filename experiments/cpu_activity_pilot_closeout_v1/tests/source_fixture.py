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
