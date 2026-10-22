"""Read-only refeed of published Issue8 numerical estimator using saved upstream frames.
This checks reproducibility of estimator states, not hidden-state physical accuracy.
"""
from pathlib import Path
import sys,json,collections,numpy as np
ROOT=Path(__file__).resolve().parents[1]/'original'
sys.path.insert(0,str(ROOT/'issue8'))
from observer import ThermalObserver
spec=json.loads((ROOT/'issue8/observer-spec.json').read_text())
rows=[json.loads(x) for x in (ROOT/'streams/issue8-Y.jsonl').read_text().splitlines()]
o=ThermalObserver(spec); first=rows[0]['generated_at_mono_s']; prev_epoch=None
errors=[]; maxstate=0.; maxcov=0.; min_eig=float('inf'); accepted=collections.Counter()
for i,s in enumerate(rows):
 tj=s['measurement']['tj']; epoch=s['identity']['source_epoch']
 frame=dict(t=s['generated_at_mono_s'],utc=s['observed_through_utc'],ref=s['observed_through_ref'],
            identity=s['identity'],measurement=s['measurement'],safety=s['safety'],
            stream_started_mono_s=first,source_reset=(prev_epoch is None or epoch!=prev_epoch),
            reset_reason='reconstructed_epoch_boundary',
            new_TJ=bool(tj and tj['source_ref']==s['observed_through_ref'] and tj.get('native_source_valid',True)))
 result=o.step(frame)['observer']; target=s['observer'];prev_epoch=epoch
 if result['phase']!=target['phase'] or result['available']!=target['available']: errors.append([i,'phase'])
 if target['available']:
  maxstate=max(maxstate,max(abs(result[k]-target[k]) for k in ('Tf_C','Ts_C','E_C')))
  p=np.array(target['uncertainty']['covariance_C2']); min_eig=min(min_eig,float(np.linalg.eigvalsh(p).min()))
  maxcov=max(maxcov,float(np.abs(np.array(result['uncertainty']['covariance_C2'])-p).max()))
 if frame['new_TJ']:accepted[target['phase']]+=1
out=dict(saved_rows=len(rows),accepted_TJ=sum(accepted.values()),accepted_phase_counts=dict(accepted),
         phase_discrepancies=errors,max_state_difference_C=maxstate,max_covariance_difference_C2=maxcov,
         saved_min_covariance_eigenvalue_C2=min_eig,
         limit='Only saved upstream projections and numerical state reproduction; not native raw source replay, new fits, physical Ts or target N305 verification')
assert not errors and maxstate<1e-8 and maxcov<1e-8
Path(__file__).with_name('numeric-replay.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
