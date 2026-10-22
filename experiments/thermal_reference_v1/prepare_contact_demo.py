"""ADD1 synthetic generic continuous export; deliberately NOT a YET file-format emulator."""
from pathlib import Path
import copy
import csv
from refprep.files import read,write,lines,sha,now_utc
from refprep.clocks import iso

ROOT=Path(__file__).absolute().parent


def prepare():
    fixture=ROOT/'fixtures/contact-synthetic';fixture.mkdir(parents=True,exist_ok=True)
    old=lines(ROOT/'fixtures/real/M-frozen.jsonl');start=old[20]['utc_s'];run=old[20]['run_id']
    session=read(ROOT/'templates/contact-session.example.json')
    session.update(run_id=run,session_id='SYNTH-contact-fin',site_id='SYNTH-contact-fin-site',
                   synthetic=True,reference_record_id='contact-bg',example_only=True)
    session['time']=dict(clock_domain='synthetic_instrument_elapsed',timezone=None,sync_anchors=[
        dict(clock_time=0,run_utc=iso(start),uncertainty_s=.2,evidence='SYNTHETIC independent start clock check'),
        dict(clock_time=120,run_utc=iso(start+120.012),uncertainty_s=.2,evidence='SYNTHETIC independent end clock check')])
    write(fixture/'fin-session.json',session)
    back=copy.deepcopy(session);back.update(session_id='SYNTH-contact-back',site_id='SYNTH-contact-back-site',reference_record_id=None)
    back['contact']['fixed_position']='SYNTHETIC separate backplate site, not actual installation'
    write(fixture/'back-session.json',back)
    rows=[]
    for i in range(121):
        if i==75:continue  # missing sample remains missing, no row invented
        for ch in ['A','B']:
            value='ERR' if i==44 and ch=='A' else '' if i==52 and ch=='A' else f'{41+(i//10)*.1+(ch=="B"):.1f}'
            rows.append(dict(sample=i,channel=ch,temperature=value,unit='C',
                             id='contact-bg' if i==0 and ch=='A' else f'contact-{ch}-{i}'))
    with (fixture/'generic-continuous.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['sample','channel','temperature','unit','id']);writer.writeheader();writer.writerows(rows)
    mapping=dict(input_path='numeric_export',synthetic_only=True,
        columns=dict(record_id='id',measured_at_raw='sample',original_value='temperature',original_unit='unit',original_channel='channel'),
        constants=dict(synthetic=True,time_source='synthetic_instrument_sample_index',time_uncertainty_s=.1),
        channels={'A':dict(session_id=session['session_id'],site_id=session['site_id']),
                  'B':dict(session_id=back['session_id'],site_id=back['site_id'])},
        time_axis=dict(mode='sample_index',index_origin=0,sample_interval_s=1,
                       interval_basis='SYNTHETIC explicitly selected 1s setting, not actual YET evidence'),
        exported_at_raw='SYNTHETIC export-time unknown',csv=dict(encoding='utf-8-sig',delimiter=','))
    write(fixture/'mapping.json',mapping)
    write(fixture/'description.json',dict(synthetic=True,not_real_YET_format=True,rows=len(rows),
        planned_interval_s=1,deliberately_missing_index=75,rejected_value=dict(index=44,channel='A',raw='ERR'),
        missing_numeric=dict(index=52,channel='A'),equal_adjacent_readings_are_new_samples=True,
        start_anchor_utc=iso(start),run_id=run,ambient_temperature_c=None))
    files={str(p.relative_to(ROOT)):sha(p) for p in sorted(fixture.glob('*')) if p.is_file()}
    write(ROOT/'contact-source-index.json',dict(contract='TTO-REF-PREP-v1.0-ADD1',written_at_utc=now_utc(),
        entirely_synthetic_external_data=True,real_YET_CSV_mapping_accepted=False,files=files))


if __name__=='__main__':prepare()
