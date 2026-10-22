"""Read saved states only. No observer execution, source replay, fitting or device."""
import hashlib,json,math
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
model='dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0'
spec='2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b'
results=[]
for name in ('experiments/thermal_fixed_anchors_frozen_v1/inputs/field/states.jsonl','evidence/cpu-runtime-threads-20261020/inputs/recorded-run/states.jsonl'):
    p=ROOT.parents[1]/name;seen=set();excluded=Counter();count=ordered=0;negative=[]
    with p.open() as f:
        for line in f:
            row=json.loads(line);s=row.get('state',row);identity=s.get('identity',{});o=s.get('observer',{});tj=(s.get('measurement') or {}).get('tj') or {}
            if identity.get('model_sha256')!=model or identity.get('spec_sha256')!=spec:excluded['other_identity']+=1;continue
            if o.get('phase') not in ('tracking','degraded'):excluded['phase']+=1;continue
            if not tj.get('raw_valid') or s.get('observed_through_ref')!=tj.get('source_ref'):excluded['not_new_valid_tj']+=1;continue
            values=[o.get(k) for k in ('Tf_C','Ts_C','E_C')]
            if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in values):excluded['nonfinite']+=1;continue
            key=(identity.get('run_id'),identity.get('source_epoch'),tj['source_ref'])
            if key in seen:excluded['duplicate']+=1;continue
            seen.add(key);count+=1
            if values[0]>=values[1]>=values[2]:ordered+=1
            elif len(negative)<5:negative.append(dict(source_ref=tj['source_ref'],values=values))
    results.append(dict(input=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),eligible_unique_new_tj=count,ordered=ordered,ordered_fraction=ordered/count if count else None,excluded=dict(excluded),reversal_examples=negative))
value=dict(scope='existing saved states only, not a fresh replay or field validation; finite sample ordering is not a guarantee',model=model,spec=spec,criterion='same frozen identity; tracking/degraded; raw_valid TJ and observed_through_ref == TJ.source_ref; dedup run/epoch/TJ ref; finite states',results=results)
(ROOT/'evidence/history-rc4/ordering.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
