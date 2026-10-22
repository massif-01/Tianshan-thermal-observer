"""Read-only audit of the supplied 0.2.4 midload experiment. No network or fitting."""
from pathlib import Path
import argparse,bisect,collections,hashlib,json,math,statistics,sys,zipfile
import numpy as np
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive',required=True,help='Original full midload evidence ZIP')
parser.add_argument('--summary',help='Optional independently supplied runner-summary.json')
parser.add_argument('--workdir',required=True,help='Separate output directory')
args=parser.parse_args()
B=Path(args.workdir).resolve();B.mkdir(parents=True,exist_ok=True)
CODE=Path(__file__).resolve().parent/'reference_code'
ARCHIVE=Path(args.archive).resolve()
S=B/'source';T=B/'trial'
def unpack(src,dest):
    with zipfile.ZipFile(src) as z:
        assert z.testzip() is None
        for info in z.infolist():
            assert (dest/info.filename).resolve().is_relative_to(dest.resolve())
        if not dest.exists():
            dest.mkdir(parents=True);z.extractall(dest)
unpack(ARCHIVE,S);unpack(S/'trial-result.zip',T)
R=next((T/'collection').iterdir());O=B/'results';O.mkdir(exist_ok=True)
def load(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):(O/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def stats(x):
 a=np.array(x,dtype=float)
 return {'n':len(a),'mean':float(a.mean()),'median':float(np.median(a)),'p95':float(np.quantile(a,.95)),'min':float(a.min()),'max':float(a.max())} if len(a) else {'n':0}
integrity={}
for root,idx,key in [(S,'package-SHA256.json','outer'),(T,'SHA256.json','inner'),(R,'files.json','run')]:
 d=load(root/idx);checks=[]
 for name,info in d.items():
  h=info if isinstance(info,str) else info['sha256'];p=root/name
  checks.append({'file':name,'sha_matches':sha(p)==h,'bytes':p.stat().st_size,'size_matches':isinstance(info,str) or p.stat().st_size==info.get('bytes',p.stat().st_size)})
 assert all(x['sha_matches'] and x['size_matches'] for x in checks)
 integrity[key]={'files':len(checks),'all_match':True,'checks':checks}
integrity['standalone_summary_matches_nested']=(Path(args.summary).read_bytes()==(T/'summary.json').read_bytes()) if args.summary else None
integrity['zip_sha256']=sha(ARCHIVE)
integrity['trial_zip_sha256']=sha(S/'trial-result.zip')
m=load(R/'manifest.json');sm=load(R/'summary.json');rs=load(T/'summary.json');ev=rows(T/'events.jsonl');req=rows(T/'requests.jsonl');obs=rows(R/'observations-0001.jsonl');qe=rows(R/'events.jsonl');pred=rows(R/'predictions.jsonl');score=rows(R/'scores.jsonl')
identity=[]
for fn,h in m['source_identity']['files'].items():
 p=CODE/'tto'/fn;identity.append({'file':fn,'sha_matches':sha(p)==h})
assert all(x['sha_matches'] for x in identity)
integrity['source_modules_against_reviewed_024']={'files':len(identity),'all_match':True,'checks':identity}
integrity['runner_original_native_matches_supplied']=sha(S/'original/health.py')==sha(S/'execution-copy/thermal_trials/health_native.py')
save('integrity.json',integrity)
# Protocol data, without reproducing potentially private response contents.
protocol=[]
for r in req:
 lines=(T/'responses'/f"{r['request_id']}.response").read_text().splitlines();objs=[];done=False
 for line in lines:
  if not line.startswith('data:'):continue
  data=line[5:].strip()
  if data=='[DONE]':done=True;continue
  objs.append(json.loads(data))
 ids={x.get('id') for x in objs if x.get('id')}; usages=[x['usage'] for x in objs if x.get('usage')];finishes=[c['finish_reason'] for x in objs for c in x.get('choices',[]) if c.get('finish_reason')]
 check={'request_id':r['request_id'],'done':done,'ids_match':ids=={r['server_request_id']},'usage_matches':bool(usages) and usages[-1]==r['usage'],'finish_matches':bool(finishes) and finishes[-1]==r['finish_reason'],'time_arithmetic_matches':abs((r['client_end_mono_s']-r['submit_mono_s'])-r['duration_s'])<0.001,'duration_field_vs_end_difference_s': r['duration_s']-(r['client_end_mono_s']-r['submit_mono_s']), 'duration_s':r['duration_s'],'ttft_s':r['first_content_mono_s']-r['submit_mono_s'],'finish_reason':r['finish_reason']}
 assert all(check[k] for k in ['done','ids_match','usage_matches','finish_matches','time_arithmetic_matches']);protocol.append(check)
assert all(b['submit_mono_s']>=a['client_end_mono_s'] for a,b in zip(req,req[1:]))
save('request_protocol.json',{'count':len(req),'all_protocol_verified':True,'nonoverlap':True,'completion_tokens':sum(x['usage']['completion_tokens'] for x in req),'duration_s':stats([x['duration_s'] for x in req]),'ttft_s':stats([x['first_content_mono_s']-x['submit_mono_s'] for x in req]),'requests':protocol})
# Replay the actual saved source through the byte-matched production processor and both health policies.
sys.path.insert(0,str(CODE))
sys.path.insert(0,str(S/'execution-copy/thermal_trials'))
from tto.engine import engine_for
from health import TrialHealth
engine=engine_for(m['config'],record_schema=m['record_schema']);health=TrialHealth()
qby={x['ref']:x for x in qe if 'accepted' in x};replayed=[];nodes=[];replay_predictions=[];replay_scores=[]
for r in obs:
 out=engine.process(r);health.observe(r,out,engine)
 if out['quality']:
  q=out['quality'];saved=qby[r['ref']]
  assert all(saved[k]==v for k,v in q.items()),r['ref']
  if q['accepted']:replayed.append({'t':r['mono_s'],'utc':r['received_at_utc'],'ref':r['ref'],'seq':q['key'][-1],'segment':q['segment'],'values':q['values'],'gpu':q.get('gpu'), 'control':engine.control_qualification(r['mono_s'])})
 if out['prediction']:replay_predictions.append(out['prediction'])
 replay_scores+=out['scores']
 nodes.append(dict(health.native.nodes[-1]))
replay_scores+=engine.invalidate('run_end')
assert replay_predictions==pred, 'prediction replay differs'
assert replay_scores==score,'score replay differs'
h=load(T/'input-health.json');new=health.snapshot(h['checked_at_mono_s'])
assert new==h,'health replay differs'
save('replay.json',{'observations':len(obs),'events':len(qe),'source_results_matched':len(qby),'accepted_new_TJ':len(replayed),'predictions_exact_match':len(pred),'scores_exact_match':len(score),'health_snapshot_exact_match':True,'native_coverage':new['original_rule_snapshot']['input_coverage'],'override_coverage':new['input_coverage'],'native_abnormal_latched':new['original_rule_snapshot']['abnormal'],'override_abnormal_latched':new['abnormal'],'quality_counts':dict(engine.q.counts),'has_model':m['model_sha256'] is not None,'prediction_methods':dict(collections.Counter(k for x in pred for k in x['values']))})
# Strict intervals are measured on native health, not the override.
segments=[];current=None;gaps=[]
for a,b in zip(nodes,nodes[1:]):
 lo=a['t']; hi=b['t'];edge=min(hi,a['valid_until']) if a['complete'] else lo
 if edge>lo:
  if current is None:current={'start':lo,'end':edge,'first_ref':a['ref'],'last_ref':a['ref']}
  elif abs(current['end']-lo)<1e-8:current['end']=edge;current['last_ref']=a['ref']
  else:segments.append(current);current={'start':lo,'end':edge,'first_ref':a['ref'],'last_ref':a['ref']}
 if edge<hi-1e-10:
  if current:segments.append(current);current=None
  gaps.append({'start':edge,'end':hi,'reason':a['reasons'] or ['input_validity_expired'],'ref':a['ref']})
if current:segments.append(current)
for x in segments:x['duration_s']=x['end']-x['start']
save('strict_intervals.json',{'segments':segments,'gaps':gaps,'coverage_fraction':sum(x['duration_s'] for x in segments)/(nodes[-1]['t']-nodes[0]['t'])})
# Recompute poll timing and continuous accepted input statistics.
fans=[];temps=[]
for r in obs:
 if r['kind']=='fan' and r.get('payload',{}).get('code')==0:
  f=[x for x in r['payload']['data']['fans'] if x['id']==0][0];fans.append({'t':r['mono_s'],'utc':r['received_at_utc'],'ref':r['ref'],**f})
 elif r['kind']=='temp':temps.append({'t':r['mono_s'],'ref':r['ref'],**r['payload']['data']})
P={}
for kind in ['fan','temp']:
 oo=[x for x in obs if x['kind']==kind];ret=[x['received_mono_s'] for x in oo];send=[x['sent_mono_s'] for x in oo]
 result={'n':len(oo),'errors':sum('error_class' in x for x in oo),'return_interval_s':stats(np.diff(ret)), 'send_interval_s':stats(np.diff(send)),'rtt_ms':stats([x['round_trip_ms'] for x in oo])}
 expected=sm['polling_health']['endpoints'][kind]
 assert abs(result['return_interval_s']['max']-expected['return_interval_s']['max'])<1e-9
 assert abs(result['rtt_ms']['p95']-expected['rtt_ms']['p95'])<1e-9
 P[kind]=result
TT=[x['t'] for x in replayed];FT=[x['t'] for x in fans]
phases=[]
start_ev={x['phase']:x for x in ev if x['event']=='phase_start'};end_ev={x['phase']:x for x in ev if x['event']=='phase_end'}
def source_at(t):
 i=bisect.bisect_right(TT,t)-1
 return replayed[i] if i>=0 else None
def fan_at(t):
 i=bisect.bisect_right(FT,t)-1
 return fans[i] if i>=0 else None
def source_mean(lo,hi,key):
 total=w=0.
 for a,b in zip(replayed,replayed[1:]):
  l=max(lo,a['t']);right=min(hi,b['t']);dt=max(0,right-l)
  v=a['values'].get(key)
  if dt>0 and v is not None:total+=dt*v;w+=dt
 return total/w if w else None
for id_,st in start_ev.items():
 en=end_ev[id_];lo=st['actual_start_mono_s'];hi=en['actual_end_mono_s'];subset=[r for r in replayed if lo<=r['t']<hi];ff=[r for r in fans if lo<=r['t']<hi];bfr=source_at(lo);bff=fan_at(lo);requests=[r for r in req if r['request_id'].startswith(id_+'-')]
 entry={'phase':id_,'start_mono':lo,'end_mono':hi,'start_utc':st['occurred_at_utc'],'end_utc':en['occurred_at_utc'],'planned_s':st['duration_s'],'actual_s':hi-lo,'n_new_TJ':len(subset),'TJ_before_c':bfr['values']['tj'] if bfr else None,'TJ_first_c':subset[0]['values']['tj'],'TJ_last_c':subset[-1]['values']['tj'],'TJ_peak_c':max(r['values']['tj'] for r in subset),'TJ_peak_ref':max(subset,key=lambda r:r['values']['tj'])['ref'],'TJ_mean_c':source_mean(lo,hi,'tj'),'PWM_before':bff['duty'] if bff else None,'PWM_min':min(x['duty'] for x in ff),'PWM_max':max(x['duty'] for x in ff),'PWM_peak_ref':max(ff,key=lambda x:x['duty'])['ref'],'gain_before':bff['controller_gain'] if bff else None,'gain_last':ff[-1]['controller_gain'],'GPU_busy_mean_pct':source_mean(lo,hi,'gpu_busy'),'GPU_W_mean':source_mean(lo,hi,'vdd_gpu'),'CPU_W_mean':source_mean(lo,hi,'vdd_cpu_soc_mss'),'5V_W_mean':source_mean(lo,hi,'vin_sys_5v0'),'requests':len(requests),'client_busy_s':sum(r['duration_s'] for r in requests),'bad_fan_snapshots':sum(f['temp_stale'] or f['fault'] or f['guard_active'] for f in ff)}
 if requests:
  entry['all_submissions_in_window']=all(lo<=r['submit_mono_s']<st['window_deadline_mono_s'] for r in requests)
  entry['within_block_gaps_s']=stats([b['submit_mono_s']-a['client_end_mono_s'] for a,b in zip(requests,requests[1:])])
  entry['pre30_TJ_median']=float(np.median([r['values']['tj'] for r in replayed if lo-30<=r['t']<lo]));entry['busy_fraction']=entry['client_busy_s']/entry['actual_s']
  points={}
  end=requests[-1]['client_end_mono_s']
  for d in [0,5,15,30,60,90,180,300,420,600]:
   i=bisect.bisect_left(TT,end+d)
   if i<len(TT) and TT[i]-(end+d)<=2 and TT[i] < (start_ev.get({'M20':'M60','M60':'M180'}.get(id_,''),{}).get('actual_start_mono_s',math.inf)):
    q=replayed[i];f=fan_at(q['t']);points[str(d)]={'TJ':q['values']['tj'],'PWM':f['duty'],'gain':f['controller_gain'],'actual_offset_s':q['t']-end,'ref':q['ref'],'fan_ref':f['ref'],'fan_temp_stale':f['temp_stale']}
  entry['after_request_end']=points
  # First observed return to own pre30 median +1 C, not thermal equilibrium.
  p=next((r for r in replayed if r['t']>=end and r['values']['tj']<=entry['pre30_TJ_median']+1),None)
  entry['first_return_pre30_plus1_s']=p['t']-end if p else None
 phases.append(entry)
save('phases.json',phases)
changes=[]
for i,f in enumerate(fans):
 if i==0 or f['controller_gain']!=fans[i-1]['controller_gain']:changes.append({k:f[k] for k in ['t','utc','ref','controller_gain','duty','control_temperature','slope_c_per_min','cooling_response']})
stale=[f for f in fans if f['temp_stale']]
raw={
 'counts':dict(collections.Counter(x['kind'] for x in obs)),
 'source_intervals_s':stats(np.diff(TT)),
 'source_streams':len({tuple(x.get('key',[])[:2]) for x in qe if x.get('accepted')}),
 'TJ_c':stats([x['values']['tj'] for x in replayed]),
 'fan_modes':dict(collections.Counter(x['mode'] for x in fans)),
 'fan_flags':{k:sum(bool(x[k]) for x in fans) for k in ['temp_stale','guard_active','fault']},
 'temp_valid_false':sum(not x['valid'] for x in temps),'active_sources':dict(collections.Counter(x['active_source'] for x in temps)),
 'PWM':stats([x['duty'] for x in fans]),'rpm_distinct':sorted({x['rpm'] for x in fans}),
 'gain_changes':changes,'stale_snapshots':stale,'ambient_records':sum(x['event']=='ambient_snapshot' for x in ev),
 'ambient_nonnull':sum(x['event']=='ambient_snapshot' and x['record'].get('temperature_c') is not None for x in ev),
 'resource_cpu_single_core_pct':stats(sm['cpu_pct_single_core']),'resource_RSS_MiB':stats(sm['rss_mib']),
 'polling':P,
 'stored_predictions':len(pred),'stored_scores':dict(collections.Counter(x['status'] for x in score))}
if stale:
 f=stale[0];i=next(i for i,x in enumerate(fans) if x['ref']==f['ref']);raw['stale_neighbours']=fans[max(0,i-2):i+3];raw['stale_after_last_request_s']=f['t']-req[-1]['client_end_mono_s']
save('raw_summary.json',raw)
# Every 1-second accepted origin with 60-second strict past and fully strict future; no model generation.
coverage=[]
for phase in phases:
 lo,hi=phase['start_mono'],phase['end_mono'];ps=[p for p in replayed if lo<=p['t']<hi]
 item={'phase':phase['phase'],'accepted_origins':len(ps),'past60_strict':0,'strict_labels':{str(h):0 for h in [15,45,90]},'scope':'eligibility count only; no new G2 forecast or fit'}
 for p in ps:
  s=next((s for s in segments if s['start']+60<=p['t']<=s['end']),None)
  if not s:continue
  item['past60_strict']+=1
  for h in [15,45,90]:
   j=bisect.bisect_left(TT,p['t']+h)
   if j<len(TT) and TT[j]<=p['t']+h+2 and TT[j]<=s['end']:item['strict_labels'][str(h)]+=1
 coverage.append(item)
save('prospective_coverage.json',coverage)
# Audit field-based mean with no external claims; reader receives full raw references.
print('INTEGRITY',[(k,v['files']) for k,v in integrity.items() if isinstance(v,dict) and 'files'in v])
print('REPLAY',len(obs),len(replayed),len(pred),len(score), 'HEALTH EXACT')
print('COVERAGE',health.native.coverage,'SEGMENTS',segments)
print('PHASES')
for x in phases:print({k:x[k] for k in ['phase','actual_s','TJ_before_c','TJ_peak_c','PWM_max','GPU_busy_mean_pct','GPU_W_mean','requests','gain_before','gain_last']})
print('STORED SCORE',raw['stored_scores']);print('RESOURCE',raw['resource_cpu_single_core_pct'],raw['resource_RSS_MiB'])
print('STRICT LABELS',coverage)
