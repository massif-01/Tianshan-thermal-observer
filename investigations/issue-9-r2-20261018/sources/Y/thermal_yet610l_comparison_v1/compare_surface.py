"""Strict time eligibility plus explicitly uncorrected nominal/offset diagnostics."""
from pathlib import Path
import bisect,csv,datetime as dt,json,sys
from collections import Counter
from zoneinfo import ZoneInfo
import numpy as np
ROOT=Path(__file__).absolute().parent
sys.path.insert(0,str(ROOT/'vendor'))
from common import read,write,sha
from refprep.clocks import align_time
from trajectories import jsonl,qualified_support


def stamp(t):return dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat()
def load_lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def phase_at(phases,t):return next((p['name'] for p in phases if p['start']<=t<p['end']),'outside_phases')
def stats(v):
    v=np.asarray(v,dtype=float)
    return dict(n=len(v),min=float(v.min()),max=float(v.max()),median=float(np.median(v)),mean=float(v.mean()),amplitude=float(np.ptp(v))) if len(v) else dict(n=0)


def compare(evidence,data,out):
    evidence=Path(evidence);out=Path(out);spec=read(ROOT/'spec.json')
    original=evidence/'original-csv/26071081-20261018002850.csv'
    assert sha(original)=='698c3842216bb34a263ba630a2760aaf9858a6232050de798d5922a47eb15e80'
    normalized=evidence/'imported-instrument-v2/normalized'
    records=load_lines(normalized/'records.jsonl');session=read(normalized/'sessions/yet610l-ch1-trial.json')
    assert session['run_id']==spec['trial_id'] and data['run_id']==spec['run_id'] and len(records)==2027
    # Actual vendor mapping is now checked on the original bytes, not just assumed from metadata.
    lines=original.read_text().splitlines();reader=csv.DictReader(lines[30:]);source_rows=list(reader)
    assert len(source_rows)==len(records)
    csv_times=[]
    for i,(r,raw) in enumerate(zip(records,source_rows),32):
        assert r['provenance']['original_row']['source_line']==str(i)
        assert float(raw['CH1'])==r['temperature_c']
        calendar=dt.datetime.strptime(raw['Date']+' '+raw['Time'],'%Y/%m/%d %H:%M:%S')
        assert calendar.isoformat()==r['measured_at_raw']
        assert r['synthetic'] is False and not r['model_input'] and not r['control_input']
        csv_times.append(calendar.replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp())
    assert all(b-a==1 for a,b in zip(csv_times,csv_times[1:]))
    mapping_receipt=dict(status='pass',scope='this actual file/CH1/date-time representation only, not every YET firmware/format',
        raw_original_sha256=sha(original),extracted_table_sha256=load_lines(normalized/'imports.jsonl')[0]['input_sha256'],
        normalized_rows=2027,original_data_lines=[32,2058],adjacent_equal_temperatures=sum(a['temperature_c']==b['temperature_c'] for a,b in zip(records,records[1:])),
        actual_interval_s=1,clock_timezone_in_original=False,physical_mapping_validated=False,
        binding=dict(original_instrument_trial_id=session['run_id'],linked_TTO_run_id=data['run_id'],basis='same archived session plus user handoff; original run_id field never rewritten'))
    write(out/'actual-CSV-mapping-verification.json',mapping_receipt)
    strict=[align_time(r,session) for r in records]
    assert all(x['interval_utc_s'] is None for x in strict)
    strict_status=Counter(x['status'] for x in strict)
    baseline=next(p for p in data['phases'] if p['name']=='resident-baseline')
    reference_index=bisect.bisect_left(csv_times,baseline['start']+150)
    reference=records[reference_index];reference_value=reference['temperature_c']
    write(out/'fixed-reference.json',dict(record_id=reference['record_id'],original_instrument_time=reference['measured_at_raw'],
        temperature_C=reference_value,rule=spec['reference'],nominal_UTC=stamp(csv_times[reference_index]),
        model_reference_available=False,not_thermal_equilibrium=True,chosen_by_phase_time_not_temperature=True))
    samples=data['samples'];sample_times=[a['wall'] for a in samples]
    states=load_lines(out/'states-causal60.jsonl');by_model={m:[s for s in states if s['model']==m] for m in ['primary','old_LS','A24']}
    # Current native contract has no >=60 s segment. Export attempts at every accepted row, not old-M curves.
    attempts=[];state_ledger=[]
    for model in by_model:
        for s in data['segments']:
            attempts.append(dict(model=model,model_sha256=sha(ROOT/'models'/(model+'.json')),run_id=data['run_id'],
                segment=s['id'],first_ref=s['rows'][0]['ref'],last_ref=s['rows'][-1]['ref'],samples=len(s['rows']),
                actual_span_s=s['span_s'],required_prefix_s=60,available=s['span_s']>=60,
                reason='native_qualified_segment_shorter_than_frozen_initialization' if s['span_s']<60 else None))
        smap={s['ref']:s for s in by_model[model]}
        for a in samples:
            s=smap.get(a['ref'])
            state_ledger.append(dict(model=model,run_id=data['run_id'],ref=a['ref'],utc=a['utc'],t=a['t'],phase=a['phase'],
                source_valid_TJ=a['target_valid'],strict_segment=a.get('research_segment'),
                Tf=s['Tf_A_long'] if s else None,Ts=s['Ts'] if s else None,
                available=s is not None,reason=None if s else 'current_native_input_or_control_unqualified' if not a.get('research_segment') else 'no_60s_native_qualified_prefix',
                no_external_temperature_input=True))
    jsonl(out/'model-initialization-attempts.jsonl',attempts);jsonl(out/'new-run-trajectory-availability.jsonl',state_ledger)
    jsonl(out/'native-input-qualification-ledger.jsonl',data['nodes'])
    points=[];phase_stats=[];offsets=spec['clock']['offset_sensitivity_s']
    for offset in offsets:
        for i,r in enumerate(records):
            wall=csv_times[i]+offset;index=bisect.bisect_right(sample_times,wall)-1
            a=samples[index] if index>=0 else None
            TJ=None
            if a and a['target_valid'] and a['wall']<=wall<a['wall']+a['source_valid_until']-a['t']:TJ=a['values']['tj']
            points.append(dict(record_id=r['record_id'],source_original_line=r['provenance']['original_row']['source_line'],
                original_instrument_calendar=r['measured_at_raw'],temperature_C=r['temperature_c'],
                trial_id=spec['trial_id'],run_id=data['run_id'],scenario_offset_s=offset,nominal_UTC=stamp(wall),nominal_wall=wall,
                nominal_phase=phase_at(data['phases'],wall),strict_clock_status=strict[i]['status'],
                strictly_time_paired=False,scenario_is_proven_error_bound=False,
                diagnostic_source_TJ_C=TJ,diagnostic_source_ref=a['ref'] if TJ is not None else None,
                G2_surface_model_comparison=None,comparison_unavailable_reason='no_native_qualified_60s_model_state',
                surface_delta_from_one_reference_C=r['temperature_c']-reference_value,
                reference_record_id=reference['record_id'],not_Ts_accuracy=True))
        for phase in [p['name'] for p in data['phases']]:
            chosen=[p for p in points if p['scenario_offset_s']==offset and p['nominal_phase']==phase]
            phase_stats.append(dict(scenario_offset_s=offset,phase=phase,temperature=stats([p['temperature_C'] for p in chosen]),
                phase_assignment_is_approximate=True,model_comparison_points=0))
    jsonl(out/'surface-comparison-points.jsonl',points);write(out/'surface-phase-sensitivity.json',phase_stats)
    q=qualified_support(data['nodes']);rawgood=sum(max(0,s['end']-s['start']) for s in q)
    rawspan=data['nodes'][-1]['t']-data['nodes'][0]['t']
    summary=dict(run_id=data['run_id'],actual_CSV_mapping_verified=True,actual_surface_records=2027,
        actual_surface_temperature=stats([r['temperature_c'] for r in records]),TJ_temperature=stats([a['values']['tj'] for a in samples]),
        strict_clock_qualified_points=0,strict_clock_statuses=dict(strict_status),strict_model_states={m:len(s) for m,s in by_model.items()},
        frozen_model_initialization_attempts=len(attempts),strict_model_surface_comparisons=0,
        accepted_TJ=len(samples),native_source_valid_TJ=sum(a['target_valid'] for a in samples),
        strict_current_origins=data['coverage']['strict_current'],strict_segments=len(data['segments']),
        longest_strict_segment_s=max(s['span_s'] for s in data['segments']),native_qualified_input_support_s=rawgood,
        raw_observer_span_s=rawspan,native_input_support_fraction=rawgood/rawspan,
        native_quality=data['quality'],native_isolated_segments=data['isolated_segments'],
        approximate_offset_scenarios=offsets,offset_scenarios_are_bounds=False,selected_best_offset=False,
        no_offset_or_drift_fit=True,new_ambient_C=None,old_M_ambient_not_reused=True,
        external_temperature_used_for_model=False,dynamic_parameter_updates=0,
        state_correction_from_surface=False,control_benefit_claim=False,
        interpretation='actual measurements available; native strict 60s state initialization unavailable, plus independent clock uncertainty unknown; no valid model/surface ranking')
    write(out/'comparison-summary.json',summary)
    return summary
