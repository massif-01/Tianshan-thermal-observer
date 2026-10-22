"""Prove the wording fix preserves actual prior demonstration values and qualifications."""
from pathlib import Path
import json
import hashlib
import sys
ROOT=Path(__file__).absolute().parent.parent
sys.path.insert(0,str(ROOT))
from refprep.files import read,lines,write,sha
fields=['status','distinct_records','history_revisions','numeric_points','real_numeric_points','synthetic_numeric_points',
        'paired_points','unpaired_reasons','reference_statuses','trajectory_sha256','coverage','model_sha256']
record_fields=['record_id','run_id','session_id','site_id','measurement_kind','temperature_c','original_value','original_unit',
               'measured_at_raw','measured_interval_raw','clock_domain','time_uncertainty_s','measurement_flags','synthetic']
counts={}
for name in ['synthetic-report','contact-report','zero-report']:
    old=ROOT/'results/release-check'/name;new=ROOT/'review_fix_v1/results/full-flow'/name
    a=read(old/'comparison.json');b=read(new/'comparison.json')
    for key in fields:assert a[key]==b[key],(name,key)
    semantic_event=lambda e:{k:v for k,v in e.items() if k not in ['event_id','recorded_at_utc']}
    assert [semantic_event(e) for e in a['session_events']]==[semantic_event(e) for e in b['session_events']]
    first=lines(old/'paired-points.jsonl');second=lines(new/'paired-points.jsonl');assert len(first)==len(second)
    for x,y in zip(first,second):
        for key in record_fields:assert x['record'].get(key)==y['record'].get(key),(name,key)
        for key in ['time_alignment','model_match','delta','reference_status','physical_mapping_validated']:
            left=x[key];right=y[key]
            if key=='model_match':
                left={k:v for k,v in left.items() if k!='event_id'}
                right={k:v for k,v in right.items() if k!='event_id'}
            assert left==right,(name,key)
    counts[name]=dict(records=len(first),numeric=a['numeric_points'],paired=a['paired_points'])
archive=ROOT/'TTO-测温记录准备与路线图同步-证据包.zip'
assert sha(archive)=='f32ccb4c3a70d9005a74c66c2f0b736f5362c9e6ebe85d64f9e912feaef48b1c'
assert sha(ROOT/'TTO-测温记录准备与路线图同步-实施报告.md')=='62efbbc9101628fed4bdd7e43d2f85b88cf200c1daa15abda33028acc993ed18'
write(ROOT/'review_fix_v1/unchanged-results-receipt.json',dict(status='pass',cases=counts,
    temperature_time_model_range_reference_and_qualification_equal=True,
    excluded_run_specific_fields=['new write/import/mark timestamps','revision/event UUIDs; event semantics verified separately','output paths'],
    original_accepted_archive_unchanged=True,original_delivery_report_unchanged=True))
print('PASS: prior numeric/time/qualification results and accepted archive/report unchanged.')
