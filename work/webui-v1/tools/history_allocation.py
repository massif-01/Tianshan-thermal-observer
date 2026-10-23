"""Allocation evidence in a supplied installed interpreter, no source imports."""
import gc,hashlib,json,os,tracemalloc
from pathlib import Path
import tto_web
from tto_web.state import State
tracemalloc.start(1)
s=State({'advisory':{}});gc.collect();before=tracemalloc.get_traced_memory()[0]
if hasattr(s,'model_history'):
    from tto_web.state import ModelRow
    for i in range(18002):
        s.model_history.append(ModelRow(i*199.9,(float(i%90),float(i%80),float(i%70),float(i%60)),str(i)+'/'+'a'*32,'2026-10-21T00:00:00Z','synthetic/'+str(i)+'/'+'b'*32,'tracking',None))
gc.collect();after=tracemalloc.get_traced_memory()[0];snap=tracemalloc.take_snapshot()
result=dict(module=tto_web.__file__,version=tto_web.__version__,rows=len(s.model_history) if hasattr(s,'model_history') else 0,baseline_bytes=before,retained_bytes=after,increment_MiB=(after-before)/1024**2,largest=[str(s) for s in snap.statistics('lineno')[:8]])
if hasattr(s,'model_history'):
    for _ in range(5):s.model_series(['temperature.tj','model.Tf_C','model.Ts_C','model.E_C'],0,3600000,2000)
    gc.collect();result['after_queries_bytes']=tracemalloc.get_traced_memory()[0]
    s.model_history.clear();gc.collect();result['after_clear_bytes']=tracemalloc.get_traced_memory()[0]
result['pass']=result['increment_MiB']<=16
Path(os.environ['TTO_ALLOCATION_OUT']).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
