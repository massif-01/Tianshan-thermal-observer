"""Independent raw CPU-count windows and saved point-score arithmetic; standard library only."""
from pathlib import Path
import argparse,base64,json,statistics,hashlib

def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x]
def read(p):return json.loads(p.read_text())
def cores(text):
 out=[]
 for x in text.strip().split(','):
  if '-' in x:
   a,b=map(int,x.split('-'));out.extend(range(a,b+1))
  else:out.append(int(x))
 return out
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);r=ap.parse_args().root
f=r/'field_original/evidence/remote-result/run';out=r/'deliverable/results'
a=lines(f/'cpu-sidecar-arrivals.jsonl');w=lines(f/'cpu-sidecar-wire.jsonl');assert len(a)==len(w)==27
windows=[];max_error=0.
for i,(v,q) in enumerate(zip(a,w)):
 source=v['source'];raw=base64.b64decode(q['raw_base64']);assert json.loads(raw)==source
 assert v['received_at_mono_s']==q['received_at_mono_s'];assert v['native_run_id']==q['native_run_id']
 current=source['raw_cpu']
 parsed={s.split()[0]:list(map(int,s.split()[1:])) for s in current['raw_proc_stat'].splitlines() if s.startswith('cpu')}
 assert parsed==current['counters']
 if i==0:assert source['previous_raw_cpu'] is None and source['cpu'] is None;continue
 assert source['previous_raw_cpu']==a[i-1]['source']['raw_cpu']
 previous=source['previous_raw_cpu'];assert current['online_text']==previous['online_text']
 values={}
 for n in cores(current['online_text']):
  k=f'cpu{n}';delta=[x-y for x,y in zip(parsed[k][:8],previous['counters'][k][:8])]
  assert all(x>=0 for x in delta);total=sum(delta);assert total>0
  values[k]=100*(total-delta[3]-delta[4])/total
 expected=source['cpu'];assert len(values)==expected['valid_core_count']
 for k,vv in values.items():max_error=max(max_error,abs(vv-expected['per_core_percent'][k]))
 mean=statistics.mean(values.values());mx=max(values.values());max_error=max(max_error,abs(mean-expected['mean_percent']),abs(mx-expected['max_percent']))
 windows.append({'seq':source['seq'],'online_cores':len(values),'mean_pct':mean,'max_pct':mx,'SC_CLK_TCK':current['SC_CLK_TCK'],
                 'source_read_start_mono_s':source['read_start_mono_s'],'receiver_mono_s':v['received_at_mono_s']})
period=[b['source']['read_start_mono_s']-c['source']['read_start_mono_s'] for c,b in zip(a,a[1:])]
res={'raw_wire_equal_source_rows':len(a),'complete_windows':len(windows),'missing_first_window':True,'online':a[0]['source']['raw_cpu']['online_text'],
 'possible':a[0]['source']['raw_cpu']['possible_text'],'max_recomputed_utilization_difference_pct':max_error,
 'median_source_period_s':statistics.median(period),'source_span_s':sum(period),'windows':windows}
(out/'cpu-windows-independent.json').write_text(json.dumps(res,indent=2)+'\n')
pts=lines(r/'model_replay/joint/evaluate-stream/actual-arrived-points.jsonl');tables=lines(r/'model_replay/joint/evaluate-stream/actual-arrived-common.jsonl')
summary=[]
for table in tables:
 h=table['h'];methods=list(table['errors']);ps=[x for x in pts if x['h']==h and x['label'] is not None and not x.get('label_rejection') and all(m in x['prediction'] and x['prediction'][m] is not None for m in methods)]
 assert len(ps)==table['n'];result={}
 for method in methods:
  diffs=[p['prediction'][method]-p['label']['value'] for p in ps]
  mae=statistics.mean([abs(e) for e in diffs]) if diffs else None
  assert mae is None if table['errors'][method]['MAE_C'] is None else abs(mae-table['errors'][method]['MAE_C'])<1e-12
  result[method]={'n':len(ps),'MAE_C':mae,'bias_C':statistics.mean(diffs) if diffs else None}
 summary.append({'h':h,'common_n':len(ps),'scores':result,'origin_refs':[p['ref'] for p in ps]})
(out/'scores-independent.json').write_text(json.dumps(summary,indent=2)+'\n')
print('27 wire matches; 26 raw windows recomputed; max % diff',max_error);print('Common cohorts',[(x['h'],x['common_n']) for x in summary])
