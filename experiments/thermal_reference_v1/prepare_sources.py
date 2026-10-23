"""Prepare minimal real adapters and explicitly synthetic reference fixtures; no live inputs."""
from pathlib import Path
import ast
import base64
import copy
import json
import sys
from refprep.files import read,write,lines,dump_lines,sha
from refprep.clocks import iso,utc_seconds
from refprep.cues import DEFAULT_PLAN
from refprep.trajectory import adapt

ROOT=Path(__file__).absolute().parent


def prepare(slowstate=None,events=None):
    slowstate=Path(slowstate) if slowstate else ROOT.parent/'thermal_slowstate_v1'
    events=Path(events) if events else ROOT.parents[1]/'evidence/midload-024-useroverride-20261014/runner-events.jsonl'
    real=ROOT/'fixtures/real';demo=ROOT/'fixtures/synthetic'
    real.mkdir(parents=True,exist_ok=True);demo.mkdir(parents=True,exist_ok=True)
    if slowstate.exists():adapt(slowstate,real/'M-frozen.jsonl','M')
    if events.exists():
        keys=['event','phase','kind','mono_s','occurred_at_utc','written_at_utc','actual_start_mono_s',
              'actual_end_mono_s','duration_s','planned_end_mono_s','actual_duration_s','request_id','client_end_mono_s','reason']
        subset=[{k:v for k,v in row.items() if k in keys} for row in lines(events)
                if row.get('event') in ['phase_start','phase_end','request_end','schedule_end']]
        dump_lines(real/'M-runner-events-subset.jsonl',subset)
        write(real/'event-provenance.json',dict(original_file_sha256=sha(events),
            subset_sha256=sha(real/'M-runner-events-subset.jsonl'),rows=len(subset),
            fields='literal original timing/phase metadata only; no requests issued, no admission override inherited'))
    rows=lines(real/'M-frozen.jsonl')
    if not rows:raise ValueError('Prepare needs existing frozen M output or shipped minimal fixture')
    run=rows[0]['run_id']
    session=read(ROOT/'handoff/templates/reference-session.example.json')
    session.update(run_id=run,session_id='SYNTH-fin',site_id='fin-A',synthetic=True,
                   reference_record_id='fin-bg',example_only=True)
    session['time']=dict(clock_domain='run_utc',timezone='+00:00',sync_basis='SYNTHETIC fixture UTC coordinates only',
                         sync_uncertainty_s=0,sync_anchors=[])
    write(demo/'fin-session.json',session)
    back=copy.deepcopy(session);back.update(session_id='SYNTH-back',site_id='back-A',
        measurement_kind='backplate_surface_ir',site_description='合成背板独立点，不合并到鳍片',reference_record_id='back-bg')
    write(demo/'back-session.json',back)
    marks=[rows[30],rows[1050],rows[1150],rows[1900]]
    write(demo/'point-times.json',{k:r['utc'] for k,r in zip(['background','work','recovery','late'],marks)})
    # A generic color image is evidence only, not radiometric temperature data.
    (demo/'image-evidence.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg=='))
    import csv
    with (demo/'external.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['id','session','reading','units','capture_time','uncertainty','photo','note'])
        writer.writeheader()
        for row in [dict(id='fin-work',session='SYNTH-fin',reading='108.5',units='F',capture_time=marks[1]['utc'],uncertainty='0',photo='',note='合成值，不是现场测温'),
                    dict(id='fin-recovery',session='SYNTH-fin',reading='41.2',units='C',capture_time=marks[2]['utc'],uncertainty='0',photo='',note='合成值'),
                    dict(id='fin-image-only',session='SYNTH-fin',reading='',units='C',capture_time='',uncertainty='',photo='image-evidence.png',note='只有合成图片，没有数字，不按颜色解温度')]:writer.writerow(row)
    mapping=dict(columns=dict(record_id='id',session_id='session',original_value='reading',original_unit='units',
        measured_at_raw='capture_time',time_uncertainty_s='uncertainty',artifact_path='photo',note='note'),
        constants=dict(time_source='synthetic_fixture_explicit_UTC',synthetic=True))
    write(demo/'csv-mapping.json',mapping)
    write(demo/'external.json',[dict(id='back-bg',session='SYNTH-back',value=36.0,unit='C',time=marks[0]['utc'],uncertainty=0),
        dict(id='back-work',session='SYNTH-back',value=37.3,unit='C',time=marks[1]['utc'],uncertainty=0)])
    write(demo/'json-mapping.json',dict(columns=dict(record_id='id',session_id='session',original_value='value',
        original_unit='unit',measured_at_raw='time',time_uncertainty_s='uncertainty'),
        constants=dict(synthetic=True,time_source='synthetic_fixture_explicit_UTC')))
    base=utc_seconds('2030-01-01T00:00:00+00:00');event_rows=[]
    for phase,start,end,nominal in [('resident_background',0,180,180),('sparse',180,545,360),
            ('between_groups',545,845,300),('continuous',845,1001,150),('cooldown',1001,1400,399),
            ('optional_medium',1400,1467,60),('final_cooldown',1467,1800,333)]:
        for event,t in [('phase_start',start),('phase_end',end)]:
            row=dict(event=event,phase=phase,mono_s=1000+t,occurred_at_utc=iso(base+t),written_at_utc=iso(base+t),
                     duration_s=nominal,synthetic=True)
            row['actual_start_mono_s' if event=='phase_start' else 'actual_end_mono_s']=1000+t
            if event=='phase_end':row['planned_end_mono_s']=1000+start+nominal
            event_rows.append(row)
    event_rows.append(dict(event='schedule_end',mono_s=2801,actual_end_mono_s=2801,occurred_at_utc=iso(base+1801),written_at_utc=iso(base+1801),synthetic=True))
    dump_lines(demo/'events.jsonl',event_rows)
    plan=copy.deepcopy(DEFAULT_PLAN);plan['run_id']='SYNTHETIC-CUE-RUN';plan['bindings']['medium']='optional_medium'
    plan['bindings']['pre_medium']='cooldown';plan['pre_medium_offset_s']=369
    write(demo/'cue-plan.json',plan)
    historic=copy.deepcopy(DEFAULT_PLAN);historic['run_id']=run;historic['bindings']['medium']='M60'
    historic['bindings']['pre_medium']='cooldown_1';historic['pre_medium_offset_s']=390
    write(real/'M-cue-plan.json',historic)
    # Maintenance copy of the ONE affected old test; only its numerical equality changes.
    original=ROOT/'handoff/references/slowstate-snapshot/tests/test_slowstate.py'
    text=original.read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='test_two_dimensional_export_and_anchor_not_forecast')
    old='\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])+'\n'
    new=old.replace("assert all(r['Tf']==r['sealed_Tf'] for r in long)","assert all(abs(r['Tf']-r['sealed_Tf'])<=1e-10 for r in long)")
    assert old!=new
    maintenance=ROOT/'maintenance';maintenance.mkdir(exist_ok=True)
    (maintenance/'original-target-test.txt').write_text(old)
    (maintenance/'tolerance-target-test.py.txt').write_text(new)
    write(maintenance/'provenance.json',dict(original_test_file_sha256=sha(original),
        original_target_sha256=sha(maintenance/'original-target-test.txt'),
        maintained_target_sha256=sha(maintenance/'tolerance-target-test.py.txt'),
        change='Only recomputed Tf numerical == becomes abs difference <=1e-10. Original file/model/archive SHA stay exact.',
        source='immutable provided slowstate test snapshot',old_research_file_modified=False))
    write(ROOT/'source-index.json',dict(attachment=read(ROOT/'attachment-identity.json'),
        original_slowstate_spec_sha256=sha(ROOT/'handoff/references/slowstate-snapshot/slowstate-spec.json'),
        frozen_models={p.name:sha(p) for p in (ROOT/'frozen/models').glob('*.json')},
        local_real_fixture_files={str(p.relative_to(ROOT)):sha(p) for p in real.iterdir() if p.is_file()},
        synthetic_fixture_files={str(p.relative_to(ROOT)):sha(p) for p in demo.iterdir() if p.is_file()},
        ambient_new_run=None,no_model_refit=True,no_device_actions=True))
    print('Prepared minimal M adapter, original event subset and explicitly synthetic reference fixtures.')


if __name__=='__main__':prepare(*(sys.argv[1:3]))
