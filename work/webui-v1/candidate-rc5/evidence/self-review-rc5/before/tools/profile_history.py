"""Local allocation diagnosis using synthetic records; no network, fitting or device."""
import os,sys,time,tracemalloc,json,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['TTO_WEB_TEST_BOOT_ID']='history-allocation-test'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor'),str(ROOT/'tests')]
import psutil
from producer import Producer,web_config
from tto_web.state import State
tracemalloc.start(10)
p=Producer(time.monotonic()-1800);s=State(web_config());results=[]
for t in range(601):
    packet=p.step(t);s.accept(packet,now=p.start+t+.01)
    for j in range(10):s.refresh(p.start+t+.01+j*.09)
    if t in (0,120,300,600):
        gc.collect();sample=tracemalloc.take_snapshot()
        result=dict(t=t,rss_MiB=psutil.Process().memory_info().rss/1024**2,traced_MiB=tracemalloc.get_traced_memory()[0]/1024**2,predictions=len(s.predictions),history=sum(map(len,s.history.values())),largest=[str(v) for v in sample.statistics('lineno')[:12]])
        results.append(result);print(json.dumps(result),flush=True)
(ROOT/'evidence/history-allocation.json').write_text(json.dumps(results,indent=2))
