"""Finite descriptive strata, added after first scores; no candidate selection or tuning."""
from pathlib import Path
import argparse
import collections
import numpy as np
from prepare import read,write
from run_study import lines,error_stats,cohort_id


def run(out):
    write(out/'descriptive-diagnostics-spec.json',dict(posthoc_descriptive=True,
          reason='Separate within-stage response from predictions crossing known retrospective stage boundaries',
          strata=['same stage versus crossing','first60 / middle / last60 seconds at origin',
                  'observed future context','two recorded single-lane blocks at +60 through +300 seconds'],
          forecast_recomputed=False,models_selected=False,parameters_changed=False,
          clock_selected=False,extra_field_runs=0))
    points=list(lines(out/'predictions.jsonl'))
    samples=list(lines(out/'samples-and-causal-states.jsonl'))
    phases=read(out/'phases.json')
    pmap={p['name']:p for p in phases}
    metrics=[]
    for kind in ('A_roll','B_HOLD'):
        for h in (15,45,90):
            base=[r for r in points if r['h']==h and r['label'] and 'B1' in r['baselines'] and 'AUGMENTED-KF' in r[kind]]
            for phase in ['all']+list(pmap):
                rs=[r for r in base if phase=='all' or r['phase']==phase]
                for stage_relation in ('all','same_stage','crosses_stage'):
                    chosen=[r for r in rs if stage_relation=='all' or (r['phase']==r['label']['phase'])==(stage_relation=='same_stage')]
                    metrics.append(dict(kind=kind,h=h,phase=phase,stage_relation=stage_relation,n=len(chosen),cohort_SHA256=cohort_id(chosen),
                        errors={b:error_stats([r[kind][b]-r['label']['value'] for r in chosen]) for b in ('AUGMENTED-KF',)},
                        baselines={b:error_stats([r['baselines'][b]-r['label']['value'] for r in chosen]) for b in ('B0','B1')}))
    write(out/'stage-boundary-metrics.json',metrics)
    windows=[]
    for phase,p in pmap.items():
        for window in ('first60','middle','last60'):
            rs=[]
            for r in points:
                if r['h']!=45 or r['phase']!=phase or not r['label'] or 'B1' not in r['baselines'] or 'AUGMENTED-KF' not in r['B_HOLD']:
                    continue
                from run_study import seconds
                elapsed=seconds(r['utc'])-p['start'];remaining=p['end']-seconds(r['utc'])
                if (window=='first60' and elapsed<60) or (window=='last60' and remaining<=60) or (window=='middle' and elapsed>=60 and remaining>60):
                    rs.append(r)
            windows.append(dict(phase=phase,origin_window=window,h=45,n=len(rs),cohort_SHA256=cohort_id(rs),
                KF_B_HOLD=error_stats([r['B_HOLD']['AUGMENTED-KF']-r['label']['value'] for r in rs]),
                B0=error_stats([r['baselines']['B0']-r['label']['value'] for r in rs])))
    write(out/'time-window-metrics.json',windows)
    worst=[]
    for kind in ('A_roll','B_HOLD'):
        for h in (15,45,90):
            rs=[r for r in points if r['h']==h and r['label'] and 'AUGMENTED-KF' in r[kind]]
            for r in sorted(rs,key=lambda r:r[kind]['AUGMENTED-KF']-r['label']['value'])[:10]:
                worst.append(dict(kind=kind,h=h,origin_ref=r['ref'],origin_utc=r['utc'],origin_phase=r['phase'],
                     target_ref=r['label']['ref'],target_phase=r['label']['phase'],target_t=r['label']['t'],
                     prediction_C=r[kind]['AUGMENTED-KF'],actual_C=r['label']['value'],
                     error_C=r[kind]['AUGMENTED-KF']-r['label']['value']))
    write(out/'worst-underprediction-cases.json',worst)
    repeats=[]
    for phase in ('1-work','7-work'):
        p=pmap[phase]
        aa=[a for a in samples if a['phase']==phase and p['start']+60<=a['wall']<p['start']+300 and a['raw_input']]
        u=np.array([a['raw_input'] for a in aa])
        repeats.append(dict(phase=phase,window='fixed +60 to +300 seconds from actual phase start; no task-state reset',n=len(aa),
             rails_GPU_CPU_SOC_MSS_W_means=u[:,:2].mean(axis=0).tolist(),PWM_mean_percent=float(u[:,2].mean()*100),
             TJ_mean_C=float(np.mean([a['current'] for a in aa])),
             Ts_KF_mean_C=float(np.mean([a['states']['AUGMENTED-KF']['Ts_C'] for a in aa])),
             E_mean_C=float(np.mean([a['states']['AUGMENTED-KF']['E_C'] for a in aa])),
             interpretation='same request profile at two thermal histories, not two independent episodes or a controlled identical-power experiment'))
    write(out/'repeat-single-lane-descriptive.json',repeats)
    kf=[a['states']['AUGMENTED-KF'] for a in samples if a['states']['AUGMENTED-KF']['available']]
    write(out/'state-diagnostics.json',dict(cold_starts=max(a['cold_starts'] for a in kf),
         E_range_C=[min(a['E_C'] for a in kf),max(a['E_C'] for a in kf)],
         Ts_range_C=[min(a['Ts_C'] for a in kf),max(a['Ts_C'] for a in kf)],
         posterior_Tf_vs_current_TJ=error_stats([a['states']['AUGMENTED-KF']['Tf_C']-a['current'] for a in samples]),
         posterior_temperature_feedback=True,posterior_error_is_not_forecast=True,
         covariance_calibrated=False,theta_updated=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.output)
