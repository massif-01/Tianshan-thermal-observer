"""Actual unchanged observe.2 + delegated Runner/Requester + live self-owned SSE.
Only the injected TEST clock starts at 7200; real field Clock and wheel are untouched.
Gate uses actual live observer/host times. Shift is explicit and NOT a field timing claim.
"""
import asyncio,json,sys,time,uuid,socket
from pathlib import Path
from datetime import datetime,timedelta,timezone
from aiohttp import web
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'executor'))
from program import Clock
from admission import evaluate
from supervision import read_json
from runner import Runner,Control
from vendor.requester import Requester
sys.path.insert(0,str(Path(__file__).parent))
from fake_source import FakeSource

class Source(FakeSource):
    def __init__(self):super().__init__();self.mode='complete';self.api_calls=0
    async def inference(self,r):
        self.api_calls+=1;payload=await r.json();assert payload['max_tokens']==256 and payload['stream']
        response=web.StreamResponse(headers={'Content-Type':'text/event-stream'});await response.prepare(r)
        for row in [dict(id='owned-response',choices=[dict(delta=dict(content='测试内容'),finish_reason=None)]),dict(id='owned-response',choices=[dict(delta={},finish_reason='stop')],usage=dict(prompt_tokens=12,completion_tokens=4,total_tokens=16))]:
            await response.write(('data: '+json.dumps(row)+'\n\n').encode());await asyncio.sleep(.1)
        if self.api_calls==1:await response.write(b'data: [DONE]\n\n')
        await response.write_eof();return response

async def main(prefix,out):
    out.mkdir();start_receipts=[]
    async with Source() as src:
        # FakeSource app is frozen after startup; register the request API on a second owned app.
        app=web.Application();app.router.add_post('/v1/chat/completions',src.inference);api=web.AppRunner(app);await api.setup();site=web.TCPSite(api,'127.0.0.1',0);await site.start();url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        cfg=dict(orin=dict(base_url=src.url,source_sample_interval_ms=1000,source_interval_evidence='owned synthetic source'),tianshan=dict(base_url=src.url))
        reg=dict(device_id='joint-owned',thermal_config_id='joint-owned-config',session_id=str(uuid.uuid4()),observer_host_id=socket.gethostname())
        c=out/'config.json';c.write_text(json.dumps(cfg));rr=out/'registration.json';rr.write_text(json.dumps(reg));entry=prefix/'bin/tto-observe'
        p=await asyncio.create_subprocess_exec(str(entry),'preview','--config',str(c),'--registration',str(rr),'--duration','35',stdout=asyncio.subprocess.PIPE);data,_=await p.communicate();assert p.returncode==0
        grant=json.loads(data)['grant_template'];now=datetime.now(timezone.utc);grant.update(explicit_user_start=True,evidence='OWNED LOOPBACK ONLY',self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=90)).isoformat());g=out/'observe-grant.json';g.write_text(json.dumps(grant));run=out/'observe'
        with (out/'observe.stdout').open('wb') as stdout,(out/'observe.stderr').open('wb') as stderr:
            child=await asyncio.create_subprocess_exec(str(entry),'observe','--config',str(c),'--registration',str(rr),'--grant',str(g),'--duration','35','--output',str(run),'--allow-network','--local-loopback',stdout=stdout,stderr=stderr)
        try:
            ready=None;wall=time.monotonic()
            while time.monotonic()-wall<20:
                await asyncio.sleep(.2)
                if (run/'launch.json').exists() and (run/'status.json').exists():
                    launch=read_json(run/'launch.json');st=read_json(run/'status.json');ident={k:launch['registration'][k] for k in ('device_id','thermal_config_id','session_id','observer_host_id','boot_id')};ident.update(model_sha256='dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0',spec_sha256='2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b')
                    ready=evaluate(launch,st,time.monotonic(),ident,alive=child.returncode is None,process_created=launch['process_created'])
                    if ready['action']=='allow':break
            assert ready and ready['action']=='allow',ready
            raw_events=[]
            class InjectedTestClock:
                def __init__(self):self.start=time.monotonic();self.offset=7200
                def now(self):return time.monotonic()-self.start+self.offset
                def utc(self):return datetime.now(timezone.utc).isoformat()
                async def sleep(self,seconds):await asyncio.sleep(seconds)
            clk=InjectedTestClock()
            binding=dict(observer_session_id=reg['session_id'],native_run_id=st['native_run_id'],device_id=reg['device_id'],config_sha256=launch['config_sha256'],clock_domain='synthetic-test-shifted-relative-only')
            def admission():return evaluate(launch,read_json(run/'status.json'),time.monotonic(),ident,alive=child.returncode is None,process_created=launch['process_created'])
            def emit(e,row):raw_events.append(dict(event=e,row=row))
            requester=Requester(dict(model='OWNED-MOCK',base_url=url,stream=True,sampling={}),out,clk,lambda *a,**k:None)
            original_request=requester.request
            async def requested(*args,**kwargs):
                result=await original_request(*args,**kwargs)
                if src.api_calls==1:clk.offset+=7646-clk.now() # TEST-only jump after the real first end
                return result
            requester.request=requested
            driver=Runner(clk,requester,read_json(HERE/'executor/frozen-plan.json'),admission,emit,Control(binding))
            result=await asyncio.wait_for(driver.run(),10);results=[result]
            assert result['protocol_completed']==1 and result['submissions']==2 and result['unknown_server_end'] and result['reason']=='protocol_end_unknown_no_retry'
            assert src.api_calls==2 and src.model_gets==0
            (out/'actual-emits.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in raw_events))
            (out/'joint-receipt.json').write_text(json.dumps(dict(scope=__doc__,observer_version=launch['version'],native_run_id=st['native_run_id'],same_live_observer_gate=ready,api_requests=src.api_calls,model_queries=0,results=results,second_collector=False,future_plan_sent_to_observer=False),ensure_ascii=False,indent=2)+'\n')
        finally:
            if child.returncode is None:child.terminate();await asyncio.wait_for(child.wait(),10)
            await api.cleanup()
        assert child.returncode==0
        p=await asyncio.create_subprocess_exec(str(entry),'archive','--session',str(run),'--output',str(out/'observe.zip'),stdout=asyncio.subprocess.PIPE);data,_=await p.communicate();assert p.returncode==0;(out/'archive-receipt.json').write_bytes(data)
    print('joint real source, gate, two SSE cases and archive passed')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
