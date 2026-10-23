import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from make_plan import generate,plan_digest
from runner import Runner,Control
from fixtures.fake_runtime import VirtualClock,make_requester,Journal,BINDING

def selected(times, **budget):
    p=generate();base=p['slots'][0]
    p['slots']=[dict(base,slot_id=f'T{i:04d}',planned_submit_s=t,latest_submit_s=min(t+5,84570),issue_window_end_s=84600 if t>=64800 else 21600,stage_id='irregular_mix' if t>=64800 else 'sparse_qa') for i,t in enumerate(times)]
    p.update(budget);p['plan_sha256']=plan_digest(p);return p

class PlanTests(unittest.TestCase):
    def test_frozen_reproducibility_and_rest(self):
        p=generate();self.assertEqual(p,generate());self.assertEqual(p,json.loads((ROOT/'frozen-plan.json').read_text()))
        self.assertEqual(p['plan_sha256'],plan_digest(p));self.assertEqual(len(p['slots']),386)
        self.assertEqual(len({x['task_id'] for x in p['slots']}),8)
        self.assertTrue(all(7200<=s['planned_submit_s']<=84570 and not 32400<=s['planned_submit_s']<64800 for s in p['slots']))

class RunTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().set_debug(False)

    async def run_case(self,plan=None,*,start=0,mode='complete',duration=3,admission=None,stop=None,paused=None,journal=None):
        clock=VirtualClock(start);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        r=make_requester(tmp.name,clock,mode,duration);sink=journal or Journal()
        control=Control(BINDING.copy(),stop=(lambda:stop(clock)) if stop else lambda:False,paused=(lambda:paused(clock)) if paused else lambda:False)
        gate=(lambda:admission(clock)) if admission else lambda:dict(action='allow',reasons=[])
        driver=Runner(clock,r,plan or selected([7200]),gate,sink,control)
        summary=await driver.run()
        self.assertTrue(r.session.closed)
        return summary,sink,r,driver

    async def test_full_day_actual_requester_emit_and_no_network(self):
        with patch('socket.create_connection',side_effect=AssertionError('network prohibited')):
            summary,sink,r,_=await self.run_case(generate())
        self.assertEqual(summary['reason'],'completed');self.assertEqual(summary['actual_elapsed_s'],86400)
        self.assertLessEqual(summary['submissions'],600);self.assertLessEqual(summary['client_inflight_seconds'],18000)
        self.assertEqual(summary['submissions'],summary['protocol_completed'])
        self.assertTrue(all(x['max_tokens']==256 and x['stream'] and x['stream_options']=={'include_usage':True} for x in r.session.posts))
        raw=[r for e,r in sink.rows if e=='request_submit'];normalized=[r for e,r in sink.rows if e=='workload_event']
        self.assertEqual(len(raw),summary['submissions']);self.assertTrue(all('planned_submit_s' in x and 'actual_elapsed_s' in x for x in raw))
        self.assertTrue(all(not any(k in x for k in ['slots','seed','planned_submit_s','issue_window_end_s']) for x in normalized))
        self.assertEqual(max(x['client_inflight'] for x in normalized),1)
        self.assertTrue(all(x['gpu_kernel_start'] is None and x['gpu_kernel_end'] is None for x in normalized))
        self.assertTrue(all(x['session_id']==BINDING['native_run_id'] for x in normalized))
        self.assertEqual({x['current_stage'] for e,x in sink.rows if e=='stage_observed'},{s['id'] for s in generate()['stages']})

    async def test_pause_skips_then_resumes_no_extension(self):
        s,sink,_,_=await self.run_case(selected([7200,7225,7300]),paused=lambda c:7200<=c.now()<7220)
        self.assertEqual((s['submissions'],s['skipped_opportunities']),(2,1));self.assertEqual(s['actual_elapsed_s'],86400)
        submits=[x['mono_s'] for e,x in sink.rows if e=='request_submit'];self.assertEqual(submits,[7225,7300])

    async def test_pause_grace_stops_after_sixty(self):
        s,_,_,_=await self.run_case(paused=lambda c:c.now()>=7200)
        self.assertEqual((s['reason'],s['submissions']),('unready_grace_exhausted',0))
        self.assertGreaterEqual(s['actual_elapsed_s'],7260);self.assertLessEqual(s['actual_elapsed_s'],7261)

    async def test_background_health_pending_then_automatic_allow(self):
        s,_,_,_=await self.run_case(admission=lambda c:dict(action='pause' if c.now()<7200 else 'allow',reasons=['health_checkpoint_pending'] if c.now()<7200 else []))
        self.assertEqual(s['reason'],'completed');self.assertEqual(s['submissions'],1)

    async def test_stop_in_background(self):
        s,_,_,_=await self.run_case(stop=lambda c:c.now()>=100)
        self.assertEqual((s['reason'],s['submissions'],s['actual_elapsed_s']),('user_stop',0,100))

    async def test_stop_before_queued_request_starts(self):
        count=0
        def gate(clock):
            nonlocal count
            count+=1
            return dict(action='allow' if count<3 else 'stop',reasons=['observer_exited'])
        s,_,r,_=await self.run_case(start=7200,admission=gate)
        self.assertEqual(s['submissions'],0)
        self.assertEqual(len(r.session.posts),0)

    async def test_stop_inflight_natural_drain(self):
        s,sink,_,_=await self.run_case(selected([7200,7250]),start=7200,duration=10,stop=lambda c:c.now()>=7202)
        self.assertEqual(s['reason'],'user_stop');self.assertEqual(s['submissions'],1);self.assertEqual(s['protocol_completed'],1)
        self.assertFalse(s['unknown_server_end']);self.assertFalse(any(e=='request_cancel' for e,_ in sink.rows))

    async def test_observer_exit_stops_new_work_with_original_drain(self):
        s,_,_,_=await self.run_case(selected([7200,7250]),start=7200,duration=8,admission=lambda c:dict(action='stop' if c.now()>=7202 else 'allow',reasons=['observer_exited']))
        self.assertTrue(s['reason'].startswith('admission_stop:observer_exited'));self.assertEqual(s['submissions'],1)

    async def test_truncated_unknown_no_retry(self):
        s,sink,_,_=await self.run_case(selected([7200,7250]),start=7200,mode='truncated')
        self.assertEqual(s['reason'],'protocol_end_unknown_no_retry');self.assertEqual(s['submissions'],1)
        self.assertTrue(s['unknown_server_end'])
        self.assertEqual([r['terminal'] for e,r in sink.rows if e=='workload_event' and r['event']=='request_end'],['client_ended_server_end_unknown'])

    async def test_protocol_thirty_second_deadline(self):
        s,sink,_,_=await self.run_case(selected([7200,7250]),start=7200,mode='hang')
        self.assertEqual(s['submissions'],1);self.assertTrue(s['unknown_server_end']);self.assertLessEqual(s['client_inflight_seconds'],30)
        self.assertEqual(sum(e=='request_cancel' for e,r in sink.rows),1)

    async def test_submission_ceiling_includes_failure(self):
        s,_,_,_=await self.run_case(selected([7200,7250],max_submissions=1),start=7200)
        self.assertEqual((s['submissions'],s['reason']),(1,'request_budget_exhausted'))
        s,_,_,_=await self.run_case(selected([7200,7250],max_submissions=1),start=7200,mode='truncated')
        self.assertEqual(s['submissions'],1)

    async def test_client_budget_reserved_not_shortened(self):
        s,_,_,_=await self.run_case(selected([7200,7250],max_client_inflight_seconds=31),start=7200,duration=3)
        self.assertEqual((s['submissions'],s['reason']),(1,'request_budget_exhausted'))

    async def test_busy_slots_are_skipped_no_catchup(self):
        s,sink,_,_=await self.run_case(selected([7200,7205,7210,7250]),start=7200,duration=20)
        self.assertEqual((s['submissions'],s['skipped_opportunities']),(2,2))
        self.assertEqual([r['mono_s'] for e,r in sink.rows if e=='request_submit'],[7200,7250])

    async def test_final_recovery_and_late_start_no_catchup(self):
        s,sink,_,_=await self.run_case(selected([7200,84570]),start=84570,duration=5)
        self.assertEqual(s['submissions'],1);self.assertEqual(s['actual_elapsed_s'],86400)
        self.assertEqual([x['mono_s'] for e,x in sink.rows if e=='request_submit'],[84570])

    async def test_reject_changed_plan_or_identity(self):
        p=selected([7200]);p['max_submissions']=601
        with self.assertRaises(ValueError): await self.run_case(p)
        p['plan_sha256']=plan_digest(p)
        with self.assertRaises(ValueError): await self.run_case(p)
        with tempfile.TemporaryDirectory() as tmp:
            c=VirtualClock();r=make_requester(tmp,c)
            with self.assertRaises(ValueError): Runner(c,r,selected([7200]),lambda:dict(action='allow'),Journal(),Control({}))

if __name__=='__main__': unittest.main()
