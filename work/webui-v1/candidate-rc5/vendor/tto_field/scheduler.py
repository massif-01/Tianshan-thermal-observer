"""One clock-driven scheduling state machine, shared by virtual and loopback drivers."""
import hashlib,json,math
from pathlib import Path
from .gate import readiness

class Registry:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def claim(self,run_id,command_id):
        for kind,value in [('command',command_id),('run',run_id)]:
            path=self.root/(kind+'-'+hashlib.sha256(value.encode()).hexdigest()+'.json')
            with path.open('x') as f:json.dump(dict(run_id=run_id,command_id=command_id,status='claimed_no_auto_restart'),f)

class Scheduler:
    def __init__(self,profile,policy,run_id,command_id,formal=False):
        self.profile=profile;self.policy=policy;self.run_id=run_id;self.command_id=command_id;self.formal=formal
        self.now=0.;self.state='prepare';self.index=-1;self.phase_start=0.;self.window_end=None
        self.pending={};self.requests=[];self.events=[];self.submitted=0;self.peak=0
        self.reason=None;self.unready_since=None;self.stopping_at=None;self.unknown_requests=[]
        self.emit('run_created',collector_count=1,request_executor_count=1,mode='formal' if formal else 'local_demo')
    def emit(self,event,**kw):self.events.append(dict(event=event,mono_s=self.now,run_id=self.run_id,command_id=self.command_id,**kw))
    @property
    def terminal(self):return self.state=='terminal'
    def stop(self,reason,*,now):
        if now<self.now:raise ValueError('monotonic clock moved backwards')
        self.now=float(now)
        if self.reason is None:
            self.reason=reason;self.stopping_at=self.now;self.state='stopping';self.emit('stop_new_requests',reason=reason)
    def next_phase(self):
        if self.index>=0:self.emit('phase_end',index=self.index,kind=self.profile['stages'][self.index]['kind'],elapsed_s=self.now-self.phase_start)
        self.index+=1
        if self.index>=len(self.profile['stages']):self.stop('completed',now=self.now);return
        self.phase_start=self.now;stage=self.profile['stages'][self.index];self.window_end=self.now+stage['seconds'];self.state='stage'
        self.emit('phase_start',index=self.index,stage=stage,window_end=self.window_end)
    def tick(self,now,snapshot,completed=(),user_stop=False):
        if now<self.now:raise ValueError('monotonic clock moved backwards')
        self.now=float(now);actions=[]
        for result in completed:
            ident=result['request_id']
            if ident not in self.pending:raise ValueError('unknown or duplicate completion')
            submitted=self.pending.pop(ident);result=dict(submitted,**result);self.requests.append(result)
            self.emit('request_end',result=result)
            if result['status']!='completed':
                self.unknown_requests.append(ident);self.stop('request_termination_unknown',now=self.now)
        gate=readiness(snapshot,self.now,self.run_id,self.formal)
        if user_stop:self.stop('user_stop',now=self.now)
        if gate['explicit_stop']:self.stop('explicit_protection_or_mode_binding',now=self.now)
        hard=self.profile['hard_limit_seconds'];cleanup=self.profile['cleanup_reserve_seconds']
        if self.now>=hard-cleanup:self.stop('hard_budget_cleanup_boundary',now=self.now)
        if self.state not in ('prepare','stopping','terminal'):
            if gate['start_allowed']:self.unready_since=None
            else:
                if self.unready_since is None:self.unready_since=self.now;self.emit('input_unready',layers=gate)
                if self.now-self.unready_since>=self.policy['max_data_unready_seconds']:self.stop('data_or_observer_unavailable_too_long',now=self.now)
        if self.state=='prepare':
            if self.now>self.profile['preparation_reserve_seconds']:self.stop('preparation_budget_exhausted',now=self.now)
            elif gate['start_allowed']:self.emit('preparation_ready',layers=gate);self.next_phase()
        if self.state=='stage':
            stage=self.profile['stages'][self.index]
            if self.now>=self.window_end:
                if stage['kind']=='work':self.state='drain';self.emit('work_start_window_closed',index=self.index,inflight=len(self.pending))
                else:self.next_phase()
            if self.state=='stage' and stage['kind']=='work' and self.now<self.window_end and gate['start_allowed']:
                occupied={v['slot'] for v in self.pending.values()}
                for slot in range(stage['concurrency']):
                    if slot in occupied:continue
                    if self.submitted>=self.policy['max_total_requests']:self.stop('request_count_cap',now=self.now);break
                    self.submitted+=1;ident=f'R{self.submitted:04d}'
                    row=dict(request_id=ident,slot=slot,stage_index=self.index,submit_mono_s=self.now,
                             timeout_s=min(self.policy['max_request_seconds'],30),repeat_key=stage.get('repeat_key'))
                    self.pending[ident]=row;actions.append(dict(kind='submit',**row));self.emit('request_submit',**row)
                self.peak=max(self.peak,len(self.pending))
        if self.state=='drain':
            if not self.pending:self.emit('natural_drain_complete',index=self.index);self.next_phase()
            elif self.now-self.window_end>=self.profile['drain_per_work_max_seconds']:self.stop('drain_deadline_unknown',now=self.now)
        if self.state=='stopping':
            max_drain=self.profile['drain_per_work_max_seconds']
            if self.pending and (self.now>=hard-cleanup or self.now-self.stopping_at>=max_drain):
                cancelled=list(self.pending)
                for ident in cancelled:
                    self.unknown_requests.append(ident);actions.append(dict(kind='cancel_client',request_id=ident))
                    result=dict(self.pending.pop(ident),status='termination_unknown',client_end_mono_s=self.now,
                                first_content_mono_s=None,usage=None,finish_reason=None,done=False,
                                server_state='unknown',error='client_cancelled_at_bounded_stop')
                    self.requests.append(result);self.emit('request_end',result=result)
                self.emit('server_completion_unconfirmed',request_ids=cancelled)
            if not self.pending:
                self.state='terminal';self.emit('run_end',reason=self.reason,server_completion='unknown' if self.unknown_requests else 'protocol_observed',
                                                 elapsed_s=self.now,cleanup_reserved_s=cleanup)
        return actions,gate

def resolve_plan(plan,name):
    p=next(dict(x) for x in plan['profiles'] if x['id']==name)
    if p.get('inherits'):
        parent=resolve_plan(plan,p['inherits']);parent.update(p);p=parent
    nominal=sum(s['seconds'] for s in p['stages'])
    work=sum(s['kind']=='work' for s in p['stages'])
    worst=nominal+p['preparation_reserve_seconds']+work*p['drain_per_work_max_seconds']+p['cleanup_reserve_seconds']
    assert nominal==p['nominal_seconds'] and worst<=p['hard_limit_seconds']
    assert all(s.get('concurrency',1)<=plan['request_policy']['max_concurrency'] for s in p['stages'])
    return dict(p,budget=dict(nominal_s=nominal,work_blocks=work,worst_reserved_s=worst,remaining_s=p['hard_limit_seconds']-worst))
