"""Target dependency compatibility on saved projections; no native raw replay, fitting or new data."""
import json,sys,collections
from pathlib import Path
import numpy as np
from tto_field.research.observer import ThermalObserver
from tto_field.runtime import ROOT
rows=[json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines()]
spec=json.loads((ROOT/'research/observer-spec.json').read_text());observer=ThermalObserver(spec);epoch=None;first=rows[0]['generated_at_mono_s'];maxstate=maxcov=0.;errors=[]
for i,s in enumerate(rows):
 tj=s['measurement']['tj'];current=s['identity']['source_epoch']
 f=dict(t=s['generated_at_mono_s'],utc=s['observed_through_utc'],ref=s['observed_through_ref'],identity=s['identity'],measurement=s['measurement'],safety=s['safety'],stream_started_mono_s=first,
        source_reset=epoch is None or current!=epoch,reset_reason='reconstructed_saved_epoch',new_TJ=bool(tj and tj['source_ref']==s['observed_through_ref'] and tj.get('native_source_valid',True)))
 r=observer.step(f)['observer'];target=s['observer'];epoch=current
 if r['phase']!=target['phase'] or r['available']!=target['available']:errors.append(i)
 if target['available']:
  maxstate=max(maxstate,max(abs(r[k]-target[k]) for k in ['Tf_C','Ts_C','E_C']))
  maxcov=max(maxcov,float(np.abs(np.array(r['uncertainty']['covariance_C2'])-target['uncertainty']['covariance_C2']).max()))
assert not errors and maxstate<1e-8 and maxcov<1e-8
out=dict(rows=len(rows),phase_discrepancies=errors,max_state_difference_C=maxstate,max_covariance_difference_C2=maxcov,theta_fits=0,
         interpretation='installed target candidate numerical compatibility only; not physical Ts accuracy or new forecast scoring')
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print(out)
