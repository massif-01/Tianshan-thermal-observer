from pathlib import Path
import json,collections
R=Path(__file__).resolve().parents[1];src=R/'sources/Y-raw';obs=[json.loads(x) for x in next(src.rglob('observations-0001.jsonl')).read_text().splitlines()];fans=[x for x in obs if x['kind']=='fan'];temps=[x for x in obs if x['kind']=='temp'];bins=collections.defaultdict(collections.Counter);i=0
for f in fans:
 while i+1<len(temps) and temps[i+1]['sent_mono_s']<=f['sent_mono_s']:i+=1
 offset=f['sent_mono_s']-temps[i]['sent_mono_s'];k=int(offset) if offset>=0 else -1;bins[k]['total']+=1;bins[k]['timeouts']+=bool(f.get('error_class'));bins[k]['rtt_gt_1s']+=f['round_trip_ms']>1000
(R/'analysis/fan-temp-phase-association.json').write_text(json.dumps({str(k):dict(v) for k,v in sorted(bins.items())},indent=2)+'\n')
r=[json.loads(x) for x in next(src.rglob('requests.jsonl')).read_text().splitlines()];bad=[x for x in fans if x.get('error_class')];c=collections.Counter()
for x in bad:
 a=x['sent_mono_s'];b=x.get('received_mono_s',x['mono_s']);c['overlaps_model_request' if any(z['submit_mono_s']<=b and z['end_mono_s']>=a for z in r) else 'outside_model_requests']+=1
(R/'analysis/load-overlap.json').write_text(json.dumps({'first_fan_timeout_utc':bad[0]['received_at_utc'],'timeouts_before_first_inference':sum(x['sent_mono_s']<r[0]['submit_mono_s'] for x in bad),'request_count':len(r),'counts':dict(c),'semantics':'Same N305 mono domain; interval overlap only, not causation'},indent=2)+'\n')
