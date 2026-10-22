"""Separate source-valid TJ labels from strict physical-input paths."""
import bisect
import hashlib
import numpy as np
from common import balanced_weights, write
from ridge_reference import held_mean


def index_evidence(e):
    e['_sample_times'] = [s['t'] for s in e['samples']]
    e['_node_times'] = [n['t'] for n in e['nodes']]
    e['_sample_lookup'] = {s['ref']:s for s in e['samples']}
    return e


def interval_context(e, start, end):
    # This is the handoff AVAIL-v2 interval rule, with explicit unknown context.
    ns=e['nodes']; ts=e['_node_times']; lo=bisect.bisect_right(ts,start)-1; hi=bisect.bisect_right(ts,end)
    if lo<0: return dict(complete=False,control_context='unclassified_gap',reasons=['no_origin_context'])
    used=ns[lo:hi]; complete=True; abnormal=False; unknown=False; reasons=[]
    for i,n in enumerate(used):
        left=max(start,n['t']); right=min(end,used[i+1]['t'] if i+1<len(used) else end)
        if n['observed_abnormal_or_changed']: abnormal=True; reasons.append(n['ref']+':observed_abnormal_or_changed')
        if right>left and (not n['complete'] or n['valid_until']<right-1e-9):
            complete=False; unknown |= not n['context_known']; reasons.append(n['ref']+':input_or_aux_context_gap')
    context='observed_abnormal_or_changed' if abnormal else 'confirmed_normal' if complete else 'unclassified_gap' if unknown else 'aux_observation_gap'
    return dict(complete=complete,control_context=context,reasons=reasons)


def target_label(e, origin, h, tolerance=2):
    if not origin['target_valid']: return None,'origin_source_invalid'
    i=bisect.bisect_left(e['_sample_times'],origin['t']+h)
    if i>=len(e['samples']) or e['samples'][i]['t']>origin['t']+h+tolerance: return None,'no_TJ_answer'
    a=e['samples'][i]
    if not a['target_valid']: return None,'target_source_isolated_or_invalid'
    if a['source_epoch']!=origin['source_epoch'] or a['source_identity']!=origin['source_identity']: return None,'source_identity_or_validity_boundary'
    return dict(value=a['values']['tj'],ref=a['ref'],t=a['t'],offset_s=a['t']-origin['t']-h),None


def strict_segments(e):
    groups=[]; group=[]; rejected=[]; breaks=[]
    for a in e['samples']:
        n=e['nodes'][a['node_index']]
        if not a['target_valid'] or not n['complete'] or n['valid_until']<=a['t']:
            if group: groups.append(group); group=[]
            rejected.append(a['ref']); a['research_segment']=None; continue
        if group:
            p=group[-1]; context=interval_context(e,p['t'],a['t'])
            if not context['complete'] or a['source_epoch']!=p['source_epoch']:
                breaks.append(dict(before=p['ref'],after=a['ref'],context=context))
                groups.append(group); group=[]
        group.append(a)
    if group: groups.append(group)
    segments=[]
    for j,g in enumerate(groups):
        sid=f"{e['run']}-{j:02d}"; timeline=[]
        for n in e['nodes'][g[0]['node_index']:g[-1]['node_index']+1]:
            if timeline and n['t']==timeline[-1]['t']: timeline[-1]=n
            else: timeline.append(n)
        times=[n['t'] for n in timeline]; rows=[]
        for i,a in enumerate(g):
            a['research_segment']=sid
            rows.append(dict(a,duration=g[i+1]['t']-a['t'] if i+1<len(g) else 0,
                             timeline_index=bisect.bisect_left(times,a['t'])))
        segments.append(dict(id=sid,run=e['run'],source_segment=g[0]['segment'],rows=rows,timeline=timeline,
                             span_s=g[-1]['t']-g[0]['t'],eligible_for_fit=len(g)>1))
    coverage=dict(accepted=len(e['samples']),strict_current=len(e['samples'])-len(rejected),strict_rejected_refs=rejected,
                  segments=[dict(id=s['id'],n=len(s['rows']),span_s=s['span_s'],first_ref=s['rows'][0]['ref'],last_ref=s['rows'][-1]['ref'],
                                 phases=sorted({a['phase'] for a in s['rows']})) for s in segments],breaks=breaks,
                  reset_policy='only real qualification/source break; never phase change')
    return segments,coverage


def make_examples(e, segments):
    smap={s['id']:s for s in segments}; source_group=[]; previous=None; out=[]
    for i,a in enumerate(e['samples']):
        if not a['target_valid'] or previous is None or previous['source_epoch']!=a['source_epoch'] or a['t']-previous['t']>5:
            source_group=[]
        if a['target_valid']: source_group.append(a)
        previous=a
        ts=np.array([r['t'] for r in source_group]); y=np.array([r['values']['tj'] for r in source_group]); now=a['t']
        slope={}
        for h in (10,30):
            j=np.searchsorted(ts,now-h)
            slope[h]=(y[-1]-y[j])/(now-ts[j]) if len(ts) and j<len(ts) and now-ts[j]>=min(10,h-2) else None
        tj=io=None
        if len(ts) and now-ts[0]>=60:
            vals=[y[-1]]
            for h in (5,15,30,60):
                j=np.searchsorted(ts,now-h,side='right')-1
                if j<0 or now-h-ts[j]>2: break
                vals.append(y[j]-y[-1])
            if len(vals)==5 and all(slope[h] is not None for h in (10,30)):
                vals += [held_mean(ts,y,now-h,now)-y[-1] for h in (10,30)]+[slope[10],slope[30]]
                tj=np.array(vals)
        sid=a.get('research_segment'); seg=smap.get(sid)
        ready=bool(seg and now-seg['rows'][0]['t']>=60 and interval_context(e,now-60,now)['complete'])
        if ready and tj is not None:
            lo=bisect.bisect_right(e['_node_times'],now-30)-1; hi=bisect.bisect_right(e['_node_times'],now)
            ns=e['nodes'][lo:hi]; nt=np.array([n['t'] for n in ns]); inputs=np.array([n['inputs'] for n in ns]); extra=[]
            for k in (2,0,1): extra.extend([inputs[-1,k],held_mean(nt,inputs[:,k],now-30,now)])
            io=np.r_[tj,extra]
        labels={}; rejections={}; contexts={}; a_eligible={}; strict_labels={}
        for h in (15,45,90):
            lab,reason=target_label(e,a,h); labels[str(h)]=lab; rejections[str(h)]=reason
            nominal=interval_context(e,now,now+h); outcome=interval_context(e,now,lab['t']) if lab else nominal
            contexts[str(h)]=outcome['control_context']; a_eligible[str(h)]=bool(lab and nominal['complete'])
            strict_labels[str(h)]=bool(lab and sid and e['_sample_lookup'][lab['ref']].get('research_segment')==sid)
        dt=e['samples'][i+1]['t']-now if i+1<len(e['samples']) and e['samples'][i+1]['source_epoch']==a['source_epoch'] and e['samples'][i+1]['t']-now<=5 else 0
        row={k:a[k] for k in ('run','ref','utc','wall','macro','phase','regime')}
        row.update(segment=sid,t=now,duration=dt,current=a['values']['tj'],R_TJ=tj,R_IO=io,slope=slope[30],ready=ready,
                   labels=labels,label_rejections=rejections,contexts=contexts,A_eligible=a_eligible,strict_labels=strict_labels,
                   strict_i=next((j for j,r in enumerate(seg['rows']) if r['ref']==a['ref']),None) if seg else None,
                   source_valid=a['target_valid'])
        out.append(row)
    return out


def cohort_id(rows):
    return hashlib.sha256('\n'.join(f"{r['ref']}|{r['h']}|{r['label']['ref']}" for r in rows).encode()).hexdigest()
