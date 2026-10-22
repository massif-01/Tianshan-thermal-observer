"""Immutable sessions, append-only observations/revisions, original-image content addressing."""
from pathlib import Path
import csv
import json
import math
import shutil
import uuid
from .files import read,write,lines,append,sha,fingerprint,now_utc,dump_lines
from .clocks import coordinate,nonnegative

KINDS={'fin_surface_ir','backplate_surface_ir','surface_contact','inlet_air','outlet_air','ambient_user_report'}


def identifier(value):
    if not isinstance(value,str):raise ValueError('A nonempty string ID is required; unknown run is not a real run')
    value=str(value)
    if not value or '/' in value or '\\' in value or value in ['.','..']:raise ValueError('Use a simple nonempty ID')
    return value


def session_flags(session):
    flags=[]
    for key in ['model','accuracy']:
        if session.get('instrument',{}).get(key) is None:flags.append('unknown_instrument_'+key)
    if session['measurement_kind'].endswith('_ir'):
        for path in [('instrument','model'),('instrument','accuracy'),('settings','emissivity'),
                     ('settings','reflected_temperature_c'),('settings','surface_finish'),
                     ('geometry','roi_definition'),('settings','measurement_footprint')]:
            if session.get(path[0],{}).get(path[1]) is None:flags.append('unknown_'+path[0]+'_'+path[1])
        flags.append('local_apparent_surface_not_air_or_whole_body')
    if session['measurement_kind'] in ['inlet_air','outlet_air'] and session.get('instrument',{}).get('method')!='air_probe':
        flags.append('air_probe_method_unconfirmed_not_IR_surface')
    if session['measurement_kind']=='surface_contact':
        flags.append('local_surface_not_air_whole_body_or_measured_Ts')
        for key in ['surface_condition','fixed_position','attachment_method']:
            if not session.get('contact',{}).get(key):flags.append('unknown_contact_'+key)
        if not session.get('contact',{}).get('probe_response_calibrated'):
            flags.append('probe_response_not_calibrated_sampling_interval_is_not_response_time')
        if not session.get('contact',{}).get('installation_verified'):
            flags.append('contact_installation_not_field_verified')
    return flags


def register_session(store, session):
    store=Path(store)
    for field in ['session_id','site_id','run_id']:identifier(session[field])
    if session['measurement_kind'] not in KINDS:raise ValueError('Unknown measurement kind')
    if session.get('model_input') or session.get('control_input'):raise ValueError('Reference may not be a model/control input')
    if session['measurement_kind'].endswith('_ir'):
        e=session.get('settings',{}).get('emissivity')
        if e is not None and not 0<float(e)<=1:raise ValueError('Emissivity out of range')
    session=dict(session, schema='TTO-EXTERNAL-REFERENCE-v1',model_input=False,control_input=False,
                 absolute_status='unverified_apparent_surface' if session['measurement_kind'].endswith('_ir') else 'unverified_reference')
    session['quality_limitations']=session_flags(session)
    dest=store/'sessions'/(identifier(session['session_id'])+'.json')
    if dest.exists():
        if read(dest)!=session:raise ValueError('Immutable session: changed position/settings need a new session_id')
    else:write(dest,session)
    return session


def load_session(store, session_id):
    return read(Path(store)/'sessions'/(identifier(session_id)+'.json'))


def temperature(value, unit):
    if value is None or value=='':return None
    value=float(value)
    if not math.isfinite(value):raise ValueError('NaN/Infinity is not a valid temperature')
    unit=str(unit).replace('°','').upper()
    if unit not in ['C','F']:raise ValueError('Explicit C/F unit required')
    return value if unit=='C' else (value-32)*5/9


def artifact_info(store, path, copy=False, metadata_time=None):
    if not path:return None
    path=Path(path)
    if not path.is_file():raise ValueError('Artifact is not a local regular file')
    digest=sha(path)
    rel=Path('artifacts')/(digest+path.suffix.lower())
    if copy:
        dest=Path(store)/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copyfile(path,dest)
        if sha(dest)!=digest:raise ValueError('Stored artifact differs')
    return dict(original_path=str(path.absolute()),stored_relative_path=str(rel),sha256=digest,
                bytes=path.stat().st_size,mtime_s_diagnostic_only=path.stat().st_mtime,
                image_metadata_time_raw=metadata_time,numeric_decoding='not_performed',
                color_or_OCR_temperature_inference=False)


def normalize(store, session_id, values, provenance=None):
    session=load_session(store,session_id)
    for key in ['run_id','site_id','measurement_kind']:
        if values.get(key) not in [None,'',session[key]]:raise ValueError('Record/session '+key+' mismatch')
    value=values.get('original_value')
    unit=values.get('original_unit')
    temp=temperature(value,unit)
    record_id=values.get('record_id') or None
    art=artifact_info(store,values.get('artifact_path'),metadata_time=values.get('image_metadata_time_raw'))
    actual=values.get('measured_at_raw')
    if actual=='':actual=None
    interval=values.get('measured_interval_raw') or None
    if interval:
        if not interval.get('start') or not interval.get('end'):raise ValueError('Both interval endpoints required')
        a,ak=coordinate(interval['start'],session.get('time',{}).get('timezone'))
        b,bk=coordinate(interval['end'],session.get('time',{}).get('timezone'))
        if ak!=bk or b<a:raise ValueError('Invalid measurement interval')
    if actual is not None:coordinate(actual,session.get('time',{}).get('timezone'))
    if actual is not None and interval:raise ValueError('Choose timestamp OR interval, not both')
    uncertainty=nonnegative(values.get('time_uncertainty_s'),'time uncertainty')
    if record_id is None:
        if actual is None and not interval and art is None:raise ValueError('Unknown-time imported row needs a record_id')
        record_id='external-'+fingerprint([session['run_id'],session_id,session['site_id'],actual,interval,art['sha256'] if art else None])[:24]
    identifier(record_id)
    flags=list(session['quality_limitations'])+list(values.get('measurement_flags') or [])
    if temp is None:flags.append('image_only_no_numeric_reading' if art else 'not_measured')
    if actual is None and not interval:flags.append('measurement_time_unknown')
    if uncertainty is None:flags.append('time_precision_unknown_not_zero')
    return dict(schema='TTO-EXTERNAL-REFERENCE-v1',record_id=record_id,run_id=session['run_id'],
        site_id=session['site_id'],session_id=session_id,measurement_kind=session['measurement_kind'],
        statistic=session.get('geometry',{}).get('statistic'),temperature_c=temp,
        original_value=value,original_unit=unit,measured_at_raw=actual,measured_interval_raw=interval,
        time_source=values.get('time_source'),clock_domain=values.get('clock_domain',session.get('time',{}).get('clock_domain')),
        time_uncertainty_s=uncertainty,
        prompt_due_at_utc=values.get('prompt_due_at_utc'),prompt_emitted_at_utc=values.get('prompt_emitted_at_utc'),
        checkpoint_ids=values.get('checkpoint_ids',[]),operator_mark_at_utc=values.get('operator_mark_at_utc'),
        operator_mark_mono_s=values.get('operator_mark_mono_s'),
        operator_mark_clock_domain=values.get('operator_mark_clock_domain'),
        recorded_at_utc=now_utc(),artifact=art,measurement_flags=sorted(set(flags)),
        absolute_status=session['absolute_status'],synthetic=bool(values.get('synthetic',session.get('synthetic',False))),
        note=values.get('note'),model_input=False,control_input=False,provenance=provenance or {})


def session_event(store,session_id,event_type,measured_at_raw=None,uncertainty_s=None,note=None):
    """Append site-integrity evidence; a moved/loose probe never silently resumes."""
    session=load_session(store,session_id)
    if event_type not in ['recording_start','recording_end','clock_check','probe_moved','probe_reattached','probe_loose']:
        raise ValueError('Unknown session event')
    if measured_at_raw is not None:coordinate(measured_at_raw,session.get('time',{}).get('timezone'))
    rec=dict(event_id=str(uuid.uuid4()),session_id=session_id,run_id=session['run_id'],site_id=session['site_id'],
             event_type=event_type,measured_at_raw=measured_at_raw,
             time_uncertainty_s=nonnegative(uncertainty_s,'event time uncertainty'),
             clock_domain=session.get('time',{}).get('clock_domain'),recorded_at_utc=now_utc(),
             note=note,new_session_required=event_type.startswith('probe_'),model_input=False,control_input=False)
    append(Path(store)/'session-events.jsonl',rec)
    return rec


def latest_records(store):
    current={}
    for row in lines(Path(store)/'records.jsonl'):
        current[(row['session_id'],row['record_id'])]=row
    return list(current.values())


def commit_record(store, record, artifact_path=None, allow_revision=False, index=None):
    key=(record['session_id'],record['record_id'])
    prior=index.get(key) if index is not None else next((r for r in latest_records(store) if (r['session_id'],r['record_id'])==key),None)
    ignored={'recorded_at_utc','provenance','revision','revision_id','supersedes'}
    if prior:
        # Do not erase the original operator mark when a reading is entered later.
        for field in ['operator_mark_at_utc','operator_mark_mono_s','operator_mark_clock_domain','prompt_due_at_utc','prompt_emitted_at_utc','checkpoint_ids']:
            if not record.get(field):record[field]=prior.get(field)
        a={k:v for k,v in record.items() if k not in ignored}
        b={k:v for k,v in prior.items() if k not in ignored}
        if a==b:return dict(status='duplicate',record=prior)
        if not allow_revision:raise ValueError('Existing record differs; use record --revise or explicit import supersedes')
    if artifact_path:record['artifact']=artifact_info(store,artifact_path,copy=True,
        metadata_time=(record.get('artifact') or {}).get('image_metadata_time_raw'))
    record=dict(record,revision=prior['revision']+1 if prior else 1,
        revision_id=str(uuid.uuid4()),supersedes=prior['revision_id'] if prior else None)
    append(Path(store)/'records.jsonl',record)
    if index is not None:index[key]=record
    return dict(status='revised' if prior else 'recorded',record=record)


def import_file(store, path, mapping):
    store=Path(store);path=Path(path);input_sha=sha(path);mapping_sha=fingerprint(mapping)
    already=next((v for v in lines(Path(store)/'imports.jsonl') if v['input_sha256']==input_sha and v['mapping_sha256']==fingerprint(mapping)),None)
    if already:return dict(status='duplicate_import',added=0,original_receipt=already)
    # Original bytes and mapping are retained even when particular rows are unusable.
    raw=store/'imports/raw'/(input_sha+path.suffix.lower());raw.parent.mkdir(parents=True,exist_ok=True)
    if not raw.exists():shutil.copyfile(path,raw)
    if sha(raw)!=input_sha:raise ValueError('Raw import archive SHA mismatch')
    batch=input_sha+'-'+mapping_sha
    write(store/'imports/mappings'/(mapping_sha+'.json'),mapping)
    row_lines=[]
    if path.suffix.lower()=='.csv':
        with path.open(encoding=mapping.get('csv',{}).get('encoding','utf-8-sig'),newline='') as f:
            reader=csv.DictReader(f,delimiter=mapping.get('csv',{}).get('delimiter',','))
            rows=[];previous=reader.line_num
            for row in reader:
                # csv.line_num includes the header and embedded newlines; both endpoints retained.
                start=previous+1 if rows else 2
                rows.append(row);row_lines.append([start,reader.line_num]);previous=reader.line_num
    else:
        d=read(path);rows=d['records'] if isinstance(d,dict) else d
    if not isinstance(rows,list):raise ValueError('JSON import needs a list or records list')
    axis=mapping.get('time_axis',{});mode=axis.get('mode','timestamp')
    if mode not in ['timestamp','relative_seconds','sample_index']:raise ValueError('Explicit supported time_axis.mode required')
    interval=axis.get('sample_interval_s')
    if mode in ['relative_seconds','sample_index']:
        interval=nonnegative(interval,'sample interval')
        if not interval or not axis.get('interval_basis'):raise ValueError('Relative/index time requires a positive interval and its independent setting/CSV basis')
        if mode=='sample_index' and 'index_origin' not in axis:raise ValueError('Sample index requires explicit index_origin')
    index={(r['session_id'],r['record_id']):r for r in latest_records(store)}
    results=[];ledger=[];cadence={}
    for i,row in enumerate(rows):
        prov=dict(input_sha256=input_sha,input_row=i+1,csv_line_span=row_lines[i] if row_lines else None,
                  original_row=row,raw_stored_relative_path=str(raw.relative_to(store)),mapping_sha256=mapping_sha,
                  exported_at_raw=mapping.get('exported_at_raw'),imported_at_utc=now_utc())
        outcome=dict(provenance=prov)
        try:
            values=dict(mapping.get('constants',{}))
            for target,column in mapping['columns'].items():
                if column not in row:raise ValueError('missing mapped column '+column)
                values[target]=row[column]
            channel=values.get('original_channel')
            if mapping.get('channels') is not None:
                route=mapping['channels'].get(str(channel))
                if route is None:raise ValueError('unmapped channel '+str(channel))
                values.update(route)
            session_id=values.pop('session_id');session=load_session(store,session_id)
            if mode in ['relative_seconds','sample_index']:
                anchors=session.get('time',{}).get('sync_anchors',[])
                if not any(a.get('evidence') and coordinate(a['clock_time'])[0]==0 for a in anchors):
                    raise ValueError('relative/index time needs an independent start anchor at elapsed second 0')
                sample_raw=values.get('measured_at_raw')
                prov['instrument_sample_time_raw']=sample_raw
                if sample_raw not in [None,'']:
                    value=float(sample_raw)
                    if not math.isfinite(value):raise ValueError('nonfinite sample clock')
                    if mode=='sample_index':
                        if value!=int(value):raise ValueError('sample index must be an integer')
                        value=(value-float(axis['index_origin']))*interval
                    if value<0:raise ValueError('sample time before declared recording start')
                    values['measured_at_raw']=value
            if mapping.get('input_path')=='numeric_export' and not values.get('record_id'):
                values['record_id']='export-'+fingerprint([input_sha,i+1,session_id,channel])[:24]
            if isinstance(values.get('measurement_flags'),str):values['measurement_flags']=[x for x in values['measurement_flags'].split(';') if x]
            start,end=values.pop('interval_start',None),values.pop('interval_end',None)
            if start or end:values['measured_interval_raw']=dict(start=start,end=end)
            if values.get('artifact_path'):
                a=Path(values['artifact_path']);values['artifact_path']=str(a if a.is_absolute() else path.parent/a)
            # Sampling cadence is assessed from parseable source clocks, including ERR/empty-temperature rows.
            if values.get('measured_at_raw') not in [None,'']:
                c,kind=coordinate(values['measured_at_raw'],session.get('time',{}).get('timezone'))
                try:cadence_temp=temperature(values.get('original_value'),values.get('original_unit'))
                except (ValueError,TypeError):cadence_temp=None
                key=session_id+'|'+str(channel)
                cadence.setdefault(key,[]).append((i+1,c,kind,cadence_temp))
            rec=normalize(store,session_id,values,prov)
            rec['input_path']=mapping.get('input_path','manual_or_generic_import')
            rec['original_channel']=channel
            rec['instrument_sample_time_raw']=prov.get('instrument_sample_time_raw',values.get('measured_at_raw'))
            if mapping.get('valid_temperature_c') and rec['temperature_c'] is not None:
                low,high=mapping['valid_temperature_c']
                if not low<=rec['temperature_c']<=high:raise ValueError('outside explicitly configured temperature bounds')
            if mapping.get('input_path')=='numeric_export' and rec['measured_at_raw'] in [None,'']:
                rec['measurement_flags'].append('instrument_sample_time_missing_not_reconstructed')
            prior=index.get((session_id,rec['record_id']));supersedes=values.get('supersedes')
            if supersedes and (not prior or supersedes!=prior['revision_id']):raise ValueError('supersedes must name latest revision_id')
            result=commit_record(store,rec,values.get('artifact_path'),bool(supersedes),index)
            results.append(result)
            missing=[]
            if rec['temperature_c'] is None:missing.append('missing_numeric_temperature_not_filled')
            if rec['measured_at_raw'] in [None,''] and not rec['measured_interval_raw']:missing.append('missing_sample_time_not_filled')
            outcome.update(status='accepted_with_missing_fields' if missing else result['status'],
                           reasons=missing,record_id=rec['record_id'],revision_id=result['record']['revision_id'],
                           session_id=session_id,channel=channel)
        except (ValueError,TypeError,KeyError,OSError) as error:
            outcome.update(status='rejected',reason=str(error))
        ledger.append(outcome)
    cadence_summary={}
    for key,samples in cadence.items():
        diffs=[b[1]-a[1] for a,b in zip(samples,samples[1:]) if a[2]==b[2]]
        positive=sorted(d for d in diffs if d>0)
        expected=axis.get('sample_interval_s')
        cadence_summary[key]=dict(samples_with_time=len(samples),declared_interval_s=expected,
            interval_basis=axis.get('interval_basis'),positive_interval_min_s=min(positive) if positive else None,
            positive_interval_max_s=max(positive) if positive else None,
            positive_interval_median_s=__import__('statistics').median(positive) if positive else None,
            zero_intervals=sum(d==0 for d in diffs),reversed_intervals=sum(d<0 for d in diffs),
            intervals_different_from_declared=sum(abs(d-float(expected))>1e-6 for d in diffs) if expected else None,
            equal_adjacent_temperature_pairs=sum(a[3] is not None and a[3]==b[3] for a,b in zip(samples,samples[1:])),
            conclusion='observed sampling cadence only; no missing samples filled; probe response NOT calibrated')
    ledger_path=store/'imports/rows'/(batch+'.jsonl');dump_lines(ledger_path,ledger)
    rejected=sum(r['status']=='rejected' for r in ledger)
    receipt=dict(status='imported_with_issues' if rejected else 'imported',input_sha256=input_sha,mapping_sha256=mapping_sha,
        input_name=path.name,recorded_at_utc=now_utc(),rows=len(rows),
        added=sum(r['status']!='duplicate' for r in results),duplicates=sum(r['status']=='duplicate' for r in results),
        rejected_rows=rejected,rows_with_missing_fields=sum(r['status']=='accepted_with_missing_fields' for r in ledger),
        raw_stored_relative_path=str(raw.relative_to(store)),row_ledger_relative_path=str(ledger_path.relative_to(store)),
        exported_at_raw=mapping.get('exported_at_raw'),cadence=cadence_summary,
        revision_ids=[r['record']['revision_id'] for r in results])
    append(Path(store)/'imports.jsonl',receipt)
    return receipt
