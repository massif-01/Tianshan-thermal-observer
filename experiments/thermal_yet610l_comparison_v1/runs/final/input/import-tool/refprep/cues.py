"""Read-only local trial event adapter and deterministic, model-independent reminders."""
from pathlib import Path
import time
from .files import fingerprint,now_utc,read,write,append
from .clocks import utc_seconds,iso

DEFAULT_PLAN=dict(schema='TTO-REF-CUES-v1',run_id=None,model_driven=False,max_prompts=14,
    minimum_spacing_s=30,late_grace_s=5,background_offsets_s=[30,120],sparse_mid_s=180,
    pre_continuous_offset_s=270,pre_medium_offset_s=270,
    bindings=dict(background='resident_background',sparse='sparse',pre_continuous='between_groups',
                  continuous='continuous',pre_medium=None,medium=None),
    missing_policy='record_missing_no_wait_no_rerun',actual_field_plan_confirmed=False)


def checkpoint_text(key):
    name=key.split('@')[0]
    fixed={'background-1':'背景固定计时第1点','background-2':'背景固定计时第2点',
           'sparse-fixed-middle':'稀疏组预登记中段点','continuous-before-from-idle-timer':'连续组前：前置待机固定计时点',
           'medium-before-from-idle-timer':'可选中等块前：前置待机固定计时点','continuous-after60':'连续组开始后约60秒'}
    if name in fixed:return fixed[name]
    for prefix,label in [('sparse-after','稀疏组'),('continuous-after','连续组'),('medium-after','中等块')]:
        if name.startswith(prefix):return label+'实际结束后约'+name[len(prefix):]+'秒'
    return name


def load_plan(path=None):
    plan=read(path) if path else DEFAULT_PLAN.copy()
    if plan.get('model_driven') or plan['max_prompts']>14 or plan['minimum_spacing_s']<30:
        raise ValueError('Cues must be event based, <=14 prompts and >=30s spacing')
    return plan


def read_events(path,allow_partial=False):
    import json
    text=Path(path).read_text(encoding='utf-8')
    rows=text.splitlines(keepends=True)
    if allow_partial and rows and not rows[-1].endswith('\n'):rows=rows[:-1]
    return [json.loads(s) for s in rows if s.strip()]


def actual_event(event):
    kind=event.get('event')
    if kind not in ['phase_start','phase_end','request_end','schedule_end']:return None
    if kind in ['phase_start','phase_end'] and not event.get('phase'):raise ValueError('Phase event needs phase identity')
    if 'occurred_at_utc' not in event or 'mono_s' not in event:raise ValueError('Event needs original UTC/monotonic pair')
    utc=utc_seconds(event['occurred_at_utc']);mono=float(event['mono_s'])
    key={'phase_start':'actual_start_mono_s','phase_end':'actual_end_mono_s','schedule_end':'actual_end_mono_s'}.get(kind)
    actual=float(event.get(key,mono)) if key else mono
    # Planned end/deadline never substitutes for an observed completion.
    return dict(event=kind,phase=event.get('phase'),utc_s=utc+actual-mono,mono_s=actual,
                evidence_id=fingerprint([kind,event.get('phase'),event['occurred_at_utc'],actual])[:24],
                source_time_field=key if key and key in event else 'mono_s/occurred_at_utc')


class CueEngine:
    def __init__(self,plan,replay=False,state=None):
        self.plan=plan;self.replay=replay
        self.state=state or dict(plan_sha256=fingerprint(plan),seen=[],pending=[],history=[],emitted_count=0,last_emit_s=None)
        if self.state['plan_sha256']!=fingerprint(plan):raise ValueError('Use a new cue sidecar for a changed plan')

    def log(self,status,cue,now,**extra):
        row=dict(status=status,checkpoint_ids=cue['checkpoint_ids'],
            checkpoint_labels=[checkpoint_text(k) for k in cue['checkpoint_ids']],
            prompt_due_at_utc=iso(cue['due_s']),
            original_checkpoint_due_utc={k:iso(v) for k,v in cue['original_due'].items()},
            prompt_emitted_at_utc=iso(now) if status=='prompt' and not self.replay else None,
            replay_emitted_at_utc=iso(now) if status=='prompt' and self.replay else None,
            recorded_at_utc=now_utc(),replay=self.replay,anchors=cue['anchors'],
            does_not_control_or_extend_workload=True,**extra)
        self.state['history'].append(row)
        return row

    def add(self,ident,event,offset,active_only=False):
        t=event['utc_s']+offset
        key=ident+'@'+event['evidence_id']
        cue=dict(checkpoint_ids=[key],due_s=t,original_due={key:t},anchors=[event],
                 active_phase=event['phase'] if active_only else None)
        self.state['pending'].append(cue)
        # Coalesce overlaps deterministically, retain EVERY original checkpoint and due time.
        pending=sorted(self.state['pending'],key=lambda c:(c['due_s'],c['checkpoint_ids']))
        merged=[]
        for item in pending:
            if merged and item['due_s']-merged[-1]['due_s']<self.plan['minimum_spacing_s']:
                prior=merged[-1]
                prior['checkpoint_ids']+=item['checkpoint_ids'];prior['original_due'].update(item['original_due'])
                prior['anchors']+=item['anchors'];prior['due_s']=item['due_s']
                if prior['active_phase']!=item['active_phase']:prior['active_phase']=None
            else:merged.append(item)
        self.state['pending']=merged

    def ingest(self,row,received_s):
        event=actual_event(row)
        if event is None or event['evidence_id'] in self.state['seen']:return
        self.state['seen'].append(event['evidence_id'])
        phase=event['phase'];kind=event['event'];bindings=self.plan['bindings']
        if kind=='phase_end':
            keep=[]
            for cue in self.state['pending']:
                if cue['active_phase']==phase and cue['due_s']>event['utc_s']:
                    self.log('not_collected_phase_ended',cue,received_s)
                else:keep.append(cue)
            self.state['pending']=keep
        if kind=='phase_start':
            if phase==bindings.get('background'):
                for i,offset in enumerate(self.plan['background_offsets_s']):self.add(f'background-{i+1}',event,offset,True)
            if phase==bindings.get('sparse'):self.add('sparse-fixed-middle',event,self.plan['sparse_mid_s'],True)
            if phase==bindings.get('pre_continuous'):self.add('continuous-before-from-idle-timer',event,self.plan['pre_continuous_offset_s'],True)
            if phase==bindings.get('pre_medium'):self.add('medium-before-from-idle-timer',event,self.plan['pre_medium_offset_s'],True)
            if phase==bindings.get('continuous'):self.add('continuous-after60',event,60,True)
        if kind=='phase_end':
            if phase==bindings.get('sparse'):
                for offset in [30,120]:self.add('sparse-after'+str(offset),event,offset)
            if phase in [bindings.get('continuous'),bindings.get('medium')] and phase is not None:
                prefix='continuous' if phase==bindings.get('continuous') else 'medium'
                for offset in [30,120,300]:self.add(prefix+'-after'+str(offset),event,offset)
        if kind=='schedule_end':
            for cue in self.state['pending']:self.log('not_collected_trial_ended',cue,received_s)
            self.state['pending']=[]

    def advance(self,now,startup=False):
        ready=[c for c in self.state['pending'] if c['due_s']<=now]
        self.state['pending']=[c for c in self.state['pending'] if c['due_s']>now]
        new=[]
        for cue in ready:
            if now-cue['due_s']>self.plan['late_grace_s']:
                new.append(self.log('missed_at_startup' if startup else 'missed_late_event_no_catchup',cue,now))
            elif self.state['last_emit_s'] is not None and now-self.state['last_emit_s']<self.plan['minimum_spacing_s']:
                new.append(self.log('merged_into_recent_prompt',cue,now,previous_prompt_utc=iso(self.state['last_emit_s'])))
            elif self.state['emitted_count']>=self.plan['max_prompts']:
                new.append(self.log('not_collected_prompt_cap',cue,now))
            else:
                new.append(self.log('prompt',cue,now))
                self.state['last_emit_s']=now;self.state['emitted_count']+=1
        return new


def replay_events(events,plan):
    engine=CueEngine(plan,replay=True)
    cursor=None
    for row in events:
        ev=actual_event(row)
        if ev is None:continue
        arrival=utc_seconds(row.get('arrived_at_utc',row.get('written_at_utc',row['occurred_at_utc'])))
        cursor=max(cursor,arrival) if cursor is not None else arrival
        while engine.state['pending'] and min(c['due_s'] for c in engine.state['pending'])<=cursor:
            due=min(c['due_s'] for c in engine.state['pending'])
            engine.advance(due)
        engine.ingest(row,cursor);engine.advance(cursor)
    # At EOF future points are pending, not fabricated as already emitted or collected.
    return engine.state


def watch_file(path,plan,out,follow=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    state_path=out/'reminder-state.json'
    engine=CueEngine(plan,state=read(state_path) if state_path.exists() else None)
    emitted_history=len(engine.state['history']);startup=True
    try:
        while True:
            now=utc_seconds(now_utc())
            for row in read_events(path,allow_partial=follow):engine.ingest(row,now)
            engine.advance(now,startup=startup)
            for row in engine.state['history'][emitted_history:]:
                append(out/'reminders.jsonl',row)
                if row['status']=='prompt':
                    print('测温提醒：'+'；'.join(row['checkpoint_labels'])+'。请拍/读预登记固定测点，鳍片与背板分开；来不及就记未采，不延长任务。\n引用ID：'+', '.join(row['checkpoint_ids']),flush=True)
            emitted_history=len(engine.state['history'])
            write(state_path,engine.state)
            if not follow:return engine.state
            startup=False;time.sleep(.25)
    except KeyboardInterrupt:
        write(state_path,engine.state)
        return engine.state
