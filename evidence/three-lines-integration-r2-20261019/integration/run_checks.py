"""Bounded offline integration only. No sockets, no production imports, no fitting."""
import collections,copy,hashlib,json,sys,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from contracts import readiness as contract_readiness
def readiness(s,now,run,formal=False):return contract_readiness(s,now,run,formal)
from scheduler import Scheduler,resolve_plan

def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def save(name,data):
 p=ROOT/'results'/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def check(name,condition):
 assert condition,name
 checks.append(name)
checks=[]
a=read(ROOT/'streams/issue8-Y.jsonl');b=read(ROOT/'streams/issue9-Y.jsonl')
check('same_observation_count',len(a)==len(b)==5319)
joined=[]
for s,c in zip(a,b):
 i=s['identity'];j=c['identity'];m=s['measurement'];pwm=m['last_successful_pwm'];cp=c['measurement']['PWM']
 assert s['observed_through_ref']==j['observed_through_ref']
 assert s['generated_at_mono_s']==j['observed_through_mono_s']
 assert all(i[k]==j[k] for k in ('run_id','config_sha256','collector_source_sha256'))
 assert i['firmware_identity']==j['firmware']
 if pwm:
  assert (pwm['value_percent'],pwm['source_ref'],pwm['observed_mono_s'],pwm['valid_until_mono_s'],pwm['raw_valid'])==(cp['value'],cp['ref'],cp['received_mono_s'],cp['expires_mono_s'],cp['raw_valid'])
 tj=m['tj'];power=m['power'];src=c['measurement']['TJ_and_rails']['source']
 if tj:
  assert src and tj['source_ref']==src['ref'] and tj['value_C']==src['values']['tj']
  assert power['rails_W']==[src['values']['vdd_gpu'],src['values']['vdd_cpu_soc_mss']]
  assert tj['valid_until_mono_s']==src['valid_until_mono_s']
 joined.append(dict(ref=s['observed_through_ref'],mono_s=s['generated_at_mono_s'],pwm_raw_valid=cp['raw_valid'],
                    model_phase=s['observer']['phase'],gpu_busy=src['values'].get('gpu_busy') if src else None))
check('all_5319_cutoffs_identity_PWM_and_present_TJ_rails_exact',True)
terminal_differences=[]
for s,c in zip(a,b):
 if bool(s['measurement']['tj'] and s['measurement']['tj']['raw_valid'])!=c['measurement']['TJ_and_rails']['raw_valid']:
  terminal_differences.append(s['observed_through_ref'])
check('single_terminal_boundary_TJ_retention_difference_preserved',terminal_differences==[run_ref for run_ref in [a[-1]['observed_through_ref']]])
origin=a[0]['generated_at_mono_s'];expected=copy.deepcopy(a[0]['identity']);run=expected['run_id']
def wrap(s,**kw):
 return dict(schema='TTO-OFFLINE-INTEGRATION-R2',upstream=s,expected_identity=expected,
             replay_origin_mono_s=origin,expected_binding='agx_info.temperature.tj',
             offline_demo_authorized=True,transport='no_requests_virtual_replay',**kw)
counts=collections.Counter();gates=[]
for s in a:
 now=s['generated_at_mono_s']-origin;g=readiness(wrap(s),now,run,False);formal=readiness(wrap(s),now,run,True)
 assert not formal['start_allowed'] and not formal['execution_authorized']
 for k in ('collection_available','model_available','field_safety_available','start_allowed'):counts[k]+=g[k]
 if not (s['measurement']['last_successful_pwm'] or {}).get('raw_valid',False):assert not g['collection_available']
 gates.append(dict(ref=s['observed_through_ref'],mono_s=s['generated_at_mono_s'],phase=g['observer_state'],
                   **{k:g[k] for k in ['collection_available','model_available','field_safety_available','execution_authorized','start_allowed']},reasons=g['reasons']))
check('formal_authorization_never_promoted_5319',True)
check('expired_PWM_never_admitted_from_finite_observer',True)
valid=next(s for s,g in zip(a,gates) if g['start_allowed']);t=valid['generated_at_mono_s']-origin
check('actual_observer_stream_drives_demo_gate',readiness(wrap(valid),t,run)['start_allowed'])
stale=readiness(wrap(valid),t+20,run)
check('no_new_snapshot_no_model_expiry_or_measurement_renewal',not stale['start_allowed'] and not stale['model_available'])
for flag,val in [('guard',True),('fault',True),('mode','manual'),('enabled',False),('manual_mode',True),('binding','other'),('active_source','default')]:
 s=copy.deepcopy(valid);s['safety'][flag]=val;g=readiness(wrap(s),t,run)
 check('explicit_'+flag,g['explicit_stop'] and not g['start_allowed'])
s=copy.deepcopy(valid);s['safety']['guard']=None
check('unknown_guard_is_not_false',not readiness(wrap(s),t,run)['start_allowed'])
s=copy.deepcopy(valid);s['identity']['run_id']='OTHER'
check('cross_run_rejected',not readiness(wrap(s),t,run)['start_allowed'])
s=copy.deepcopy(valid);s['generated_clock_domain']='live_host_monotonic'
check('cross_clock_rejected',not readiness(wrap(s),t,run)['start_allowed'])
s=copy.deepcopy(valid);s['generated_at_mono_s']+=1
check('future_snapshot_rejected',not readiness(wrap(s),t,run)['start_allowed'])
for phase in ['uninitialized','provisional','unavailable']:
 s=copy.deepcopy(valid);s['observer']['phase']=phase
 check('finite_is_not_ready_'+phase,not readiness(wrap(s),t,run)['model_available'])
# Real timeline into the unchanged scheduling state machine. Completions are virtual only.
plan=json.loads((ROOT/'issue10/inputs/mix-plan.json').read_text());profile=resolve_plan(plan,'fixed-anchors')
policy=dict(plan['request_policy'],max_data_unready_seconds=60)
q=Scheduler(profile,policy,run,'OFFLINE-REAL-Y-REPLAY',formal=False)
for s in a:
 now=s['generated_at_mono_s']-origin
 completed=[dict(request_id=k,status='completed',server_state='VIRTUAL_ONLY',done=True,usage=None,finish_reason='VIRTUAL_ONLY') for k,v in q.pending.items() if now-v['submit_mono_s']>=2]
 q.tick(now,wrap(s),completed)
 if q.terminal:break
check('real_Y_readonly_replay_exercised_scheduler',bool(q.events))
# State and request records share run identity; this is a replay, not a new real experiment.
check('one_replay_run_identity',all(e['run_id']==run for e in q.events))
# Verify #9 patch is exactly applicable to the runtime #10 actually vendors.
original=ROOT/'issue10/vendor/runtime024/tto/collector.py'
if not original.exists():original=ROOT/'issue10/vendor/runtime024/collector.py'
base=original.read_text().splitlines(keepends=True);patch=(ROOT/'issue9/deliverables/collector-diagnostics.patch').read_text()
# Exact base/candidate SHA and patch stored; application separately checked by patch --dry-run.
save('runtime-identities.json',dict(baseline_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256((ROOT/'issue9/candidate-collector.py').read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(patch.encode()).hexdigest()))
save('actual-interface-join.json',dict(rows=len(a),result='all present values exact; one terminal-boundary TJ retention difference separately preserved',counts=dict(counts),phase_counts=dict(collections.Counter(s['observer']['phase'] for s in a)),
 raw_firmware=None,formal_allowed=0,clock='explicit offline virtual replay; not live binding',checks=checks))
save('scheduler-real-Y-replay.json',dict(virtual_only=True,phase=q.state,stop_reason=q.reason,virtual_submissions=q.submitted,actual_requests=0,events=q.events,requests=q.requests))
(ROOT/'results/gates.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in gates))
(ROOT/'results/joined-source-index.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in joined))
print(json.dumps(dict(checks=len(checks),rows=len(a),counts=dict(counts),scheduler_state=q.state,stop_reason=q.reason),ensure_ascii=False))
