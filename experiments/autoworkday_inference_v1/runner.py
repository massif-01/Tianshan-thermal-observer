"""One bounded Requester alongside a separately owned read-only observer.
No telemetry, model discovery, collector, estimator or CLI for field execution.
"""
import asyncio
from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime, timezone
import inspect
import math
import time

from make_plan import plan_digest, STAGES
from vendor.events import Adapter

@dataclass
class Control:
    binding: dict
    stop: object = lambda: False
    paused: object = lambda: False

class RealClock:
    """Production monotonic clock; origin must be the observer's same-host origin."""
    def __init__(self, origin_mono_s):
        self.origin = origin_mono_s
    def now(self):
        return time.monotonic() - self.origin
    def utc(self):
        return datetime.now(timezone.utc).isoformat()
    async def sleep(self, seconds):
        await asyncio.sleep(seconds)

class Runner:
    def __init__(self, clock, requester, plan, admission, emit, control):
        self.clock, self.requester, self.plan = clock, requester, deepcopy(plan)
        plan = self.plan
        self.binding = dict(control.binding)
        self.admission, self.emit, self.control = admission, emit, control
        if plan_digest(plan) != plan['plan_sha256']:
            raise ValueError('plan_digest_mismatch')
        if (plan['total_elapsed_seconds'] != 86400 or plan['max_concurrency'] != 1 or
            not 0 < plan['max_submissions'] <= 600 or
            not 0 < plan['max_client_inflight_seconds'] <= 18000 or
            plan['request_max_tokens'] != 256 or plan['request_protocol_budget_seconds'] != 30 or
            plan['unready_grace_seconds'] != 60):
            raise ValueError('profile_budget_mismatch')
        if [(s['id'],s['start_s'],s['end_s'],s['workload']) for s in plan['stages']] != STAGES:
            raise ValueError('stage_contract_mismatch')
        self.tasks = {t['task_id']:t for t in plan['tasks']}
        last = -1
        for slot in plan['slots']:
            due, latest, end = (slot[k] for k in ('planned_submit_s','latest_submit_s','issue_window_end_s'))
            if not (math.isfinite(due) and last < due and 7200 <= due <= latest <= min(end-30,84570)
                    and latest <= due+5 and slot['task_id'] in self.tasks
                    and slot['min_gap_after_previous_end_s'] >= 0):
                raise ValueError('invalid_frozen_opportunity')
            stage = next((s for s in plan['stages'] if s['id']==slot['stage_id']), None)
            if stage is None or stage['workload']=='no_added_requests' or not stage['start_s']<=due<end<=stage['end_s']:
                raise ValueError('request_outside_work_stage')
            last = due
        for key in ('native_run_id','observer_session_id','device_id','config_sha256','clock_domain'):
            if not control.binding.get(key):
                raise ValueError('missing_binding_'+key)
        if requester.clock is not clock or not requester.config.get('model') or requester.config.get('stream',True) is not True or requester.config.get('sampling',{}) != {}:
            raise ValueError('requester_contract_mismatch')
        self.model_id = requester.config['model']
        self.adapter = Adapter(session_id=control.binding['native_run_id'],
                               source_clock_domain=control.binding['clock_domain'],
                               observer_clock_domain=control.binding['clock_domain'],
                               complete_from_session_start=True, publication_mode='live_from_source')
        requester.emit = self._request_event
        self.submissions = self.completed = self.skipped = 0
        self.inflight_seconds = 0.0
        self.last_end = None
        self.current_submit = None
        self.unknown_server_end = False
        self.slot = None
        self.task = None
        self.halted = None
        self.pause_since = None
        self.last_admission = None
        self.stage_id = None
        self._used = False
        self._cancel_emitted = False
        self.summary = None

    def _raw(self, event, **fields):
        row = dict(event=event, mono_s=self.clock.now(), at_utc=self.clock.utc(),
                   plan_sha256=self.plan['plan_sha256'], **self.binding)
        row.update(fields)
        row['actual_elapsed_s'] = row['mono_s']
        if self.slot is not None:
            row.update(slot_id=self.slot['slot_id'], task_id=self.slot['task_id'],
                       stage_id=self.slot['stage_id'], planned_submit_s=self.slot['planned_submit_s'])
        self.emit(event, row)
        return row

    def _request_event(self, event, **fields):
        row = self._raw(event, **fields)
        if event == 'request_submit':
            self.current_submit = row['submit_mono_s']
            self.submissions += 1
        elif event == 'request_end':
            self.last_end = row['client_end_mono_s']
            self.inflight_seconds += max(0, self.last_end-row['submit_mono_s'])
            if row.get('status')=='completed' and row.get('done') and row.get('finish_reason') is not None:
                self.completed += 1
            else:
                self.unknown_server_end = True
        out = self.adapter.feed(row, received_mono_s=self.clock.now(), received_at_utc=self.clock.utc())
        if out is not None:
            # Audit schedule stays in raw stream. Predictor sees only actual arrived events.
            out.update(observer_session_id=self.binding['observer_session_id'],
                       device_id=self.binding['device_id'], config_sha256=self.binding['config_sha256'],
                       model_id=self.model_id, cache_hit=None)
            self.emit('workload_event', out)

    def _halt(self, reason):
        if self.halted is None:
            self.halted = reason
            self._raw('request_line_stop', reason=reason)

    async def _check(self):
        now = self.clock.now()
        stage = next((s for s in self.plan['stages'] if s['start_s']<=now<s['end_s']), None)
        if stage and stage['id'] != self.stage_id:
            self.stage_id = stage['id']
            self._raw('stage_observed', current_stage=self.stage_id,
                      planned_start_s=stage['start_s'], planned_end_s=stage['end_s'])
        if self.control.stop():
            self._halt('user_stop'); return 'stop'
        if now >= self.plan['total_elapsed_seconds']:
            return 'deadline'
        decision = self.admission()
        if inspect.isawaitable(decision):
            decision = await decision
        action = decision['action']
        reasons = decision.get('reasons',[])
        if action not in ('allow','pause','stop'):
            raise ValueError('invalid_admission_action')
        if self.control.paused() and action != 'stop':
            action, reasons = 'pause', ['user_pause']
        key = (action, tuple(reasons))
        if key != self.last_admission:
            self._raw('admission_change', action=action, reasons=reasons)
            self.last_admission = key
        if action == 'stop':
            self._halt('admission_stop:'+','.join(reasons)); return 'stop'
        if action == 'pause' and now >= 7200:
            if self.pause_since is None:
                self.pause_since = now
            if now-self.pause_since >= 60:
                self._halt('unready_grace_exhausted'); return 'stop'
        else:
            # Pre-checkpoint background never consumes the request-readiness grace.
            self.pause_since = None
        return action

    async def _wait_until(self, target):
        while self.clock.now() < target and not self.halted:
            await self._check()
            if self.halted:
                return
            remaining = target-self.clock.now()
            if remaining > 0:
                await self.clock.sleep(min(1, remaining))

    async def _cancel(self, reason):
        if self.task is not None and not self.task.done():
            if self.current_submit is not None and not self._cancel_emitted:
                self._request_event('request_cancel', request_id=self.slot['slot_id'], reason=reason)
                self._cancel_emitted = True
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _one(self):
        self.requester.config['messages'] = self.tasks[self.slot['task_id']]['messages']
        if self.requester.config['model'] != self.model_id:
            raise ValueError('model_changed')
        # Require a full unchanged protocol budget before admission, never shorten timeout to fit.
        self._cancel_emitted = False
        self.current_submit = None
        self.task = asyncio.create_task(self.requester.request(self.slot['slot_id'], timeout_s=30))
        while not self.task.done():
            action = await self._check()
            if self.halted and self.current_submit is None:
                # Task was queued but never submitted: cancel it before it can send.
                await self._cancel('stopped_before_submit')
                return
            elapsed = 0 if self.current_submit is None else self.clock.now()-self.current_submit
            if action == 'deadline' or elapsed >= 30:
                self._halt(self.halted or 'protocol_deadline_server_end_unknown')
                await self._cancel('protocol_deadline_server_end_unknown')
                return
            # pause/STOP blocks new work; already submitted work gets its original <=30s drain.
            await self.clock.sleep(min(1, max(0,30-elapsed)))
        try:
            record = await self.task
        except asyncio.CancelledError:
            self._halt('client_cancelled_server_end_unknown'); return
        if (record.get('status') != 'completed' or not record.get('done') or
                record.get('finish_reason') is None):
            self._halt('protocol_end_unknown_no_retry')

    async def run(self):
        if self._used:
            raise ValueError('runner_cannot_restart_or_replay_live_requests')
        self._used = True
        opened = self.requester.session is not None
        self._raw('driver_start', model_id=self.model_id,
                  source_type='real_device_automatically_constructed_workload_if_field_authorized')
        try:
            for slot in self.plan['slots']:
                self.slot = slot
                await self._wait_until(slot['planned_submit_s'])
                if self.halted:
                    break
                # Bounded opportunity windows. Never build a backlog of paused/busy slots.
                while self.clock.now() <= slot['latest_submit_s']:
                    action = await self._check()
                    if self.halted or action=='deadline':
                        break
                    remaining = self.plan['max_client_inflight_seconds']-self.inflight_seconds
                    if self.submissions >= self.plan['max_submissions'] or remaining < 30:
                        self._halt('request_budget_exhausted'); break
                    gap_ready = self.last_end is None or self.clock.now() >= self.last_end+slot['min_gap_after_previous_end_s']
                    if action == 'allow' and gap_ready:
                        if not opened:
                            await self.requester.open()
                            opened = True
                        # Opening/callback latency is real elapsed time, not extra authorization time.
                        action = await self._check()
                        now = self.clock.now()
                        if action != 'allow' or now > slot['latest_submit_s'] or now+30 > min(slot['issue_window_end_s'],84600):
                            if self.halted: break
                        else:
                            await self._one()
                            break
                    await self.clock.sleep(min(1,max(0,slot['latest_submit_s']-self.clock.now()+0.001)))
                else:
                    self.skipped += 1
                    self._raw('opportunity_skipped', reason='missed_paused_or_busy_no_catch_up')
                if self.halted:
                    break
            self.slot = None
            if not self.halted:
                await self._wait_until(86400)
        except asyncio.CancelledError:
            self._halt('driver_cancelled')
            await self._cancel('driver_cancelled')
            raise
        except Exception as exc:
            self._halt('driver_exception:'+type(exc).__name__)
            await self._cancel(self.halted)
            raise
        finally:
            await self.requester.close()
            self.summary = dict(reason=self.halted or 'completed', submissions=self.submissions,
                                scheduled_opportunities=len(self.plan['slots']),
                                not_submitted_opportunities=len(self.plan['slots'])-self.submissions,
                                schedule_window_completed=self.halted is None and self.clock.now()>=86400,
                                all_planned_requests_protocol_completed=self.completed==len(self.plan['slots']),
                                protocol_completed=self.completed, skipped_opportunities=self.skipped,
                                client_inflight_seconds=self.inflight_seconds,
                                actual_elapsed_s=self.clock.now(), requester_closed=True,
                                unknown_server_end=self.unknown_server_end,
                                gpu_busy_seconds=None, collector_instances_created=0,
                                thermal_observer_instances_created=0, requester_instances_supplied=1,
                                plan_sha256=self.plan['plan_sha256'], **self.binding)
            self._raw('driver_end', **self.summary)
        return self.summary
