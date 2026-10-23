"""Trial-local YET report wrapper: preserve source, extract rows, use reviewed importer."""
from pathlib import Path
import csv,datetime as dt,hashlib,json,subprocess,sys,statistics,argparse
parser=argparse.ArgumentParser(description='Previously validated YET Date+Time/CH1 wrapper; fresh import only')
parser.add_argument('--file',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--trial-id',required=True)
parser.add_argument('--probe-description',type=Path)
parser.add_argument('--tool',type=Path,default=Path('/Users/massif/Tianshan-thermal-observer/experiments/thermal_reference_v1/ref.py'))
args=parser.parse_args()
D=args.output.resolve()
if D.exists():raise ValueError('Fresh output required; do not overwrite an earlier import')
for folder in ['original-csv','mapping','normalized','checks']:(D/folder).mkdir(parents=True,exist_ok=True)
TOOL=args.tool.resolve()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
original=args.file.resolve();source=D/'original-csv'/original.name
source.write_bytes(original.read_bytes())
b=source.read_bytes();text=b.decode('ascii') # all bytes ASCII: equally valid UTF-8; producer encoding not uniquely knowable
rows=list(csv.reader(text.splitlines()))
header=next(i for i,r in enumerate(rows) if r[:3]==['Date','Time','CH1'])
raw=[];timestamps=[];values=[];errors=[]
for lineno,row in enumerate(rows[header+1:],header+2):
    if not any(row):continue
    try:
        stamp=dt.datetime.strptime(row[0]+' '+row[1],'%Y/%m/%d %H:%M:%S')
        value=float(row[2]) if row[2] else None
        if value is not None and not __import__('math').isfinite(value):raise ValueError('nonfinite')
        timestamps.append(stamp);values.append(value)
        raw.append({'instrument_datetime_iso':stamp.isoformat(),'temperature_raw':row[2],'source_line':lineno,'Date':row[0],'Time':row[1],'CH1':row[2]})
    except (ValueError,IndexError) as e:errors.append({'source_line':lineno,'raw':row,'error':str(e)})
assert not errors,errors
summary_fields={r[0].split(':',1)[0]:r[0].split(':',1)[1].strip() for r in rows[:header] if r and ':' in r[0]}
declared_count=int(summary_fields['Sample Points'])
assert len(raw)==declared_count,'Source row count disagrees with instrument summary'
assert raw,'No data rows'
assert any(r[:3]==['CH1','Temp','Celsius'] for r in rows[:header]),'CH1 Celsius contract changed'
extracted=D/'mapping/extracted-data.csv'
with extracted.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
line_map=[{'derived_csv_line':i+2,'source_csv_line':r['source_line'],'source_sha256':hashlib.sha256(b).hexdigest(),'original_date':r['Date'],'original_time':r['Time'],'original_CH1':r['CH1']} for i,r in enumerate(raw)]
save(D/'mapping/source-line-map.json',line_map)
session={'run_id':args.trial_id,'session_id':'yet610l-ch1-trial','site_id':'ch1-location-see-formal-probe-record','measurement_kind':'surface_contact','site_description':'CH1测点及固定方式以正式轮次探头记录为准；导入不替代安装核对','instrument':{'model':'YET-610L','serial_alias':summary_fields.get('Serial Number'),'firmware_version':summary_fields.get('Firmware Version'),'accuracy':None},'contact':{'fixed_position':None,'surface_condition':None,'attachment_method':None,'installation_verified':False,'probe_response_calibrated':False},'geometry':{'statistic':'single_probe_reading'},'settings':{'actual_record_interval_s':1,'interval_evidence':f'CSV Logging Summary + actual {max(0,len(raw)-1)} adjacent intervals checked below'},'time':{'clock_domain':'instrument_local_datetime','timezone':None,'sync_anchors':[]},'reference_record_id':None,'synthetic':False,'model_input':False,'control_input':False}
if args.probe_description:
    probe=json.loads(args.probe_description.read_text())
    session['site_description']=probe['site_description']
    session['contact'].update(fixed_position=probe['site_description'],attachment_method=probe['attachment_method'])
    session['contact']['installation_verification']='user_confirmation_only; physical calibration not established'
    session['probe_integrity_report']=probe
mapping={'input_path':'numeric_export','columns':{'measured_at_raw':'instrument_datetime_iso','original_value':'temperature_raw'},'constants':{'session_id':session['session_id'],'original_unit':'C','original_channel':'CH1','synthetic':False,'time_source':'instrument_csv_Date_plus_Time_preserved_no_timezone_or_offset','time_uncertainty_s':None},'time_axis':{'mode':'timestamp','sample_interval_s':1,'interval_basis':session['settings']['interval_evidence']},'csv':{'encoding':'utf-8','delimiter':','},'exported_at_raw':None,'trial_adapter':{'original_sha256':hashlib.sha256(b).hexdigest(),'original_header_line':header+1,'transform':'extract Data Table; combine Date+Time into ISO local datetime without timezone; retain all original data values and line map','file_created_at_raw':summary_fields.get('File Created Date'),'file_created_time_meaning':'instrument report field; actual USB export time unknown'}}
save(D/'mapping/session.json',session);save(D/'mapping/import-mapping.json',mapping)
store=D/'normalized'
for args,name in [(['init-session','--session',str(D/'mapping/session.json')],'init-session'),(['import','--file',str(extracted),'--mapping',str(D/'mapping/import-mapping.json')],'import')]:
    p=subprocess.run([sys.executable,str(TOOL),args[0],'--store',str(store),*args[1:]],text=True,capture_output=True)
    (D/'checks'/(name+'.stdout.json')).write_text(p.stdout)
    (D/'checks'/(name+'.stderr.log')).write_text(p.stderr)
    assert p.returncode==0,p.stderr
receipt=json.loads((D/'checks/import.stdout.json').read_text())
assert receipt['added']==len(raw) and receipt['rejected_rows']==0 and receipt['rows_with_missing_fields']==0,receipt
records=[json.loads(s) for s in (store/'records.jsonl').read_text().splitlines()]
assert len(records)==len(raw)
for record,r in zip(records,raw):
    assert record['temperature_c']==float(r['CH1'])
    assert record['measured_at_raw']==r['instrument_datetime_iso']
    assert record['time_uncertainty_s'] is None
intervals=[(c-a).total_seconds() for a,c in zip(timestamps,timestamps[1:])]
summary={'format_import_passed':True,'original_bytes':len(b),'original_sha256':hashlib.sha256(b).hexdigest(),'encoding':'ASCII bytes; UTF-8 compatible; no BOM; vendor encoding not uniquely identifiable','delimiter':',','line_ending':'CRLF','original_header_line':header+1,'columns':rows[header],'temperature_column':'CH1','channel_name':'Temp','unit':'Celsius / °C','row_count':len(raw),'file_summary_count':declared_count,'first_instrument_datetime':timestamps[0].isoformat(),'last_instrument_datetime':timestamps[-1].isoformat(),'instrument_duration_s':(timestamps[-1]-timestamps[0]).total_seconds(),'intervals':{'count':len(intervals),'min_s':min(intervals),'median_s':statistics.median(intervals),'max_s':max(intervals),'zero':sum(t==0 for t in intervals),'reversed':sum(t<0 for t in intervals),'different_from_declared_1s':sum(t!=1 for t in intervals)},'empty_temperatures':sum(v is None for v in values),'error_rows':errors,'equal_adjacent_temperature_pairs':sum(a==c for a,c in zip(values,values[1:])),'temperature_min_c':min(values),'temperature_max_c':max(values),'temperature_mean_c':statistics.mean(values),'time_format':'Date YYYY/MM/DD + Time HH:MM:SS, 24-hour; no UTC offset/timezone','timestamp_display_resolution_s':1,'host_alignment':'unconfirmed; manual approximate markers; unknown error; no affine/offset applied','instrument_clock_setting':'user confirmed manual clock setting completed; use separate formal clock evidence, no automatic offset','instrument_sample_time_not_button_time':True,'importer_started_tto_collection':False,'source_original_preserved':True}
save(D/'checks/csv-verification.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
