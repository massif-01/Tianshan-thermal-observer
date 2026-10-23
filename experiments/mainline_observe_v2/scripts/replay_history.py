"""Causal replay of one previously recorded native stream; never creates network clients."""
import argparse,copy,json,time,hashlib
from pathlib import Path
from collections import deque
from tto.config import load_config,merge,validate
from tto.engine import engine_for
from tto_field.projection import SavedStream
from tto_field.comm_bridge import CommunicationBridge
from tto_field.g2_model.g2_runtime import Predictor,ThermalObserver
from tto_field.observe_predictions import Ledger
from tto_field.support import utc

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--boot-id',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir()
    mpath=next(a.run.glob('native/*/manifest.json'));m=json.loads(mpath.read_text());cfg=load_config(environ={});saved=copy.deepcopy(m['config'])
    for section in ('orin','tianshan'):saved[section]['headers_file']=saved[section]['ca_file']=None
    merge(cfg,saved);validate(cfg);engine=engine_for(cfg,record_schema=2);api=Predictor();observer=ThermalObserver(api.spec)
    projection=SavedStream(m,api.spec,engine,retain_quality_history=False);comm=CommunicationBridge(m,engine);history=deque(maxlen=181)
    old={x['generation_evidence']['native_ref']:x['state'] for x in map(json.loads,(a.run/'states.jsonl').read_text().splitlines())}
    identity=dict(device_id='historical-declared-RM01',thermal_config_id='historical-frozen-input-domain',observer_host_id='saved-N305',
        session_id=m['observer_run_id'],run_id=m['observer_run_id'],boot_id=a.boot_id,clock_domain='explicit-replay:'+m['observer_run_id'],
        model_sha256=api.manifest['model_sha256'],spec_sha256=api.manifest['observer_spec_sha256'])
    handles={};counts=0;maxdiff=0.;pairs=0
    def emit(k,x):
        if k not in handles:handles[k]=(a.output/(k+'.jsonl')).open('w')
        handles[k].write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n')
    ledger=Ledger(emit,identity,publication_mode='replay')
    def compare(x,y):
        nonlocal maxdiff,pairs
        if isinstance(x,dict):
            for k in x:compare(x[k],y[k])
        elif isinstance(x,list):
            assert len(x)==len(y)
            for v,w in zip(x,y):compare(v,w)
        elif isinstance(x,(float,int)) and not isinstance(x,bool):
            d=abs(x-y);maxdiff=max(maxdiff,d);pairs+=1;assert d<=1e-8,(x,y)
        else:assert x==y,(x,y)
    for file in sorted(mpath.parent.glob('observations-*.jsonl')):
        with file.open() as f:
            for line in f:
                raw=json.loads(line);processed=engine.process(raw);health=comm.feed(raw,processed);frame=projection.feed(raw,processed)
                if not health['measurement']['TJ_and_rails']['raw_valid']:
                    for name in ('tj','power'):
                        if frame['measurement'][name]:frame['measurement'][name]['raw_valid']=False
                    frame['new_TJ']=False
                state=observer.step(frame);counts+=1
                if raw['ref'] in old:compare(state,old[raw['ref']])
                tj=frame['measurement']['tj'];outputs=[];before=time.monotonic()
                if frame['new_TJ'] and tj and tj['raw_valid']:
                    origin=dict(ref=tj['source_ref'],value_C=tj['value_C'],received_at_mono_s=tj['observed_mono_s'],raw_valid=True,source_epoch=frame['identity']['source_epoch'],clock_domain=identity['clock_domain']);history.append(origin)
                    if ledger.last_anchor is None or frame['t']-ledger.last_anchor>=5:
                        rows=api.predict(state,origin=origin,observed_through=dict(ref=frame['ref'],mono_s=frame['t'],clock_domain=identity['clock_domain']),issued_at=dict(mono_s=frame['t'],utc=raw['received_at_utc'],clock_domain=identity['clock_domain']),identity=identity,publication_mode='replay',history=list(history))
                        outputs=[dict(method=x['method'],horizon_s=x['horizon_s'],value_C=x['value_C'],reason=x['unavailable_reasons'],assumptions=x.get('condition'),computation_id=x['prediction_id']) for x in rows]
                wall=time.monotonic();ledger.consume(frame,frame['t']+wall-before,outputs,state_status=state['observer']['phase'],wall_clock=dict(utc=utc(),mono_s=wall))
    ledger.finish(frame['t']);summary=ledger.summary()
    for h in handles.values():h.close()
    result=dict(scope='recorded causal replay, not live; no fitting/new field scores',native_run_id=m['observer_run_id'],records=counts,semantic_numeric_fields=pairs,max_abs_frozen_state_difference=maxdiff,
        publication_mode='replay',replay_issued_analysis_clock='original receive clock plus measured local computation cost; actual wall issue recorded separately',scoring=summary,
        source_manifest=str(mpath.resolve()),source_manifest_sha256=hashlib.sha256(mpath.read_bytes()).hexdigest())
    (a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(records=counts,fields=pairs,maxdiff=maxdiff,scored=summary['counts'].get('scored',0)),indent=2))
if __name__=='__main__':main()
