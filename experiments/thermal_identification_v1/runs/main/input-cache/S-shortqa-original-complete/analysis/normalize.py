from pathlib import Path
from datetime import datetime
import json
p=Path(__file__).resolve().parent.parent;w=p/'workload'
requests=[json.loads(l) for l in (w/'requests.jsonl').read_text().splitlines()];events=[json.loads(l) for l in (w/'events.jsonl').read_text().splitlines()]
ph=[]
for e in events:
 if e['event']!='phase_start':continue
 ending=next((x for x in events if x['event']=='phase_end' and x['phase']==e['phase'] and x['mono_s']>=e['mono_s']),None)
 if not ending:
  ending=next((x for x in events if x['event'] in ['parameters_frozen','workload_end','workload_paused'] and x['mono_s']>=e['mono_s']),None)
 if ending:ph.append({'phase':e['phase'],'start_utc':e['event_time_utc'],'end_utc':ending['event_time_utc']})
normalized=[]
for r in requests:
 group=r['phase'];lastwindow=next((x['end_utc'] for x in ph if x['phase']==('between-groups' if group=='sparse' else 'final-cooldown' if group=='continuous' else 'pilot')),None)
 if not lastwindow:lastwindow=r['client_end_at_utc']
 normalized.append(dict(r,stage=group,submit_utc=r['submitted_at_utc'],end_utc=r['client_end_at_utc'],first_content_utc=r.get('first_model_content_at_utc'),window_end_utc=lastwindow))
(p/'normalized-requests.json').write_text(json.dumps(normalized,ensure_ascii=False,indent=2)+'\n');(p/'normalized-phases.json').write_text(json.dumps(ph,ensure_ascii=False,indent=2)+'\n')
print('normalized',len(requests),'requests',len(ph),'phases')
