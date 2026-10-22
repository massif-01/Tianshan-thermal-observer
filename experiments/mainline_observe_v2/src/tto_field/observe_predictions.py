"""Append-only causal issuance and first-qualified-arrival labels, never future-input A."""
import math, uuid
from array import array
from collections import Counter

HORIZONS=(15,45,90)
METHODS=('G2-HOLD','B0','B1')
class Metrics:
    def __init__(self):self.n=0;self.error_sum=0.;self.abs_sum=0.;self.abs=array('d');self.under=array('d')
    def add(self,error):
        self.n+=1;self.error_sum+=error;self.abs_sum+=abs(error);self.abs.append(abs(error));self.under.append(max(-error,0.))
    def result(self):
        def q(xs):
            a=sorted(xs)
            if not a:return None
            k=(len(a)-1)*.95;lo=math.floor(k);hi=math.ceil(k);return a[lo]+(a[hi]-a[lo])*(k-lo)
        return dict(n=self.n,MAE_C=self.abs_sum/self.n if self.n else None,bias_C=self.error_sum/self.n if self.n else None,
                    P95_absolute_C=q(self.abs),P95_underestimate_C=q(self.under),max_underestimate_C=max(self.under,default=None))

class Ledger:
    def __init__(self,emit,identity,*,publication_mode='live',stride=5):
        self.emit=emit;self.identity=identity;self.mode=publication_mode;self.stride=stride
        self.last_time=None;self.pending=[];self.last_anchor=None;self.last_epoch=None;self.counts=Counter();self.stats={};self.common={}
    def _metric(self,where,key,error):where.setdefault(key,Metrics()).add(error)
    def consume(self,frame,issued,outputs,*,state_status,wall_clock):
        t=frame['t']
        if frame['identity']['run_id']!=self.identity['run_id']:raise ValueError('prediction_session_identity_conflict')
        if self.last_time is not None and t<self.last_time:raise ValueError('prediction_clock_regression')
        self.last_time=t
        epoch=frame['identity']['source_epoch'];m=frame['measurement'];tj=m['tj']
        if self.last_epoch is not None and epoch!=self.last_epoch:self.finish(t,'source_epoch_changed')
        self.last_epoch=epoch
        label=bool(frame['new_TJ'] and tj and tj['raw_valid'] and t<tj['valid_until_mono_s'])
        for batch in list(self.pending):
            target=batch['target'];expired=t>target+2
            if expired:self._missing(batch,'missing_qualified_label_within_2s');self.pending.remove(batch)
            elif label and t>=target:
                for p in batch['items']:
                    error=p['value_C']-tj['value_C']
                    row=dict(prediction_id=p['prediction_id'],**self.identity,publication_mode=self.mode,
                        horizon_s=p['horizon_s'],method=p['method'],status='scored',target_mono_s=target,
                        label_ref=tj['source_ref'],label_received_mono_s=tj['observed_mono_s'],label_value_C=tj['value_C'],
                        error_C=error,underestimate_C=max(-error,0.),source_epoch=epoch)
                    self.emit('scores',row);self._metric(self.stats,f"{p['method']}/{p['horizon_s']}",error);self.counts['scored']+=1
                methods={p['method']:p for p in batch['items']}
                if 'G2-HOLD' in methods and 'B0' in methods:
                    for name in ('G2-HOLD','B0'):
                        p=methods[name];self._metric(self.common,f"{name}/{p['horizon_s']}",p['value_C']-tj['value_C'])
                self.pending.remove(batch)
        if not label:return
        self.counts['all_valid_TJ']+=1
        if self.last_anchor is not None and t-self.last_anchor<self.stride:return
        self.last_anchor=t;self.counts['scheduled_TJ_origins']+=1
        # Bound by session hard24h and stride>=5, independent of offered source frequency.
        if self.counts['scheduled_TJ_origins']>17281:raise ValueError('prediction_origin_budget')
        by={(x['method'],x['horizon_s']):x for x in outputs}
        for horizon in HORIZONS:
            items=[]
            for method in METHODS:
                x=by.get((method,horizon),dict(value_C=None,reason='model_interface_unavailable'))
                value=x.get('value_C');late=issued>=t+horizon
                if value is not None and not math.isfinite(value):value=None;x=dict(x,reason='nonfinite_prediction')
                if late:value=None;x=dict(x,reason='issued_at_or_after_target')
                p=dict(**self.identity,prediction_id=str(uuid.uuid4()),horizon_s=horizon,method=method,value_C=value,
                    computation_id=x.get('computation_id'),calculation_started_at=x.get('calculation_started_at'),state_used=x.get('state_used'),history_refs=x.get('history_refs'),
                    reason=x.get('reason') if value is None else None,conditional_assumptions=x.get('assumptions',[]),
                    measurement_ref=tj['source_ref'],measurement_received_mono_s=tj['observed_mono_s'],measurement_utc=tj.get('observed_utc'),
                    observed_through_ref=frame['ref'],observed_through_mono_s=t,source_epoch=epoch,
                    issued_at=dict(mono_s=issued,utc=wall_clock['utc'],domain=self.identity['clock_domain'],actual_wall_mono_s=wall_clock['mono_s']),
                    target_anchor='accepted_TJ_receiver_mono',target_mono_s=t+horizon,publication_mode=self.mode,
                    control_permission=False,device_actions=False,dynamic_parameter_updates=0,
                    late=late,effective_lead_s=t+horizon-issued,origin_state_status=state_status)
                self.emit('predictions',p);self.counts[f'issued/{method}/{horizon}']+=1
                if value is not None:items.append(p);self.counts[f'valid_predictions/{method}/{horizon}']+=1
            if items:self.pending.append(dict(target=t+horizon,items=items))
    def _missing(self,batch,reason):
        for p in batch['items']:
            self.emit('scores',dict(**self.identity,prediction_id=p['prediction_id'],method=p['method'],horizon_s=p['horizon_s'],status='unscored',reason=reason,publication_mode=self.mode))
            self.counts['unscored/'+reason]+=1
    def finish(self,t,reason='session_end'):
        for batch in self.pending:self._missing(batch,'target_not_mature_at_end' if t<batch['target'] and reason=='session_end' else reason)
        self.pending.clear()
    def summary(self):
        return dict(contract='TTO-OBSERVE-SCORING-v1',publication_mode=self.mode,stride_s=self.stride,
            valid_TJ_denominator=self.counts['all_valid_TJ'],scheduled_origin_denominator=self.counts['scheduled_TJ_origins'],counts=dict(self.counts),
            per_method={k:v.result() for k,v in self.stats.items()},same_set_G2_B0={k:v.result() for k,v in self.common.items()},
            percentile='linear interpolation at (n-1)*.95; full bounded session error arrays',
            error='prediction-actual',label='first qualified received TJ at/after target within2s, same session/epoch/domain',
            statistical_unit='one session, overlapping horizons are not independent experiments')
