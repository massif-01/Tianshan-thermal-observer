"""Verify wire->arrival equality and actual source counter window provenance; no activity algorithm."""
import argparse,base64,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sample',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
r=a.sample/'run';receipt=json.loads((a.sample/'sample-receipt.json').read_text());arrivals=rows(r/'cpu-sidecar-arrivals.jsonl');wire={x['wire_seq']:x for x in rows(r/'cpu-sidecar-wire.jsonl')}
assert len(arrivals)==150==receipt['source_packets'];resets=[];online_changes=[];same_values_new_windows=0
last=None
for x in arrivals:
 w=wire[x['wire_seq']];assert json.loads(base64.b64decode(w['raw_base64']))==x['source']
 assert w['received_at_mono_s']==x['received_at_mono_s'] and x['native_run_id']==receipt['native_run_id']
 s=x['source'];c=s['raw_cpu'];p=s['previous_raw_cpu']
 if p:
  assert p['read_start_mono_s']<=p['read_end_mono_s']<=c['read_start_mono_s']<=c['read_end_mono_s']
  if any(any(y<x for x,y in zip(p['counters'][k][:8],v[:8])) for k,v in c['counters'].items() if k in p['counters']):resets.append(s['seq'])
  if p['per_core_online']!=c['per_core_online']:online_changes.append(s['seq'])
 if last and s['cpu'] and last['cpu'] and s['cpu']['mean_percent']==last['cpu']['mean_percent']:
  assert s['seq']>last['seq'] and c['read_start_mono_s']>last['raw_cpu']['read_start_mono_s'];same_values_new_windows+=1
 last=s
assert resets and len(online_changes)==2 and same_values_new_windows>0
manifests=list((r/'native').glob('run-*/manifest.json'));assert len(manifests)==1
assert json.loads(manifests[0].read_text())['observer_run_id']==receipt['native_run_id']
result=dict(synthetic=True,actual_serialized_packets_verified=150,native_run_id=receipt['native_run_id'],counter_reset_sequences=resets,online_change_sequences=online_changes,same_values_new_legal_windows_preserved=same_values_new_windows,source_lead_proven=False,zero_latency_assumed=False,device_connections=0)
with a.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,indent=2))
