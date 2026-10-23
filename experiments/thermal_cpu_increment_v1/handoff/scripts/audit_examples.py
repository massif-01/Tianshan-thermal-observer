"""Extract fixed event examples; no threshold training, correlation search or new samples."""
from pathlib import Path
import json, datetime as dt
R=Path(__file__).resolve().parents[1]
M=R/'original/evidence/modeling'
def jl(p): return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
ps=jl(M/'results/predictions.jsonl')
requests=jl(R/'original/evidence/field/remote-result/run/requests.jsonl')
cs=[p for p in ps if p['h']==45 and p['label'] and 'B1' in p['baselines'] and 'AUGMENTED-KF' in p['B_HOLD'] and p['phase']==p['label']['phase']]
w=min(cs,key=lambda p:p['B_HOLD']['AUGMENTED-KF']-p['label']['value'])
idx=int(w['phase'].split('-')[0]);first=min([r for r in requests if r['stage_index']==idx],key=lambda r:r['submit_mono_s'])
res={'selection':'worst same-phase 45-second underprediction on existing common cohort; descriptive, not a model selection rule','record':w,'first_request':first['request_id'],'first_submit_utc':first['submitted_at_utc'],'origin_seconds_after_first_submit':(dt.datetime.fromisoformat(w['utc'])-dt.datetime.fromisoformat(first['submitted_at_utc'])).total_seconds(),'independent_note':'A case just after request submission is not evidence of CPU/GPU physical onset ordering. CPU/GPU/power arrival examples are in field-audit.json.'}
(R/'results/onset-error-example.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
print(json.dumps(res,ensure_ascii=False,indent=2))
