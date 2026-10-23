"""Candidate TrialHealth -> candidate run_schedule, synthetic stream and requester only."""
import sys,json,asyncio
from pathlib import Path
b=Path(__file__).resolve().parents[1];c=b/'candidate/code'
sys.path[:0]=[str(c/'scripts/thermal_trials'),str(c/'tests')]
from health import TrialHealth
from trial import run_schedule
from test_platform_curve import new_packet
from tto.config import load_config
from tto.engine import engine_for
from tto.demo import fan_packet,temp_packet

e=engine_for(load_config(environ={}),record_schema=2);health=TrialHealth();last_accepted=None
for t in range(132):
    p=new_packet(t+1)
    if t>=71:p['temperature'].pop('tj')
    for kind,payload in [('fan',fan_packet(19)),('temp',temp_packet()),('orin',p)]:
        r=dict(kind=kind,payload=payload,mono_s=float(t),ref=f'synthetic/{kind}/{t}',observer_run_id='review-synthetic',connection_epoch=1)
        o=e.process(r);health.observe(r,o,e)
        if o['quality'] and o['quality']['accepted']:last_accepted=t
class Clock:
    t=131.0
    def now(self):return self.t
    async def sleep(self,seconds):self.t+=seconds;await asyncio.sleep(0)
class Requester:
    def __init__(self,clock):self.clock=clock;self.calls=[]
    async def request(self,ident,timeout_s):
        self.calls.append({'id':ident,'t':self.clock.now(),'last_accepted_TJ_t':last_accepted})
        await self.clock.sleep(.2)
        return {'status':'completed','client_end_mono_s':self.clock.now()}
async def main():
    clock=Clock();requester=Requester(clock);events=[];stop=asyncio.Event();collector=asyncio.create_task(stop.wait())
    try:
        result=await run_schedule(clock,health,requester,stop,collector,lambda event,**fields:events.append(dict(event=event,**fields)),
                                  phases=[('review-shortened-work','work',.15)],hard_limit_s=10,start_mono=clock.now())
    finally:stop.set();await collector
    output={'scope':'synthetic records; real candidate health and scheduler; fake requester and clock; no sockets',
            'last_accepted_TJ_t':last_accepted,'calls':requester.calls,'schedule_result':result,'events':events}
    (b/'results/readiness-to-request.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'last_accepted_TJ_t':last_accepted,'calls':requester.calls,'status':result['status']},indent=2))
    assert requester.calls and requester.calls[0]['t']-last_accepted>60
    print('COUNTEREXAMPLE CONFIRMED: production scheduling admitted work after >60 seconds without valid new TJ.')
asyncio.run(main())
