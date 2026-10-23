"""Allowlisted runner facts. Client protocol state never implies GPU/server state."""
import copy
import threading
from collections import deque
from .common import utc

LABELS={'run_created':'运行已登记','phase_start':'工作阶段开始','phase_end':'工作阶段结束','request_submit':'客户端请求已提交','request_end':'客户端请求结束','protocol_DONE':'收到协议DONE；GPU状态未确认','stop_new_requests':'停止提交新请求','natural_drain_complete':'客户端自然排空','input_unready':'数据条件暂不满足','preparation_ready':'观察准备完成','run_end':'客户端运行结束','server_completion_unconfirmed':'服务端完成状态未确认'}


class TaskContext:
    def __init__(self,binding,mode,clock):
        self.lock=threading.Lock();self.clock=clock;self.active=set();self.events=deque(maxlen=128);self.seq=0
        model=(binding.get('inference') or {}).get('model')
        self.value=dict(task_metadata_available=mode=='execute',active_requests=0 if mode=='execute' else None,client_slots=4 if mode=='execute' else None,task_model=model[:128] if isinstance(model,str) and not model.startswith('/') else None,phase=None,server_running=None,server_queued=None,model_identity_kind='task_registration',task_reason='客户端事实；不代表服务器执行或GPU停止')

    def record(self,row):
        kind=row.get('event')
        if kind not in LABELS:return
        with self.lock:
            ident=row.get('request_id') or (row.get('result') or {}).get('request_id')
            if kind=='request_submit' and ident:self.active.add(ident)
            if kind=='request_end' and ident:self.active.discard(ident)
            if kind=='phase_start':
                stage=row.get('stage',{});name=stage.get('kind');slots=stage.get('concurrency')
                self.value['phase']=name if name in ('background','work','final_recovery') else '已登记阶段'
                self.value['planned_slots']=slots if isinstance(slots,int) and 0<=slots<=4 else None
            if self.value['task_metadata_available']:self.value['active_requests']=len(self.active)
            self.seq+=1
            self.events.append(dict(seq=self.seq,event=kind,label=LABELS[kind],at_mono_s=self.clock.origin+row['mono_s'],received_at_utc=utc()))
    def snapshot(self):
        with self.lock:return dict(context=copy.deepcopy(self.value),events=copy.deepcopy(list(self.events)))
