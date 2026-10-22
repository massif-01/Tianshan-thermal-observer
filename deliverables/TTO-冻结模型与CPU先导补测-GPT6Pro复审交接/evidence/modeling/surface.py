"""Independent CH1 trajectory diagnostics; never imported by observer/forecast generation."""
import bisect
import csv
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np
from prepare import read, sha, write


def surface(root,out,samples,signals,long,phases,spec):
    from run_study import lines,jsonl,seconds,phase_at
    original=root/'inputs/instrument/imported/original-csv/26071081-20261019173740.csv'
    records=list(lines(root/'inputs/instrument/imported/normalized/records.jsonl'))
    assert sha(original)==spec['surface']['csv_sha256']
    raw=list(csv.DictReader(original.read_text().splitlines()[30:]))
    assert len(raw)==len(records)==2984
    times=[]
    for line,(a,b) in enumerate(zip(raw,records),32):
        stamp=dt.datetime.strptime(a['Date']+' '+a['Time'],'%Y/%m/%d %H:%M:%S')
        assert stamp.isoformat()==b['measured_at_raw']
        assert float(a['CH1'])==b['temperature_c']
        assert b['provenance']['original_row']['source_line']==str(line)
        assert b['run_id']==spec['run_id'] and not b['synthetic'] and not b['model_input'] and not b['control_input']
        times.append(stamp.replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp())
    assert all(b-a==1 for a,b in zip(times,times[1:]))
    ref_time=phases[0]['start']+150
    ri=bisect.bisect_left(times,ref_time)
    reference=records[ri]
    write(out/'surface-fixed-reference.json',dict(record_id=reference['record_id'],original_line=ri+32,
         original_calendar=reference['measured_at_raw'],temperature_C=reference['temperature_c'],
         nominal_UTC=dt.datetime.fromtimestamp(times[ri],dt.timezone.utc).isoformat(),
         selection='first CSV row >= background start+150s, unshifted calendar; same row in every scenario',
         not_equilibrium=True,no_scale_or_lag_fit=True))
    st=[x['wall'] for x in signals]
    lt=[seconds(x['utc']) for x in long]

    def at(wall):
        i=bisect.bisect_right(st,wall)-1
        values={};refs={};context=None
        if 0<=i<len(signals)-1:
            a=signals[i];age=wall-a['wall'];mono=a['t']+age
            context=dict(model_phase=a['model_phase'],safety=a['safety'],source_ref=a['ref'])
            if a['current_TJ_C'] is not None and mono<a['TJ_until']:
                values['TJ']=a['current_TJ_C'];refs['TJ']=a['ref']
            if a['available'] and age<2.5:
                for k,v in a['values'].items():
                    if v is not None:
                        values[k]=v;refs[k]=a['ref']
        j=bisect.bisect_right(lt,wall)-1
        if 0<=j<len(long) and wall-lt[j]<2.5 and wall<=lt[-1]:
            a=long[j]
            values.update(A_long_Tf=a['Tf_C'],A_long_Ts=a['Ts_C'])
            refs.update(A_long_Tf=a['ref'],A_long_Ts=a['ref'])
        return values,refs,context

    points,statistics=[],[]
    for offset in spec['surface']['time_scenarios_added_to_UTC8_calendar_s']:
        reference_models,_,_=at(times[ri]+offset)
        group=[]
        for k,r in enumerate(records):
            wall=times[k]+offset
            models,refs,context=at(wall)
            relative={name:v-reference_models[name] for name,v in models.items() if name in reference_models}
            delta=r['temperature_c']-reference['temperature_c']
            point=dict(record_id=r['record_id'],run_id=r['run_id'],source_original_line=k+32,
                       original_instrument_time=r['measured_at_raw'],original_value=r['original_value'],
                       CH1_C=r['temperature_c'],scenario_added_seconds=offset,scenario_wall=wall,
                       scenario_UTC=dt.datetime.fromtimestamp(wall,dt.timezone.utc).isoformat(),
                       nominal_phase=phase_at(phases,wall),strict_time_qualified=False,
                       scenario_is_calibrated_bound=False,absolute_models=models,model_refs=refs,
                       relative_surface_C=delta,relative_models_C=relative,
                       relative_difference_model_minus_surface_C={name:v-delta for name,v in relative.items()},
                       context=context,surface_used_for_state_or_forecast=False,
                       comparison_is_true_Ts_error=False)
            group.append(point)
        points.extend(group)
        for phase in ['all']+[p['name'] for p in phases]:
            chosen=[p for p in group if (phase=='all' and p['absolute_models']) or p['nominal_phase']==phase]
            for key in ('TJ','KF_Ts','CONDITIONAL_Ts','QS','LP30','LP120','A_long_Ts'):
                paired=[p for p in chosen if key in p['relative_models_C']]
                if not paired:
                    continue
                model=np.array([p['relative_models_C'][key] for p in paired])
                measured=np.array([p['relative_surface_C'] for p in paired])
                diff=model-measured
                statistics.append(dict(scenario_added_seconds=offset,phase=phase,series=key,n=len(paired),
                     model_relative_range_C=[float(model.min()),float(model.max())],
                     surface_relative_range_C=[float(measured.min()),float(measured.max())],
                     mean_relative_difference_C=float(diff.mean()),
                     mean_absolute_relative_discrepancy_C=float(abs(diff).mean()),
                     max_absolute_relative_discrepancy_C=float(abs(diff).max()),
                     interpretation='descriptive relative shape/amplitude only, not physical Ts accuracy or calibrated time pairing'))
    jsonl(out/'surface-diagnostic-points.jsonl',points)
    write(out/'surface-phase-diagnostics.json',statistics)
    write(out/'surface-summary.json',dict(actual_original_csv_sha256=sha(original),records=len(records),
         original_line_range=[32,31+len(records)],first_calendar=records[0]['measured_at_raw'],last_calendar=records[-1]['measured_at_raw'],
         sample_intervals_s=[1],adjacent_equal_pairs_retained=sum(a['temperature_c']==b['temperature_c'] for a,b in zip(records,records[1:])),
         CH1_range_C=[min(r['temperature_c'] for r in records),max(r['temperature_c'] for r in records)],
         physical_meaning='one local fin surface near outlet, fixed contact probe; no detach/move per operator',
         ambient_C=None,old_M_24C_reused=False,strict_time_qualified_pairs=0,
         diagnostic_clock_scenarios=spec['surface']['time_scenarios_added_to_UTC8_calendar_s'],
         drift_fitted=False,best_offset_selected=False,raw_calendar_changed=False,
         calibration_uncertainty_s=None,probe_response_calibrated=False,physical_Ts_accuracy_verified=False,
         model_input=False,control_input=False))
