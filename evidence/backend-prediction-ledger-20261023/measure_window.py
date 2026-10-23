"""Pure-component 60-minute ledger/cache allocation and JSON backfill cost.
No collector, model solver, Web service or device. Run with repo source paths.
"""
import argparse,json,sys,time,tracemalloc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'experiments/mainline_observe_v2/src'),str(ROOT/'work/webui-v1/src')]
from tto_field.prediction_view import PredictionView
from tto_field.observe_predictions import Ledger
from tto_field.web_encoding import SPEC,SPEC_ID
from tto_web.state import State
import tto_web.state as web_state

parser=argparse.ArgumentParser();parser.add_argument('--replay-session',type=Path,required=True);args=parser.parse_args()
with (args.replay_session/'predictions.jsonl').open() as stream:
    reference=max((r for r in map(json.loads,stream) if r['method']=='G2-HOLD' and r['conditional_assumptions']),key=lambda r:len(json.dumps(r['conditional_assumptions'])))
origin=time.monotonic()-3600
view=PredictionView(origin)
identity=dict(run_id=reference['run_id'],model_id=reference['model_id'],model_sha256=SPEC['model_sha256'],spec_sha256=SPEC_ID,clock_domain='fixture')
ledger=Ledger(view.committed,identity)
outputs=[dict(method=m,horizon_s=h,value_C=40.,assumptions=reference['conditional_assumptions']) for h in (15,45,90) for m in ('G2-HOLD','B0','B1')]
for n in range(721):
    t=origin+n*5
    frame=dict(t=t,ref=f"{reference['run_id']}/observation:{n}",new_TJ=True,source_reset=False,identity=dict(identity,source_epoch=0),
        measurement=dict(tj=dict(raw_valid=True,value_C=40.,valid_until_mono_s=t+5,source_ref=f"{reference['run_id']}/observation:{n}",observed_mono_s=t,observed_utc='2026-10-23T00:00:00.000000+00:00')),
        _communication=dict(measurement=dict(TJ_and_rails=dict(raw_valid=True))))
    ledger.consume(frame,t+.001,outputs,state_status='tracking',wall_clock=dict(utc='2026-10-23T00:00:00.000000+00:00',mono_s=t+.001))
    view.committed('context',(frame,dict(observer=dict(phase='tracking')),t+2.5))

web_state.boot_id=lambda:'test:window-cost'
state=State({'source':{'mode':'follow'},'advisory':{}});state.begin_publication('window-cost')
tracemalloc.start();begin=time.perf_counter();pages=0;max_bytes=0
while True:
    page=view.page(state.prediction_cursor)
    wire=json.dumps(dict(page,boot_id='test:window-cost',publisher_id='window-cost'),allow_nan=False).encode()
    max_bytes=max(max_bytes,len(wire));pages+=1
    state.accept_predictions(json.loads(wire))
    if not page['has_more']:break
elapsed=(time.perf_counter()-begin)*1000
_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()

def retained_size(value,seen=None):
    seen=set() if seen is None else seen
    if id(value) in seen:return 0
    seen.add(id(value));size=sys.getsizeof(value)
    if isinstance(value,dict):size+=sum(retained_size(k,seen)+retained_size(v,seen) for k,v in value.items())
    elif isinstance(value,(list,tuple)):size+=sum(retained_size(v,seen) for v in value)
    return size

terminal=dict(view.final(time.monotonic()),boot_id='test:window-cost',publisher_id='window-cost')
terminal_bytes=len(json.dumps(terminal,allow_nan=False).encode())
print(json.dumps(dict(terminal_json_bytes=terminal_bytes,source_condition='largest condition metadata in supplied real replay ledger',scope='local Python components only; no numeric observer/collector/Web HTTP; excludes pre-existing histories and process RSS',
    retained_predictions=len(state.predictions),pages=pages,max_page_bytes=max_bytes,
    view_and_web_prediction_heap_bytes=retained_size((view.rows,state.predictions,state.prediction_received_ms)),
    backfill_peak_traced_bytes=peak,backfill_json_and_cache_ms=elapsed),indent=2))
