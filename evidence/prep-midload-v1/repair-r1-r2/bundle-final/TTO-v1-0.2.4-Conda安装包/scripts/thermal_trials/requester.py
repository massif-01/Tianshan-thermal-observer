"""One inference request at a time; protocol end and unknown termination are distinct."""
import asyncio
import hashlib
import json
import ssl
from pathlib import Path
from urllib.parse import urlsplit


async def bounded_body(response,limit):
    chunks=[];size=0
    async for chunk in response.content.iter_chunked(16384):
        size+=len(chunk)
        if size>limit:raise ValueError('response_budget')
        chunks.append(chunk)
    return b''.join(chunks)


class Requester:
    def __init__(self,config,output,clock,emit):
        self.config=config;self.output=Path(output);self.clock=clock;self.emit=emit;self.session=None;self.headers=None

    async def open(self):
        import aiohttp
        from tto.config import headers
        base=self.config['base_url'];u=urlsplit(base)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('','/'):
            raise ValueError('推理服务地址格式不正确。')
        self.headers=headers({'orin':{'headers_file':self.config.get('headers_file')}},'orin')
        self.session=aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1,ssl=ssl.create_default_context(cafile=self.config.get('ca_file'))),
                       timeout=aiohttp.ClientTimeout(total=30,connect=5),trust_env=False)

    async def close(self):
        if self.session is not None:await self.session.close()

    async def check_resident_idle(self):
        async with self.session.get(self.config['base_url'].rstrip('/')+'/v1/models',headers=self.headers,allow_redirects=False) as r:
            if r.status!=200:raise ValueError('无法确认模型已驻留；本轮不启动负载。')
            if r.content_length and r.content_length>65536:raise ValueError('模型状态回复过大。')
            raw=await bounded_body(r,65536)
            models=json.loads(raw)
        model=next((m for m in models.get('data',[]) if m.get('id')==self.config['model']),None)
        if model is None:raise ValueError('未找到已驻留的指定模型；请按原方式准备。')
        async with self.session.get(self.config['base_url'].rstrip('/')+'/metrics',headers=self.headers,allow_redirects=False) as r:
            if r.status!=200:raise ValueError('无法确认已有任务状态；本轮不启动负载。')
            raw=await bounded_body(r,262144)
            text=raw.decode()
        counts={name:[] for name in ('vllm:num_requests_running','vllm:num_requests_waiting')}
        for line in text.splitlines():
            for name in counts:
                if line.startswith(name+'{') or line.startswith(name+' '):counts[name].append(float(line.split()[-1]))
        if any(not values or any(v!=0 for v in values) for values in counts.values()):raise ValueError('有活动或排队任务，或状态不完整；本轮不启动负载。')
        return dict(model_id=model['id'],reported_root=model.get('root'),request_counts=counts,one_time_read_only_check=True)

    async def request(self,ident,timeout_s=30):
        payload={k:self.config[k] for k in ('model','messages')};payload.update(self.config.get('sampling',{}));payload.update(max_tokens=256,stream=self.config.get('stream',True))
        if payload['stream']:payload['stream_options']={'include_usage':True}
        raw=json.dumps(payload,ensure_ascii=False).encode();start=self.clock.now()
        record=dict(request_id=ident,submit_mono_s=start,submitted_at_utc=self.clock.utc(),payload_sha256=hashlib.sha256(raw).hexdigest(),
                    max_tokens=256,status='termination_unknown',server_status='unknown',first_network_mono_s=None,first_content_mono_s=None,
                    finish_reason=None,done=False,usage=None,server_request_id=None)
        self.emit('request_submit',**record)
        async def protocol():
            response_path=self.output/'responses'/f'{ident}.response';response_path.parent.mkdir(exist_ok=True)
            async with self.session.post(self.config['base_url'].rstrip('/')+'/v1/chat/completions',data=raw,
                       headers={**self.headers,'Content-Type':'application/json'},allow_redirects=False) as response:
                record['http_status']=response.status
                if response.status!=200:raise ValueError('inference_HTTP_unusable')
                if payload['stream']:
                    count=0
                    with response_path.open('xb') as f:
                        async for line in response.content:
                            count+=len(line)
                            if count>4194304:raise ValueError('inference_response_budget')
                            f.write(line)
                            if record['first_network_mono_s'] is None:
                                record['first_network_mono_s']=self.clock.now();self.emit('first_network_line',request_id=ident)
                            text=line.decode().strip()
                            if not text.startswith('data:'):continue
                            text=text[5:].strip()
                            if text=='[DONE]':record['done']=True;self.emit('protocol_DONE',request_id=ident);break
                            obj=json.loads(text)
                            if obj.get('error'):raise ValueError('inference_SSE_error')
                            record['server_request_id']=obj.get('id',record['server_request_id'])
                            if obj.get('usage') is not None:record['usage']=obj['usage']
                            for choice in obj.get('choices',[]):
                                delta=choice.get('delta',{})
                                if any(delta.get(k) for k in ('content','reasoning','reasoning_content')) and record['first_content_mono_s'] is None:
                                    record['first_content_mono_s']=self.clock.now();self.emit('first_content',request_id=ident,semantics='first_received_SSE_content')
                                if choice.get('finish_reason') is not None:record['finish_reason']=choice['finish_reason']
                    if not record['done'] or record['finish_reason'] is None:raise ValueError('incomplete_SSE_EOF')
                else:
                    body=await bounded_body(response,4194304)
                    response_path.write_bytes(body);obj=json.loads(body)
                    record['first_network_mono_s']=self.clock.now();record['server_request_id']=obj.get('id');record['usage']=obj.get('usage')
                    choices=obj.get('choices',[])
                    if not choices or choices[0].get('finish_reason') is None:raise ValueError('incomplete_JSON_response')
                    record['finish_reason']=choices[0]['finish_reason']
                    if choices[0].get('message',{}).get('content'):
                        record['first_content_mono_s']=self.clock.now();self.emit('first_content',request_id=ident,semantics='complete_nonstream_response_received')
                record.update(status='completed',server_status='protocol_completion_observed')
        try:
            await asyncio.wait_for(protocol(),min(30,timeout_s))
        except asyncio.CancelledError:
            record['error_class']='CancelledError';raise
        except Exception as e:
            record['error_class']=type(e).__name__
        finally:
            record.update(client_end_mono_s=self.clock.now(),client_end_at_utc=self.clock.utc(),duration_s=self.clock.now()-start,
                          request_end_semantics='client protocol completion or unknown termination; never GPU kernel end')
            self.emit('request_end',**record)
        return record
