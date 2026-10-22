"""Activity metrics on common receiver time and availability. No physical truth inference."""
import bisect


def metrics(frames,trace,events,variant_names):
    """events carry actual submit/done in the same receiver clock, never a plan."""
    if not frames:
        return dict(status='unknown:no_frames',groups=[],events=[])
    times=[f['arrival_mono_s'] for f in frames]
    clocks={f.get('arrival_clock_id') for f in frames}
    if len(clocks)!=1 or None in clocks or any(e.get('arrival_clock_id') not in clocks for e in events):
        return dict(status='unknown:unmatched_receiver_clock',groups=[],events=events)
    if any(e.get('submit_mono_s') is None for e in events):
        return dict(status='unknown:missing_actual_submit',groups=[],events=events)
    def state_at(name,t):
        i=bisect.bisect_right(times,t)-1
        if i<0:return 'UNKNOWN',None
        a=trace[i]['states'][name]
        if a['supported_until_mono_s'] is None or t>=a['supported_until_mono_s']:
            return 'UNKNOWN',None
        return a['state'],frames[i].get('native_ref')
    def busy(t):
        return any(e['submit_mono_s']<=t<(e['done_mono_s'] if e.get('done_mono_s') is not None else times[-1]+1) for e in events)
    groups=[];event_rows=[]
    for name in variant_names:
        background_s=unknown_s=common_s=active_bg_s=0.;active_bg_events=0;prev=False
        for i,t in enumerate(times[:-1]):
            right=times[i+1]
            cuts={t,right}
            for n in variant_names:
                until=trace[i]['states'][n]['supported_until_mono_s']
                if until is not None and t<until<right:cuts.add(until)
            for e in events:
                for v in (e['submit_mono_s'],e.get('done_mono_s')):
                    if v is not None and t<v<right:cuts.add(v)
            cuts=sorted(cuts)
            for a,b in zip(cuts,cuts[1:]):
                states={n:state_at(n,(a+b)/2)[0] for n in variant_names}
                common=all(s!='UNKNOWN' for s in states.values())
                common_s+=(b-a)*common
                unknown_s+=(b-a)*(states[name]=='UNKNOWN')
                is_bg=common and not busy((a+b)/2)
                background_s+=(b-a)*is_bg
                active_bg=is_bg and states[name]=='ACTIVE'
                active_bg_s+=(b-a)*active_bg
                if active_bg and not prev:active_bg_events+=1
                prev=active_bg
        for e in events:
            end=e.get('done_mono_s')
            submit=e['submit_mono_s'];initial,ref=state_at(name,submit)
            indices=[i for i,t in enumerate(times) if submit<=t<=(end if end is not None else times[-1])]
            common_indices=[i for i in indices if all(trace[i]['states'][n]['state']!='UNKNOWN' for n in variant_names)]
            first=next((i for i in common_indices if trace[i]['states'][name]['state']=='ACTIVE'),None)
            release=next((i for i,t in enumerate(times) if end is not None and t>=end and trace[i]['states'][name]['state']=='IDLE'),None)
            event_rows.append(dict(variant=name,event_id=e['event_id'],state_at_submit=initial,state_at_submit_ref=ref,
                result='already_active' if initial=='ACTIVE' else ('detected' if first is not None else ('miss_on_client_reference' if common_indices else 'unknown')),
                delay_s=times[first]-submit if first is not None and initial!='ACTIVE' else None,
                first_active_ref=frames[first].get('native_ref') if first is not None else None,
                protocol_done_known=end is not None,
                first_IDLE_after_DONE_delay_s=times[release]-end if release is not None else None,
                thermal_process_independent=False))
        groups.append(dict(variant=name,common_available_s=common_s,own_unknown_s=unknown_s,
            common_no_client_inflight_s=background_s,common_no_client_inflight_ACTIVE_s=active_bg_s,
            common_no_client_inflight_ACTIVE_events=active_bg_events))
    repeats=[]
    for group in sorted({str(e.get('continuous_group')) for e in events if e.get('continuous_group') is not None}):
        es=[e for e in events if str(e.get('continuous_group'))==group]
        start=min(e['submit_mono_s'] for e in es)
        end=max(e['done_mono_s'] if e.get('done_mono_s') is not None else times[-1] for e in es)
        for name in variant_names:
            activations=[f.get('native_ref') for f,r in zip(frames,trace) if start<=f['arrival_mono_s']<=end
                and r['states'][name]['transition'] and r['states'][name]['state']=='ACTIVE']
            repeats.append(dict(variant=name,continuous_group=group,activation_refs=activations,
                additional_activation_count=max(0,len(activations)-1),independent_thermal_processes=1))
    return dict(status='descriptive_client_reference_only',groups=groups,events=event_rows,
        continuous_groups=repeats,physical_CPU_GPU_onset_truth=None,
        unknown_end_is_not_idle=True,independent_thermal_processes=1)
