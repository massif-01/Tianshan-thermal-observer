"""Count-based profile. Reuses native gate, original Requester and bounded stop semantics."""
import json
from pathlib import Path
from .scheduler import Scheduler
from .gate import readiness
from .support import digest_file

PLAN=Path(__file__).with_name('plans')/'cpu-pilot.json'

def pilot_profile():
    p=json.loads(PLAN.read_text());stages=[dict(kind='background',seconds=180)]
    for wait in p['isolated_post_completion_waits_s']:
        stages.extend([dict(kind='work',seconds=30,concurrency=1),dict(kind='recovery',seconds=wait)])
    stages.extend(dict(kind='work',seconds=30,concurrency=1) for _ in range(6))
    stages.append(dict(kind='final_recovery',seconds=180))
    return dict(id='cpu-activity-pilot-v1',stages=stages,hard_limit_seconds=1200,preparation_reserve_seconds=60,
                cleanup_reserve_seconds=120,drain_per_work_max_seconds=30,nominal_worst_normal_s=1170)

def sidecar_identity(side):
    from tto.util import digest
    return digest({k:side.get(k) for k in ['transport','host','remote_python','source_script_sha256','source_config_sha256','query_target_s']})

def verify_pilot_grant(c,b,mode,duration):
    from .runtime import verify_grant
    if b.get('profile_sha256')!=digest_file(PLAN):raise ValueError('pilot plan identity mismatch')
    if b.get('cpu_pilot_verified'):raise ValueError('verified marker is internal, not a user bypass')
    if mode=='diagnose' and duration!=60:raise ValueError('capability check is one bounded 60s diagnostic')
    side=b.get('sidecar')
    if not side or side.get('query_target_s')!=.2:raise ValueError('explicit 200ms sidecar configuration required')
    if not b.get('synthetic_loopback_only'):
        import shlex
        required=['existing_control_socket','remote_python','remote_source_script','remote_source_config','remote_source_permission','command_id']
        if any(not side.get(k) for k in required) or side['command_id']!=b['command_id']:
            raise ValueError('existing Thor connection and exact source paths must be bound')
        if not side.get('source_script_sha256') or not side.get('source_config_sha256'):
            raise ValueError('source installation/configuration identity evidence missing')
        if side.get('transport')!='existing_ssh_mux' or side.get('host')!='rm01@10.10.99.98':
            raise ValueError('only existing approved Thor SSH multiplexed connection')
        # Validate before mutation; config SHA for capability is of user-visible configuration.
        if 'argv' in side:raise ValueError('arbitrary live sidecar commands are forbidden')
    verify_grant(c,b,mode,duration,pilot=True)
    if mode=='execute' and not b.get('synthetic_loopback_only'):
        # A separate, reviewable capability receipt and user decision; never inferred from a model number.
        ref=b['capability_receipt'];path=Path(ref['path'])
        if digest_file(path)!=ref['sha256']:raise ValueError('capability receipt identity mismatch')
        cap=json.loads(path.read_text())
        if cap.get('candidate_version')!='0.2.4+cpu.1' or cap.get('config_sha256')!=b['config_sha256'] or cap.get('sidecar_config_sha256')!=sidecar_identity(side):
            raise ValueError('capability identity differs from proposed pilot')
        if cap.get('qualified') is not True or cap.get('evaluation_scope') not in ('source_potential','arrival_side') or not cap.get('measured_resolution_evidence') or not cap.get('resource_check_evidence'):
            raise ValueError('capability evidence/meaning not established')
        if not b.get('capability_user_decision_evidence'):raise ValueError('separate user decision to run 12 requests required')
    b['cpu_pilot_verified']=True

class PilotScheduler(Scheduler):
    def tick(self,now,snapshot,completed=(),user_stop=False):
        if now<self.now:raise ValueError('monotonic clock moved backwards')
        self.now=float(now);actions=[];gate=readiness(snapshot,now,self.run_id,self.formal)
        ended=False
        for result in completed:
            ident=result['request_id']
            if ident not in self.pending:raise ValueError('unknown or duplicate completion')
            row=dict(self.pending.pop(ident),**result);self.requests.append(row);self.emit('request_end',result=row)
            if result['status']!='completed':self.unknown_requests.append(ident);self.stop('request_termination_unknown',now=now)
            else:ended=True
        if user_stop:self.stop('user_stop',now=now)
        if gate['explicit_stop']:self.stop('explicit_protection_or_mode_binding',now=now)
        if now>=self.profile['hard_limit_seconds']-self.profile['cleanup_reserve_seconds']:self.stop('hard_budget_cleanup_boundary',now=now)
        if self.state not in ('stopping','terminal'):
            if gate['start_allowed']:self.unready_since=None
            else:
                if self.unready_since is None:self.unready_since=now;self.emit('input_unready',layers=gate)
                if now-self.unready_since>=60:self.stop('data_or_observer_unavailable_too_long',now=now)
        if self.state=='prepare' and now>=self.profile['preparation_reserve_seconds']:
            if gate['start_allowed']:self.emit('preparation_ready',layers=gate);self.next_phase()
            else:self.stop('preparation_budget_exhausted',now=now)
        elif self.state=='stage':
            stage=self.profile['stages'][self.index]
            if stage['kind']=='work':
                if ended:self.next_phase()
                elif not self.pending and gate['start_allowed']:
                    if self.submitted>=12:self.stop('request_count_cap',now=now)
                    else:
                        self.submitted+=1;ident=f'R{self.submitted:04d}'
                        row=dict(request_id=ident,slot=0,stage_index=self.index,submit_mono_s=now,timeout_s=30,repeat_key=None)
                        self.pending[ident]=row;actions.append(dict(kind='submit',**row));self.emit('request_submit',**row)
                        self.peak=max(self.peak,len(self.pending))
            elif now>=self.window_end:self.next_phase()
        if self.state=='stopping':
            if self.pending and (now>=self.profile['hard_limit_seconds']-self.profile['cleanup_reserve_seconds'] or now-self.stopping_at>=30):
                for ident,row in list(self.pending.items()):
                    self.unknown_requests.append(ident);actions.append(dict(kind='cancel_client',request_id=ident))
                    result=dict(row,status='termination_unknown',client_end_mono_s=now,server_state='unknown',error='bounded_stop_client_only')
                    self.requests.append(result);self.emit('request_end',result=result)
                self.pending.clear();self.emit('server_completion_unconfirmed',request_ids=self.unknown_requests)
            if not self.pending:self.state='terminal';self.emit('run_end',reason=self.reason,elapsed_s=now)
        return actions,gate
