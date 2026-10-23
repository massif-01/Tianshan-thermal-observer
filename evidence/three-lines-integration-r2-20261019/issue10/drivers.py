"""Virtual full-plan driver and bounded loopback driver; no device URLs accepted."""
import asyncio,copy,hashlib,heapq,importlib.util,json,random,sys,time,datetime,ipaddress
from pathlib import Path
from urllib.parse import urlsplit
from scheduler import Scheduler,Registry
from fixtures import snapshot
from contracts import StateConsumer
ROOT=Path(__file__).resolve().parent
SEED=61018010
SCHEDULING_POLICY=json.loads((ROOT/'execution-policy.json').read_text())

def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def write_lines(p,rows):p.write_text(''.join(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n' for x in rows))
def save_result(out,s,extra):
    out.mkdir(parents=True,exist_ok=True);write_lines(out/'events.jsonl',s.events);write_lines(out/'requests.jsonl',s.requests)
    write(out/'summary.json',dict(mode='offline_synthetic_not_field',reason=s.reason,elapsed_mono_s=s.now,requests=s.submitted,
                                 completed=sum(r['status']=='completed' for r in s.requests),peak_client_inflight=s.peak,
                                 unknown_server_completions=s.unknown_requests,collector_count=1,request_executor_count=1,**extra))

def virtual_run(profile,policy,out,scenario='healthy',seed=SEED,run_id='mock-run',command_id='mock-command',
                request_duration=None,unknown_request=None,user_stop_at=None,max_request_cap=None):
    out=Path(out);Registry(out.parent/'command-ledger').claim(run_id,command_id)
    if out.exists():raise FileExistsError('Fresh output only')
    out.mkdir()
    stream_path=out/'single-stream-fixture.jsonl'
    write_lines(stream_path,[snapshot(float(t),run_id,scenario) for t in range(int(profile['hard_limit_seconds'])+1)])
    source=StateConsumer.from_jsonl(stream_path)
    policy=dict(policy,max_data_unready_seconds=SCHEDULING_POLICY['unready_grace_seconds'])
    if max_request_cap is not None:policy['max_total_requests']=max_request_cap
    s=Scheduler(profile,policy,run_id,command_id);pending=[];rng=random.Random(seed);now=0.;snapshots=[]
    while not s.terminal:
        completed=[]
        while pending and pending[0][0]<=now:
            end,ident,row=heapq.heappop(pending);completed.append(row)
        state=source.at(now);actions,gate=s.tick(now,state,completed,user_stop_at is not None and now>=user_stop_at)
        if not snapshots or now%30==0 or actions:snapshots.append(state)
        for a in actions:
            if a['kind']=='submit':
                duration=request_duration if request_duration is not None else rng.randint(12,22)
                unknown=(a['request_id']==unknown_request or duration>a['timeout_s'])
                wall=min(duration,a['timeout_s']);result=dict(request_id=a['request_id'],status='termination_unknown' if unknown else 'completed',
                    client_end_mono_s=now+wall,first_content_mono_s=None if unknown else now+.5,finish_reason=None if unknown else 'length',
                    done=not unknown,usage=None if unknown else {'completion_tokens':256},server_state='unknown' if unknown else 'protocol_completion_observed')
                heapq.heappush(pending,(now+wall,a['request_id'],result))
            elif a['kind']=='cancel_client':pending=[x for x in pending if x[1]!=a['request_id']];heapq.heapify(pending)
        now+=1
        if now>profile['hard_limit_seconds']+1:raise AssertionError('Scheduler exceeded hard clock')
    save_result(out,s,{'scenario':scenario,'seed':seed,'fixture_source':'#8/#9 contract mock; upstream implementations not reviewed',
                       'request_durations':'synthetic fixed or seeded, not a measured model performance',
                       'plan_sha256':hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest()})
    write(out/'stream-proof.json',{'producer_count':1,'consumer_path':str(stream_path),'stream_sha256':hashlib.sha256(stream_path.read_bytes()).hexdigest(),'no_extra_board_polling':True,'only_as_of_rows_exposed':True})
    return s

class Clock:
    def __init__(self):self.start=time.monotonic()
    def now(self):return time.monotonic()-self.start
    def utc(self):return datetime.datetime.now(datetime.timezone.utc).isoformat()

def reused_requester():
    sys.path.insert(0,str(ROOT/'vendor/runtime024'))
    import tto
    if tto.__version__!='0.2.4' or not Path(tto.__file__).resolve().is_relative_to((ROOT/'vendor/runtime024').resolve()):raise ValueError('Wrong candidate runtime identity')
    spec=importlib.util.spec_from_file_location('reused024_requester',ROOT/'vendor/thermal_trials/requester.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Requester

def loopback_only(url):
    u=urlsplit(url)
    if u.scheme!='http' or not u.hostname or not ipaddress.ip_address(u.hostname).is_loopback:raise ValueError('Only numeric loopback fixture URLs permitted')
    return url

async def loopback_run(profile,policy,out,service,behavior='normal',run_id='http-mock',command_id='http-command'):
    out=Path(out);Registry(out.parent/'command-ledger').claim(run_id,command_id);out.mkdir()
    stream_path=out/'single-stream-fixture.jsonl'
    write_lines(stream_path,[snapshot(t/200.,run_id) for t in range(int(profile['hard_limit_seconds']*200)+1)])
    source=StateConsumer.from_jsonl(stream_path)
    clock=Clock();s=Scheduler(profile,dict(policy,max_data_unready_seconds=SCHEDULING_POLICY['unready_grace_seconds']),run_id,command_id);Requester=reused_requester()
    config=dict(base_url=loopback_only(service),headers_file=None,ca_file=None,model='SIMULATED-MODEL',
                messages=[{'role':'user','content':'SYNTHETIC ONLY: bounded test.'}],stream=True,sampling={})
    protocol=[]
    def emit(name,**details):protocol.append(dict(event=name,at_mono_s=clock.now(),**details))
    clients=[Requester(config,out,clock,emit) for _ in range(4)];tasks={};results=[]
    try:
        for client in clients:await client.open()
        await asyncio.wait_for(clients[0].check_resident_idle(),max(.001,profile['hard_limit_seconds']-profile['cleanup_reserve_seconds']-clock.now()))
        while not s.terminal:
            completed=[]
            for ident,task in list(tasks.items()):
                if task.done():
                    completed.append(task.result());del tasks[ident]
            now=clock.now();actions,gate=s.tick(now,source.at(now),completed)
            for a in actions:
                if a['kind']=='submit':
                    tasks[a['request_id']]=asyncio.create_task(clients[a['slot']].request(a['request_id'],min(a['timeout_s'],max(.001,profile['hard_limit_seconds']-profile['cleanup_reserve_seconds']-clock.now()))))
                else:
                    task=tasks.pop(a['request_id']);task.cancel();await asyncio.gather(task,return_exceptions=True)
            await asyncio.sleep(.005)
    finally:
        for task in tasks.values():task.cancel()
        await asyncio.gather(*tasks.values(),return_exceptions=True)
        for client in clients:await client.close()
    save_result(out,s,{'scenario':behavior,'transport':'real HTTP/SSE to loopback only','reused_requester_sha256':hashlib.sha256((ROOT/'vendor/thermal_trials/requester.py').read_bytes()).hexdigest()})
    write_lines(out/'protocol-events.jsonl',protocol)
    return s
