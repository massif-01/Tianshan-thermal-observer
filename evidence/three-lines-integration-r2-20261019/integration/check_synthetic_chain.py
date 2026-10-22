"""Actual frozen #8 observer -> integration gate -> unchanged #10 scheduler, SYNTHETIC ONLY."""
import copy,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'issue8'),str(ROOT/'integration')]
from observer import ThermalObserver
from scheduler import Scheduler,resolve_plan
from contracts import readiness
spec=json.loads((ROOT/'issue8/observer-spec.json').read_text());plan=json.loads((ROOT/'issue10/inputs/mix-plan.json').read_text())
profile=resolve_plan(plan,'fixed-anchors');policy=dict(plan['request_policy'],max_data_unready_seconds=60)
base=json.loads((ROOT/'streams/issue8-Y.jsonl').read_text().splitlines()[3])
identity=dict(base['identity'],run_id='SYNTHETIC-INTEGRATION',source_epoch=1)
ident=identity['run_id'];out=[]
for scenario in ['normal','short_gap','long_gap','guard','user_stop','request_unknown']:
 ob=ThermalObserver(spec);q=Scheduler(profile,policy,ident,'SYNTHETIC-'+scenario,formal=False)
 lastfan=None;normal_since=0;rows=[];ever_paused=False;resumed=False
 for t in range(451):
  gap=(scenario=='short_gap' and 330<=t<336) or (scenario=='long_gap' and 330<=t<351)
  f=copy.deepcopy(base);ref=ident+'/observation:'+str(t)
  m=f['measurement'];f['identity']=identity
  for name,x in m.items():
   x['source_ref']=ref;x['observed_mono_s']=float(t);x['observed_utc']='SYNTHETIC'
   x['valid_until_mono_s']=float(t)+{'tj':5,'power':5,'last_successful_pwm':2.5,'control_context':7.5}[name]
   x['age_s']=0.;x['raw_valid']=True
  m['tj']['value_C']=44.+0.0001*t;m['power']['rails_W']=[4.,6.]
  if gap:
   m['last_successful_pwm']=copy.deepcopy(lastfan)
   m['last_successful_pwm']['raw_valid']=t<lastfan['valid_until_mono_s']
   m['last_successful_pwm']['age_s']=t-lastfan['observed_mono_s']
   normal_since=t
  else:lastfan=copy.deepcopy(m['last_successful_pwm'])
  safe=f['safety'];freshfan=m['last_successful_pwm']['raw_valid']
  safe.update(fan_fresh=freshfan,binding_fresh=True,guard=False if freshfan else None,
              fault=False if freshfan else None,mode='auto' if freshfan else None,enabled=True if freshfan else None,
              temp_stale=False if freshfan else None,manual_mode=False,normalized_valid=True,
              active_source='variable',binding='agx_info.temperature.tj',context_changed_this_event=False,
              context_stable_s=float(t-normal_since),confirmed_normal_now=freshfan and t-normal_since>=5)
  if scenario=='guard' and t==330:
   safe['guard']=True;m['last_successful_pwm']['last_observed_flags']['guard_active']=True
  frame=dict(t=float(t),utc='SYNTHETIC',ref=ref,stream_started_mono_s=0.,identity=identity,
             source_reset=t==0,reset_reason='SYNTHETIC_START' if t==0 else None,new_TJ=True,measurement=m,safety=safe)
  s=ob.step(frame)
  env=dict(schema='TTO-OFFLINE-INTEGRATION-R2',upstream=s,expected_identity=identity,
           replay_origin_mono_s=0.,expected_binding='agx_info.temperature.tj',offline_demo_authorized=True,
           transport='no_requests_virtual_replay')
  completed=[]
  for k,v in list(q.pending.items()):
   if t-v['submit_mono_s']>=2:
    status='termination_unknown' if scenario=='request_unknown' and t>=330 else 'completed'
    completed.append(dict(request_id=k,status=status,done=status=='completed',server_state='VIRTUAL_ONLY' if status=='completed' else 'unknown'))
  actions,g=q.tick(t,env,completed,user_stop=scenario=='user_stop' and t==330)
  if 333<=t<=336 and scenario=='short_gap':
   assert not any(x['kind']=='submit' for x in actions);ever_paused=True
  if scenario=='short_gap' and t>341 and any(x['kind']=='submit' for x in actions):resumed=True
  rows.append(dict(t=t,phase=s['observer']['phase'],raw_PWM_valid=m['last_successful_pwm']['raw_valid'],
                   model_available=g['model_available'],start_allowed=g['start_allowed'],actions=actions))
  if q.terminal:break
 if scenario=='short_gap':assert ever_paused and resumed and not q.terminal
 if scenario=='long_gap':
  assert any(r['phase']=='unavailable' for r in rows) and any(r['model_available'] for r in rows if r['t']>360)
 if scenario=='guard':assert q.reason=='explicit_protection_or_mode_binding'
 if scenario=='user_stop':assert q.reason=='user_stop'
 if scenario=='request_unknown':
  assert q.reason=='request_termination_unknown' and q.unknown_requests
  stop=next(e['mono_s'] for e in q.events if e['event']=='stop_new_requests')
  assert not any(e['event']=='request_submit' and e['mono_s']>=stop for e in q.events)
 out.append(dict(scenario=scenario,steps=len(rows),virtual_requests=q.submitted,actual_requests=0,
                 stop_reason=q.reason,unknown=q.unknown_requests,events=q.events,states=rows))
(ROOT/'results/synthetic-chain.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([dict(scenario=x['scenario'],steps=x['steps'],reason=x['stop_reason']) for x in out]))
