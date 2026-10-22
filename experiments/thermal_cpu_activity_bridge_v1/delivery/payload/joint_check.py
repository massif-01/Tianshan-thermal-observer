"""Actual producer/receiver artifact -> unique adapter -> unchanged model consumers."""
import argparse
import base64
import collections
import json
import os
from pathlib import Path
import subprocess
import sys
from io_utils import ROOT,read,lines,write,jsonl,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adapted',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    wire={x['wire_seq']:x for x in lines(a.run_dir/'cpu-sidecar-wire.jsonl')}
    arrivals=lines(a.run_dir/'cpu-sidecar-arrivals.jsonl')
    for row in arrivals:
        w=wire[row['wire_seq']]
        assert not w['truncated'] and json.loads(base64.b64decode(w['raw_base64']))==row['source']
        assert w['received_at_mono_s']==row['received_at_mono_s'] and w['receiver_domain']==row['receiver_domain']
    sys.path.insert(0,str(ROOT/'frozen'))
    from activity import load_candidate,Processor
    c,f=load_candidate(ROOT/'frozen');processor=Processor(c,f)
    frames=lines(a.adapted/'frames.jsonl');outputs=[processor.process(x) for x in frames]
    jsonl(a.output/'processor.jsonl',outputs)
    counts={n:dict(collections.Counter(r['variants'][n]['activity']['state'] for r in outputs)) for n in c['variants']}
    assert all(sum(count for state,count in x.items() if state!='UNKNOWN')>0 for x in counts.values())
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    args=[sys.executable,str(ROOT/'frozen/evaluate_stream.py'),'--frames',str(a.adapted.resolve()/'frames.jsonl'),
        '--origins',str(a.adapted.resolve()/'thermal-origins.jsonl'),'--registration',str(a.adapted.resolve()/'registration.json'),
        '--output',str(a.output.resolve()/'evaluate-stream')]
    with (a.output/'evaluate-stream.log').open('w') as log:
        subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    write(a.output/'joint-receipt.json',dict(contract='TTO-CPU-PREP-CLOSE-v1.0-R1',
        actual_wire_to_source_rows_verified=len(arrivals),frames=len(frames),Activity_counts=counts,
        actual_sender_receiver_artifacts_used=True,manual_model_FRAME_used=False,
        original_TJ_origins=len(lines(a.adapted/'thermal-origins.jsonl')),
        revocations=dict(collections.Counter(x['reason'] for x in lines(a.adapted/'revocations.jsonl'))),
        candidate_sha256=sha(ROOT/'frozen/candidate.json'),analysis_spec_sha256=sha(ROOT/'frozen/analysis-spec.json'),
        evaluate_stream_called=True,actual_and_1s_delivery_conditions_written=True,
        synthetic_only=True,new_physical_temperature_scores=False,source_lead_or_control_benefit=False,
        network_clients=0,device_connections=0,parameter_search=0))
    print('Joint chain passed:',len(arrivals),'actual serialized/received rows ->',len(frames),'frames -> frozen Activity/evaluate_stream.')


if __name__=='__main__':main()
