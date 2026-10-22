import json,time,datetime,urllib.request,hashlib,re,socket,os
from pathlib import Path
P=Path(__file__).resolve().parent
RUN='d2a7593a-e68a-4b6f-9d4d-875fafa73c02'; EP='tto-short-qa-v1-20261013-052807'
BASE=P.parent; OBS=Path('/home/rm01/TTO/runs/run-2026-10-13T052811.443181_0000-d2a7593a')
URL='http://10.10.99.98:58000'; MODEL='RM-01 VLM'
END=datetime.datetime.fromisoformat('2026-10-13T06:08:11.445979+00:00').timestamp()
DEADLINE=time.monotonic()+END-time.time(); phase='initializing'; records=[]; bad_since=None
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def append(path,obj):
 with (P/path).open('a') as f: f.write(json.dumps(obj,ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
def event(name,**details):
 append('events.jsonl',{'event':name,'event_time_utc':now(),'mono_s':time.monotonic(),'episode':EP,'run':RUN,'source':'client_on_TTO_host','precision':'microsecond_timestamp_not_hardware_precision','phase':phase,**details})
def status(state,**details):
 d={'state':state,'phase':phase,'updated_at_utc':now(),'episode':EP,'run':RUN,'completed_requests':len(records),'hard_deadline_utc':'2026-10-13T06:08:11.445979Z',**details}
 tmp=P/'status.tmp'; tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n'); tmp.replace(P/'status.json')
def health():
 global bad_since
 state=json.loads((BASE/'state.json').read_text())
 if state['status']!='running': raise RuntimeError('TTO collection not running')
 lines=(OBS/'observations-0001.jsonl').read_bytes()[-300000:].splitlines()
 latest={}
 for line in reversed(lines):
  try: d=json.loads(line)
  except Exception: continue
  if d['kind'] in ('fan','orin') and d['kind'] not in latest: latest[d['kind']]=d
  if len(latest)==2: break
 good=len(latest)==2
 for d in latest.values():
  age=time.time()-datetime.datetime.fromisoformat(d['received_at_utc']).timestamp()
  if age>15: good=False
 fan=latest.get('fan',{}).get('payload',{}).get('data',{}).get('fans',[])
 if fan:
  f=fan[0]
  if f.get('fault') or f.get('guard_active'): raise RuntimeError('fan guard/fault observed; pause new load')
  good=good and f.get('duty_valid',False) and not f.get('temp_stale',True) and f.get('mode')=='auto'
 else: good=False
 tj=latest.get('orin',{}).get('payload',{}).get('temperature',{}).get('tj')
 good=good and isinstance(tj,(float,int))
 if good: bad_since=None
 elif bad_since is None: bad_since=time.monotonic(); event('telemetry_temporarily_invalid')
 elif time.monotonic()-bad_since>=30: raise RuntimeError('key telemetry unavailable for >=30s')
 return good
def gate():
 if time.monotonic()>=DEADLINE: raise RuntimeError('hard deadline reached; no new load')
 return health()
def wait_until(target):
 while time.monotonic()<target:
  gate(); time.sleep(min(1,target-time.monotonic(),max(.001,DEADLINE-time.monotonic())))
def stage(name,seconds=None):
 global phase
 phase=name; event('phase_start',planned_duration_seconds=seconds); status('running')
 if seconds is not None: wait_until(time.monotonic()+seconds); event('phase_end')
def get(path):
 with urllib.request.urlopen(URL+path,timeout=10) as r: return r.read()
def metrics():
 text=get('/metrics').decode(); (P/'last-metrics.txt').write_text(text)
 values={}
 for line in text.splitlines():
  if line.startswith('#'): continue
  m=re.match(r'([^ {]+)(?:\{[^}]*\})?\s+([-+0-9.eE]+)',line)
  if m and m.group(1).endswith(('num_requests_running','num_requests_waiting')): values[m.group(1)]=values.get(m.group(1),0)+float(m.group(2))
 if len(values)<2: raise RuntimeError('request metrics unavailable')
 return values
def request(q,budget):
 while not gate(): wait_until(time.monotonic()+1)
 counts=metrics(); event('pre_request_metrics',question_id=q['id'],counts=counts)
 if any(counts.values()): raise RuntimeError('other active/waiting requests detected; do not overlap')
 payload={'model':MODEL,'messages':[{'role':'user','content':questions['request_instruction']+q['question']}],'max_tokens':budget,'stream':True,'stream_options':{'include_usage':True}}
 ident=q['id']; (P/(ident+'-payload.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 rec={'run':RUN,'episode':EP,'phase':phase,'question_id':ident,'request_id':ident,'endpoint':URL+'/v1/chat/completions','model':MODEL,'settings':payload,'submitted_at_utc':now(),'submit_mono_s':time.monotonic(),'first_network_at_utc':None,'first_model_content_at_utc':None,'first_visible_content_at_utc':None,'usage':None,'finish_reason':None,'done':False,'eof':False,'server_request_id':None,'cache_information':'unknown','end_semantics':'client response completion; not GPU end'}
 if records: rec['interval_since_previous_client_end_seconds']=rec['submit_mono_s']-records[-1]['end_mono_s']
 event('request_submit',question_id=ident,submitted_at_utc=rec['submitted_at_utc'],max_tokens=budget)
 limit=min(DEADLINE,time.monotonic()+120)
 try:
  req=urllib.request.Request(URL+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=max(.1,limit-time.monotonic())) as response,(P/(ident+'-response.sse')).open('wb') as rawfile:
   rec['http_headers']=dict(response.headers); rec['http_status']=response.status
   sock=response.fp.raw._sock
   while True:
    if time.monotonic()>=limit: raise TimeoutError('request deadline reached; service termination unknown')
    sock.settimeout(max(.1,limit-time.monotonic()))
    raw=response.readline()
    if not raw: rec['eof']=True; break
    rawfile.write(raw); rawfile.flush()
    if rec['first_network_at_utc'] is None:
     rec['first_network_at_utc']=now(); event('first_network_packet',question_id=ident)
    line=raw.decode().strip()
    if not line.startswith('data: '): continue
    data=line[6:]
    if data=='[DONE]': rec['done']=True; event('sse_done',question_id=ident); break
    obj=json.loads(data)
    if obj.get('error'): raise RuntimeError('SSE error '+str(obj['error']))
    if obj.get('id'): rec['server_request_id']=obj['id']
    if obj.get('usage') is not None: rec['usage']=obj['usage']
    for choice in obj.get('choices',[]):
     delta=choice.get('delta',{}); reasoning=delta.get('reasoning_content') or delta.get('reasoning') or ''; visible=delta.get('content') or ''
     if (reasoning or visible) and rec['first_model_content_at_utc'] is None:
      rec['first_model_content_at_utc']=now(); rec['first_model_content_wait_seconds']=time.monotonic()-rec['submit_mono_s']; event('first_model_content',question_id=ident,content_type='reasoning' if reasoning else 'visible')
     if visible and rec['first_visible_content_at_utc'] is None: rec['first_visible_content_at_utc']=now(); event('first_visible_content',question_id=ident)
     if choice.get('finish_reason') is not None: rec['finish_reason']=choice['finish_reason']; rec['finish_reason_at_utc']=now(); event('finish_reason',question_id=ident,finish_reason=rec['finish_reason'])
  if rec['finish_reason'] is None: raise RuntimeError('missing finish_reason; service termination unknown')
  rec['status']='completed'
 except Exception as e:
  rec['status']='termination_unknown'; rec['error']=repr(e)
 finally:
  rec['client_end_at_utc']=now(); rec['end_mono_s']=time.monotonic(); rec['duration_seconds']=rec['end_mono_s']-rec['submit_mono_s']; append('requests.jsonl',rec); records.append(rec); event('request_end',question_id=ident,status=rec['status'],duration_seconds=rec['duration_seconds']); status('running',last_request=rec)
 if rec['status']!='completed': raise RuntimeError('pause after request exception: '+rec.get('error','unknown'))
 return rec
questions=json.loads((P/'questions.json').read_text())
try:
 event('workload_start',hard_deadline_utc='2026-10-13T06:08:11.445979Z'); status('running')
 counts=metrics(); (P/'initial-metrics.txt').write_text((P/'last-metrics.txt').read_text())
 if any(counts.values()): raise RuntimeError('initial conflicting requests detected')
 models=json.loads(get('/v1/models')); model=next(m for m in models['data'] if m['id']==MODEL)
 if model.get('root')!='/home/rm01/models/dev/llm/Qwen3.8-27B-NVFP4/': raise RuntimeError('model root mismatch')
 (P/'identity.json').write_text(json.dumps({'checked_at_utc':now(),'host':socket.gethostname(),'model':model,'metrics':counts,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'questions_sha256':hashlib.sha256((P/'questions.json').read_bytes()).hexdigest(),'default_sampling':'temperature/top_p/template/cache not overridden','max_tokens_contract':'vLLM generation budget, all generated tokens; observed usage retained','weights_hash':'unknown'},ensure_ascii=False,indent=2)+'\n')
 stage('pilot'); a=request(questions['pilot'][0],64); budget=64
 if a['duration_seconds']<3: budget=128
 elif a['duration_seconds']>10: budget=32
 if budget!=64:
  b=request(questions['pilot'][1],budget)
  if b['duration_seconds']>=20: raise RuntimeError('pilot remains >=20 seconds; pause formal questions')
 elif a['duration_seconds']>=20: raise RuntimeError('pilot long; pause formal questions')
 (P/'frozen-plan.json').write_text(json.dumps({'frozen_at_utc':now(),'max_tokens':budget,'sequence':questions,'sparse_interval_seconds':90,'continuous_interval_seconds':10,'baseline_seconds':180,'between_groups_seconds':300,'final_cooldown_seconds':300,'hard_deadline_utc':'2026-10-13T06:08:11.445979Z'},ensure_ascii=False,indent=2)+'\n'); event('parameters_frozen',max_tokens=budget)
 stage('resident-baseline',180); stage('sparse')
 for i,q in enumerate(questions['sparse']):
  r=request(q,budget)
  if i<5: wait_until(r['end_mono_s']+90)
 event('phase_end'); stage('between-groups',300); stage('continuous')
 for i,q in enumerate(questions['continuous']):
  r=request(q,budget)
  if i<11: wait_until(r['end_mono_s']+10)
 event('phase_end'); stage('final-cooldown',300); phase='complete'; event('workload_end'); status('completed')
 result='completed'
except Exception as e:
 event('workload_paused',error=repr(e)); status('paused',reason=repr(e)); result='paused'
(P/'summary.json').write_text(json.dumps({'run':RUN,'episode':EP,'status':result,'ended_at_utc':now(),'requests':len(records),'completed_requests':sum(r['status']=='completed' for r in records),'usage_by_request':{r['question_id']:r['usage'] for r in records},'TTO_stop_authority':'collection side; workload does not stop TTO'},ensure_ascii=False,indent=2)+'\n')
