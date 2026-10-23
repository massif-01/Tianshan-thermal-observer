"""Independent checks of saved actual sender/receiver artifacts; no model fit or device I/O."""
from pathlib import Path
import json,base64,hashlib,statistics,collections,sys
R=Path('/mnt/data/tto_cpu2_independent_review_20261020')
RUN=R/'original/field/field-evidence/joint-sample-complete/run'
A=R/'work/model-replay-2/adapted';O=R/'work/model-replay-2/joint'
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x]
ar=rows(RUN/'cpu-sidecar-arrivals.jsonl');wire={x['wire_seq']:x for x in rows(RUN/'cpu-sidecar-wire.jsonl')}
bad=[];valid=0;partial=0;equal=0;first8diff=0
for i,x in enumerate(ar):
 w=wire[x['wire_seq']]
 assert json.loads(base64.b64decode(w['raw_base64']))==x['source']
 assert w['received_at_mono_s']==x['received_at_mono_s']<=x['decision_generated_mono_s']
 s=x['source'];a=s.get('previous_raw_cpu');b=s['raw_cpu']
 if not a:partial+=1;continue
 on={k for k,v in b['per_core_online'].items() if v};prev={k for k,v in a['per_core_online'].items() if v}
 if on!=prev:partial+=1;continue
 values=[]
 for k in sorted(on):
  d=[b['counters'][k][j]-a['counters'][k][j] for j in range(8)]
  if min(d)<0 or sum(d)<=0:break
  values.append(100*(1-(d[3]+d[4])/sum(d)))
 else:
  if not s['cpu']['complete_online_set']:partial+=1;continue
  mean=sum(values)/len(values);mx=max(values)
  assert abs(mean-s['cpu']['mean_percent'])<1e-10
  assert abs(mx-s['cpu']['max_percent'])<1e-10
  valid+=1
  continue
 partial+=1
frames=rows(A/'frames.jsonl');ori=rows(A/'thermal-origins.jsonl');rev=rows(A/'revocations.jsonl')
assert len({x['ref'] for x in ori})==len(ori)
assert all(x['measurement_received_mono_s']<=x['t'] for x in ori)
coarse_count=0;support_count=0
for i,f in enumerate(frames):
 if f['adapter_event']=='cpu':
  if i and f['epoch']==frames[i-1]['epoch']:
   for k in ('gpu_pct','gpu_W','cpu_soc_mss_W'):assert f['features'].get(k)==frames[i-1]['features'].get(k)
   coarse_count+=1
  for k in ('cpu_mean_pct','cpu_max_pct'):
   v=f['features'].get(k,{})
   if v.get('valid'):
    assert v['valid_until_mono_s']==v['receiver_received_at_mono_s']+1
    assert v['available_at_mono_s']>=v['receiver_decision_generated_mono_s']
    support_count+=1
out=rows(O/'processor.jsonl');counts={k:dict(collections.Counter(x['variants'][k]['activity']['state'] for x in out)) for k in out[0]['variants']}
coverage=rows(O/'evaluate-stream/actual-arrived-coverage.jsonl')
result={'wire_rows_independent_checked':len(ar),'valid_complete_stable_cpu_windows':valid,'nonusable_or_transition_windows':partial,'frames':len(frames),'original_TJ_decision_origins':len(ori),'coarse_preservation_CPU_events_checked':coarse_count,'CPU_support_endpoints_checked':support_count,'counts':counts,'revocation_reasons':dict(collections.Counter(x['reason'] for x in rev if x.get('event')=='CPU_qualification_revoked')),'coverage':coverage,'limits':'same synthetic artifact; complete-window percentage is not recognition precision; no physics/lead/control validation'}
(R/'results/independent-semantics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='coverage'},ensure_ascii=False,indent=2))
