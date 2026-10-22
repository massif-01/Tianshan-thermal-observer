"""Observe the one collector's processed stream; no network health poller."""
import math
import threading


class TrialHealth:
    def __init__(self):
        self.lock=threading.Lock();self.nodes=[];self.latest_source=None
        self.last_control_context=None;self.observed_abnormal=False
        self.coverage={'complete_input_s':0.,'unknown_input_s':0.,'longest_continuous_s':0.,'current_continuous_s':0.,'reasons_seconds':{}}

    def observe(self,record,out,engine):
        with self.lock:
            t=record['mono_s'];q=out['quality']
            if self.nodes:
                previous=self.nodes[-1];known=max(0,min(t,previous['valid_until'])-previous['t']) if previous['complete'] else 0
                unknown=max(0,t-previous['t']-known);self.coverage['complete_input_s']+=known;self.coverage['unknown_input_s']+=unknown
                self.coverage['current_continuous_s']+=known
                self.coverage['longest_continuous_s']=max(self.coverage['longest_continuous_s'],self.coverage['current_continuous_s'])
                if unknown:
                    reason=','.join(previous['reasons']) or 'input_validity_expired_or_source_unusable'
                    self.coverage['reasons_seconds'][reason]=self.coverage['reasons_seconds'].get(reason,0)+unknown
                    self.coverage['current_continuous_s']=0.
            if q and q['accepted']:
                self.latest_source=dict(values=dict(q['values']),ref=record['ref'],platform=q.get('input_contract'),
                                        period_known=q.get('period_known',False))
            fan=engine.fan['data'] if engine.fan else {};temp=engine.temp['data'] if engine.temp else {}
            scope,eligible,reasons=engine.control_qualification(t)
            source=self.latest_source
            source_until=engine.q.anchor_t+(engine.q.timeout_ms-engine.q.anchor_age)/1000 if source else t
            until=min(source_until,engine.fan['t']+2.5 if engine.fan else t,engine.temp['t']+7.5 if engine.temp else t)
            power=bool(source and all(isinstance(source['values'].get(k),(int,float)) and math.isfinite(source['values'][k]) for k in ('vdd_gpu','vdd_cpu_soc_mss')))
            context=(fan.get('mode'),fan.get('enabled'),temp.get('manual_mode'),temp.get('active_source'),temp.get('bound_variable'))
            known=engine.fan is not None and engine.temp is not None and all(v is not None for v in context[:4])
            changed=bool(known and self.last_control_context is not None and context!=self.last_control_context)
            if known:self.last_control_context=context
            abnormal=(any(fan.get(k) is True for k in ('guard_active','temp_stale','fault')) or fan.get('enabled') is False or
                      temp.get('manual_mode') is True or temp.get('normalized_valid') is False or
                      fan.get('mode') is not None and fan.get('mode')!='auto' or changed)
            self.observed_abnormal|=bool(abnormal)
            good=bool(source and source['platform'] and source['period_known'] and power and eligible and scope=='auto' and
                      not engine.q.blocked and not engine.q.quarantined and not engine.mixed_profiles and not abnormal)
            node=dict(t=t,ref=record['ref'],complete=good,valid_until=until,observed_abnormal=bool(abnormal),control_context_changed=changed,
                      control_mode=scope,reasons=reasons,TJ=source['values'].get('tj') if source else None,
                      source_ref=source['ref'] if source else None,fan_ref=engine.fan['ref'] if engine.fan else None,
                      P_g=source['values'].get('vdd_gpu') if source else None,P_c=source['values'].get('vdd_cpu_soc_mss') if source else None,
                      fan_age_s=t-engine.fan['t'] if engine.fan else None,PWM=fan.get('successful_duty'),gain=fan.get('controller_gain'),
                      source_age_ms=(t-engine.q.anchor_t)*1000+engine.q.anchor_age if source else None,source_period_ms=engine.c['orin']['source_sample_interval_ms'])
            self.nodes.append(node)
            # Only the 180-second check history is needed here; original facts remain in TTO logs.
            while len(self.nodes)>1 and self.nodes[1]['t']<t-180:self.nodes.pop(0)

    def snapshot(self,now):
        with self.lock:
            nodes=[dict(n) for n in self.nodes]
            coverage={**self.coverage,'reasons_seconds':dict(self.coverage['reasons_seconds'])}
            abnormal=self.observed_abnormal
        if not nodes:return dict(current_ready=False,continuous_60s=False,abnormal=False,gaps_180s=[dict(reason='no_data')],latest=None)
        last=nodes[-1];current=last['complete'] and last['valid_until']>=now;start=now-60
        recent=[n for n in nodes if n['t']>=start]
        anchor=next((n for n in reversed(nodes) if n['t']<=start),None)
        if anchor and (not recent or recent[0]['t']!=anchor['t']):recent.insert(0,anchor)
        gaps=[]
        for i,n in enumerate(nodes):
            right=nodes[i+1]['t'] if i+1<len(nodes) else now;left=max(n['t'],now-180)
            if right>left and (not n['complete'] or n['valid_until']<right):
                gaps.append(dict(from_t=max(left,n['valid_until']) if n['complete'] else left,to_t=right,ref=n['ref'],reasons=n['reasons']))
        continuous=bool(anchor and current and not any(g['to_t']>start for g in gaps))
        return dict(current_ready=bool(current),continuous_60s=continuous,abnormal=abnormal,
                    gaps_180s=gaps,latest=last,checked_at_mono_s=now,observed_span_s=now-nodes[0]['t'],
                    input_coverage=coverage,coverage_measured_until_mono_s=last['t'])
