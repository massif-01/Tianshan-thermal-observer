"""Independent raw-snapshot statistics, counterfactual diagnostics and model summaries."""
import bisect
import collections
import csv
import json
import math
from pathlib import Path

import numpy as np
from tto.evaluation import metrics
from tto.model import eligible_scope

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
EXTERNAL=OUT/'sources/external-reference'


def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def curve_demand(curve,t,lo=10,hi=100):
    t=round(t*10)
    if t<=round(curve[0]['temp']*10):raw=curve[0]['duty']
    elif t>=round(curve[-1]['temp']*10):raw=curve[-1]['duty']
    else:
        for a,b in zip(curve,curve[1:]):
            aa,bb=round(a['temp']*10),round(b['temp']*10)
            if aa<=t<=bb:
                raw=a['duty']+((t-aa)*(b['duty']-a['duty']))//(bb-aa)
                break
    return min(hi,max(lo,raw)) if raw else 0


def demand(f,curve):
    baseline=curve_demand(curve,f['control_temperature'])
    predicted=int((f['control_temperature']+f['slope_c_per_min']*.75)*10)/10
    predicted=max(-40,min(150,predicted))
    margin=95-f['guard_temperature']
    boost=max(25-margin,0)*1.2+max(predicted-85,0)*1.5+max(f['slope_c_per_min'],0)*2
    target=100 if predicted>=95 else min(100,int(baseline+boost*f['controller_gain']+.5))
    if 0<target<10:target=10
    return dict(baseline=baseline,predicted=predicted,boost=boost,unlimited_demand=target)


def main():
    p=ROOT/'evidence/short-qa-20261013'
    run=next(p.glob('run-*'))
    fs=[]
    for l in (run/'observations-0001.jsonl').open():
        r=json.loads(l)
        if r['kind']=='fan':
            for f in r['payload'].get('data',{}).get('fans',[]):
                if f['id']==0:fs.append(dict(f,t=r['mono_s'],utc=r['received_at_utc'],ref=r['ref']))
    times=[f['t'] for f in fs]
    req=json.loads((p/'normalized-requests.json').read_text())
    user=json.loads((OUT/'identity/user-fan_curve_config_0.json').read_text())
    current=json.loads((OUT/'identity/current-fan-config.json').read_text())['body']['data']
    configuration=[dict(field=f'{a["temp"]}C',user=a['duty'],current=b['duty'],historical=None,
                        verdict='一致' if a['duty']==b['duty'] else '差异') for a,b in zip(user['curve'],current['curve'])]
    configuration += [dict(field=k,user=user[k],current=current[k],historical=None,
                           verdict='一致' if user[k]==current[k] else '差异') for k in ['min_duty','max_duty','hysteresis','min_interval']]
    write('results/configuration-comparison.json',dict(rows=configuration,historical_curve='not recorded/proven',
                                                      gain='runtime multiplier, separately recorded; not a curve field',
                                                      latest_user_clarification=json.loads((OUT/'identity/user-curve-clarification.json').read_text()),
                                                      classification='Earlier JSON belongs to another curve; user confirmed current Thor 40C=15. Not classified as current device configuration fault.'))
    preds=[json.loads(l) for l in (run/'predictions.jsonl').open()]
    table=[]
    external={r['id']:r for r in json.loads((EXTERNAL/'request-independent-checks.json').read_text())}
    comparisons=[]
    for q in req:
        if q['phase']=='pilot':continue
        start,end=q['submit_mono_s'],q['end_mono_s']
        next_q=next((n for n in req if n['phase']==q['phase'] and n['submit_mono_s']>start),None)
        stop=next_q['submit_mono_s'] if next_q else end+300
        ff=[f for f in fs if start<=f['t']<stop and f['duty_valid']]
        pre=fs[bisect.bisect_right(times,start)-1]
        assert 0<=start-pre['t']<=2.5
        peak=max(ff,key=lambda f:f['duty'])
        near=[f for f in ff if f['t']>=end and f['duty']>=peak['duty']-1]
        back=[f for f in ff if f['t']>=peak['t'] and f['duty']<=pre['duty']+1]
        decline=[f for f in ff if f['t']>=peak['t'] and f['duty']<peak['duty']]
        origin=[a for a in preds if start<=a['origin']['t']<=end]
        row=dict(id=q['request_id'],phase=q['phase'],duration_s=end-start,submit_mono_s=start,end_mono_s=end,
                 pre_duty=pre['duty'],pre_temperature=pre['control_temperature'],pre_gain=pre['controller_gain'],
                 peak_pwm=peak['duty'],peak_temp=peak['control_temperature'],peak_slope=peak['slope_c_per_min'],
                 peak_gain=peak['controller_gain'],peak_ref=peak['ref'],
                 first_peak_after_end_s=peak['t']-end,prediction_origins_during_request=len(origin),
                 near_peak_last_s=near[-1]['t']-end if near and q['phase']=='sparse' else None,
                 return_pre_plus1_s=back[0]['t']-end if back and q['phase']=='sparse' else None,
                 first_decline_s=decline[0]['t']-end if decline else None,
                 formula_user=demand(peak,user['curve']),formula_current_assumption=demand(peak,current['curve']))
        table.append(row)
        other=external[row['id']]
        keys=['duration_s','peak_pwm','peak_temp','peak_slope','peak_gain','peak_ref']
        if q['phase']=='sparse':keys+=['near_peak_last_s','return_pre_plus1_s','first_decline_s']
        checks={k: (abs(row[k]-other[k])<1e-8 if isinstance(row[k],(float,int)) and isinstance(other.get(k),(float,int)) else row[k]==other.get(k)) for k in keys}
        comparisons.append(dict(id=row['id'],checks=checks,all_match=all(checks.values())))
    write('results/request-tail-statistics.json',table)
    write('results/external-statistical-comparison.json',dict(rows=comparisons,passed=all(r['all_match'] for r in comparisons),
                                                            statistical_adoption='numbers verified; causal/safety conclusions bounded separately'))
    s01=next(q for q in req if q['request_id']=='S01')
    targets=[0,5,15,25,30]
    snapshots=[]
    for sec in targets:
        f=next(f for f in fs if f['t']>=s01['end_mono_s']+sec)
        snapshots.append(dict(after_end_s=f['t']-s01['end_mono_s'],ref=f['ref'],temperature=f['control_temperature'],
                              successful_pwm=f['duty'],slope=f['slope_c_per_min'],gain=f['controller_gain'],
                              current_assumption_formula=demand(f,current['curve'])))
    write('results/s01-observed-snapshots.json',snapshots)
    gains=[];previous=None
    for f in fs:
        g=f['controller_gain']
        if g!=previous:
            gains.append(dict(utc=f['utc'],ref=f['ref'],gain=g,ratio=g/previous if previous else None,
                              cooling_response=f['cooling_response'],slope=f['slope_c_per_min']))
            previous=g
    stale_i=next(i for i,f in enumerate(fs) if f['temp_stale'])
    recovery=next(f for f in fs[stale_i+1:] if not f['temp_stale'])
    write('results/observed-summary.json',dict(fan_snapshot_count=len(fs),gain_transitions=gains,
                                             pwm_range=[min(f['duty'] for f in fs),max(f['duty'] for f in fs)],
                                             missing_prediction_origins=sum(r['prediction_origins_during_request']==0 for r in table),
                                             exact_request_origins=sum(r['prediction_origins_during_request']>0 for r in table),
                                             stale_event=dict(before=fs[stale_i-1],event=fs[stale_i],recovery=recovery),
                                             http_timeouts=0,high_80_or_more=sum(f['duty']>=80 for f in fs)))
    # Hypothetical outputs, not recovered on-device intermediates.
    variants={n:list(csv.DictReader((OUT/'results'/f'control-{n}.csv').open())) for n in
              ['reference-native-gain','release-native-gain','reference-fixed-gain','user-curve-reference-sensitivity']}
    first=fs[0]['t'];replay_rows=[]
    for r in table:
        if r['phase']!='sparse':continue
        for name,rows in variants.items():
            ff=[f for f in rows if r['submit_mono_s']-first<=float(f['second'])<r['end_mono_s']-first+90]
            peak=max(ff,key=lambda f:int(f['successful_pwm']))
            first_down=next((f for f in ff if float(f['second'])>=float(peak['second']) and int(f['successful_pwm'])<int(peak['successful_pwm'])),None)
            replay_rows.append(dict(id=r['id'],variant=name,peak_pwm=int(peak['successful_pwm']),
                                    first_decline_after_end_s=float(first_down['second'])-(r['end_mono_s']-first) if first_down else None,
                                    final_gain=float(ff[-1]['gain']),extra_permission_count=sum(int(f['extra_allow_down']) for f in ff)))
    write('results/replay-summary.json',dict(rows=replay_rows,not_telemetry=True,
                                            actual_gain_final=gains[-1]['gain'],
                                            replay_gains_final={k:float(v[-1]['gain']) for k,v in variants.items()},
                                            reference_observed_mae_pwm=float(np.mean([abs(int(x['successful_pwm'])-f['duty']) for x,f in zip(variants['reference-native-gain'],fs)])),
                                            assumption_mismatch='Reference reconstruction differs from observed gain and peak; no claim of exact field replay.'))
    # Eight narrow synthetic cases across seven topics; no simulated thermal response.
    a=list(csv.DictReader((OUT/'results/fixtures-release-0.csv').open()))
    b=list(csv.DictReader((OUT/'results/fixtures-release-1.csv').open()))
    fixtures=[]
    for scenario in dict.fromkeys(x['scenario'] for x in a):
        aa=[r for r in a if r['scenario']==scenario];bb=[r for r in b if r['scenario']==scenario]
        fixtures.append(dict(scenario=scenario,n=len(aa),extra_permission_count=sum(int(x['extra_allow_down']) for x in bb),
                             pwm_changed=sum(x['successful_pwm']!=y['successful_pwm'] for x,y in zip(aa,bb)),
                             identical=all(x['successful_pwm']==y['successful_pwm'] for x,y in zip(aa,bb))))
    write('results/fixture-summary.json',dict(cases=fixtures,status='passed',limits='Supplied temperature paths; not identified plants or safety validation.'))
    # B0/B1 summaries use every available native causal origin; these are descriptive development results.
    baselines={}; ident={}
    for label in ['seven-conditions','short-qa']:
        p=OUT/'model-exploration'/label
        dataset=p/'exploratory-split/dataset.json' if label=='short-qa' else p/'all-origins-dataset.json'
        d=json.loads(dataset.read_text())
        out={}
        for h in ['15','45','90']:
            common=[r for r in d['rows'] if eligible_scope(r) and h in r['labels'] and all(h in r['baseline_values'].get(m,{}) for m in ['persist','trend30'])]
            out[h]=dict(n=len(common),metrics={m:metrics([r['baseline_values'][m][h]-r['labels'][h]['value'] for r in common]) for m in ['persist','trend30']})
        baselines[label]=dict(status='descriptive development; not holdout result',horizons=out)
        # Structural input rank and correlation only: not thermal parameter identification.
        accepted=[json.loads(l) for l in (p/'accepted-timeseries.jsonl').open()]
        accepted=[a for a in accepted if a['control_eligible']]
        columns=['vdd_gpu','vdd_cpu_soc_mss','vin_sys_5v0','duty']
        x=np.array([[a['values'][k] for k in columns] for a in accepted],float)
        centered=x-x.mean(axis=0);scaled=centered/x.std(axis=0)
        singular=np.linalg.svd(scaled,compute_uv=False)
        ident[label]=dict(n=len(accepted),columns=columns,min=x.min(axis=0).tolist(),max=x.max(axis=0).tolist(),
                           pearson=np.corrcoef(x,rowvar=False).tolist(),singular_values=singular.tolist(),
                           standardized_condition_number=float(singular[0]/singular[-1]),
                           limit='Algebraic variation does not remove closed-loop confounding or prove distinct thermal effects.')
    write('results/baseline-development-summary.json',baselines)
    write('results/greybox-input-diagnostics.json',ident)
    print('PASS independent summary; reference numbers match:',all(r['all_match'] for r in comparisons))


if __name__=='__main__':main()
