"""Peaks, early cooldown and C*s trajectory descriptions, never energy estimates."""
import statistics


def event_metrics(samples,nodes,event,model_rows):
    start,end=event['start'],event['end'];before=[s for s in samples if start-30<=s['t']<start and s['target_valid']]
    reference=statistics.median(s['values']['tj'] for s in before) if len(before)>=20 and before[-1]['t']-before[0]['t']>=25 else None
    window=[s for s in samples if start<=s['t']<=end+5 and s['target_valid']]
    lookup={r['ref']:r for r in model_rows};common=[s for s in window if s['ref'] in lookup]
    peak=max(window,key=lambda s:s['values']['tj']) if window else None
    comparisons={}
    for model in ('G1','G2'):
        if common:
            actual=max(s['values']['tj'] for s in common);predicted=max(lookup[s['ref']]['A'][model] for s in common)
            comparisons[model]=dict(common_n=len(common),actual_peak_C=actual,model_peak_C=predicted,peak_error_C=predicted-actual,
                                    common_refs=[s['ref'] for s in common],peak_window_incomplete=len(common)<len(window))
    area=0.;covered=0.
    if reference is not None:
        for a,b in zip(window,window[1:]):
            dt=b['t']-a['t']
            if a['source_epoch']==b['source_epoch'] and dt<=5:
                area+=max(0,a['values']['tj']-reference)*dt;covered+=dt
    cooldown=[]
    for lo,hi in [(0,5),(5,15),(15,45),(45,90)]:
        group=[s for s in samples if end+lo<=s['t']<end+hi and s['target_valid']]
        valid_s=0.;pwms=[]
        for a,b in zip(nodes,nodes[1:]):
            left=max(end+lo,a['t']);right=min(end+hi,b['t'],a['valid_until'])
            if a['complete'] and right>left:valid_s+=right-left
        for s in group:
            if s['control_eligible'] and s['values'].get('duty') is not None:pwms.append(s['values']['duty'])
        cooldown.append(dict(window_s=[lo,hi],TJ_n=len(group),TJ_mean_C=statistics.mean(s['values']['tj'] for s in group) if group else None,
                             TJ_first_C=group[0]['values']['tj'] if group else None,TJ_last_C=group[-1]['values']['tj'] if group else None,
                             PWM_mean_pct=statistics.mean(pwms) if pwms else None,complete_input_seconds=valid_s))
    return dict(event=event,reference_TJ_C=reference,reference_n=len(before),reference_span_s=before[-1]['t']-before[0]['t'] if before else 0,
                actual_peak_C=peak['values']['tj'] if peak else None,peak_ref=peak['ref'] if peak else None,
                peak_time=peak['t'] if peak else None,temperature_rise_C=peak['values']['tj']-reference if peak and reference is not None else None,
                positive_temperature_rise_area_C_s=area if reference is not None else None,area_covered_s=covered,
                model_peak_comparison= comparisons,cooldown=cooldown,not_energy_or_heat_capacity=True)
