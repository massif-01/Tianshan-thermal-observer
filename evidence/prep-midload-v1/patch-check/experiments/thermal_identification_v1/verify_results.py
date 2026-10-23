"""Read-back verification of saved artifacts; no refitting or device access."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from common import read,write,sha,stamp
from evaluation import load_jsonl,cohort_id
from greybox import matrices


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=a.run
    assert not a.output.exists()
    freeze=read(root/'freeze.json');assert all(sha(root/k)==v for k,v in freeze['files'].items())
    direction=read(root/'directions-frozen.json');assert all(sha(root/k)==v for k,v in direction['files'].items())
    data=read(root/'data.json');observations={r['ref']:r for r in data['accepted']};checks=[];independent45=0
    for eid in ('F-LS','F-SL','F-POOL'):
        pred=load_jsonl(root/'evaluation'/eid/'predictions.jsonl');states=load_jsonl(root/'evaluation'/eid/'states.jsonl')
        smap={(r['ref'],r['model']):r for r in states if r['window']==60}
        index={(r['ref'],r['h']):r for r in pred}
        assert read(root/'evaluation'/eid/'evaluation-identity.json')['evaluated_at']>direction['frozen_at']
        max_error=0.;counts=0
        for r in pred:
            original=observations[r['ref']]
            assert original['mono_s']==r['t'] and r['input_available_cutoff']==r['t']
            if r['label']:
                label=observations[r['label']['ref']]
                assert label['research_segment']==original['research_segment']
                assert label['values']['tj']==r['label']['value']
                assert 0<=label['mono_s']-(r['t']+r['h'])<=2
            if r['h']==45 and r['label'] and index[(r['ref'],90)]['label'] is None:independent45+=1
        for m in ('G1','G2'):
            artifact=read(root/'fits'/f'{eid}-{m}/model.json');p=np.array(list(artifact['dynamic'].values()))
            # Every 17th scored origin across all horizons: independent augmented-expm HOLD.
            candidates=[r for r in pred if r['label'] and f'{m}-HOLD' in r['B']]
            for r in candidates[::17]:
                state=smap[(r['ref'],m)];ev=state['evidence']
                assert ev['end']<=r['t'] and observations[ev['last_ref']]['mono_s']<=r['t']
                assert ev['start']>=r['t']-60-1e-8
                original=observations[r['ref']];u=[original['values']['vdd_gpu'],original['values']['vdd_cpu_soc_mss'],original['values']['duty']/100]
                A,f=matrices(m,p,state['E'],u);n=len(A);M=np.zeros((n+1,n+1));M[:n,:n]=A;M[:n,-1]=f
                got=(expm(M*r['h'])@np.r_[state['state'][:n],1])[0];delta=abs(got-r['B'][f'{m}-HOLD'])
                assert delta<1e-8;max_error=max(max_error,delta);counts+=1
            trials=[read(root/'fits'/f'{eid}-{m}/N{k}.json') for k in range(1,7)]
            selected=min((t for t in trials if t['converged'] and t['finite']),key=lambda t:t['J'])
            assert selected['seed']==artifact['selected_seed'] and all(t['actual_residual_calls']<=1500 for t in trials)
        for r in read(root/'evaluation'/eid/'B-metrics.json'):
            methods=list(r['metrics']);group=[p for p in pred if p['h']==r['h'] and p['label'] and all(m in p['B'] for m in methods)]
            if r['scope']!='all':group=[p for p in group if p[r['scope']]==r['value']]
            assert cohort_id(group)==r['cohort_id']
            for m,v in r['metrics'].items():
                assert len(group)==v['n'];w=np.array([p['duration'] for p in group]);w=w/w.sum()
                mae=float(w@np.array([abs(p['B'][m]-p['label']['value']) for p in group]));assert abs(mae-v['mae'])<1e-10
        checks.append(dict(experiment=eid,forecast_rows=len(pred),independent_expm_cases=counts,max_abs_expm_difference=max_error,all_cohorts_recomputed=True))
    assert independent45>0
    write(a.output,dict(checked_at=stamp(),freeze_verified=True,direction_models_unchanged=True,checks=checks,
                       retained_45_labels_without_90_across_experiment_views=independent45,main_attempts=36,nested_attempts=1,
                       control_authorization='none',target_validation='not_performed'))
    print('saved results verified:',checks,'45 without 90:',independent45)


if __name__=='__main__':main()
