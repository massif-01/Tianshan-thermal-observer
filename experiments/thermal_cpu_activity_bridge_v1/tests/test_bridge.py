import base64
import copy
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from io_utils import read,lines,sha
from bridge import Bridge,adapt,cpu_window
sys.path.insert(0,str(ROOT/'frozen'))
from activity import load_candidate,Processor
from evaluate_stream import evaluate,downsample_1s

SAMPLE=ROOT/'inputs/joint-complete'
RUN=SAMPLE/'run'


def all_data():
    b,frames,origins=adapt(RUN,read(SAMPLE/'source-config.json'))
    return b,frames,origins


def start_with_actual_window():
    binding=read(RUN/'native-binding.json');launch=read(RUN/'launch.json')
    mp=RUN/binding['native_manifest'];b=Bridge(read(mp),binding,launch,read(SAMPLE/'source-config.json'))
    b.raw_by_ref={r['ref']:r for r in lines(mp.parent/'observations-0001.jsonl')}
    rows=lines(RUN/'cpu-sidecar-arrivals.jsonl')
    for e in lines(RUN/'states.jsonl'):
        if e['clock']['generated_at_mono_s']>rows[1]['decision_generated_mono_s']:break
        b.native_event(e,b.raw_by_ref[e['generation_evidence']['native_ref']],e['clock']['generated_at_mono_s'])
    for i,r in enumerate(rows[:2],1):b.cpu_event(r,'actual-arrival:'+str(i),r['decision_generated_mono_s'])
    assert b.features['cpu_mean_pct']['valid']
    return b,rows


def test_actual_wire_and_code_identity_and_all_variants_usable():
    receipt=read(SAMPLE/'sample-receipt.json')
    assert sha(ROOT/'inputs/emitter-receiver-source/cpu_source.py')==receipt['source_code_sha256']
    assert sha(ROOT/'inputs/emitter-receiver-source/cpu_transport.py')==receipt['receiver_code_sha256']
    wires={x['wire_seq']:x for x in lines(RUN/'cpu-sidecar-wire.jsonl')}
    for row in lines(RUN/'cpu-sidecar-arrivals.jsonl'):
        w=wires[row['wire_seq']]
        assert json.loads(base64.b64decode(w['raw_base64']))==row['source']
        assert row['received_at_mono_s']==w['received_at_mono_s']
    b,frames,origins=all_data();c,f=load_candidate(ROOT/'frozen');p=Processor(c,f)
    outputs=[p.process(x) for x in frames]
    assert all(any(r['variants'][n]['activity']['state']!='UNKNOWN' for r in outputs) for n in c['variants'])
    assert len(origins)==len({r['ref'] for r in origins})
    assert all(r['t']>=r['measurement_received_mono_s'] for r in origins)


@pytest.mark.parametrize('reason',['counter_reset_iowait_decrease_or_zero_window','online_set_changed','native_epoch_changed'])
def test_actual_invalid_revokes_and_later_actual_valid_window_recovers(reason):
    b,frames,_=all_data()
    event=next(e for e in b.audit if e['reason']==reason and (reason!='native_epoch_changed' or e['available_at_mono_s']>frames[0]['arrival_mono_s']+30))
    i=next(i for i,f in enumerate(frames) if f['arrival_mono_s']==event['available_at_mono_s'] and not f['features']['cpu_mean_pct'].get('valid'))
    assert not frames[i]['features']['cpu_max_pct'].get('valid')
    if reason!='native_epoch_changed':
        previous=next(f for f in reversed(frames[:i]) if f['features'].get('cpu_mean_pct',{}).get('valid'))
        assert previous['features']['cpu_mean_pct']['valid_until_mono_s']>frames[i]['arrival_mono_s']
    assert any(x['features'].get('cpu_mean_pct',{}).get('valid') for x in frames[i+1:])
    c,f=load_candidate(ROOT/'frozen');p=Processor(c,f)
    outputs=[p.process(x) for x in frames]
    assert outputs[i]['variants']['INPUT-MEAN']['activity']['state']=='UNKNOWN'
    assert outputs[i]['variants']['INPUT-CORE']['activity']['state']=='UNKNOWN'


def test_actual_new_CPU_never_renews_old_coarse_cache_and_native_gap_stays_unknown():
    _,frames,_=all_data();checked=0
    for a,b in zip(frames,frames[1:]):
        if b['adapter_event']=='cpu' and a['epoch']==b['epoch']:
            for name in ('gpu_pct','gpu_W','cpu_soc_mss_W'):
                assert a['features'].get(name)==b['features'].get(name)
            checked+=1
    assert checked>100
    gap=[x for x in frames if x['adapter_event']=='cpu' and x['features'].get('cpu_mean_pct',{}).get('valid')
         and not x['features'].get('gpu_W',{}).get('valid')]
    assert gap
    c,f=load_candidate(ROOT/'frozen');p=Processor(c,f)
    lookup={x['native_ref']:p.process(x) for x in frames}
    assert all(lookup[x['native_ref']]['variants']['INPUT-BASE']['activity']['state']=='UNKNOWN' for x in gap)


def test_repeated_actual_packet_does_not_renew_and_equal_new_windows_survive():
    b,rows=start_with_actual_window();old=copy.deepcopy(b.features['cpu_mean_pct'])
    duplicate=copy.deepcopy(rows[1]);t=rows[1]['decision_generated_mono_s']+.4
    duplicate['received_at_mono_s']+=.4;duplicate['decision_generated_mono_s']=t
    b.cpu_event(duplicate,'reread-actual-buffer',t)
    assert b.features['cpu_mean_pct']==old
    next_row=rows[2]
    assert cpu_window(rows[1]['source'])['mean_percent']==cpu_window(next_row['source'])['mean_percent']
    b.cpu_event(next_row,'actual-next-window',next_row['decision_generated_mono_s'])
    assert b.features['cpu_mean_pct']['update_id']!=old['update_id']
    assert b.features['cpu_mean_pct']['value']==old['value']


@pytest.mark.parametrize('mutation,reason',[
    ('foreign_run','sidecar_foreign_run_or_command'),
    ('unknown_source_clock','source_identity_or_clock_unknown'),
    ('regressed_seq','source_sequence_regression'),
    ('new_session','source_identity_changed')])
def test_negative_derivatives_of_actual_envelopes_never_fall_back(mutation,reason):
    b,rows=start_with_actual_window();x=copy.deepcopy(rows[2]);t=x['decision_generated_mono_s']
    if mutation=='foreign_run':x['native_run_id']='other-run'
    elif mutation=='unknown_source_clock':x['source']['identity']['clock']=None
    elif mutation=='regressed_seq':x['source']['seq']=1
    else:x['source']['identity']['source_session']='new-source-session'
    b.cpu_event(x,'negative-derivative-of-real-envelope',t)
    assert not b.features['cpu_mean_pct'].get('valid') and not b.features['cpu_max_pct'].get('valid')
    assert b.audit[-1]['reason']==reason
    assert b.features['gpu_W']['valid']


def test_partial_online_set_is_not_silently_averaged_and_unmapped_receiver_rejected():
    b,rows=start_with_actual_window();x=copy.deepcopy(rows[2]);t=x['decision_generated_mono_s']
    for name in ('raw_cpu','previous_raw_cpu'):x['source'][name]['per_core_online'].pop('cpu1')
    b.cpu_event(x,'incomplete-online-map',t)
    assert not b.features['cpu_mean_pct'].get('valid')
    assert b.audit[-1]['reason']=='incomplete_possible_or_online_set'
    x=copy.deepcopy(rows[3]);x['receiver_domain']='unknown-other-clock'
    with pytest.raises(ValueError,match='receiver_clock_unmapped'):b.cpu_event(x,'unknown-receiver',x['decision_generated_mono_s'])


def test_future_source_records_cannot_change_earlier_predictions_and_horizons_independent():
    _,frames,origins=all_data();c,f=load_candidate(ROOT/'frozen')
    original=evaluate(frames,origins,c,f)
    cutoff=origins[len(origins)//2]['t']
    # Keep the actual artifact prefix. Changing/deleting future delivered records
    # cannot change an already-generated prediction (labels may legitimately differ).
    prefix=[x for x in frames if x['arrival_mono_s']<=cutoff]
    short=evaluate(prefix,origins,c,f)
    assert [x['prediction'] for x in original['points'] if x['t']<=cutoff]==[x['prediction'] for x in short['points'] if x['t']<=cutoff]
    cov={(x['method'],x['h']):x for x in original['coverage']}
    assert cov['B0',15]['valid_labels']>0 and cov['B0',90]['valid_labels']==0
    assert cov['INPUT-CORE',15]['predictions']>0 and cov['INPUT-CORE',45]['predictions']>0
    coarse=downsample_1s(frames)
    assert all(x['actual_original_arrival_mono_s']<=x['arrival_mono_s'] for x in coarse)
    assert all(x['features'].get('cpu_mean_pct',{}).get('source_read_window') is None or
               x['features']['cpu_mean_pct']['source_clock_mapping']=='unknown' for x in coarse)


def test_original_model_and_activity_files_stay_byte_exact():
    manifest=read(ROOT/'frozen-source.json')
    for rel,digest in manifest['files'].items():assert sha(ROOT/'frozen'/rel)==digest


def test_receiver_budget_anchors_actual_receive_not_late_parse_or_duplicate_reads():
    b,rows=start_with_actual_window();row=copy.deepcopy(rows[2])
    row['decision_generated_mono_s']=row['received_at_mono_s']+1.1
    b.cpu_event(row,'delayed-actual-envelope-decision',row['decision_generated_mono_s'])
    assert not b.features['cpu_mean_pct']['valid']
    assert b.features['cpu_mean_pct']['valid_until_mono_s']==row['received_at_mono_s']+1.
