"""Fixed single-process midload schedule; injectable clock enables finite offline tests."""
import asyncio
import json
import time
from datetime import datetime,timezone


PHASES=[('resident_background','passive',600),('M20','work',20),('cooldown_1','passive',420),('M60','work',60),('cooldown_2','passive',600),('M180','work',180),('final_cooldown','passive',600)]


class RealClock:
    def now(self):return time.monotonic()
    def utc(self):return datetime.now(timezone.utc).isoformat()
    async def sleep(self,seconds):await asyncio.sleep(seconds)


async def run_schedule(clock,health,requester,stop,collector_task,emit,phases=PHASES,hard_limit_s=2700,max_requests=256,start_mono=None):
    start=clock.now() if start_mono is None else start_mono;hard=start+hard_limit_s;cleanup_start=hard-min(10,hard_limit_s*.05)
    count=0;last_end=None;results=[];reason='completed';plan_cursor=start;checks=[]
    def stopping():
        if stop.is_set() or collector_task.done():return 'collector_or_operator_stop'
        if clock.now()>=cleanup_start:return 'hard_deadline'
        if health.snapshot(clock.now())['abnormal']:return 'observed_abnormal'
        return None
    for phase,kind,duration in phases:
        if stopping():reason=stopping();break
        phase_start=clock.now();deadline=phase_start+duration
        emit('phase_start',phase=phase,kind=kind,planned_start_mono_s=plan_cursor,actual_start_mono_s=phase_start,window_deadline_mono_s=deadline,duration_s=duration)
        if phase=='resident_background':print('正在记录背景温度，暂不运行任务。',flush=True)
        if kind=='passive':
            check_done=False
            while clock.now()<deadline:
                if stopping():reason=stopping();break
                await clock.sleep(min(.5,deadline-clock.now(),max(0,cleanup_start-clock.now())))
                if phase=='resident_background' and not check_done and clock.now()>=phase_start+180:
                    check=health.snapshot(clock.now());checks.append(check);emit('background_check',phase=phase,health=check);check_done=True
            if reason!='completed':break
        else:
            check=health.snapshot(clock.now());checks.append(check);emit('work_admission',phase=phase,health=check)
            if not check['continuous_60s']:
                reason='background_inputs_incomplete';print('风扇数据暂时不完整，本轮先不启动负载；记录已保存。',flush=True);break
            print('正在运行'+phase+'工作段，结束后会继续记录降温过程。',flush=True)
            paused=False
            while clock.now()<deadline:
                status=stopping()
                if status:reason=status;break
                check=health.snapshot(clock.now())
                if not check['current_ready']:
                    if not paused:emit('admission_paused',phase=phase,health=check);paused=True
                    await clock.sleep(min(.25,deadline-clock.now()));continue
                if paused:emit('admission_resumed',phase=phase,health=check);paused=False
                if count>=max_requests:reason='request_count_limit';break
                count+=1;ident=f'{phase}-{count:03d}'
                now=clock.now();timeout=min(30,cleanup_start-now,deadline+30-now)
                emit('work_gap',phase=phase,request_id=ident,gap_s=now-last_end if last_end is not None else None,health=check)
                job=asyncio.create_task(requester.request(ident,timeout_s=timeout));abort_after=None
                while not job.done():
                    if stop.is_set() or collector_task.done() or clock.now()>=min(cleanup_start,deadline+30,now+30):
                        reason='collector_or_operator_stop' if stop.is_set() or collector_task.done() else 'request_termination_unknown'
                        job.cancel();await asyncio.gather(job,return_exceptions=True);break
                    if health.snapshot(clock.now())['abnormal']:abort_after='observed_abnormal'
                    await clock.sleep(min(.1,max(0,min(cleanup_start,deadline+30,now+30)-clock.now())))
                if reason!='completed':break
                result=await job;results.append(result);last_end=result['client_end_mono_s']
                if result['status']!='completed':reason='request_termination_unknown';break
                if abort_after:reason=abort_after;break
            if reason!='completed':break
        emit('phase_end',phase=phase,actual_end_mono_s=clock.now(),planned_end_mono_s=plan_cursor+duration,
             actual_duration_s=clock.now()-phase_start,last_request_end_mono_s=last_end)
        plan_cursor+=duration
    if reason=='request_termination_unknown':print('已停止发起新请求。最后一条请求是否结束仍未确认，请不要再次启动测试。',flush=True)
    emit('schedule_end',reason=reason,requests=count,actual_end_mono_s=clock.now(),hard_deadline_mono_s=hard)
    return dict(status='completed' if reason=='completed' else 'stopped',stop_reason=reason,requests=count,completed_requests=sum(r['status']=='completed' for r in results),
                elapsed_schedule_s=clock.now()-start,hard_limit_s=hard_limit_s,cleanup_reserved_s=hard-cleanup_start,checks=checks,
                server_request_completion='unknown' if reason in ('request_termination_unknown','collector_or_operator_stop') else 'protocol_observed_for_completed_requests_only',
                new_model_training='not_performed',control_authorization='none')
