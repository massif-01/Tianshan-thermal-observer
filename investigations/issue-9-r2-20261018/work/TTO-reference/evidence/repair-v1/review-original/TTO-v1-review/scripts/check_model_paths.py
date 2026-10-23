"""Synthetic-only independent probes through the installed TTO package.
No user/device/network data. No candidate source modifications.
"""
import copy,json,sys
from pathlib import Path
from tto.demo import record_demo
from tto.dataset import freeze_split,load_dataset,check_split
from tto.model import load_model
from tto.training import train
from tto.evaluation import evaluate,value_conclusion
from tto.engine import Engine
from tto.storage import Journal
from tto.report import summarize,run_report
from tto.util import read_json,write_json,seal

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=False)
# 1. Full-model feature loss must not erase evidence about TJ-only model.
base_runs=record_demo(root/'base-runs',count=5,seconds=720)
inputs=root/'baseline';inputs.mkdir()
base_split=freeze_split(base_runs,inputs/'frozen')
train(base_split/'dataset.json',base_split/'split.json',inputs/'model-simulation.json')
d=load_dataset(inputs/'frozen/dataset.json');s=read_json(inputs/'frozen/split.json')
m=load_model(inputs/'model-simulation.json')
field=next(c for c in m['methods']['ridge_full']['columns'] if c.startswith('vdd_'))
ids=set(s['partitions']['test'])
for r in d['rows']:
 if r['id'] in ids:
  for key in list(r['features']):
   if key==field or key.startswith(field+'_mean_'):r['features'][key]=None
for o in (d,s):o.pop('sha256',None)
d=seal(d);s['dataset_sha256']=d['sha256'];s=seal(s)
p=root/'missing-full';p.mkdir();write_json(p/'dataset.json',d);write_json(p/'split.json',s)
new_model=train(p/'dataset.json',p/'split.json',p/'model.json')
ev=evaluate(p/'dataset.json',p/'split.json',p/'model.json',p/'eval')
# Explicit unit-test flags only: not a real deployment or real performance assessment.
decision_d=copy.deepcopy(d);decision_d['simulated']=False
for run in decision_d['runs']:run['deployment_status']='user_recorded_not_independently_verified'
rows=[r for r in d['rows'] if r['id'] in ids]
from tto.evaluation import group_metrics
matched={n:[] for n in ('persist','trend30','ridge_tj')}
for row in d['rows']:
 if row['id'] not in ids or not row['normal_auto'] or '45' not in row['labels']:continue
 from tto.model import infer
 prediction=infer(new_model,'ridge_tj',row['features'])[0]
 if prediction is None or 'trend30' not in row['baseline_values']:continue
 for n in matched:
  value=prediction['45'] if n=='ridge_tj' else row['baseline_values'][n]['45']
  matched[n].append({'episode':row['episode'],'error':value-row['labels']['45']['value']})
res1={'synthetic_only':True,'three_method_matched':{n:group_metrics(ps) for n,ps in matched.items()},'missing_test_field':field,
 'same_training_methods':new_model['methods']==m['methods'],
 'all_four_intersection':ev['same_origin_intersection_count'],
 'method45':{n:{'scorable':ev['coverage']['45'][n].get('scorable',0),'mae':ev['all_available_metrics']['45'][n]['episode_equal_macro'].get('mae')} for n in ev['coverage']['45']},
 'decision_function_with_explicit_test_flags':value_conclusion(decision_d,s,rows,ev['same_origin_metrics'],{'45':[]},{})}
# 2. Chronological partition accepts non-contiguous reused episode names.
runs=record_demo(root/'chrono-runs',count=6,seconds=400)
for i,r in enumerate(runs):
 manifest=read_json(r/'manifest.json');ep='A' if i in (0,5) else chr(ord('A')+i)
 manifest['episode']=ep;manifest['started_at_utc']=f'2026-01-{i+1:02d}T00:00:00+00:00'
 (r/'manifest.json').write_text(json.dumps(manifest))
 for obs in r.glob('observations-*.jsonl'):
  data=[json.loads(l) for l in obs.read_text().splitlines()]
  for row in data:row['episode']=ep
  obs.write_text(''.join(json.dumps(x)+'\n' for x in data))
frozen=freeze_split(runs,root/'chrono-frozen')
cd=load_dataset(frozen/'dataset.json');cs=read_json(frozen/'split.json');check_split(cd,cs)
part_by_id={id_:p for p,ids_ in cs['partitions'].items() for id_ in ids_}
chronology=[]
for run in cd['runs']:
 parts=sorted({part_by_id[r['id']] for r in cd['rows'] if r['run_id']==run['observer_run_id']})
 chronology.append({'episode':run['episode'],'started_at_utc':run['started_at_utc'],'parts':parts})
res2={'synthetic_only':True,'accepted_by_frozen_split_and_check':True,'run_chronology':chronology,'training_can_include_last_run_after_test':chronology[-1]['parts']==['train']}
# 3. A completed model shadow run is reported without reading its saved model results.
source_run=runs[1];source_manifest=read_json(source_run/'manifest.json');config=source_manifest['config']
journal=Journal(config,root/'shadow-runs',simulated=True,episode='shadow-fixture')
e=Engine(config,m);pn=0;sn=0
for file in sorted(source_run.glob('observations-*.jsonl')):
 for line in file.read_text().splitlines():
  r=json.loads(line)
  out=e.process(journal.observation(r))
  if out['prediction']:
   journal.append('predictions',out['prediction']);pn+=int('ridge_full' in out['prediction']['values'])
  for score in out['scores']:
   journal.append('scores',score);sn+=int('ridge_full' in score.get('errors',{}))
for score in e.invalidate('run_end'):journal.append('scores',score)
journal.close({'stop_reason':'fixture_completed'})
report_before=summarize(journal.path)
run_report(journal.path,root/'shadow-report')
# Negative control on this generated fixture only: unavailable persisted results.
pred=journal.path/'predictions.jsonl';scores=journal.path/'scores.jsonl'
pred.rename(journal.path/'predictions.removed-by-reviewer');scores.rename(journal.path/'scores.removed-by-reviewer')
report_after=summarize(journal.path)
res3={'synthetic_only':True,'stored_full_model_predictions':pn,'stored_full_model_scores':sn,
 'summary_unchanged_when_saved_predictions_and_scores_absent':report_before==report_after,
 'summary_keys':list(report_before),'report_text':(root/'shadow-report/report.md').read_text()}
all_results={'missing_full_model':res1,'chronological_split':res2,'shadow_reporting':res3}
(root/'findings.json').write_text(json.dumps(all_results,indent=2,ensure_ascii=False))
print(json.dumps(all_results,indent=2,ensure_ascii=False))
