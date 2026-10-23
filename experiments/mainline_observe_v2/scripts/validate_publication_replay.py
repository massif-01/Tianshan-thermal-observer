"""Replay actual Consumer outputs against Web's encoder/State without serving Web.

Virtual receive time is explicit, used only in this local validation process.
Raw recorded times are retained. No network clients are created.
"""
import argparse
import copy
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'experiments/mainline_observe_v2/src'),str(ROOT/'work/webui-v1/src')]
from tto_field.numeric_policy import initialize
initialize()
from tto.engine import engine_for
from tto_field.observe_runtime import Consumer
import tto_field.observe_runtime as runtime
from tto_field.observe_storage import SessionStore
from tto_field.web_encoding import WebEncoder,short
from tto_web.adapter import Adapter
from tto_web.state import State
import tto_web.adapter as web_adapter
import tto_web.state as web_state

BOOT='test:observe-publication-replay'
web_adapter.boot_id=web_state.boot_id=lambda:BOOT

class Capture:
    def __init__(self,manifest):
        self.encoder=WebEncoder(manifest['observer_run_id'],manifest['config_sha256'],BOOT,test_replay=True)
        # Dummy owners prevent Adapter's legacy constructor from creating any processor.
        self.reference=Adapter(manifest,None,test_replay=True,owner=SimpleNamespace(projection=SimpleNamespace(),communication=None,observer=None))
        self.web=State({'source':{'mode':'follow'},'advisory':{}})
        self.rows=[];self.packet_count=0;self.native_models={}
    def invalidate(self):raise AssertionError('unexpected replay model/publication gap')
    def submit(self,raw,processed,frame,state,deadline):
        p=self.encoder.encode(raw,processed,frame,frame['_communication'],state,deadline)
        reference=self.reference.encode(raw,processed,frame,frame['_communication'],state)
        for key in ('generated_mono_s','consumable_until_mono_s','software_version'):
            reference.pop(key,None)
        candidate=copy.deepcopy(p)
        for key in ('generated_mono_s','consumable_until_mono_s','software_version'):candidate.pop(key,None)
        assert candidate==reference,'public allowlist/values differ from established Web encoder'
        self.packet_count+=1
        # JSON round-trip is the public receiver boundary.
        p=json.loads(json.dumps(p,allow_nan=False))
        assert p['model']==state['observer']
        assert p['model_id']==frame['identity']['model_sha256'] and p['spec_id']==frame['identity']['spec_sha256']
        assert p['input_mono_s']==frame['t'] and p['source_epoch']==frame['identity']['source_epoch']
        self.native_models[raw['ref']]=p['model']
        old=len(self.web.predictions)
        self.web.accept(p,now=frame['t']+.002)
        self.rows.extend(copy.deepcopy(list(self.web.predictions)[old:]))


def read_stream(root,name):
    index=json.loads((root/'stream-index.json').read_text())
    return [json.loads(line) for filename in index['streams'].get('./'+name,[]) for line in (root/filename).read_text().splitlines()]


def validate(run,output):
    manifest=json.loads((run/'manifest.json').read_text())
    rows=[json.loads(line) for file in sorted(run.glob('observations-*.jsonl')) for line in file.read_text().splitlines()]
    store=SessionStore(output/'session',budget=256*1024**2,min_free=0)
    native=store.root/'native'/'run-replay';native.mkdir(parents=True)
    (native/'manifest.json').write_text(json.dumps(manifest))
    capture=Capture(manifest)
    now=[rows[0]['mono_s']]
    real_time=runtime.time
    runtime.time=SimpleNamespace(monotonic=lambda:now[0]+.001)
    loop=SimpleNamespace(call_soon_threadsafe=lambda fn:fn())
    stop=threading.Event()
    reg=dict(device_id='recorded-local-replay',thermal_config_id='recorded-config',observer_host_id='offline',session_id='replay')
    consumer=Consumer(store,reg,SimpleNamespace(domain='explicit-recorded-replay',origin=now[0]),stop,loop,publication=capture)
    engine=engine_for(manifest['config'],record_schema=2)
    try:
        for raw in rows:
            now[0]=raw['mono_s']
            consumer.on_record(raw,engine.process(raw),engine)
            consumer.queue.join()
        assert consumer.close() and consumer.fatal is None
        assert consumer.model_errors==consumer.publication_errors==consumer.dropped==0
        assert consumer.stateful_observers==1
        consumer.ledger.finish(now[0]);store.close()
    finally:runtime.time=real_time
    states=read_stream(store.root,'states')
    assert len(states)==capture.packet_count==len(rows)
    for row in states:assert capture.native_models[row['native_ref']]==row['model']
    predictions=read_stream(store.root,'predictions')
    first=rows[0]['mono_s']
    def key(p):return (round(p['origin_elapsed_ms']/1000+first,6),p['horizon_s'])
    web_by={key(p):p for p in capture.rows}
    differences=[];shared=0
    for p in predictions:
        if p['method']!='G2-HOLD' or p['value_C'] is None:continue
        w=web_by.get((round(p['measurement_received_mono_s'],6),p['horizon_s']))
        if w:
            shared+=1;differences.append(abs(p['value_C']-w['value_C']))
    assert shared>0 and max(differences)==0
    report=dict(scope='offline recorded replay; virtual receive clock; no Web service/device',
        source_run=str(run),records=len(rows),recorded_states=len(states),encoded_packets=capture.packet_count,
        stateful_observers=consumer.stateful_observers,publication_callback_errors=consumer.publication_errors,
        established_encoder_packets_equal=capture.packet_count,public_model_equal_to_recorded_state=len(states),
        shared_G2_HOLD_predictions=shared,shared_max_absolute_difference_C=max(differences),
        backend_G2_origins=len([p for p in predictions if p['method']=='G2-HOLD' and p['horizon_s']==15]),
        web_G2_origins=len([p for p in capture.rows if p['horizon_s']==15]),
        backend_scoring=consumer.ledger.summary(),
        web_scores={str(h):dict(n=len(xs),MAE_C=sum(abs(x['error_C']) for x in xs)/len(xs) if xs else None)
            for h in (15,45,90) for xs in [[p for p in capture.web.predictions if p['horizon_s']==h and p['status']=='matched']]},
        differences=['backend stride 5s; Web minimum 1s','backend accepts provisional; Web tracking/degraded only',
                     'issue times and interruption matching belong to each receiver; whole ledgers/MAE are not equal'])
    (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('backend_scoring',)},indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False);validate(args.run,args.output)
