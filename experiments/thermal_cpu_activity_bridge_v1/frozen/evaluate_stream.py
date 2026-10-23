"""Future recorded-arrival evaluation, offline only. No acquisition or scheduling.

Inputs: original ~1s qualified thermal origins; independent timestamped activity
frames; a data-role registration. Both cadence conditions use identical origins.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse
import bisect
import copy
import math
from pathlib import Path
from common import ROOT, read, lines, jsonl, write, cohort, sha
from activity import Activity, load_candidate
from analyse import score
from stream_metrics import metrics as activity_metrics


def downsample_1s(frames):
    """Causal latest-arrived at integer receiver-monotonic seconds; never backdate."""
    if not frames:return []
    times=[f['arrival_mono_s'] for f in frames]
    result=[]
    for tick in range(math.ceil(times[0]),math.floor(times[-1])+1):
        i=bisect.bisect_right(times,tick)-1
        if i<0:continue
        f=copy.deepcopy(frames[i])
        f['actual_original_arrival_mono_s']=f['arrival_mono_s']
        f['arrival_mono_s']=float(tick)
        f['cadence_condition']='causal simulated 1s delivery selection from same recorded arrivals'
        result.append(f)
    return result


def evaluate(frames,origins,config,forecast):
    times=[f['arrival_mono_s'] for f in frames]
    origin_times=[s['t'] for s in origins]
    if times!=sorted(times) or origin_times!=sorted(origin_times):
        raise ValueError('input arrival/origin regression; do not sort away original evidence')
    activity={n:Activity(config,n) for n in config['variants']}
    latest={};index=0;history=[];points=[];trace=[]
    for s in origins:
        t=s['t']
        while index<len(frames) and frames[index]['arrival_mono_s']<=t:
            f=frames[index]
            states={n:a.step(f,cutoff=t) for n,a in activity.items()}
            latest={n:(f,r) for n,r in states.items()}
            trace.append(dict(native_ref=f.get('native_ref'),arrival_mono_s=f['arrival_mono_s'],states=states))
            index+=1
        if not s['source_valid'] or (history and (s['epoch']!=history[-1]['epoch'] or t-history[-1]['t']>5)):
            history=[]
        if s['source_valid']:history.append(s)
        j=bisect.bisect_left([h['t'] for h in history],t-30)
        slope=(s['current']-history[j]['current'])/(t-history[j]['t']) if j<len(history) and t-history[j]['t']>=10 else None
        for h in (15,45,90):
            target=bisect.bisect_left(origin_times,t+h)
            label=None;reject=None
            if not s['source_valid']:reject='origin_source_invalid'
            elif target>=len(origins) or origins[target]['t']>t+h+2:reject='no_TJ_answer'
            else:
                a=origins[target]
                if not a['source_valid']:reject='target_source_invalid'
                elif a['epoch']!=s['epoch'] or a['source_key']!=s['source_key']:reject='source_identity_or_validity_boundary'
                else:label=dict(ref=a['ref'],t=a['t'],value=a['current'],offset_s=a['t']-t-h)
            predictions={};states={};used={}
            if s['source_valid']:
                predictions['B0']=s['current']
                if slope is not None:predictions['B1']=s['current']+h*slope
                hold=forecast.predict(s.get('thermal'),'HOLD',h)
                if hold is not None:predictions['G2-HOLD']=hold
                for name in activity:
                    state='UNKNOWN'
                    if name in latest:
                        f,r=latest[name]
                        # Clock/epoch equality is required, not inferred by matching curves.
                        if (f.get('arrival_clock_id')==s.get('arrival_clock_id') and f.get('epoch')==s['epoch']
                                and r['supported_until_mono_s'] is not None and t<r['supported_until_mono_s']):
                            state=r['state']
                            used[name]=f.get('native_ref')
                    states[name]=state
                    value=forecast.predict(s.get('thermal'),state,h)
                    if value is not None:predictions[name]=value
            points.append(dict(ref=s['ref'],t=t,h=h,label=label,label_rejection=reject,prediction=predictions,
                activity=states,activity_input_refs=used,source_valid=s['source_valid'],
                future_activity_or_inputs_used=False))
    methods=['B0','B1','G2-HOLD']+list(activity)
    tables=[];coverage=[]
    for h in (15,45,90):
        rows=[r for r in points if r['h']==h]
        common=[r for r in rows if r['label'] and all(n in r['prediction'] for n in methods)]
        tables.append(dict(h=h,n=len(common),cohort_SHA256=cohort(common),
            errors={n:score([r['prediction'][n]-r['label']['value'] for r in common]) for n in methods}))
        for n in methods:
            own=[r for r in rows if r['label'] and n in r['prediction']]
            coverage.append(dict(h=h,method=n,valid_labels=sum(r['label'] is not None for r in rows),scored=len(own),
                predictions=sum(n in r['prediction'] for r in rows),source_valid_origins=sum(r['source_valid'] for r in rows),
                cohort_SHA256=cohort(own),errors=score([r['prediction'][n]-r['label']['value'] for r in own])))
    return dict(points=points,common=tables,coverage=coverage,activity_trace=trace)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frames',type=Path,required=True)
    ap.add_argument('--origins',type=Path,required=True)
    ap.add_argument('--registration',type=Path,required=True)
    ap.add_argument('--actual-events',type=Path,help='optional actual client event refs in matching receiver monotonic clock')
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();config,forecast=load_candidate()
    registration=read(a.registration)
    if registration['candidate_sha256']!=sha(ROOT/'candidate.json') or registration['analysis_spec_sha256']!=sha(ROOT/'analysis-spec.json'):
        raise ValueError('registration must bind the frozen candidate and spec')
    if registration.get('saw_new_data_for_parameter_selection'):
        role='development_exploration'
    else:
        role=registration['declared_role']
    if registration['run_id']=='5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3' and role=='independent_confirmation':
        raise ValueError('old run is already development')
    frames=list(lines(a.frames));origins=list(lines(a.origins))
    if any(not math.isfinite(f.get('arrival_mono_s',math.nan)) for f in frames):
        raise ValueError('no receiver arrival: source-side potential only, not arrival-side scoring')
    a.output.mkdir(parents=True,exist_ok=False)
    results={}
    events=list(lines(a.actual_events)) if a.actual_events else None
    for cadence,fs in [('actual-arrived',frames),('causal-1s-decimation',downsample_1s(frames))]:
        result=evaluate(fs,origins,config,forecast);results[cadence]=result
        for key,rows in result.items():
            jsonl(a.output/f'{cadence}-{key}.jsonl',rows)
        if events is not None:
            fs=fs[:len(result['activity_trace'])]
            write(a.output/f'{cadence}-activity-metrics.json',activity_metrics(fs,result['activity_trace'],events,list(config['variants'])))
    # A cadence difference must also be scored on the intersection of origins/labels
    # across both cadence conditions, not just on each condition's own coverage.
    joint=[]
    actual={ (r['ref'],r['h']):r for r in results['actual-arrived']['points'] }
    coarse={ (r['ref'],r['h']):r for r in results['causal-1s-decimation']['points'] }
    methods=['B0','B1','G2-HOLD']+list(config['variants'])
    for h in (15,45,90):
        keys=[k for k,r in actual.items() if r['h']==h and r['label'] and k in coarse
            and coarse[k]['label']==r['label'] and all(n in r['prediction'] and n in coarse[k]['prediction'] for n in methods)]
        joint.append(dict(h=h,n=len(keys),cohort_SHA256=cohort([actual[k] for k in keys]),
            conditions={name:{n:score([data[k]['prediction'][n]-data[k]['label']['value'] for k in keys]) for n in methods}
                for name,data in [('actual-arrived',actual),('causal-1s-decimation',coarse)]}))
    write(a.output/'cadence-joint-common.json',joint)
    write(a.output/'data-role-and-sources.json',dict(registration=registration,effective_role=role,
        inputs={str(p):sha(p) for p in [a.frames,a.origins,a.registration]},
        theta_fits=0,labels_interpolated=False,device_access=False,
        field_time_resolution_verified_by_this_program=False,
        note='declaration cannot by itself establish source timing validity; retain source windows/arrival evidence and unknowns'))


if __name__=='__main__':
    main()
