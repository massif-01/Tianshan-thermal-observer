"""Execute unchanged nested esp32 bodies with real loopback HTTP.
This does NOT test Socket.IO or claim full collect() integration coverage.
"""
import ast,asyncio,json,time,textwrap,hashlib,contextlib
from pathlib import Path
from aiohttp import web
from tto.collector import sessions
from tto.config import load_config,headers
from tto.demo import fan_packet,temp_packet
b=Path(__file__).resolve().parents[1]

def extract(path):
    text=path.read_text();tree=ast.parse(text)
    outer=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='collect')
    fn=next(n for n in ast.walk(outer) if isinstance(n,ast.AsyncFunctionDef) and n.name=='esp32')
    body=textwrap.dedent('\n'.join(text.splitlines()[fn.lineno-1:fn.end_lineno]))
    wrapper='def build(config, stats, clock_start, polls, stop, put, sessions):\n    esp_inflight=0\n    esp_peak=0\n'+textwrap.indent(body,'    ')+'\n    return esp32, lambda: (esp_inflight, esp_peak)\n'
    namespace={'asyncio':asyncio,'time':time,'json':json,'math':__import__('math'),'headers':headers}
    exec(compile(wrapper,str(path)+'#unchanged-esp32-body','exec'),namespace)
    return namespace['build'],hashlib.sha256(body.encode()).hexdigest()

async def check(label,path):
    trace=[];active={'fan':0,'temp':0};peak={'fan':0,'temp':0,'total':0};app=web.Application()
    def handler(kind,delay):
        async def get(request):
            active[kind]+=1;peak[kind]=max(peak[kind],active[kind]);peak['total']=max(peak['total'],sum(active.values()))
            trace.append({'kind':kind,'event':'request','time':time.monotonic()})
            try:
                await asyncio.sleep(delay)
                return web.json_response(fan_packet(19) if kind=='fan' else temp_packet())
            finally:active[kind]-=1
        return get
    app.router.add_get('/api/v1/fan/status',handler('fan',.06));app.router.add_get('/api/v1/temp/status',handler('temp',1.8))
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]);c=load_config(environ={});c['tianshan']['base_url']=origin
    stop=asyncio.Event();rows=[];stats={'stop_reason':'duration','poll_count':0,'poll_missed':0,'poll_rtt_ms':[]}
    polls={key:{'sent':[],'received':[],'rtt_ms':[],'http_ok':0,'errors':0,'skipped':0,'cancelled':0,'inflight':0,'peak_inflight':0} for key in ('fan','temp')}
    def put(kind,payload=None,**extra):rows.append(dict(kind=kind,payload=payload,mono_s=time.monotonic(),**extra))
    factory,digest=extract(path);fn,counters=factory(c,stats,time.monotonic(),polls,stop,put,sessions)
    task=asyncio.create_task(fn())
    try:
        await asyncio.sleep(11.4);stop.set();task.cancel();await asyncio.gather(task,return_exceptions=True)
    finally:
        stop.set();task.cancel();await asyncio.gather(task,return_exceptions=True);await server.cleanup()
    if task.done() and not task.cancelled() and task.exception():raise task.exception()
    returns=[r['mono_s'] for r in rows if r['kind']=='fan' and not r.get('error_class')]
    gaps=[y-x for x,y in zip(returns,returns[1:])]
    return dict(label=label,extraction_sha256=digest,request_scope='own_loopback_two_status_GETs_only',
                rows=rows,server_trace=trace,server_peak=peak,client_counters_at_end=list(counters()),max_fan_return_gap_s=max(gaps),fan_returns=len(returns),
                scope='unchanged nested esp32 body; no Socket.IO or full collect integration')

async def main():
    c=b/'candidate/code';old=c/'tests/fixtures/polling/collector-before.py';new=c/'src/tto/collector.py'
    results=[await check('before',old),await check('after',new)]
    (b/'results/polling-http-independent.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('label','server_peak','client_counters_at_end','max_fan_return_gap_s','fan_returns')} for r in results],indent=2))
    assert results[0]['max_fan_return_gap_s']>2.4
    assert results[1]['max_fan_return_gap_s']<1.3 and results[1]['client_counters_at_end']==[0,2]
    assert results[1]['server_peak']=={'fan':1,'temp':1,'total':2}
    for key,period in [('fan',1),('temp',5)]:
        sends=[r['sent_mono_s'] for r in results[1]['rows'] if r['kind']==key]
        assert all(y-x>=period for x,y in zip(sends,sends[1:]))
    print('PASS: independent scheduling effect reproduced; no full Socket.IO assertion made.')

asyncio.run(main())
