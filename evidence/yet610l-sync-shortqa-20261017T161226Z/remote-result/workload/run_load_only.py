"""Single stream workload only. Default preparation; no collector and no pilot.
Execution requires coordinator-provided run binding/native admission and explicit --execute.
"""
import argparse,datetime,hashlib,json,os,re,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
UTC=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
class StopLoad(Exception):pass

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--binding',type=Path);args=ap.parse_args()
 plan=json.loads((HERE/'frozen-request-plan.json').read_text())
 if not args.execute:
  print(json.dumps({'status':'prepared_not_started','requests':18,'pilots':0,'max_tokens':64,'collector_started':False}));return
 if not args.binding:raise StopLoad('Coordinator run binding required')
 binding=json.loads(args.binding.read_text())
 if binding['authorization']!='可以开始本轮':raise StopLoad('Explicit start authorization absent')
 if binding.get('operator_override'):raise StopLoad('Old override prohibited')
 run=binding['run_id'];out=Path(binding['output_directory']);out.mkdir(parents=True,exist_ok=True)
 if (out/'events.jsonl').exists():raise StopLoad('Existing events: no automatic rerun')
 start_epoch=datetime.datetime.fromisoformat(binding['collection_started_at_utc']).timestamp()
 deadline_epoch=min(start_epoch+2400,datetime.datetime.fromisoformat(binding['deadline_utc']).timestamp())
 deadline=time.monotonic()+deadline_epoch-time.time();phase='initializing';records=[]
 def append(name,obj):
  with (out/name).open('a') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
 def event(name,**details):append('events.jsonl',{'event':name,'event_time_utc':UTC(),'mono_s':time.monotonic(),'run_id':run,'session_id':binding['session_id'],'phase':phase,**details})
 def status(state,**details):
  target=out/'status.json';tmp=out/'status.tmp';tmp.write_text(json.dumps({'state':state,'phase':phase,'run_id':run,'updated_at_utc':UTC(),'completed_requests':len(records),**details},ensure_ascii=False,indent=2)+'\n');tmp.replace(target)
 def admission():
  if time.monotonic()>=deadline:raise StopLoad('Hard deadline: no extension')
  d=json.loads(Path(binding['native_admission_file']).read_text())
  if d['run_id']!=run or d['clock_host']!=binding['clock_host']:raise StopLoad('Native admission run/clock mismatch')
  if d.get('operator_override'):raise StopLoad('Native admission must not use override')
  if d['collection_state']!='running':raise StopLoad('Collector stopped')
  if d['abnormal']:raise StopLoad('Native abnormal condition')
  return bool(d['current_ready'] and time.monotonic()<=d['valid_until_mono_s'])
 def wait_until(target):
  while time.monotonic()<target:
   admission();time.sleep(min(.5,target-time.monotonic()))
 def stage(name,duration=None):
  nonlocal phase
  phase=name;event('phase_start',planned_seconds=duration);status('running')
  if duration is not None:wait_until(time.monotonic()+duration);event('phase_end')
 def pre_request_service_check(ident):
  base=binding['endpoint'].removesuffix('/v1/chat/completions')
  if base==binding['endpoint']:raise StopLoad('Unexpected endpoint path')
  evidence={}
  for path in ['/v1/models','/metrics']:
   remaining=deadline-time.monotonic()
   if remaining<=0:raise StopLoad('Hard deadline before service check')
   with urllib.request.urlopen(base+path,timeout=min(10,remaining)) as response:body=response.read().decode()
   evidence[path]=body
  (out/(ident+'-service-check.json')).write_text(json.dumps({'checked_at_utc':UTC(),'evidence':evidence},ensure_ascii=False,indent=2)+'\n')
  models=json.loads(evidence['/v1/models']);model=next((m for m in models['data'] if m['id']=='RM-01 VLM'),None)
  if not model or model.get('root')!='/home/rm01/models/dev/llm/Qwen3.8-27B-NVFP4/':raise StopLoad('Model identity/root changed')
  counts={}
  for line in evidence['/metrics'].splitlines():
   match=re.match(r'(vllm:num_requests_running|vllm:num_requests_waiting)(?:\{[^}]*\})?\s+(\S+)',line)
   if match:counts[match[1]]=counts.get(match[1],0)+float(match[2])
  if len(counts)!=2:raise StopLoad('Missing running/waiting metrics')
  event('pre_request_service_check',question_id=ident,model_root=model['root'],counts=counts)
  if any(counts.values()):raise StopLoad('Other model requests detected; stop further submissions')
 def request(item):
  while not admission():time.sleep(.25)
  pre_request_service_check(item['question_id'])
  while not admission():time.sleep(.25)
  ident=item['question_id'];payload=item['payload'];(out/(ident+'-payload.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
  rec={'question_id':ident,'run_id':run,'phase':phase,'submitted_at_utc':UTC(),'submit_mono_s':time.monotonic(),'finish_reason':None,'usage':None,'done':False,'eof':False,'server_request_id':None,'status':'termination_unknown','first_response_line_at_utc':None,'first_model_content_at_utc':None,'first_visible_content_at_utc':None,'response_time_semantics':'client observations, not GPU kernel timestamps'}
  if records:rec['interval_since_previous_end_seconds']=rec['submit_mono_s']-records[-1]['end_mono_s']
  event('request_submit',question_id=ident,submitted_at_utc=rec['submitted_at_utc'])
  limit=min(deadline,time.monotonic()+120)
  try:
   req=urllib.request.Request(binding['endpoint'],data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=max(.001,limit-time.monotonic())) as response,(out/(ident+'-response.sse')).open('wb') as rawfile:
    rec['http_status']=response.status;rec['http_headers']=dict(response.headers);sock=response.fp.raw._sock
    while True:
     if time.monotonic()>=limit:raise TimeoutError('Request deadline; service termination unknown')
     sock.settimeout(max(.001,limit-time.monotonic()));raw=response.readline()
     if not raw:rec['eof']=True;break
     rawfile.write(raw);rawfile.flush()
     if rec['first_response_line_at_utc'] is None:rec['first_response_line_at_utc']=UTC();event('first_response_line',question_id=ident)
     line=raw.decode().strip()
     if not line.startswith('data: '):continue
     data=line[6:]
     if data=='[DONE]':rec['done']=True;event('protocol_DONE',question_id=ident);break
     obj=json.loads(data)
     if obj.get('error'):raise StopLoad('SSE error '+str(obj['error']))
     if obj.get('id'):rec['server_request_id']=obj['id']
     if obj.get('usage') is not None:rec['usage']=obj['usage']
     for c in obj.get('choices',[]):
      delta=c.get('delta',{});reason=delta.get('reasoning_content') or delta.get('reasoning') or '';visible=delta.get('content') or ''
      if (reason or visible) and rec['first_model_content_at_utc'] is None:
       rec['first_model_content_at_utc']=UTC();rec['first_content_wait_seconds']=time.monotonic()-rec['submit_mono_s'];event('first_model_content',question_id=ident,content_type='reasoning' if reason else 'visible')
      if visible and rec['first_visible_content_at_utc'] is None:rec['first_visible_content_at_utc']=UTC();event('first_visible_content',question_id=ident)
      if c.get('finish_reason') is not None:rec['finish_reason']=c['finish_reason'];event('finish_reason',question_id=ident,finish_reason=c['finish_reason'])
   if rec['finish_reason'] is None or not (rec['done'] or rec['eof']):raise StopLoad('No reliable protocol completion')
   rec['status']='completed'
  except BaseException as e:rec['error']=repr(e)
  finally:
   rec['client_end_at_utc']=UTC();rec['end_mono_s']=time.monotonic();rec['duration_seconds']=rec['end_mono_s']-rec['submit_mono_s'];append('requests.jsonl',rec);records.append(rec);event('request_end',question_id=ident,status=rec['status']);status('running',last_request=rec)
  if rec['status']!='completed':raise StopLoad('Stop subsequent requests: service completion unknown')
  return rec
 result='stopped'
 try:
  event('workload_start',deadline_utc=datetime.datetime.fromtimestamp(deadline_epoch,datetime.timezone.utc).isoformat());stage('resident-baseline',300)
  for group,gap in [('sparse',90),('continuous',10)]:
   if group=='continuous':stage('between-groups',300)
   stage(group);items=[i for i in plan['payloads'] if i['phase']==group]
   for index,item in enumerate(items):
    rec=request(item)
    if index<len(items)-1:wait_until(rec['end_mono_s']+gap)
   event('phase_end')
  stage('final-cooldown',600);result='completed';event('workload_end');status(result)
 except BaseException as e:event('workload_stopped',reason=repr(e));status('stopped',reason=repr(e))
 finally:
  (out/'summary.json').write_text(json.dumps({'status':result,'run_id':run,'ended_at_utc':UTC(),'requests':len(records),'usage_by_request':{r['question_id']:r['usage'] for r in records},'collector_control':'none; coordinator owns collector','operator_override':False},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
