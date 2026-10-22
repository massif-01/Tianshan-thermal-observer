"""Independent contract checks on saved data, without I02/observer replay."""
import argparse
import bisect
from pathlib import Path
from common import ROOT, read, lines, write, sha
from activity import load_candidate
from evaluate_stream import evaluate


def verify(result, output, check_originals=False):
    c,f=load_candidate()
    copied=[]
    for s in read(ROOT/'sources.json')['sources']:
        p=ROOT/s['local_path']
        assert sha(p)==s['sha256'] and p.stat().st_size==s['bytes'],str(p)
        if check_originals:
            assert sha(Path(s['source_path']))==s['sha256'],s['source_path']
        copied.append(s['local_path'])
    frames=list(lines(result/'feature-frames.jsonl'))
    fm={f['native_ref']:f for f in frames}
    samples=list(lines(ROOT/'inputs/results/samples-and-causal-states.jsonl'))
    origins=[]
    for s in samples:
        x=fm.get(s['ref'])
        origins.append(dict(s,thermal=x['thermal'] if x else None,
                            arrival_clock_id=x['arrival_clock_id'] if x else None))
    fresh=evaluate(frames,origins,c,f)
    original=list(lines(ROOT/'inputs/results/predictions.jsonl'))
    assert len(fresh['points'])==len(original)
    max_hold=0.;label_checks=baseline_checks=0
    for a,b in zip(fresh['points'],original):
        assert (a['ref'],a['h'])==(b['ref'],b['h'])
        if a['label']:
            assert b['label']
            for k in ('ref','t','value','offset_s'):assert a['label'][k]==b['label'][k]
        else:assert not b['label'] and a['label_rejection']==b['label_rejection']
        label_checks+=1
        for n in ('B0','B1'):
            assert (n in a['prediction'])==(n in b['baselines'])
            if n in a['prediction']:
                assert abs(a['prediction'][n]-b['baselines'][n])<1e-10
                baseline_checks+=1
        if 'G2-HOLD' in a['prediction']:
            max_hold=max(max_hold,abs(a['prediction']['G2-HOLD']-b['B_HOLD']['AUGMENTED-KF']))
    assert max_hold<1e-8
    current=list(lines(result/'temperature-points.jsonl'))
    for a,b in zip(fresh['points'],current):
        assert set(a['prediction'])==set(b['prediction'])
        for name,value in a['prediction'].items():
            if name=='G2-HOLD':
                assert abs(value-b['prediction'][name])<1e-8
            else:
                assert value==b['prediction'][name]
    protected=[]
    if check_originals:
        for p in read(ROOT/'protected-before.json'):
            path=Path(p['path'])
            assert path.stat().st_size==p['bytes'] and sha(path)==p['sha256'],p['path']
            protected.append(p['path'])
    # The original failed test was a test HTTPConnection context-manager use;
    # no activity parameter has changed since freeze, and scientific predictions
    # are byte-identical before/after the additional event-count diagnostics.
    initial=ROOT/'runs/attempt-01'
    identical=[]
    if initial.exists() and initial.resolve()!=result.resolve():
        for name in ['activity-and-candidate-predictions.jsonl','temperature-points.jsonl',
                     'temperature-common.json','temperature-coverage.json','stale-and-context-sensitivity.json',
                     'incremental-activity-information.json']:
            assert sha(initial/name)==sha(result/name),name
            identical.append(name)
    summary=dict(copied_sources_checked=len(copied),source_checks=copied,
        label_decisions_independently_rebuilt=label_checks,baseline_values_checked=baseline_checks,
        old_HOLD_max_abs_difference_C=max_hold,
        future_stream_entry_reproduces_old_candidate_predictions=True,
        protected_original_files_checked=len(protected),
        original_path_checks_requested=check_originals,
        pre_and_post_diagnostic_predictions_byte_identical=identical,
        provenance_metadata_correction='CPU backend/window explicitly unverified; no values, times, parameters or predictions changed',
        parameter_attempts=1,theta_fits=0,device_access=False)
    write(output,summary)
    print(summary)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--check-originals',action='store_true')
    a=ap.parse_args()
    verify(a.result.resolve(),a.output.resolve(),a.check_originals)
