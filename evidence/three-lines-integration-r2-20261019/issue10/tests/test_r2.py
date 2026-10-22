import asyncio,copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scheduler import Scheduler,Registry,resolve_plan
from contracts import readiness,StateConsumer
from fixtures import snapshot
from drivers import virtual_run,loopback_run,loopback_only
from mix import scaled_http_profile,main
PLAN=json.loads((ROOT/'inputs/mix-plan.json').read_text())
POLICY=dict(PLAN['request_policy'],max_data_unready_seconds=60)

class R2(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def run_case(self,name='healthy',profile='fixed-anchors',**kw):
  return virtual_run(resolve_plan(PLAN,profile),POLICY,self.root/name,name,run_id=name,command_id=name,**kw)
 def test_budget_and_other_model_inherits(self):
  a=resolve_plan(PLAN,'fixed-anchors');b=resolve_plan(PLAN,'irregular-confirm-after-freeze');c=resolve_plan(PLAN,'same-plan-other-model')
  self.assertEqual(a['budget']['worst_reserved_s'],3450);self.assertEqual(b['budget']['worst_reserved_s'],3420)
  self.assertEqual(a['stages'],c['stages']);self.assertFalse(c['auto_execute_after_previous'])
 def test_full_fixed_schedule_and_drain_before_recovery(self):
  s=self.run_case();self.assertEqual(s.reason,'completed');self.assertEqual(s.peak,4)
  starts=[e for e in s.events if e['event']=='phase_start'];self.assertEqual(len(starts),9)
  for e in starts:
   stage=e['stage']
   if stage['kind']=='work':
    rows=[r for r in s.requests if r['stage_index']==e['index']]
    self.assertTrue(all(r['submit_mono_s']<e['window_end'] for r in rows))
    after=next(x for x in starts if x['index']==e['index']+1)
    self.assertGreaterEqual(after['mono_s'],max(r['client_end_mono_s'] for r in rows))
  for e in s.events:
   if e['event']=='phase_end' and e['kind'] in ('recovery','background','final_recovery'):
    self.assertGreaterEqual(e['elapsed_s'],s.profile['stages'][e['index']]['seconds'])
 def test_irregular_reproducibility(self):
  a=self.run_case('healthy','irregular-confirm-after-freeze');b=virtual_run(resolve_plan(PLAN,'irregular-confirm-after-freeze'),POLICY,self.root/'again','healthy',run_id='again',command_id='again')
  self.assertEqual([(r['stage_index'],r['submit_mono_s'],r['client_end_mono_s']) for r in a.requests],[(r['stage_index'],r['submit_mono_s'],r['client_end_mono_s']) for r in b.requests])
 def test_start_missing_then_recovers(self):
  s=self.run_case('startup');self.assertEqual(s.reason,'completed');self.assertEqual(next(e for e in s.events if e['event']=='phase_start')['mono_s'],20)
 def test_short_gap_continues_collection_and_resumes(self):
  s=self.run_case('short_gap');self.assertEqual(s.reason,'completed')
  self.assertFalse(any(402<=r['submit_mono_s']<415 for r in s.requests))
  self.assertTrue(any(r['submit_mono_s']>=415 for r in s.requests))
 def test_long_gap_stops_separately(self):self.assertEqual(self.run_case('long_gap').reason,'data_or_observer_unavailable_too_long')
 def test_http_timeout_does_not_invalidate_current_TJ(self):
  d=snapshot(400,'run','http_timeout');r=readiness(d,400,'run',False)
  self.assertTrue(r['collection_available']);self.assertTrue(r['start_allowed']);self.assertEqual(d['measurement']['http_status'],'timeout')
 def test_protected_mode_binding_guard_fault(self):
  for kind in ('mode_change','binding_change','guard','fault'):
   with self.subTest(kind=kind):self.assertEqual(self.run_case(kind).reason,'explicit_protection_or_mode_binding')
 def test_unknown_safety_stays_unknown(self):
  d=snapshot(401,'run','unknown_safety');r=readiness(d,401,'run',False);self.assertFalse(r['field_safety_available']);self.assertIsNone(d['safety']['fault'])
 def test_unavailable_estimator_no_formal_start(self):
  for kind in ('unavailable_observer','permission_missing'):
   s=self.run_case(kind);self.assertEqual(s.submitted,0);self.assertEqual(s.reason,'preparation_budget_exhausted')
 def test_estimator_number_is_not_permission(self):
  d=snapshot(0,'run','permission_missing',True);self.assertTrue(readiness(d,0,'run')['model_available']);self.assertFalse(readiness(d,0,'run')['start_allowed'])
 def test_formal_instrument_clock_missing_and_null_error(self):
  d=snapshot(0,'run',formal=True);self.assertTrue(readiness(d,0,'run')['start_allowed']);self.assertIsNone(d['instrument']['uncertainty_s'])
  d['instrument']['start_clock_evidence']=None;self.assertFalse(readiness(d,0,'run')['start_allowed'])
 def test_invalid_PWM_not_renewed_by_estimate(self):
  d=snapshot(410,'run','short_gap');before=copy.deepcopy(d['measurement']);r=readiness(d,410,'run',False)
  self.assertTrue(r['model_available']);self.assertFalse(r['collection_available']);self.assertEqual(d['measurement'],before);self.assertEqual(r['successful_PWM_age_s'],11)
 def test_raw_false_nan_and_future_identity_refused(self):
  for mutate in ('rawfalse','nan','future','wrongrun','observernan','wrongclock'):
   d=snapshot(10,'run')
   if mutate=='rawfalse':d['measurement']['TJ']['raw_valid']=False
   elif mutate=='nan':d['measurement']['TJ']['value']=float('nan')
   elif mutate=='future':d['identity']['observed_until_mono']=11
   elif mutate=='observernan':d['observer']['Tf']=float('nan')
   elif mutate=='wrongclock':d['identity']['clock_domain']='another_host_unmapped_clock'
   else:d['identity']['run_id']='other'
   self.assertFalse(readiness(d,10,'run',False)['start_allowed'])
 def test_state_consumer_one_ordered_stream_no_future(self):
  rows=[snapshot(5,'run'),snapshot(8,'run')];c=StateConsumer(rows);self.assertEqual(c.at(4),{});self.assertIs(c.at(5),rows[0]);self.assertIs(c.at(9),rows[1])
  with self.assertRaises(ValueError):StateConsumer(rows[::-1])
 def test_unknown_completion_no_more_submits(self):
  s=self.run_case(unknown_request='R0001');self.assertEqual(s.reason,'request_termination_unknown');self.assertEqual(s.submitted,1);self.assertTrue(s.unknown_requests)
 def test_timeout_not_server_completion(self):
  s=self.run_case(request_duration=100);self.assertEqual(s.reason,'request_termination_unknown');self.assertEqual(s.requests[0]['server_state'],'unknown')
 def test_user_stop_drains_and_no_restart(self):
  s=self.run_case(user_stop_at=312);self.assertEqual(s.reason,'user_stop');self.assertLess(s.now,500)
  with self.assertRaises(FileExistsError):self.run_case(user_stop_at=312)
 def test_duplicate_run_or_command_claim(self):
  r=Registry(self.root);r.claim('run','cmd')
  with self.assertRaises(FileExistsError):r.claim('run2','cmd')
  with self.assertRaises(FileExistsError):r.claim('run','cmd2')
 def test_request_cap_stops(self):self.assertEqual(self.run_case(max_request_cap=3).reason,'request_count_cap')
 def test_hard_budget_cancels_unknown(self):
  p=resolve_plan(PLAN,'fixed-anchors');p['hard_limit_seconds']=330;p['cleanup_reserve_seconds']=10
  s=virtual_run(p,POLICY,self.root/'hard',request_duration=100,run_id='hard',command_id='hard')
  self.assertEqual(s.reason,'hard_budget_cleanup_boundary');self.assertLessEqual(s.now,330);self.assertIn('R0001',s.unknown_requests);self.assertEqual(len(s.requests),s.submitted);self.assertEqual(s.requests[0]['server_state'],'unknown')
 def test_field_and_nonloopback_requests_are_disabled(self):
  with self.assertRaises(ValueError):main(['execute','--binding','does-not-exist.json'])
  for url in ('http://10.10.99.98:58000','https://example.com','http://localhost:1'):
   with self.assertRaises(ValueError):loopback_only(url)
 def test_observer_has_no_future_schedule_or_measurement_leak(self):
  d=snapshot(100,'run');self.assertNotIn('stages',d['observer']);self.assertNotIn('next_request',d['observer']);self.assertNotIn('future_PWM',d['observer']);self.assertEqual(d['observer']['E_source'],'synthetic_preregistered_new_run_prior_not_ambient')
 def test_vendor_candidate_unchanged(self):
  spec=json.loads((ROOT/'inputs/candidate-artifact-identity.json').read_text())
  self.assertTrue(all(hashlib.sha256((ROOT/'vendor'/k).read_bytes()).hexdigest()==v for k,v in spec['vendor_files'].items()))

class HTTP(unittest.IsolatedAsyncioTestCase):
 async def test_actual_HTTP_SSE_normal(self):
  from fake_http import FakeService
  with tempfile.TemporaryDirectory() as tmp:
   async with FakeService() as service:
    s=await loopback_run(scaled_http_profile(resolve_plan(PLAN,'fixed-anchors')),POLICY,Path(tmp)/'http',service.url)
    self.assertEqual(s.reason,'completed');self.assertEqual(s.peak,4);self.assertGreaterEqual(service.peak,2);self.assertLessEqual(service.peak,4)
    self.assertTrue(all(r['done'] and r['finish_reason']=='length' and r['usage']['completion_tokens']==256 and r['first_content_mono_s'] is not None for r in s.requests))
 async def test_incomplete_SSE_stops_new_requests(self):
  from fake_http import FakeService
  with tempfile.TemporaryDirectory() as tmp:
   async with FakeService('incomplete') as service:
    s=await loopback_run(scaled_http_profile(resolve_plan(PLAN,'fixed-anchors')),POLICY,Path(tmp)/'http',service.url,'incomplete')
    self.assertEqual(s.reason,'request_termination_unknown');self.assertEqual(service.posts,1);self.assertEqual(s.requests[0]['server_status'],'unknown')
 async def test_HTTP503_no_retry(self):
  from fake_http import FakeService
  with tempfile.TemporaryDirectory() as tmp:
   async with FakeService('http503') as service:
    s=await loopback_run(scaled_http_profile(resolve_plan(PLAN,'fixed-anchors')),POLICY,Path(tmp)/'http',service.url,'http503')
    self.assertEqual(s.reason,'request_termination_unknown');self.assertEqual(service.posts,1);self.assertEqual(s.requests[0]['http_status'],503)
 async def test_client_timeout_does_not_prove_server_end(self):
  from fake_http import FakeService
  with tempfile.TemporaryDirectory() as tmp:
   async with FakeService() as service:
    policy=dict(POLICY,max_request_seconds=.04)
    s=await loopback_run(scaled_http_profile(resolve_plan(PLAN,'fixed-anchors')),policy,Path(tmp)/'http',service.url,'timeout')
    self.assertEqual(s.reason,'request_termination_unknown');self.assertEqual(service.posts,1);self.assertEqual(s.requests[0]['server_status'],'unknown')
    self.assertNotEqual(s.requests[0].get('error_class'),None)
if __name__=='__main__':unittest.main()
