"""Local-only health supervisor. Actual source validity remains owned by observe.2."""
import json,os,time,shutil
from pathlib import Path
from collections import deque
from admission import evaluate

def read_json(path):
    p=Path(path)
    if p.stat().st_size>1024**2:raise ValueError('local_state_size')
    return json.loads(p.read_text())

class Budget:
    def __init__(self,cpu,rss):self.cpu=cpu;self.rss=rss;self.rows=deque();self.over=None;self.unknown=None;self.mean=None
    def tick(self,t,cpu,rss):
        if cpu is not None:self.rows.append((t,cpu))
        while self.rows and t-self.rows[0][0]>10:self.rows.popleft()
        self.mean=sum(x[1] for x in self.rows)/len(self.rows) if self.rows else None
        if rss is None or (cpu is None and t>2):self.unknown=t if self.unknown is None else self.unknown
        else:self.unknown=None
        high=self.mean is not None and len(self.rows)>=8 and self.mean>self.cpu
        self.over=(t if self.over is None else self.over) if high else None
        return 'RSS_budget' if rss is not None and rss>self.rss else 'sustained_CPU_budget' if self.over is not None and t-self.over>=30 else 'resource_unknown' if self.unknown is not None and t-self.unknown>=10 else None

class Health:
    def __init__(self,identity,checkpoint_s=7200):
        self.identity=identity;self.checkpoint_s=checkpoint_s;self.checked=False;self.unready=None;self.load_stop=None;self.last=None;self.resource_stop=None
        self.own=Budget(5,64*1024**2);self.total=Budget(8,192*1024**2)
    def update(self,t,launch,status,now,*,alive,created,resource=None):
        gate=evaluate(launch,status,now,self.identity,alive=alive,process_created=created)
        if gate['action']=='allow':self.unready=None
        elif self.unready is None:self.unready=t
        if gate['action']=='stop':self.load_stop=gate['reasons'][0]
        # Background is a health inspection, not 2h continuously green active readiness.
        if t>=self.checkpoint_s and self.unready is not None and t-max(self.checkpoint_s,self.unready)>=60:self.load_stop='active_conditions_unready_60s'
        if resource:
            for name,b,cpu,rss in [('driver',self.own,resource['own_cpu'],resource['own_rss']),('combined',self.total,resource['total_cpu'],resource['total_rss'])]:
                reason=b.tick(t,cpu,rss)
                if reason:self.resource_stop=name+'_'+reason;self.load_stop=self.resource_stop
        checkpoint=None
        if not self.checked and t>=self.checkpoint_s:
            self.checked=True
            checkpoint=dict(elapsed_s=t,software_healthy=gate['software_healthy'],active_allowed=gate['action']=='allow' and not self.load_stop,active_reasons=gate['reasons'],resource_stop=self.resource_stop,model_score_used=False,human_confirmation_required=False)
        if self.load_stop:gate=dict(gate,action='stop',reasons=[self.load_stop])
        self.last=gate
        return gate,checkpoint

class DiskEvidence:
    def __init__(self,root,limit=256*1024**2):
        self.root=Path(root);self.limit=limit;self.files={};self.written=0;self.external=0
    def emit(self,name,row):
        b=(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode()
        if self.written+self.external+len(b)>self.limit:raise ValueError('driver_evidence_budget')
        if name not in self.files:self.files[name]=(self.root/(name+'.jsonl')).open('xb')
        self.files[name].write(b);self.files[name].flush();self.written+=len(b)
    def check_disk(self):
        self.external=sum(p.stat().st_size for p in (self.root/'responses').glob('*') if p.is_file())
        if self.written+self.external>self.limit:raise ValueError('driver_evidence_budget')
        if shutil.disk_usage(self.root).free<1024**3:raise ValueError('driver_min_free_bytes')
    def close(self):
        for f in self.files.values():f.flush();os.fsync(f.fileno());f.close()

class Controls:
    def __init__(self,path):self.path=Path(path);self.last_sequence=-1;self.paused=False;self.stopped=False
    def read(self):
        if self.path.exists():
            x=read_json(self.path)
            if type(x.get('sequence')) is not int or x['sequence']<self.last_sequence:raise ValueError('control_sequence_regression')
            if x['sequence']>self.last_sequence:
                if x.get('action') not in ('pause','resume','stop'):raise ValueError('unknown_control')
                self.last_sequence=x['sequence']
                if x['action']=='pause':self.paused=True
                if x['action']=='resume':self.paused=False
                if x['action']=='stop':self.stopped=True
        return dict(paused=self.paused,stopped=self.stopped,sequence=self.last_sequence)


def request_admission(health,launch,status,now,*,alive,created):
    if health.load_stop:return dict(action='stop',reasons=[health.load_stop])
    if not health.checked:return dict(action='pause',reasons=['automatic_checkpoint_pending'])
    return evaluate(launch,status,now,health.identity,alive=alive,process_created=created)
