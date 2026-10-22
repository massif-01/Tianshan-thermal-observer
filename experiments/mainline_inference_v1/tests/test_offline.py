import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from events import Adapter
from supplement import run

def event(kind, mono=1, rid='a', **extra):
    return dict(event=kind, mono_s=mono, native_run_id='s', request_id=rid, **extra)

class Events(unittest.TestCase):
    def adapter(self, complete=True):
        return Adapter(session_id='s', source_clock_domain='source',observer_clock_domain='observer',complete_from_session_start=complete)
    def test_causal_prefix_and_duplicates(self):
        a=self.adapter();r=event('request_submit')
        self.assertEqual(a.feed(r)['client_inflight'],1);self.assertIsNone(a.feed(r))
        self.assertEqual(a.feed(event('first_content',2))['client_inflight'],1)
        end=a.feed(event('request_end',3,status='completed',done=True,finish_reason='length'))
        self.assertEqual((end['client_inflight'],end['terminal']),(0,'protocol_completed'))
        self.assertIsNone(end['gpu_kernel_end'])
    def test_cancel_not_server_end(self):
        a=self.adapter();a.feed(event('request_submit'))
        self.assertEqual(a.feed(event('request_cancel',2))['client_inflight'],1)
        end=a.feed(event('request_end',3,error_class='CancelledError'))
        self.assertEqual(end['terminal'],'client_cancelled_server_end_unknown')
        self.assertEqual(end['client_inflight'],0)
    def test_absent_or_midstream_unknown(self):
        self.assertIsNone(self.adapter(False).feed(event('request_submit'))['client_inflight'])
        self.assertIsNone(self.adapter().feed(event('request_end'))['client_inflight'])
    def test_gap_does_not_restore_zero(self):
        a=self.adapter();a.feed(event('request_submit'));a.unavailable('gap')
        self.assertIsNone(a.feed(event('request_end',2))['client_inflight'])
    def test_late_and_wrong_identity(self):
        a=self.adapter();a.feed(event('request_submit',3))
        self.assertEqual(a.feed(event('first_content',2))['reason'],'out_of_order_source_event')
        r=event('request_end',4);r['native_run_id']='other'
        self.assertIsNone(a.feed(r)['client_inflight'])
    def test_missing_finish_is_unknown(self):
        a=self.adapter();a.feed(event('request_submit'))
        self.assertEqual(a.feed(event('request_end',2,status='completed',done=True))['terminal'],'client_ended_server_end_unknown')

class Clock:
    def now(self): return time.monotonic()
    def utc(self): return 'synthetic-clock'
class Content:
    def __init__(self, lines): self.lines=lines
    def __aiter__(self): return self.iterate()
    async def iterate(self):
        for line in self.lines:
            await asyncio.sleep(0)
            yield line.encode()
class Response:
    status=200
    def __init__(self, lines): self.content=Content(lines)
    async def __aenter__(self): return self
    async def __aexit__(self,*args): pass
class Session:
    def __init__(self,lines): self.lines=lines
    def post(self,*args,**kwargs): return Response(self.lines)

spec=importlib.util.spec_from_file_location('accepted_requester',ROOT/'reference/requester.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class RequesterFixtures(unittest.IsolatedAsyncioTestCase):
    async def check(self,filename):
        events=[]
        with tempfile.TemporaryDirectory() as tmp:
            requester=module.Requester(dict(base_url='http://synthetic.invalid',model='fixture',messages=[]),tmp,Clock(),lambda e,**k:events.append(dict(event=e,**k)))
            requester.headers={};requester.session=Session((ROOT/'fixtures'/filename).read_text().splitlines(True))
            record=await requester.request('fixture')
        return record,events
    async def test_complete_SSE_same_Requester(self):
        record,events=await self.check('complete.sse')
        self.assertEqual(record['status'],'completed');self.assertTrue(record['done'])
        self.assertEqual(sum(e['event']=='first_content' for e in events),1)
    async def test_truncated_SSE_unknown_same_Requester(self):
        record,_=await self.check('truncated.sse')
        self.assertEqual(record['status'],'termination_unknown')
        self.assertEqual(record['error_class'],'ValueError')

class Scenario(unittest.IsolatedAsyncioTestCase):
    async def check(self,unknown=False,gate=lambda:True):
        class Virtual:
            value=0
            def now(self): return self.value
            async def sleep(self,seconds): self.value+=seconds; await asyncio.sleep(0)
        class Requester:
            calls=0
            async def request(self,*args,**kwargs):
                self.calls+=1
                return dict(status='termination_unknown' if unknown else 'completed',done=not unknown,finish_reason='length' if not unknown else None)
        clock=Virtual();requester=Requester();events=[]
        await run(requester,gate=gate,stop=lambda:False,emit=lambda e,**k:events.append(dict(event=e,**k)),now=clock.now,sleep=clock.sleep)
        return requester,events,clock
    async def test_bounded_single_client(self):
        r,events,clock=await self.check()
        self.assertEqual(r.calls,24);self.assertEqual(events[-1]['reason'],'completed');self.assertEqual(clock.value,1140)
    async def test_unknown_stops_no_retry(self):
        r,events,_=await self.check(True)
        self.assertEqual(r.calls,1);self.assertEqual(events[-1]['reason'],'protocol_end_unknown_no_retry')
    async def test_inflight_cancelled_when_gate_lost(self):
        class V:
            value=0
            def now(self): return self.value
            async def sleep(self,seconds): self.value+=seconds; await asyncio.sleep(0)
        class WaitingRequester:
            cancelled=False
            async def request(self,*args,**kwargs):
                try: await asyncio.Event().wait()
                finally: self.cancelled=True
        v=V();r=WaitingRequester();events=[]
        await run(r,gate=lambda:v.value<302,stop=lambda:False,
                  emit=lambda e,**k:events.append(dict(event=e,**k)),now=v.now,sleep=v.sleep)
        self.assertTrue(r.cancelled)
        self.assertEqual(events[-1]['reason'],'stop_or_gate_or_deadline_server_end_unknown')

    async def test_old_gate_required(self):
        with self.assertRaises(ValueError): await self.check(gate=lambda:False)

if __name__=='__main__': unittest.main()
