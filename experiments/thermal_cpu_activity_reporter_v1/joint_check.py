"""Reporter 1.0.1: original bridge and frozen consumers, explicit source declarations."""
import argparse
import base64
import collections
import json
import os
from pathlib import Path
import subprocess
import sys

from provenance import classify, sha

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = ROOT.parent/'thermal_cpu_activity_bridge_v1'
sys.path.insert(0, str(MODEL_ROOT))
from io_utils import read, lines, write, jsonl


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adapted', type=Path, required=True)
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    freeze = read(ROOT/'reporter-manifest.json')
    for name, digest in freeze['reporter_files'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('reporter identity changed: '+name)
    for name, digest in freeze['unchanged_model_line_files'].items():
        if sha(MODEL_ROOT/name) != digest:
            raise ValueError('frozen model-line identity changed: '+name)
    provenance = classify(a.run_dir, a.adapted)
    receipt = dict(contract='TTO-CPU-PREP-CLOSE-v1.0-R1', reporter_version=freeze['version'],
                   reporter_manifest_sha256=sha(ROOT/'reporter-manifest.json'),
                   data_source=provenance, synthetic_only=provenance['synthetic_only'],
                   new_physical_temperature_scores=False, source_lead_or_control_benefit=False,
                   evaluate_stream_called=False, analysis_complete=False,
                   reporter_execution=dict(network_clients=0, device_connections=0, parameter_search=0))
    if not provenance['identity_association_verified']:
        receipt['status'] = 'unresolved_source_association'
        write(a.output/'joint-receipt.json', receipt)
        print('Unresolved source association; frozen analysis not called. See joint-receipt.json.')
        return
    wire = {x['wire_seq']: x for x in lines(a.run_dir/'cpu-sidecar-wire.jsonl')}
    arrivals = lines(a.run_dir/'cpu-sidecar-arrivals.jsonl')
    for row in arrivals:
        w = wire[row['wire_seq']]
        assert not w['truncated'] and json.loads(base64.b64decode(w['raw_base64'])) == row['source']
        assert w['received_at_mono_s'] == row['received_at_mono_s'] and w['receiver_domain'] == row['receiver_domain']
    sys.path.insert(0, str(MODEL_ROOT/'frozen'))
    from activity import load_candidate, Processor
    c, f = load_candidate(MODEL_ROOT/'frozen')
    processor = Processor(c, f)
    frames = lines(a.adapted/'frames.jsonl')
    outputs = [processor.process(x) for x in frames]
    jsonl(a.output/'processor.jsonl', outputs)
    counts = {n: dict(collections.Counter(r['variants'][n]['activity']['state'] for r in outputs)) for n in c['variants']}
    availability = {n: any(state != 'UNKNOWN' and count > 0 for state, count in x.items()) for n, x in counts.items()}
    # UNKNOWN is a retained result, not a reason to change the adapter or candidate.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    args = [sys.executable, str(MODEL_ROOT/'frozen/evaluate_stream.py'),
            '--frames', str(a.adapted.resolve()/'frames.jsonl'),
            '--origins', str(a.adapted.resolve()/'thermal-origins.jsonl'),
            '--registration', str(a.adapted.resolve()/'registration.json'),
            '--output', str(a.output.resolve()/'evaluate-stream')]
    with (a.output/'evaluate-stream.log').open('w') as log:
        subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    receipt.update(status='analysed', analysis_complete=True,
                   source_declaration_unresolved=provenance['category'] == 'unknown',
                   actual_wire_to_source_rows_verified=len(arrivals), frames=len(frames), Activity_counts=counts,
                   variant_has_nonUNKNOWN=availability,
                   activity_comparison_status='some_available' if all(availability.values()) else 'unresolved_variant_availability',
                   actual_sender_receiver_artifacts_used=bool(arrivals), manual_model_FRAME_used=False,
                   original_TJ_origins=len(lines(a.adapted/'thermal-origins.jsonl')),
                   revocations=dict(collections.Counter(x['reason'] for x in lines(a.adapted/'revocations.jsonl'))),
                   candidate_sha256=sha(MODEL_ROOT/'frozen/candidate.json'),
                   analysis_spec_sha256=sha(MODEL_ROOT/'frozen/analysis-spec.json'),
                   evaluate_stream_called=True, actual_and_1s_delivery_conditions_written=True)
    write(a.output/'joint-receipt.json', receipt)
    print('Frozen analysis written:', provenance['label_zh'], len(arrivals), 'wire rows;', len(frames), 'frames.')


if __name__ == '__main__':
    main()
