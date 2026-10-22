"""Finite old-development comparison and event stratification. No refit or device I/O."""
import os
for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_key]='1'
import argparse
import bisect
import collections
import datetime as dt
import platform
import resource
import sys
import time
import numpy as np
import scipy
from common import ROOT, read, lines, write, jsonl, sha, cohort
from activity import load_candidate, Processor
from adapter import old_frames


def seconds(s):
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()


def score(errors):
    e=np.asarray(errors,float)
    if not len(e):
        return dict(n=0,MAE_C=None,P95_absolute_C=None,P95_under_C=None,max_under_C=None,bias_C=None,fraction_under_gt2C=None)
    u=np.maximum(-e,0)
    return dict(n=len(e),MAE_C=float(abs(e).mean()),P95_absolute_C=float(np.percentile(abs(e),95)),
        P95_under_C=float(np.percentile(u,95)),max_under_C=float(u.max()),bias_C=float(e.mean()),
        fraction_under_gt2C=float((u>2).mean()))


def request_reference(root):
    requests=list(lines(root/'inputs/field/requests.jsonl'))
    protocol=list(lines(root/'inputs/field/protocol.jsonl'))
    ends={r['request_id']:r for r in protocol if r['event']=='protocol_DONE'}
    result=[]
    for r in requests:
        end=ends.get(r['request_id'])
        result.append(dict(request_id=r['request_id'],stage_index=r['stage_index'],
            submit_utc=r['submitted_at_utc'],submit_wall=seconds(r['submitted_at_utc']),
            done_utc=end['at_utc'] if end else None,done_wall=seconds(end['at_utc']) if end else None,
            submit_source='field/requests.jsonl:'+r['request_id'],done_source='field/protocol.jsonl:protocol_DONE:'+r['request_id'],
            role='dependent client protocol reference, not GPU kernel activity truth'))
    return result


def block_reference(requests,frames,outputs):
    blocks=[]
    for stage in sorted({r['stage_index'] for r in requests}):
        rs=[r for r in requests if r['stage_index']==stage]
        start=min(r['submit_wall'] for r in rs)
        end=max(r['done_wall'] for r in rs if r['done_wall'] is not None)
        onset=next((f for f,o in zip(frames,outputs) if start <= seconds(f['arrived_at_utc']) <= end
                    and o['variants']['INPUT-BASE']['activity']['state']=='ACTIVE'),None)
        blocks.append(dict(stage=stage,start=start,end=end,
            first_submit_ref=min(rs,key=lambda r:r['submit_wall'])['submit_source'],
            last_done_ref=max(rs,key=lambda r:r['done_wall'] or -1)['done_source'],
            first_BASE_arrived_active_wall=seconds(onset['arrived_at_utc']) if onset else None,
            first_BASE_active_ref=onset['native_ref'] if onset else None,requests=len(rs)))
    return blocks


def stratum(wall,blocks):
    for b in blocks:
        if b['start'] <= wall < b['end']:
            onset=b['first_BASE_arrived_active_wall']
            if onset is None or wall < onset:
                return 'submitted_not_yet_observed'
            if wall < onset+15:
                return 'observed_startup_15s'
            return 'sustained'
    if any(0 < b['start']-wall <= 90 for b in blocks):
        return 'pre_submit_90s'
    if any(0 <= wall-b['end'] <= 90 for b in blocks):
        return 'after_DONE_90s'
    return 'background'


def stale_audit(root,out):
    raw=list(lines(root/'inputs/inputs/native/observations-0001.jsonl'))
    fans=[r for r in raw if r['kind']=='fan']
    index=next(i for i,r in enumerate(fans) if r['ref'].endswith('observation:4682'))
    a,b,c=fans[index-1:index+2]
    f=b['payload']['data']['fans'][0]
    assert f['temp_stale'] is True and f['auto_state']=='stale' and f['duty']==25
    assert a['payload']['data']['fans'][0]['duty']==66 and c['payload']['data']['fans'][0]['duty']==37
    audit=dict(role='new explanatory addendum; old scores and control policy unchanged',
        raw_records=[a,b,c],start_mono_s=b['mono_s'],recovery_observation_mono_s=c['mono_s'],
        observed_stale_feedback=True,HTTP_returned_success=True,successful_PWM_percent=25,
        packet_temp_valid=b['payload']['data']['temp_valid'],
        interval_s=c['mono_s']-b['mono_s'],
        interpretation='explicit temp_stale feedback, not merely unknown context; observed recovery does not identify the exact unobserved recovery instant')
    write(out/'stale4682-addendum.json',audit)
    return audit


def at_state(frame_times,frames,outputs,name,wall):
    i=bisect.bisect_right(frame_times,wall)-1
    if i<0:
        return 'UNKNOWN',None
    f,o=frames[i],outputs[i]['variants'][name]['activity']
    until=o['supported_until_mono_s']
    if until is None or wall-frame_times[i] >= until-f['arrival_mono_s']:
        return 'UNKNOWN',None
    return o['state'],f['native_ref']


def activity_metrics(requests,blocks,frames,outputs,out,config):
    walls=[seconds(f['arrived_at_utc']) for f in frames]
    native_refs=[f['native_ref'] for f in frames]
    onset_rows=[]; per_request=[]; totals=[]; discrepancy_intervals_all=[]
    end=walls[-1]
    def busy(t):
        return any(r['submit_wall']<=t<(r['done_wall'] if r['done_wall'] is not None else end) for r in requests)
    for name in config['variants']:
        known_s=unknown_s=background_active_s=settled_background_active_s=0.
        false_events=settled_false_events=0; prev_background_active=prev_settled=False
        discrepancy_intervals=[]
        total_s=walls[-1]-walls[0]
        for i,(f,o) in enumerate(zip(frames,outputs)):
            left=walls[i]
            right=walls[i+1] if i+1<len(walls) else left
            state=o['variants'][name]['activity']
            until=state['supported_until_mono_s']
            supported=min(right,left+max(0,until-f['arrival_mono_s'])) if until is not None else left
            cuts={left,supported,right}
            for r in requests:
                for t in (r['submit_wall'],r['done_wall']):
                    if t is not None and left<t<right:cuts.add(t)
            for b in blocks:
                if left<b['end']+3<right:cuts.add(b['end']+3)
            cuts=sorted(cuts)
            for a,b in zip(cuts,cuts[1:]):
                current=state['state'] if a<supported else 'UNKNOWN'
                known_s+=(b-a)*(current!='UNKNOWN')
                unknown_s+=(b-a)*(current=='UNKNOWN')
                active_bg=current=='ACTIVE' and not busy((a+b)/2)
                settled=False
                if active_bg:
                    background_active_s+=b-a
                    # A separate settled-background diagnostic avoids treating the
                    # tiny protocol gap between serial requests as known GPU idle.
                    if not any(q['start'] <= (a+b)/2 < q['end']+3 for q in blocks):
                        settled_background_active_s+=b-a
                        settled=True
                    discrepancy_intervals.append(dict(variant=name,start_wall=a,end_wall=b,
                        seconds=b-a,source_ref=f['native_ref'],settled_background=settled,
                        interpretation='no client request in flight; true GPU inactivity unknown'))
                if active_bg and not prev_background_active:false_events+=1
                if settled and not prev_settled:settled_false_events+=1
                prev_background_active=active_bg
                prev_settled=settled
        for b in blocks:
            idxs=[i for i,t in enumerate(walls) if b['start']<=t<=b['end']]
            active=[i for i in idxs if outputs[i]['variants'][name]['activity']['state']=='ACTIVE']
            before,ref=at_state(walls,frames,outputs,name,b['start'])
            first=active[0] if active else None
            release=next((i for i,t in enumerate(walls) if t>=b['end'] and outputs[i]['variants'][name]['activity']['state']=='IDLE'),None)
            transitions=[i for i in idxs if outputs[i]['variants'][name]['activity']['transition']
                and outputs[i]['variants'][name]['activity']['state']=='ACTIVE']
            known=any(outputs[i]['variants'][name]['activity']['state']!='UNKNOWN' for i in idxs)
            onset_rows.append(dict(variant=name,stage=b['stage'],submit_wall=b['start'],done_wall=b['end'],
                state_at_submit=before,state_at_submit_ref=ref,
                status='already_active' if before=='ACTIVE' else ('detected' if first is not None else ('miss' if known else 'unknown')),
                first_after_submit_ref=native_refs[first] if first is not None else None,
                delay_s=walls[first]-b['start'] if first is not None and before!='ACTIVE' else None,
                repeated_ACTIVEs_during_block=max(0,len(transitions)-1),
                first_IDLE_after_DONE_ref=native_refs[release] if release is not None else None,
                recovery_delay_s=walls[release]-b['end'] if release is not None else None,
                semantics='N305 arrived information relative to client event; not physical CPU/GPU onset'))
        for r in requests:
            state,ref=at_state(walls,frames,outputs,name,r['submit_wall'])
            idxs=[i for i,t in enumerate(walls) if r['submit_wall']<=t<=(r['done_wall'] or end)]
            active=next((i for i in idxs if outputs[i]['variants'][name]['activity']['state']=='ACTIVE'),None)
            known=any(outputs[i]['variants'][name]['activity']['state']!='UNKNOWN' for i in idxs)
            per_request.append(dict(variant=name,request_id=r['request_id'],state_at_submit=state,source_ref=ref,
                result='already_active' if state=='ACTIVE' else ('detected' if active is not None else ('miss' if known else 'unknown')),
                first_active_ref=native_refs[active] if active is not None else None,
                delay_s=walls[active]-r['submit_wall'] if active is not None and state!='ACTIVE' else None,
                independent_thermal_episode=False))
        totals.append(dict(variant=name,frames=len(frames),observed_span_s=total_s,known_s=known_s,unknown_s=unknown_s,
            coverage_fraction=known_s/total_s,
            active_while_no_client_inflight_s=background_active_s,
            no_client_inflight_active_events=false_events,
            settled_background_active_s=settled_background_active_s,
            settled_background_active_events=settled_false_events,
            false_trigger_truth='client-reference discrepancy only; true inference/GPU label unknown',
            all_request_results=dict(collections.Counter(r['result'] for r in per_request if r['variant']==name))))
        discrepancy_intervals_all.extend(discrepancy_intervals)
    write(out/'activity-metrics.json',dict(groups=totals,block_onsets=onset_rows,
        independent_real_episodes=1,recorded_dependent_workblock_onsets=len(blocks),physical_lead_ms=None,
        high_frequency_real_evidence=False,all_variants_same_arrival_cadence=True))
    jsonl(out/'all-request-activity-reference.jsonl',per_request)
    jsonl(out/'background-active-intervals.jsonl',discrepancy_intervals_all)
    return onset_rows


def evaluate(root,out):
    wall_start=time.perf_counter(); cpu_start=time.process_time()
    c,f=load_candidate(root)
    frames=list(old_frames(root)); processor=Processor(c,f)
    outputs=[processor.process(frame) for frame in frames]
    assert len(frames)==2706
    jsonl(out/'feature-frames.jsonl',frames)
    jsonl(out/'activity-and-candidate-predictions.jsonl',outputs)
    mapping={f['native_ref']: (f,o) for f,o in zip(frames,outputs)}
    requests=request_reference(root)
    jsonl(out/'actual-client-events.jsonl',requests)
    blocks=block_reference(requests,frames,outputs)
    write(out/'block-onset-reference.json',blocks)
    activity_metrics(requests,blocks,frames,outputs,out,c)
    stale=stale_audit(root,out)
    originals=list(lines(root/'inputs/results/predictions.jsonl'))
    points=[]; max_hold_diff=0.
    for r in originals:
        frame,derived=mapping.get(r['ref'],(None,None))
        row=dict(ref=r['ref'],t=r['t'],utc=r['utc'],h=r['h'],label=r['label'],
            label_rejection=r['label_rejection'],phase=r['phase'],source_valid=r['source_valid'],
            origin_context=r['origin_context'],prediction={},activity={},
            posthoc_stratum=stratum(seconds(r['utc']),blocks),
            posthoc_stale_intersection=r['t']<=stale['recovery_observation_mono_s'] and r['t']+r['h']>=stale['start_mono_s'],
            old_common=bool(r['label'] and 'B1' in r['baselines'] and all(b in r['B_HOLD'] for b in ['AUGMENTED-KF','CONDITIONAL-HOLD','QS','LP30','LP120'])))
        row['prediction'].update(r['baselines'])
        if 'AUGMENTED-KF' in r['B_HOLD']:
            row['prediction']['G2-HOLD']=r['B_HOLD']['AUGMENTED-KF']
            assert frame is not None
            val=f.predict(frame['thermal'],'HOLD',r['h'])
            max_hold_diff=max(max_hold_diff,abs(val-row['prediction']['G2-HOLD']))
        if derived:
            for name, result in derived['variants'].items():
                row['activity'][name]=result['activity']['state']
                val=result['temperature_C'][str(r['h'])]
                if val is not None:row['prediction'][name]=val
        points.append(row)
    assert max_hold_diff<1e-8
    jsonl(out/'temperature-points.jsonl',points)
    methods=['B0','B1','G2-HOLD']+list(c['variants'])
    common_tables=[];coverage=[];sensitivity=[]
    for h in (15,45,90):
        base=[r for r in points if r['h']==h]
        common=[r for r in base if r['old_common'] and all(n in r['prediction'] for n in methods)]
        strata=['all']+sorted({r['posthoc_stratum'] for r in base})
        for category in strata:
            rows=[r for r in common if category=='all' or r['posthoc_stratum']==category]
            common_tables.append(dict(h=h,posthoc_stratum=category,n=len(rows),cohort_SHA256=cohort(rows),
                errors={n:score([r['prediction'][n]-r['label']['value'] for r in rows]) for n in methods}))
        for name in methods:
            rows=[r for r in base if r['label'] and name in r['prediction']]
            coverage.append(dict(h=h,method=name,source_valid_origins=sum(r['source_valid'] for r in base),
                total_origins=len(base),valid_labels=sum(r['label'] is not None for r in base),
                predictions=sum(name in r['prediction'] for r in base),scored=len(rows),cohort_SHA256=cohort(rows),
                own_score=score([r['prediction'][name]-r['label']['value'] for r in rows]),
                original_rejections=dict(collections.Counter(r['label_rejection'] for r in base if not r['label']))))
        for criterion in ('origin_context','posthoc_stale_intersection'):
            for value in sorted({r[criterion] for r in common},key=str):
                rows=[r for r in common if r[criterion]==value]
                sensitivity.append(dict(h=h,criterion=criterion,value=value,n=len(rows),cohort_SHA256=cohort(rows),
                    role='new descriptive sensitivity, no old score rewritten',
                    errors={n:score([r['prediction'][n]-r['label']['value'] for r in rows]) for n in methods}))
    write(out/'temperature-common.json',common_tables)
    write(out/'temperature-coverage.json',coverage)
    write(out/'stale-and-context-sensitivity.json',sensitivity)
    r45=[r for r in originals if r['h']==45 and r['label'] and 'B1' in r['baselines'] and all(b in r['B_HOLD'] for b in ['AUGMENTED-KF','CONDITIONAL-HOLD','QS','LP30','LP120'])]
    cross=[r for r in r45 if r['phase']!=r['label']['phase']]
    fraction=sum(abs(r['B_HOLD']['AUGMENTED-KF']-r['label']['value']) for r in cross)/sum(abs(r['B_HOLD']['AUGMENTED-KF']-r['label']['value']) for r in r45)
    review=read(root/'handoff/results/numeric-audit.json')
    assert len(cross)==360 and abs(fraction-review['cross_fraction_of_total_absolute_error'])<1e-12
    case=next(r for r in points if r['h']==45 and r['ref'].endswith('observation:2482'))
    write(out/'A1-independent-audit-readback.json',dict(independent_review_sources=['handoff/results/field-audit.json','handoff/results/numeric-audit.json','handoff/results/onset-error-example.json'],
        old45_common_n=len(r45),cross_stage_n=len(cross),cross_fraction_absolute_error=fraction,
        onset_after_submit_case=case,old_HOLD_max_abs_numerical_difference_C=max_hold_diff,
        old_A_long=read(root/'inputs/results/A-long-summary.json'),
        old90_LP120_better_than_KF=True,field_runs=1,new_field_runs=0,theta_fits=0))
    agreements={}
    for a,b in [('INPUT-BASE','INPUT-MEAN'),('INPUT-MEAN','INPUT-CORE')]:
        different=[dict(ref=f['native_ref'],arrival_mono_s=f['arrival_mono_s'],left=o['variants'][a]['activity']['state'],right=o['variants'][b]['activity']['state'])
            for f,o in zip(frames,outputs) if o['variants'][a]['activity']['state']!=o['variants'][b]['activity']['state']]
        agreements[a+' vs '+b]=dict(different_state_frames=len(different),examples=different)
    write(out/'incremental-activity-information.json',dict(comparisons=agreements,
        role='development-only recorded arrival result; not independent high-frequency conclusion',
        no_CPU_GPU_lag_search=True,no_best_core_selection=True,parameter_attempts=1))
    write(out/'environment-resource.json',dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,
        wall_s=time.perf_counter()-wall_start,process_cpu_s=time.process_time()-cpu_start,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
        theta_fits=0,CUDA=False,network_connections=0,producer_acquisition=False,production_modules_imported=False))
    print('Old development analysis completed; all h label contracts retained; no parameter search.',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=lambda v:__import__('pathlib').Path(v),required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    evaluate(ROOT,args.output)
