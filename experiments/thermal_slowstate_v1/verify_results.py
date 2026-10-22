"""Independent file/cohort/metric readback; local only, no model selection."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import numpy as np
from prepare import read, jsonlines, write, digest

ROOT=Path(__file__).absolute().parent
BRANCHES=['STATE-G2','STATE-QS','STATE-LP30','STATE-LP120']


def verify(root=ROOT):
    root=Path(root);checks={}
    inv=read(root/'source-inventory.json')
    for item in inv:
        if item['kind']=='member':
            assert digest((root/item['copied_to']).read_bytes())==item['sha256']
    checks['immutable_source_member_hashes']=sum(i['kind']=='member' for i in inv)
    for item in read(root/'historical-provenance-index.json'):
        assert digest((root/item['copied_to']).read_bytes())==item['sha256']
    checks['historical_private_vs_shared_identity_preserved']=True
    freeze=read(root/'stage1-freeze.json')
    assert digest((root/'slowstate-spec.json').read_bytes())==freeze['spec_sha256']
    assert read(root/'stage3-complete.json')['spec_sha256']==freeze['spec_sha256']
    for name,sha in read(root/'stage3-complete.json')['results'].items():
        assert digest((root/'results'/name).read_bytes())==sha,name
    checks['stages_match_frozen_spec']=True
    points=jsonlines(root/'results/four-branch-predictions.jsonl')
    rows=read(root/'results/temperature-metrics.json')
    count=0
    for cell in rows:
        if cell['scale']!='run':continue
        selected=[]
        for point in points:
            if point['run']!=cell['group'] or point['h']!=cell['h'] or point['label'] is None or not point[cell['kind']]:continue
            st=cell['stratum']
            if st=='legacy_strict' and not point['strict_label']:continue
            if st not in ['legacy_strict','all_contexts'] and st!=point['control_context']:continue
            selected.append(point)
        assert len(selected)==cell['n']
        cohort='\n'.join(f"{p['ref']}|{p['h']}|{p['label']['ref']}" for p in selected)
        assert hashlib.sha256(cohort.encode()).hexdigest()==cell['cohort_sha256']
        for branch in BRANCHES:
            e=np.array([p[cell['kind']][branch]-p['label']['value'] for p in selected])
            actual=cell['metrics'][branch]
            independent=dict(MAE=float(np.mean(abs(e))),bias=float(np.mean(e)),
                P95_abs=float(np.quantile(abs(e),.95)),max_under=max(0,float(-min(e))),max_over=max(0,float(max(e))))
            for key,value in independent.items():assert abs(value-actual[key])<1e-11,(cell['group'],key)
            count+=1
    checks['independent_per_run_metric_cells']=count
    orig=read(root/'sources/registered/data.json')
    accepted={r['ref']:r for r in orig['accepted']}
    states=jsonlines(root/'results/states-causal60.jsonl')
    for s in states:
        assert s['Tf']==accepted[s['ref']]['values']['tj']
        assert s['Tf_is_observation_anchor'] and not s['state_truth_available']
        assert s['evidence']['end']<=s['t']+1e-9 and s['input_cutoff']<=s['t']+1e-9
    for c in read(root/'results/replay-checks.json'):
        assert c['match'] and c['max_abs_Tf_replay_error_C']<=1e-10
    checks['all_causal_states_prefix_only']=len(states)
    # The observed fast channel remains independent of whether slow demand is available.
    ledger=jsonlines(root/'results/fast-status-and-demand-ledger.jsonl')
    abnormal=[l for l in ledger if l['fast_status']['observed_abnormal_or_changed']]
    assert abnormal and all(l['normal_extra_demand_index'] is None for l in abnormal)
    assert any(l['measured_TJ_valid'] and l['normal_extra_demand_index'] is None for l in ledger)
    checks['abnormal_nodes_null_immediately']=len(abnormal)
    checks['whole_run_availability_seconds']={r:sum(l['duration_s'] for l in ledger if l['run']==r and l['ordinary_available']) for r in ['L','S','M']}
    figs=read(root/'figures/figure-index.json')
    assert len(figs)==4 and all(len(f['caption'])==3 for f in figs)
    for f in figs:
        assert (root/'figures'/f['png']).stat().st_size>10000
        assert (root/'figures'/f['svg']).stat().st_size>10000
    checks['four_chinese_figure_classes']=True
    # A portable extracted package need not contain the original repo. In the actual worktree it must match.
    repo=root.parents[1] if len(root.parents)>1 else root
    protected=read(root/'protected-before.json')
    if (repo/'src/tto').exists() and (repo/'experiments/thermal_identification_r2').exists():
        changed=[n for n,sha in protected.items() if not (repo/n).exists() or digest((repo/n).read_bytes())!=sha]
        assert not changed,changed
        checks['protected_original_files_unchanged']=len(protected)
    else:
        checks['protected_original_files_unchanged']='original checkout absent; immutable copied source hashes checked'
    write(root/'readback-checks.json',dict(status='pass',checks=checks,deployable=False,
          scope='offline research only; no device/control/sound/safety acceptance'))
    print(json.dumps(dict(status='pass',checks=checks),ensure_ascii=False))


if __name__=='__main__':verify()
