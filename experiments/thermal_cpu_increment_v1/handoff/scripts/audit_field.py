"""Independent raw-file audit; no author evaluator import, network, or model fit."""
from pathlib import Path
import json, csv, hashlib, math, statistics as st, datetime as dt
from collections import Counter, defaultdict
ROOT=Path(__file__).resolve().parents[1]; O=ROOT/'original'; F=O/'evidence/field/remote-result/run'; M=O/'evidence/modeling'
def jl(p):
 with Path(p).open() as f:
  for line in f:
   if line.strip():yield json.loads(line)
def js(p):return json.loads(Path(p).read_text())
def sec(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def brief(xs):return dict(n=len(xs),min=min(xs),median=st.median(xs),mean=st.mean(xs),max=max(xs))
native=next((F/'native').glob('run-*')); raw=list(jl(native/'observations-0001.jsonl'))
requests=list(jl(F/'requests.jsonl')); protocol=list(jl(F/'protocol.jsonl')); sched=list(jl(F/'scheduler-events.jsonl')); admission=list(jl(F/'admission.jsonl')); summary=js(F/'summary.json')
run=summary['native_run_id']; assert len(requests)==179
assert sha(native/'observations-0001.jsonl')==sha(M/'inputs/native/observations-0001.jsonl')
assert sha(F/'states.jsonl')==sha(M/'inputs/field/states.jsonl')
assert all(r['observer_run_id']==run for r in raw)
assert all(b['mono_s']>=a['mono_s'] for a,b in zip(raw,raw[1:]))
proby=defaultdict(list)
for p in protocol:
 if p.get('request_id'):proby[p['request_id']].append(p)
phases={s['index']:dict(start=s['mono_s'],window_end=s['window_end'],stage=s['stage'],utc=s['recorded_at_utc']) for s in sched if s['event']=='phase_start'}
for s in sched:
 if s['event']=='phase_end':phases[s['index']]['end']=s['mono_s']
request_check=[]
for r in requests:
 data=[line.strip()[5:].strip() for line in (F/'responses'/f"{r['request_id']}.response").read_text().splitlines() if line.startswith('data:')]
 done=data.count('[DONE]'); chunks=[json.loads(s) for s in data if s!='[DONE]']
 final=[c for c in chunks if c.get('usage')][-1]['usage']; reasons=[ch['finish_reason'] for c in chunks for ch in c.get('choices',[]) if ch.get('finish_reason')]
 assert done==1 and final==r['usage'] and r['finish_reason'] in reasons
 assert r['status']=='completed' and r['done'] and r['http_status']==200 and r['usage']['completion_tokens']==256
 assert r['server_request_id'] in {c.get('id') for c in chunks}
 assert any(ch.get('delta',{}).get('content') for c in chunks for ch in c.get('choices',[]))
 assert r['submit_mono_s'] <= r['first_content_mono_s'] <= r['client_end_mono_s']
 phase=phases[r['stage_index']]
 assert phase['start']<=r['submit_mono_s']<=phase['window_end']
 assert r['client_end_mono_s']<=phase['end']
 assert Counter(x['event'] for x in proby[r['request_id']])==Counter(dict(request_submit=1,first_network_line=1,first_content=1,protocol_DONE=1,request_end=1))
 request_check.append(dict(request_id=r['request_id'],phase=r['stage_index'],source_file=f"responses/{r['request_id']}.response",first_content_latency_s=r['first_content_mono_s']-r['submit_mono_s'],protocol_duration_s=r['duration_s']))
work=[]
for ix,p in phases.items():
 if p['stage']['kind']!='work':continue
 rr=[r for r in requests if r['stage_index']==ix]; events=sorted([(r['submit_mono_s'],1) for r in rr]+[(r['client_end_mono_s'],-1) for r in rr])
 count=peak=0; anybusy=slotseconds=0.;prev=p['start']
 for t,d in events:
  anybusy+=(t-prev)*bool(count);slotseconds+=(t-prev)*count;count+=d;peak=max(peak,count);prev=t
 assert count==0 and peak==p['stage']['concurrency']
 work.append(dict(index=ix,n=len(rr),actual_s=p['end']-p['start'],issue_window_s=p['stage']['seconds'],peak_client_inflight=peak,any_client_active_s=anybusy,active_fraction=anybusy/(p['end']-p['start']),slot_seconds=slotseconds))
rawhealth={};abnormal=[]
for kind in ['fan','temp']:
 rr=[r for r in raw if r['kind']==kind]; good=[r for r in rr if r.get('payload') is not None and not r.get('error')]
 gaps=[b['mono_s']-a['mono_s'] for a,b in zip(good,good[1:])]
 rawhealth[kind]=dict(requests=len(rr),successful_payloads=len(good),gaps_s=brief(gaps),over_fan_TTL=sum(x>2.5 for x in gaps) if kind=='fan' else None)
 if kind=='fan':
  for i,r in enumerate(rr):
   fan=r['payload']['data']['fans'][0]
   if fan['temp_stale'] or fan['fault'] or fan['guard_active']:
    abnormal.append(dict(ref=r['ref'],utc=r['received_at_utc'],raw_fan=fan,packet_temp_valid=r['payload']['data']['temp_valid']))
    abnormal[-1]['nearby']=[dict(ref=q['ref'],utc=q['received_at_utc'],PWM=q['payload']['data']['fans'][0]['duty'],temp_stale=q['payload']['data']['fans'][0]['temp_stale']) for q in rr[max(0,i-2):i+7]]
# Independently integrate the declared previous-gate holding convention.
coverage={k:0. for k in ['observed_s','measurement_usable_s','model_usable_s','context_ready_s','joint_ready_s']};phase_s=defaultdict(float)
for a,b in zip(admission,admission[1:]):
 duration=b['scheduler_mono_s']-a['scheduler_mono_s'];assert duration>=0
 coverage['observed_s']+=duration
 for dest,key in [('measurement_usable_s','collection_available'),('model_usable_s','model_available'),('context_ready_s','field_safety_available')]:coverage[dest]+=duration*bool(a[key])
 coverage['joint_ready_s']+=duration*bool(a['collection_available'] and a['model_available'] and a['field_safety_available']);phase_s[a['observer_state']]+=duration
for k,v in coverage.items():assert abs(v-summary['time_coverage'][k])<1e-6,(k,v,summary['time_coverage'][k])
# Current accepted cohort still from sealed/replayed quality, raw CPU/rail values independently read.
samples=list(jl(M/'results/samples-and-causal-states.jsonl')); valid={r['ref']:r for r in samples if r['source_valid']}
cpuraw=[r for r in raw if r['ref'] in valid]
onsets=[]
for ix in [1,3,5,7]:
 rq=min((r for r in requests if r['stage_index']==ix),key=lambda r:r['submit_mono_s']); t=sec(rq['submitted_at_utc']); rows=[]
 for r in cpuraw:
  delta=sec(r['received_at_utc'])-t
  if -2.1<=delta<=3.1:
   p=r['payload'];c=p['cpu']['cores'];rows.append(dict(ref=r['ref'],observer_delta_from_client_submit_s=delta,cpu_mean_pct=st.mean(z['usage'] for z in c),cpu_max_pct=max(z['usage'] for z in c),gpu_util_pct=p['gpu']['utilization_pct'],gpu_rail_W=p['power']['vdd_gpu']['current']/1000,cpu_soc_mss_W=p['power']['vdd_cpu_soc_mss']['current']/1000,gpu_age_at_source_receive_ms=p['gpu']['age_at_telemetry_receive_ms'],tj_C=p['temperature']['tj']))
 onsets.append(dict(stage=ix,request=rq['request_id'],submitted_at_utc=rq['submitted_at_utc'],neighbors=rows))
# Original CH1 and normalized samples.
csvpath=M/'inputs/instrument/imported/original-csv/26071081-20261019173740.csv';rawcsv=list(csv.DictReader(csvpath.read_text().splitlines()[30:]));normalized=list(jl(M/'inputs/instrument/imported/normalized/records.jsonl'))
assert len(rawcsv)==len(normalized)==2984
for i,(a,b) in enumerate(zip(rawcsv,normalized),32):
 stamp=dt.datetime.strptime(a['Date']+' '+a['Time'],'%Y/%m/%d %H:%M:%S').isoformat();assert stamp==b['measured_at_raw'] and float(a['CH1'])==b['temperature_c'] and str(i)==b['provenance']['original_row']['source_line']
 assert b['run_id']==run and not b['model_input'] and not b['control_input']
res=list(jl(F/'resources.jsonl'));cp=[r['cpu_pct_single_core'] for r in res if r['cpu_pct_single_core'] is not None]
output=dict(run_id=run,raw_events=len(raw),raw_kinds=Counter(r['kind'] for r in raw),field_modeling_raw_and_states_same_bytes=True,requests=179,request_phase_counts=Counter(r['stage_index'] for r in requests),payloads=sorted(set(r['payload_sha256'] for r in requests)),request_checks=request_check,work_blocks=work,health=rawhealth,abnormal_fan_snapshots=abnormal,coverage=coverage,phase_seconds=dict(phase_s),CH1=dict(rows=len(rawcsv),sha256=sha(csvpath),min_C=min(float(x['CH1']) for x in rawcsv),max_C=max(float(x['CH1']) for x in rawcsv),adjacent_equal_pairs=sum(a['CH1']==b['CH1'] for a,b in zip(rawcsv,rawcsv[1:]))),resources=dict(cpu_single_core=brief(cp),rss_max_MiB=max(r['rss_bytes'] for r in res)/2**20),onset_observations=onsets,scope='raw-file and semantic checks only; no device, training or new classifier')
(ROOT/'results/field-audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in output.items() if k not in ['request_checks','onset_observations']},ensure_ascii=False,indent=2))
