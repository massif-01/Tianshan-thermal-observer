"""Deterministic clock regression for external stop, with no device or inference."""
import unittest
from unittest.mock import patch
from tto_field.scheduler import Scheduler

class StopClockTests(unittest.TestCase):
    def setUp(self):
        self.gate=patch('tto_field.scheduler.readiness',return_value={'explicit_stop':False,'start_allowed':True})
        self.gate.start();self.addCleanup(self.gate.stop)
        p=dict(stages=[dict(kind='work',seconds=20,concurrency=1)],hard_limit_seconds=60,
               cleanup_reserve_seconds=5,preparation_reserve_seconds=10,drain_per_work_max_seconds=3)
        self.s=Scheduler(p,dict(max_request_seconds=30,max_total_requests=10,max_data_unready_seconds=60),'RUN','COMMAND')
        a,_=self.s.tick(2.,None);self.assertEqual(len(a),1)
        self.ident=a[0]['request_id']
    def test_external_stop_uses_observation_time_and_drains_from_it(self):
        self.s.stop('collector_exited',now=2.125)
        self.assertEqual(self.s.stopping_at,2.125)
        stop=next(e for e in self.s.events if e['event']=='stop_new_requests')
        self.assertEqual(stop['mono_s'],2.125)
        self.assertLess(self.s.pending[self.ident]['submit_mono_s'],stop['mono_s'])
        a,_=self.s.tick(5.124,None);self.assertEqual(a,[]);self.assertIn(self.ident,self.s.pending)
        a,_=self.s.tick(5.125,None);self.assertEqual(a,[dict(kind='cancel_client',request_id=self.ident)])
        self.assertTrue(self.s.terminal)
        self.assertEqual([e['mono_s'] for e in self.s.events],sorted(e['mono_s'] for e in self.s.events))
    def test_repeated_notification_keeps_first_stop_and_natural_completion(self):
        self.s.stop('collector_exited',now=2.125)
        self.s.stop('collector_or_signal_stop',now=2.2)
        self.assertEqual(self.s.stopping_at,2.125);self.assertEqual(self.s.reason,'collector_exited')
        a,_=self.s.tick(2.3,None,[dict(request_id=self.ident,status='completed')])
        self.assertEqual(a,[]);self.assertTrue(self.s.terminal);self.assertFalse(self.s.unknown_requests)
        self.assertEqual(sum(e['event']=='stop_new_requests' for e in self.s.events),1)
    def test_missing_or_backwards_time_is_rejected(self):
        with self.assertRaises(TypeError):self.s.stop('collector_exited')
        with self.assertRaisesRegex(ValueError,'monotonic'):self.s.stop('collector_exited',now=1.9)
        self.assertIsNone(self.s.reason)
    def test_tick_internal_stop_also_uses_current_time(self):
        self.s.tick(2.125,None,user_stop=True)
        self.assertEqual(self.s.stopping_at,2.125)
        self.assertEqual(next(e for e in self.s.events if e['event']=='stop_new_requests')['mono_s'],2.125)

if __name__=='__main__':unittest.main()
