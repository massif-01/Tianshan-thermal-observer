"""TTO-EVAL-AVAIL-v2.0: use the original source processor, separate A/B availability."""
import bisect
import copy
import json
import math
from pathlib import Path
from tto.config import load_config,merge,validate
from tto.engine import engine_for

VERSION='TTO-EVAL-AVAIL-v2.0'


def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)


def replay_evidence(run):
    run=Path(run);manifest=json.loads((run/'manifest.json').read_text());config=load_config(environ={})
    saved=copy.deepcopy(manifest['config'])
    for section in ('orin','tianshan'):saved[section]['headers_file']=saved[section]['ca_file']=None
    merge(config,saved);validate(config);engine=engine_for(config,record_schema=2)
    samples=[];nodes=[];isolated=set();source_epoch=0;last_identity=None;last_context=None;latest=None
    raw_count=0
    for file in sorted(run.glob('observations-*.jsonl')):
        for line in file.open():
            r=json.loads(line);raw_count+=1
            assert r['ref']==f"{manifest['observer_run_id']}/observation:{raw_count}"
            assert not nodes or r['mono_s']>=nodes[-1]['t']
            previous_blocked=engine.q.blocked
            previous_long_gap=engine.q.counts['boundary_long_gap']
            out=engine.process(r);q=out['quality'];t=r['mono_s']
            if (engine.q.blocked and not previous_blocked) or engine.q.counts['boundary_long_gap']>previous_long_gap:
                source_epoch+=1
            if r['kind']=='boundary' or r.get('preceding_queue_gap'):source_epoch+=1
            if q:
                if q.get('invalidated_segment') is not None:isolated.add(q['invalidated_segment'])
                if q.get('lifecycle_violation') or q['reason'] in ('identity_conflict','sequence_regression','retired_stream','stale_or_missing_tj','stale_duplicate','invalid_numeric_contract'):
                    source_epoch+=1
                if q['accepted']:
                    identity=(tuple(q['key'][:2]),r.get('connection_epoch'),repr(engine.q.lifecycle_settings),engine.q.lifecycle_uuid)
                    if last_identity is not None and identity!=last_identity:source_epoch+=1
                    last_identity=identity;s=engine.features.history[-1]
                    latest=dict(ref=r['ref'],t=t,utc=r['received_at_utc'],values=dict(s['values']),segment=s['segment'],source_epoch=source_epoch,
                                source_identity=repr(identity),sample_seq=r['payload']['telemetry_meta']['sample_seq'],
                                target_valid=q.get('period_known',False) and q.get('input_contract') is not None,
                                control_eligible=s['control_eligible'])
                    samples.append(latest)
            fan=engine.fan['data'] if engine.fan else {};temp=engine.temp['data'] if engine.temp else {}
            _,eligible,reasons=engine.control_qualification(t)
            context=(fan.get('mode'),fan.get('enabled'),temp.get('manual_mode'),temp.get('active_source'),temp.get('bound_variable'))
            context_known=engine.fan is not None and engine.temp is not None and all(v is not None for v in context[:4])
            changed=bool(context_known and last_context is not None and context!=last_context)
            if context_known:last_context=context
            abnormal=(any(fan.get(k) is True for k in ('temp_stale','guard_active','fault')) or
                      fan.get('mode') is not None and fan.get('mode')!='auto' or fan.get('enabled') is False or
                      temp.get('manual_mode') is True or temp.get('normalized_valid') is False or changed)
            source_until=(engine.q.anchor_t+(engine.q.timeout_ms-engine.q.anchor_age)/1000) if latest else t
            power_ok=bool(latest and all(finite(latest['values'].get(k)) for k in ('vdd_gpu','vdd_cpu_soc_mss')) and not engine.q.blocked)
            deadline=min(source_until,engine.fan['t']+2.5 if engine.fan else t,engine.temp['t']+7.5 if engine.temp else t)
            complete=bool(power_ok and eligible and fan.get('mode')=='auto' and not abnormal and latest['target_valid'])
            nodes.append(dict(t=t,ref=r['ref'],complete=complete,valid_until=deadline,source_until=source_until,
                              power_ok=power_ok,control_eligible=eligible,mode=fan.get('mode'),
                              observed_abnormal_or_changed=bool(abnormal),context_change=changed,
                              reasons=reasons,fan_ref=engine.fan['ref'] if engine.fan else None,
                              fan_age_s=t-engine.fan['t'] if engine.fan else None,
                              temp_ref=engine.temp['ref'] if engine.temp else None,power_ref=latest['ref'] if latest else None,
                              source_epoch=source_epoch))
    for s in samples:
        if s['segment'] in isolated:s['target_valid']=False;s['isolation_reason']='original_source_isolation'
    return dict(run_id=manifest['observer_run_id'],samples=samples,nodes=nodes,isolated_segments=sorted(isolated),
                _sample_times=[s['t'] for s in samples],_node_times=[n['t'] for n in nodes])


def interval_context(evidence,start,end):
    nodes=evidence['nodes'];times=evidence['_node_times'];lo=bisect.bisect_right(times,start)-1;hi=bisect.bisect_right(times,end)
    if lo<0:return dict(complete=False,control_context='unclassified_gap',reasons=['no_origin_context'])
    used=nodes[lo:hi];complete=True;abnormal=False;reasons=[]
    for i,n in enumerate(used):
        left=max(start,n['t']);right=min(end,used[i+1]['t'] if i+1<len(used) else end)
        if n['observed_abnormal_or_changed']:abnormal=True;reasons.append(dict(ref=n['ref'],reason='observed_abnormal_or_changed'))
        if right>left and (not n['complete'] or n['valid_until']<right-1e-9):
            complete=False;reasons.append(dict(ref=n['ref'],reason='input_or_aux_context_gap',from_t=left,to_t=right,valid_until=n['valid_until'],details=n['reasons']))
    context='observed_abnormal_or_changed' if abnormal else 'confirmed_normal' if complete else 'aux_observation_gap'
    return dict(complete=complete,control_context=context,reasons=reasons)


def target_label(evidence,origin_ref,t,h,tolerance=2):
    lookup={s['ref']:s for s in evidence['samples']};origin=lookup.get(origin_ref)
    if not origin or not origin['target_valid']:return None,'origin_source_invalid'
    i=bisect.bisect_left(evidence['_sample_times'],t+h)
    if i>=len(evidence['samples']) or evidence['samples'][i]['t']>t+h+tolerance:return None,'no_TJ_answer'
    answer=evidence['samples'][i]
    if not answer['target_valid']:return None,'target_source_isolated_or_invalid'
    if answer['source_epoch']!=origin['source_epoch'] or answer['source_identity']!=origin['source_identity']:return None,'source_identity_or_validity_boundary'
    return dict(value=answer['values']['tj'],ref=answer['ref'],t=answer['t'],offset_s=answer['t']-t-h),None


def origin_method_valid(evidence,prediction,method):
    t=prediction['t'];i=bisect.bisect_left(evidence['_sample_times'],t)
    if i>=len(evidence['samples']):return False
    origin=evidence['samples'][i]
    if origin['ref']!=prediction['ref'] or not origin['target_valid']:return False
    window=0 if method=='B0' else 10 if method=='B1' else 60
    if not window:return True
    lo=bisect.bisect_right(evidence['_sample_times'],t-window)-1
    if lo<0 or t-window-evidence['samples'][lo]['t']>2:return False
    history=evidence['samples'][lo:i+1]
    if any(not s['target_valid'] or s['source_epoch']!=origin['source_epoch'] for s in history):return False
    if any(b['t']-a['t']>5 for a,b in zip(history,history[1:])):return False
    if method in ('R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30'):
        return interval_context(evidence,t-window,t)['complete'] and origin['control_eligible'] and finite(origin['values'].get('duty'))
    return True


def assess_saved_prediction(evidence,prediction):
    label,reason=target_label(evidence,prediction['ref'],prediction['t'],prediction['h'])
    nominal=interval_context(evidence,prediction['t'],prediction['t']+prediction['h'])
    outcome=interval_context(evidence,prediction['t'],label['t']) if label else nominal
    return dict(rule_version=VERSION,target_valid=label is not None,label=label,target_rejection=reason,
                origin_inputs_valid={method:origin_method_valid(evidence,prediction,method) for method in prediction['B']},
                original_prediction_unavailable=prediction.get('unavailable',{}),
                future_inputs_complete=nominal['complete'],control_context=outcome['control_context'],
                context_evidence=outcome['reasons'],A_eligible=label is not None and nominal['complete'],
                B_values=copy.deepcopy(prediction['B']),prediction_source='frozen_offline_replay_not_historical_live_emission')
