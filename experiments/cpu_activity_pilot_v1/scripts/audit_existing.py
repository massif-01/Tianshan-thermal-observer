from pathlib import Path
import json,hashlib,statistics,zipfile
root=Path('/Users/massif/Tianshan-thermal-observer');ev=root/'evidence/cpu-activity-pilot-prep-20261019';dest=ev/'inputs'
identity=json.loads((root/'evidence/device-update-20261013/identity.json').read_text())
source=Path('/Users/massif/rm01OrinStatus/src/tegrastats_api')
findings={}
for n in ('parser.py','platform_gpu.py','server.py'):
 data=(source/n).read_bytes();(dest/('current-local-'+n)).write_bytes(data)
 findings[n]={'sha256':hashlib.sha256(data).hexdigest(),'matches_20261013_receipt':hashlib.sha256(data).hexdigest()==identity['source_sha256'][n]}
for wh in Path('/Users/massif/rm01OrinStatus/evidence/orin-thor-service-closeout-20261012').glob('*/tegrastats_api-1.1.1*.whl'):
 with zipfile.ZipFile(wh) as z:
  b=z.read('tegrastats_api/parser.py')
  if hashlib.sha256(b).hexdigest()==identity['source_sha256']['parser.py']:
   (dest/'historical-installed-parser.py').write_bytes(b);findings['matched_historical_parser']=str(wh)
(dest/'ws-historical-identity.json').write_text(json.dumps(identity,indent=2))
raw=root/'experiments/thermal_fixed_anchors_frozen_v1/inputs/native/observations-0001.jsonl';ages=[];intervals=set();seqs=set();cpu_count=set();examples=[];stale=[]
for line in raw.open():
 r=json.loads(line);p=r.get('payload')
 if r['kind']=='orin' and p:
  seqs.add(p['telemetry_meta']['sample_seq']);ages.append(p['gpu']['age_at_telemetry_receive_ms']);intervals.add(p['gpu']['sample_interval_ms']);cpu_count.add(len(p['cpu']['cores']))
 if r['ref'].endswith(tuple('observation:'+str(i) for i in (2482,2485,2488,2491,4679,4682,4685))):examples.append(r)
(ev/'checks/original-examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2))
result=dict(existing_run='5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3',data_role='already-used development, not new experiment',
  raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),unique_source_sequences=len(seqs),cpu_core_counts=sorted(cpu_count),recorded_gpu_period_ms=sorted(intervals),gpu_reported_age_median_ms=statistics.median(ages),
  source_files=findings,shared_jtop_conclusion='local reviewed WS source uses own tegrastats child and NVML reader, no jtop IPC/import. Current installed jtop/version/service interval and 20261019 WS exact parser bytes not yet proven; no UI or interval change authorized.',
  original_cpu_read_window='not in native raw: tegrastats source period1000ms is not an exact per-core counter window',
  high_frequency_claim=False,latency_zero_claim=False,field_connections_this_phase=0,thermal_fits_this_phase=0)
(ev/'checks/offline-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
