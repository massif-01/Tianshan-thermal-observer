"""Owned in-memory SSE fixtures and virtual clock. Never used by field runtime."""
import asyncio
from datetime import datetime, timedelta, timezone
import heapq
import json
from pathlib import Path
from vendor.requester import Requester

class VirtualClock:
    def __init__(self, start=0):
        self.value = start
        self.pending = []
        self.serial = 0
        self.scheduled = False
    def now(self):
        return self.value
    def utc(self):
        return (datetime(2026,10,22,tzinfo=timezone.utc)+timedelta(seconds=self.value)).isoformat()
    async def sleep(self, seconds):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.serial += 1
        heapq.heappush(self.pending,(self.value+seconds,self.serial,future))
        self._schedule()
        await future
    def _schedule(self):
        if not self.scheduled:
            self.scheduled = True
            asyncio.get_running_loop().call_later(0,self._advance)
    def _advance(self):
        self.scheduled = False
        while self.pending and self.pending[0][2].done():
            heapq.heappop(self.pending)
        if not self.pending: return
        self.value=max(self.value,self.pending[0][0])
        while self.pending and self.pending[0][0]<=self.value:
            _,_,future=heapq.heappop(self.pending)
            if not future.done(): future.set_result(None)
        # Sleepers awakened at this instant get a turn before advancing time again.
        if self.pending: self._schedule()

class Response:
    status=200
    def __init__(self, clock, mode, duration, number):
        self.clock,self.mode,self.duration,self.number=clock,mode,duration,number
        self.content=self
    async def __aenter__(self): return self
    async def __aexit__(self,*args): return False
    def __aiter__(self): return self.lines()
    async def lines(self):
        if self.mode=='hang':
            await asyncio.Event().wait()
        await self.clock.sleep(self.duration)
        ident=f'synthetic-chat-{self.number}'
        yield ('data: '+json.dumps(dict(id=ident,choices=[dict(delta=dict(reasoning_content='synthetic reasoning'),finish_reason=None)]))+'\n').encode()
        yield ('data: '+json.dumps(dict(id=ident,choices=[dict(delta=dict(content='synthetic text'),finish_reason=None)]))+'\n').encode()
        if self.mode=='truncated': return
        yield ('data: '+json.dumps(dict(id=ident,choices=[dict(delta={},finish_reason='length' if self.number%2==0 else 'stop')]))+'\n').encode()
        yield ('data: '+json.dumps(dict(id=ident,choices=[],usage=dict(prompt_tokens=12,completion_tokens=16,total_tokens=28)))+'\n').encode()
        yield b'data: [DONE]\n'

class MemorySession:
    def __init__(self, clock, mode='complete', duration=3):
        self.clock,self.mode,self.duration=clock,mode,duration
        self.posts=[]
        self.closed=False
        self.active=0
    def post(self, url, *, data, headers, allow_redirects):
        assert url=='http://synthetic.invalid/v1/chat/completions'
        assert not allow_redirects
        self.posts.append(json.loads(data))
        return Response(self.clock,self.mode,self.duration,len(self.posts))
    async def close(self): self.closed=True

def make_requester(out, clock, mode='complete', duration=3):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    r=Requester(dict(base_url='http://synthetic.invalid',model='synthetic-resident-model',
                     messages=[],stream=True,sampling={},max_tokens=256,request_timeout_s=30),out,clock,lambda *a,**k:None)
    r.session=MemorySession(clock,mode,duration);r.headers={}
    return r

BINDING=dict(native_run_id='synthetic-native-run',observer_session_id='synthetic-observe-session',
             device_id='synthetic-device',config_sha256='synthetic-config',
             clock_domain='synthetic-observer-origin-domain')

class Journal:
    def __init__(self, out=None):
        self.rows=[];self.out=Path(out) if out else None
        if self.out: self.out.mkdir(parents=True,exist_ok=True)
    def __call__(self,event,row):
        self.rows.append((event,row))
        if self.out:
            name='workload-events.jsonl' if event=='workload_event' else 'protocol.jsonl'
            with (self.out/name).open('a',encoding='utf8') as f:
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
