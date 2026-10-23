"""Read-only adapter of the accepted frozen slowstate outputs. No estimator or fitter."""
from pathlib import Path
from .files import read,lines,sha,write,dump_lines
from .clocks import utc_seconds

PRIMARY_SHA='dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0'


def adapt(source,output,run=None):
    source=Path(source);output=Path(output)
    assert sha(source/'sources/models/primary.json')==PRIMARY_SHA
    files=['states-causal60.jsonl','states-A-long.jsonl','four-state-origins.jsonl','normal-demand-origins.jsonl',
           'fast-status-and-demand-ledger.jsonl']
    a_long={r['ref']:r for r in lines(source/'results'/files[1]) if r['model']=='primary'}
    four={r['ref']:r for r in lines(source/'results'/files[2])}
    demands={r['ref']:r for r in lines(source/'results'/files[3])}
    # Reuse the already-frozen quality ledger. Fresh successful input arrivals may
    # maintain qualification between state origins; they do not renew an old TTL.
    leases={}
    for node in lines(source/'results'/files[4]):
        if not node['ordinary_available'] or not node.get('shape_ref'):continue
        lease=leases.setdefault(node['shape_ref'],dict(end=node['t'],refs=[]))
        lease['end']=max(lease['end'],node['t']+node['duration_s'])
        lease['refs'].append(node['ref'] or node['trigger_ref'])
    selected=[r for r in lines(source/'results'/files[0]) if r['model']=='primary' and (run is None or r['run']==run)]
    exact_clock_pairs={(r['run'],r['t']):utc_seconds(r['utc']) for r in selected}
    out=[]
    for r in selected:
        assert r['model_sha256']==PRIMARY_SHA and r['input_cutoff']<=r['t']+1e-9
        assert four[r['ref']]['parameter_model_sha256']==PRIMARY_SHA
        utc=utc_seconds(r['utc'])
        deadline=min(r['source_valid_until'],r['current_input_valid_until'])
        lease=leases.get(r['ref'])
        end=lease['end'] if lease else deadline
        until=exact_clock_pairs.get((r['run'],end),utc+(end-r['t']))
        states=four[r['ref']]['states'];long=a_long.get(r['ref']);demand=demands.get(r['ref'])
        out.append(dict(schema='TTO-FROZEN-REFERENCE-TRAJECTORY-v1',run_id=r['ref'].split('/')[0],
            run_alias=r['run'],ref=r['ref'],segment=r['segment'],source_epoch=r['source_epoch'],
            utc=r['utc'],utc_s=utc,mono_s=r['t'],valid_until_utc_s=until,
            original_snapshot_valid_until_mono_s=deadline,asof_qualification_until_mono_s=end,
            original_qualification_refs=lease['refs'] if lease else [],
            validity_source='sealed original fast-status ledger; no new quality parser or TTL',model_sha256=PRIMARY_SHA,
            state_input_cutoff_utc_s=utc+(r['input_cutoff']-r['t']),
            measured_TJ_C=r['Tf'],causal_Tf_is_observed_anchor=True,
            Tf_A_long_C=long['Tf'] if long else None,Ts_A_long_C=long['Ts'] if long else None,
            STATE_G2_C=states['STATE-G2'],STATE_QS_C=states['STATE-QS'],
            STATE_LP30_C=states['STATE-LP30'],STATE_LP120_C=states['STATE-LP120'],
            actual_successful_PWM_percent_at_state_origin=r['current_inputs'][2]*100,
            offline_extra_demand={b:v['z_output'] for b,v in demand['branches'].items()} if demand else None,
            fan_ref=r['fan_ref'],power_ref=r['power_ref'],temp_ref=r['temp_ref'],
            synthetic=False,external_temperature_used=False,parameter_learning=False))
    dump_lines(output,out)
    # Measured TJ is kept independently through periods where model state is unavailable.
    registered=read(source/'sources/registered/data.json')
    telemetry=[]
    for r in registered['accepted']:
        if run is not None and r['run']!=run:continue
        utc=utc_seconds(r['utc'])
        telemetry.append(dict(run_id=r['ref'].split('/')[0],run_alias=r['run'],ref=r['ref'],utc_s=utc,
            mono_s=r['mono_s'],source_epoch=r['source_epoch'],measured_TJ_C=r['values']['tj'],
            source_valid_until_utc_s=utc+(r['source_valid_until']-r['mono_s']),
            actual_successful_PWM_percent_at_observation=r['values'].get('duty'),
            control_eligible=r['control_eligible'],original_research_segment=r.get('research_segment')))
    dump_lines(output.with_suffix('.telemetry.jsonl'),telemetry)
    write(output.with_suffix('.provenance.json'),dict(source_contract='TTO-SLOWSTATE-v1.0',
        primary_model_sha256=PRIMARY_SHA,source_files={n:sha(source/'results'/n) for n in files},
        output_sha256=sha(output),output_rows=len(out),run=run,
        measured_telemetry_file_sha256=sha(output.with_suffix('.telemetry.jsonl')),
        original_registered_data_sha256=sha(source/'sources/registered/data.json'),
        behavior='copy existing frozen states, no interpolation, estimation or fitting',
        validity='sealed original current-qualification intervals including genuinely fresh arrivals; all original snapshot deadlines retained, no new TTL or interpolation'))
    return dict(rows=len(out),output=str(output),sha256=sha(output))
