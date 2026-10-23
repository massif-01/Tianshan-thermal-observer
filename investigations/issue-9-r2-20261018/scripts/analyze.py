import json,collections,statistics,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; results={}
def quant(a):
 a=sorted(a)
 def p(q):
  x=(len(a)-1)*q;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
 return {'n':len(a),'min':a[0] if a else None,'p50':p(.5) if a else None,'p95':p(.95) if a else None,'max':a[-1] if a else None}
for name,where in [('Y','Y-raw'),('M','M-raw')]:
 run=next((ROOT/'sources'/where).rglob('observations-0001.jsonl')).parent
 rows=[json.loads(x) for x in (run/'observations-0001.jsonl').read_text().splitlines()];manifest=json.loads((run/'manifest.json').read_text());summary=json.loads((run/'summary.json').read_text());stats={}
 timeline=[]
 for kind in ['fan','temp']:
  rs=[x for x in rows if x['kind']==kind];good=[x for x in rs if not x.get('error_class')];bad=[x for x in rs if x.get('error_class')];gaps=[b['mono_s']-a['mono_s'] for a,b in zip(good,good[1:])]
  stats[kind]={'total':len(rs),'success':len(good),'errors':dict(collections.Counter(x['error_class'] for x in bad)),'RTT_success_ms':quant([x['round_trip_ms'] for x in good]),'RTT_error_ms':quant([x['round_trip_ms'] for x in bad]),'gaps_success_s':quant(gaps),'gaps_gt_2_5':sum(x>2.5 for x in gaps),'sent_lateness_ms':quant([(x['sent_mono_s']-x.get('planned_mono_s',x['sent_mono_s']))*1000 for x in rs]),'response_canonical_bytes':quant([len(json.dumps(x['payload'],separators=(',',':')).encode()) for x in good])}
  for x in rs:timeline.append({'endpoint':kind,'utc':x['received_at_utc'],'sent_mono_s':x['sent_mono_s'],'received_mono_s':x.get('received_mono_s',x['mono_s']),'rtt_ms':x['round_trip_ms'],'error_class':x.get('error_class',''),'ref':x['ref'],'successful_PWM':next(iter((x.get('payload') or {}).get('data',{}).get('fans',[])),{}).get('duty'),'raw_temp_stale':next(iter((x.get('payload') or {}).get('data',{}).get('fans',[])),{}).get('temp_stale')})
 with (ROOT/'analysis'/f'{name}-http-timeline.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(timeline[0]));w.writeheader();w.writerows(sorted(timeline,key=lambda x:x['sent_mono_s']))
 fanbad=[x for x in rows if x['kind']=='fan' and x.get('error_class')];temps=[x for x in rows if x['kind']=='temp'];pairs=[]
 for f in fanbad:
  near=[x for x in temps if x['sent_mono_s']<=f['mono_s'] and x['mono_s']>=f['sent_mono_s']]
  pairs.extend(near)
 stale=[x['ref'] for x in rows if x['kind']=='fan' and any(f.get('temp_stale') for f in (x.get('payload') or {}).get('data',{}).get('fans',[]))]
 results[name]={'run_id':manifest['observer_run_id'],'version':manifest['version'],'source_identity':manifest['source_identity'],'firmware_identity':manifest.get('firmware_identity'),'http':stats,'polling_health':summary.get('polling_health'),'stale_fan_refs':stale,'temp_requests_overlapping_fan_errors':{'total':len(pairs),'errors':sum(bool(x.get('error_class')) for x in pairs)},'host_resources':{k:summary.get(k) for k in ['dropped','queue_peak_items','queue_peak_bytes','cpu_pct_single_core','rss_mib']},'network_config':manifest['config']['network'],'config_sha':manifest['config_sha256']}
(ROOT/'analysis/comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'http':v['http'],'overlap':v['temp_requests_overlapping_fan_errors'],'stale':len(v['stale_fan_refs'])} for k,v in results.items()},ensure_ascii=False,indent=2))
