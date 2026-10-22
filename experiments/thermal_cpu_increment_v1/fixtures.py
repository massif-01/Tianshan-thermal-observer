"""Explicitly synthetic timing fixtures; not YET, Thor or new activity measurements."""
import argparse
import copy
from pathlib import Path
from common import ROOT, write, jsonl, read, sha


def frame(t, *, active=False, core_only=False, sequence=None, until=None):
    config=read(ROOT/'candidate.json')
    sequence=t if sequence is None else sequence
    level=copy.deepcopy(config['levels']['active' if active else 'idle'])
    if core_only:level['cpu_max_pct']=30.
    features={k:dict(value=v,available_at_mono_s=t,valid_until_mono_s=t+5 if until is None else until,
        update_id=f'synthetic:{k}:{sequence}',source_order=sequence,valid=True,
        feature_source='SYNTHETIC fixture only',source_host='SYNTHETIC-Thor',source_clock_id='synthetic-source-clock',
        source_boot_id='synthetic-boot',source_sample_mono_s=t-.04,source_read_start_mono_s=t-.05,
        source_read_end_mono_s=t-.03,window_start_mono_s=t-.24,window_end_mono_s=t-.04,
        age_lower_bound_ms=40.,transport_delay_ms=20.,source_window_verified=True,
        update_evidence='synthetic explicitly generated independent counter window',original_ref=f'synthetic:{sequence}',
        unknowns=[],raw_unit='percent' if k.endswith('_pct') else 'W') for k,v in level.items()}
    return dict(schema='TTO-CPU-ACTIVITY-FRAME-v1',synthetic=True,source_only=False,
        native_ref=f'synthetic:{sequence}',arrival_clock_id='synthetic-receiver-clock',arrival_mono_s=t,
        arrival_host='SYNTHETIC-N305',arrival_boot_id='synthetic-receiver-boot',epoch=1,features=features,
        thermal=dict(available=True,current_TJ_C=50.,Ts_C=44.,E_C=35.,
            conditional_inputs_rails_W_PWM=[2.,6.,.4],state_native_ref=f'synthetic:{sequence}',
            model_sha256=config['immutable']['model_sha256'],
            observer_spec_sha256=config['immutable']['observer_spec_sha256']))


def make(destination):
    destination.mkdir(parents=True,exist_ok=False)
    seq=[frame(round(i*.2,6),active=i>=10,core_only=7<=i<10) for i in range(30)]
    jsonl(destination/'synthetic-200ms.jsonl',seq)
    duplicate=frame(1.,active=True,sequence=1,until=1.5)
    reread=copy.deepcopy(duplicate);reread['arrival_mono_s']=2.
    for f in reread['features'].values():
        f['available_at_mono_s']=2.
        f['valid_until_mono_s']=7.
    jsonl(destination/'synthetic-repeated-buffer.jsonl',[duplicate,reread])
    source=frame(3.,active=True);source['source_only']=True;source['arrival_clock_id']=None
    jsonl(destination/'synthetic-source-only.jsonl',[source])
    write(destination/'README.json',dict(synthetic=True,field_data=False,expected_real_sample_interval_ms=None,
        purpose='exercise incremental CORE, timestamp availability, repeated cache and source-only rejection; never evidence of real 200ms resolution'))
    stream=[frame(i/5,active=i>=13,core_only=10<=i<13) for i in range(301)]
    jsonl(destination/'synthetic-stream-200ms.jsonl',stream)
    origins=[]
    for t in range(61):
        x=frame(float(t))
        origins.append(dict(ref=f'synthetic-origin:{t}',t=float(t),current=50.,source_valid=True,synthetic=True,
            epoch=1,source_key=['synthetic','synthetic-stream'],thermal=x['thermal'],arrival_clock_id=x['arrival_clock_id']))
    jsonl(destination/'synthetic-origins-1s.jsonl',origins)
    jsonl(destination/'synthetic-actual-events.jsonl',[
        dict(event_id='synthetic-request-1',submit_mono_s=1.5,done_mono_s=20.,arrival_clock_id='synthetic-receiver-clock',continuous_group='synthetic'),
        dict(event_id='synthetic-request-2',submit_mono_s=25.,done_mono_s=40.,arrival_clock_id='synthetic-receiver-clock',continuous_group='synthetic')])
    write(destination/'synthetic-registration.json',dict(run_id='synthetic-cpu-interface-001',synthetic=True,field_data=False,
        declared_role='synthetic_interface_verification_only',saw_new_data_for_parameter_selection=False,
        candidate_sha256=sha(ROOT/'candidate.json'),analysis_spec_sha256=sha(ROOT/'analysis-spec.json')))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    make(ap.parse_args().output)
