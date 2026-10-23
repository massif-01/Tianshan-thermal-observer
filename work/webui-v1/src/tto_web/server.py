"""Same-origin read-only HTTP and bounded SSE. Service health is not device health."""
import asyncio
import contextlib
import copy
import hashlib
import hmac
import ipaddress
import json
import logging
import math
import os
import psutil
import secrets
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit
from aiohttp import web
from . import __version__
from .common import load, utc
from .state import State, MODEL_IDS, MODEL_LABELS
from .source import follow, observe

STATIC=Path(__file__).parent/'static'


def password_hash(password, salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),200000).hex()


def configuration(path):
    c=load(path)
    w=c['web'];s=c['source']
    try:ipaddress.ip_address(w['bind'])
    except ValueError:raise ValueError('bind must be an explicit local/LAN IP')
    if w.get('port',59009)!=59009:raise ValueError('Web端口固定59009')
    if s.get('mode') not in ('follow','observe'):raise ValueError('source mode must be follow or observe')
    if w.get('access_mode')=='local':
        if w['bind'] not in ('127.0.0.1','::1'):raise ValueError('local mode requires loopback bind')
    elif w.get('access_mode')=='lan':
        if not w.get('password_hash') or not w.get('allowed_origins'):raise ValueError('LAN requires credential and explicit allowed origins')
        for origin in w['allowed_origins']:
            parsed=urlsplit(origin)
            if parsed.scheme not in ('http','https') or parsed.path or parsed.query or parsed.username:raise ValueError('invalid allowed origin')
    else:raise ValueError('explicit local/LAN mode required')
    return c


def app_for(config, *, start_source=True, state=None):
    state=state or State(config);sessions={};failures=deque(maxlen=100)
    stop=asyncio.Event();source_task=None;timer_task=None
    process=psutil.Process();process.cpu_percent(None);host_sample=0.
    clock_previous=(time.monotonic(),time.time())
    sent=deque(maxlen=64);sse_clients=set();last_send=0.;last_quality=None

    @web.middleware
    async def guard(request, handler):
        origin=request.headers.get('Origin')
        local_origins={'http://localhost:59009','http://127.0.0.1:59009','http://[::1]:59009'}
        allowed=local_origins if config['web']['access_mode']=='local' else set(config['web']['allowed_origins'])
        if origin and origin not in allowed:raise web.HTTPForbidden(text='cross-origin denied')
        host=request.host.lower()
        allowed_hosts={urlsplit(o).netloc.lower() for o in allowed}
        if host not in allowed_hosts:raise web.HTTPForbidden(text='Host is not configured')
        if request.path.startswith('/api/'):
            if request.method not in ('GET','HEAD') and request.path!='/api/v1/session':raise web.HTTPMethodNotAllowed(request.method,['GET'])
            if config['web']['access_mode']=='lan' and request.path!='/api/v1/session':
                token=request.cookies.get('tto_session');expiry=sessions.get(token,0)
                if expiry<time.monotonic():raise web.HTTPUnauthorized(text='只读访问需要登录')
        response=await handler(request)
        response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"})
        return response

    app=web.Application(middlewares=[guard],client_max_size=8192)
    app['state']=state;app['sse_clients']=sse_clients;app['stop']=stop

    def response(obj):return web.json_response(obj,dumps=lambda o:json.dumps(o,ensure_ascii=False,allow_nan=False))
    async def health(r):return response({'web':'running','version':__version__,'pid':os.getpid(),'device_health_is_separate':True})
    async def bootstrap(r):
        s=state.snapshot()
        return response(dict(version=__version__,schema_version=s['schema_version'],service_epoch=state.epoch,clock_domain_id=s['clock_domain_id'],run_id=s['run_id'],source_mode=config['source']['mode'],timezone=config['web'].get('timezone','Asia/Shanghai'),capabilities=dict(read_only=True,g2_hold=True,task_metadata=s['context']['task_metadata_available'],rpm_verified=False,demand_provider=False,advisory_provider='CURVE-REFERENCE-v1' if state.curve else None),available_fields=[dict(id=m['id'],label=m['label'],unit=m['unit']) for m in s['metrics']],series_capabilities=dict(model_state_history=True,alignment_group='tj_model',time_basis='tj_sample',estimate_stage='posterior',max_rows=18002,window_ms=3600000),available_series=[dict(id=id,label=label,unit='°C',kind='estimate') for id,label in zip(MODEL_IDS,MODEL_LABELS)]))
    async def snapshot(r):return response(state.refresh())
    async def model(r):
        s=state.snapshot();p=state.packet
        latest=[v for v in s['predictions'] if v['prediction_id'] in s['forecast']['latest_prediction_ids']]
        condition=(latest[-1].get('conditional_assumptions') or {}) if latest else {}
        return response(dict(**s['model'],provider=dict(method_id='frozen_g2_hold',provider_id='observe-ledger',horizons_s=[15,45,90],stride_s=5,assumption_codes=condition.get('assumptions',[]),TJ_anchor='recorded_prediction_origin',state_cutoff_elapsed_ms=latest[-1]['input_cutoff_elapsed_ms'] if latest else None),uncertainty=(p or {}).get('model',{}).get('uncertainty'),innovation_C=(p or {}).get('model',{}).get('latest_innovation_C'),reasons=(p or {}).get('model',{}).get('reasons',[]),advisory=dict(**s['advisory'],basis=state.last_advisory_basis),demand=dict(status='not_available',value=None,unit='index',reason='本轮未计算：没有当前合法provider和固定参考')))
    def bounded_number(r,key,default,lo,hi):
        try:v=float(r.query.get(key,default))
        except ValueError:raise web.HTTPBadRequest(text='invalid number')
        if not math.isfinite(v) or v<lo or v>hi:raise web.HTTPBadRequest(text='number outside budget')
        return v
    def window(r):
        end=state.snapshot()['run_elapsed_ms'] or 0
        hi=bounded_number(r,'to',end,0,max(end,1))
        lo=bounded_number(r,'from',max(0,hi-600000),0,max(end,1))
        if lo>hi or hi-lo>3600000:raise web.HTTPBadRequest(text='range limited to 60 minutes')
        return lo,hi
    async def series(r):
        lo,hi=window(r);n=int(bounded_number(r,'max_points',2000,16,5000))
        ids=r.query.get('ids','temperature.tj,temperature.cpu,temperature.gpu,power.gpu,power.cpu_soc_mss,fan.pwm.actual,fan.pwm.target').split(',')
        s=state.snapshot()
        return response(dict(snapshot_seq=s['snapshot_seq'],service_epoch=s['service_epoch'],run_id=s['run_id'],
            source_epoch=s['source_epoch'],model_id=s['model']['model_id'],spec_id=s['model']['spec_id'],
            series=state.series(ids,lo,hi,n)))
    async def predictions(r):
        h=int(bounded_number(r,'horizon_s',45,15,90))
        if h not in (15,45,90):raise web.HTTPBadRequest(text='horizon must be 15/45/90')
        lo,hi=window(r)
        after=bounded_number(r,'records_after',0,0,max(state.snapshot()['run_elapsed_ms'] or 0,1)) if 'records_after' in r.query else None
        return response(state.prediction_view(h,lo,hi,records_after=after))
    async def events(r):
        limit=int(bounded_number(r,'limit',100,1,1000));after=int(bounded_number(r,'after',0,0,10**12))
        rows=[copy.deepcopy(e) for e in state.current_events() if int(e['id'])>after]
        if r.query.get('source'):rows=[v for v in rows if v['source']==r.query['source']]
        if r.query.get('severity'):rows=[v for v in rows if v['severity']==r.query['severity']]
        return response(dict(events=rows[:limit],cursor=rows[min(len(rows),limit)-1]['id'] if rows else str(after)))
    async def metrics(r):
        q=r.query.get('q','').lower();group=r.query.get('group','')
        rows=[m for m in state.snapshot()['metrics'] if q in (m['label']+' '+m['id']).lower() and m['id'].startswith(group)]
        offset=int(bounded_number(r,'offset',0,0,10000));limit=int(bounded_number(r,'limit',100,1,500))
        return response(dict(metrics=rows[offset:offset+limit],total=len(rows)))
    async def context(r):
        s=state.snapshot()
        return response(dict(**s['context'],observation_status=state.source_status,mode=s['mode'],run_id=s['run_id'],source_epoch=s['source_epoch'],run_elapsed_ms=s['run_elapsed_ms'],thermal_model=s['model']['model_id'],platform=(state.packet or {}).get('platform'),task_model=(state.packet or {}).get('task',{}).get('context',{}).get('task_model'),client_slots=(state.packet or {}).get('task',{}).get('context',{}).get('client_slots'),planned_slots=(state.packet or {}).get('task',{}).get('context',{}).get('planned_slots'),task_phase=(state.packet or {}).get('task',{}).get('context',{}).get('phase'),server_running=None,server_queued=None,source_health=(state.packet or {}).get('source_health',{}),display_resync_count=state.dropped,task_reason=('任务信息来自runner登记' if s['context']['task_metadata_available'] else '未接入任务记录')+'；客户端完成不代表服务端停止',source_instances_owned=int(config['source']['mode']=='observe' and state.source_connected)))
    async def session(r):
        if r.method=='DELETE':
            sessions.pop(r.cookies.get('tto_session'),None);resp=response({'logged_in':False});resp.del_cookie('tto_session');return resp
        if r.method!='POST':raise web.HTTPMethodNotAllowed(r.method,['POST','DELETE'])
        if config['web']['access_mode']!='lan':raise web.HTTPBadRequest(text='LAN session is not configured')
        now=time.monotonic()
        while failures and failures[0]<now-60:failures.popleft()
        if len(failures)>=10:raise web.HTTPTooManyRequests(text='稍后重试')
        data=await r.json();password=data.get('password','')
        if not isinstance(password,str) or len(password)>512:raise web.HTTPBadRequest()
        stored=config['web']['password_hash'];salt=stored.split(':')[0]
        calculated=await asyncio.to_thread(password_hash,password,salt)
        if not hmac.compare_digest(calculated,stored):failures.append(now);raise web.HTTPUnauthorized(text='只读口令不匹配')
        for token,expiry in list(sessions.items()):
            if expiry<now:del sessions[token]
        if len(sessions)>=32:raise web.HTTPTooManyRequests()
        token=secrets.token_urlsafe(32);sessions[token]=now+12*3600
        resp=response({'logged_in':True});resp.set_cookie('tto_session',token,httponly=True,samesite='Strict',max_age=43200,secure=r.secure);return resp

    async def stream(r):
        if len(sse_clients)>=4:raise web.HTTPServiceUnavailable(text='display client budget reached')
        queue=asyncio.Queue(maxsize=8);sse_clients.add(queue)
        resp=web.StreamResponse(headers={'Content-Type':'text/event-stream','Cache-Control':'no-store','X-Accel-Buffering':'no'})
        try:
            await resp.prepare(r)
            last=r.headers.get('Last-Event-ID');current=state.snapshot()
            event='snapshot'
            if last:
                ids=[v[0] for v in sent]
                if last in ids:
                    missed=list(sent)[ids.index(last)+1:]
                    if len(missed)>8:event='resync'
                    else:
                        for item in missed:queue.put_nowait(item)
                else:event='resync'
            if queue.empty():queue.put_nowait((f'{state.epoch}:{current["snapshot_seq"]}',event,current))
            while True:
                try:
                    item=await asyncio.wait_for(queue.get(),5.)
                    if item is None:break
                    id,event,data=item
                    wire=f'id: {id}\nevent: {event}\nretry: 1000\ndata: {json.dumps(data,ensure_ascii=False,allow_nan=False)}\n\n'
                except asyncio.TimeoutError:wire='event: heartbeat\ndata: {}\n\n'
                await asyncio.wait_for(resp.write(wire.encode()),2.)
        except (OSError,asyncio.TimeoutError,asyncio.CancelledError):pass
        finally:sse_clients.discard(queue)
        return resp

    async def timer():
        nonlocal last_send,last_quality,host_sample,clock_previous
        while True:
            now=time.monotonic();wall=time.time()
            if abs((wall-clock_previous[1])-(now-clock_previous[0]))>1.:state.event('clock','墙钟发生跳变；持续时间和成熟标签继续使用单调时钟')
            clock_previous=(now,wall)
            if now-host_sample>=1.:
                state.host_values={'host.cpu':process.cpu_percent(None),'host.rss':process.memory_info().rss/1024**2}
                state.host_sample_mono=now;state.host_sample_utc=utc();host_sample=now
            # New publications already refreshed the state. Between them rebuild
            # only for a display tick or a qualification deadline, not at 10 Hz.
            s=state._snapshot
            packet=state.packet
            statuses={m['id']:m['status'] for m in s['metrics']}
            expired=packet and (any(statuses.get(m['id'])=='valid' and m['_expiry']<=now for m in packet['metrics']) or (s['model']['phase']!='unavailable' and packet['consumable_until_mono_s']<=now))
            if now-last_send>=1. or expired:s=state.refresh(now)
            quality=(s['run_id'],s['source_epoch'],s['model']['phase'],s['health']['protection_status'],tuple((m['id'],m['status']) for m in s['metrics']))
            changed=last_quality is not None and quality!=last_quality
            if changed or now-last_send>=1.:
                event='run_changed' if changed and quality[:2]!=last_quality[:2] else 'quality' if changed else 'snapshot'
                item=(f'{state.epoch}:{s["snapshot_seq"]}',event,s);sent.append(item)
                for queue in tuple(sse_clients):
                    if queue.full():
                        while not queue.empty():queue.get_nowait()
                        state.dropped+=1;state.event('web','显示队列丢帧，已重新同步');queue.put_nowait((item[0],'resync',item[2]))
                    else:queue.put_nowait(item)
                last_send=now;last_quality=quality
            await asyncio.sleep(.1)
    async def startup(app):
        nonlocal source_task,timer_task
        timer_task=asyncio.create_task(timer())
        if start_source:
            async def source_run():
                try:
                    mode=config['source']['mode']
                    if mode=='observe' and config['source'].get('observation_config'):await observe(config,state,stop)
                    else:await follow(config,state,stop)
                except (ValueError,OSError):state.disconnect('观察配置不可用；等待本地配置或生产者注册')
            source_task=asyncio.create_task(source_run())
    async def shutdown(app):
        stop.set()
        # End long-lived display requests before aiohttp waits for HTTP handlers.
        for queue in tuple(sse_clients):
            while not queue.empty():queue.get_nowait()
            queue.put_nowait(None)
        if source_task:
            if config['source']['mode']=='follow':source_task.cancel()
            await asyncio.gather(source_task,return_exceptions=True)
        if timer_task:timer_task.cancel();await asyncio.gather(timer_task,return_exceptions=True)
    app.on_startup.append(startup);app.on_shutdown.append(shutdown)
    routes={'bootstrap':bootstrap,'snapshot':snapshot,'stream':stream,'series':series,'model':model,'predictions':predictions,'events':events,'metrics':metrics,'context':context}
    for name,handler in routes.items():app.router.add_get('/api/v1/'+name,handler)
    app.router.add_route('*','/api/v1/session',session)
    app.router.add_get('/healthz',health)
    async def favicon(r):return web.Response(status=204)
    app.router.add_get('/favicon.ico',favicon)
    async def index(r):return web.FileResponse(STATIC/'index.html')
    app.router.add_get('/',index)
    app.router.add_static('/assets/',STATIC/'assets',show_index=False)
    return app
