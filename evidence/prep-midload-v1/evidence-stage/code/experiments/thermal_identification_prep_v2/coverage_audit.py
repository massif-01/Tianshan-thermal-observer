"""Read frozen predictions; write a new availability audit, never fit or emit missing values."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import zipfile
from datetime import datetime
from eligibility import replay_evidence,assess_saved_prediction,VERSION
from event_metrics import event_metrics


def read(path):return json.loads(Path(path).read_text())
def write(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def jsonl(path):return [json.loads(line) for line in Path(path).open()]
def cohort(rows):return hashlib.sha256('\n'.join(f"{r['ref']}|{r['h']}|{r['v2']['label']['ref']}" for r in rows).encode()).hexdigest()


def compare(rows,methods):
    common=[r for r in rows if r['v2']['target_valid'] and all(m in r['B'] and r['v2']['origin_inputs_valid'][m] for m in methods)]
    return dict(n=len(common),cohort_id=cohort(common),metrics={m:dict(n=len(common),point_MAE_C=statistics.mean(abs(r['B'][m]-r['v2']['label']['value']) for r in common) if common else None,
                         bias_C=statistics.mean(r['B'][m]-r['v2']['label']['value'] for r in common) if common else None) for m in methods})


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--handoff',type=Path,required=True);ap.add_argument('--frozen',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);cache=a.output/'input-cache';cache.mkdir()
    manifest=read(a.handoff/'inputs/input-index.json')
    for entry in manifest['archives'][:2]:
        source=a.handoff/entry['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['sha256']
        with zipfile.ZipFile(source) as z:assert z.testzip() is None;z.extractall(cache/source.stem)
    evidence={label:replay_evidence(next((cache/name).glob('run-*'))) for label,name in [('L','L-seven-conditions-original'),('S','S-shortqa-original-complete')]}
    original=read(a.frozen/'runs/main/data.json');old_counts={r['run']:sum(d['reason']=='TTL_expires_inside_interval' for gap in r['interval_rejections'] for d in gap['details']) for r in original['runs']}
    assert old_counts=={'L':12,'S':27}
    sources={s['ref']:s for e in evidence.values() for s in e['samples']}
    for s in original['accepted']:
        assert s['values']==sources[s['ref']]['values'] and s['mono_s']==sources[s['ref']]['t']
    sreqs=read(cache/'S-shortqa-original-complete/normalized-requests.json');phases=read(cache/'S-shortqa-original-complete/normalized-phases.json');continuous=next(p for p in phases if p['phase']=='continuous')
    lower=datetime.fromisoformat(continuous['start_utc']).timestamp();upper=datetime.fromisoformat(continuous['end_utc']).timestamp()
    all_results=[];waterfall=[];sets=[]
    methods=['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']
    for eid,targets in [('F-LS',['S']),('F-SL',['L']),('F-POOL',['L','S'])]:
        predictions=jsonl(a.frozen/'runs/main/evaluation'/eid/'predictions.jsonl');new=[]
        for r in predictions:
            r['v2']=assess_saved_prediction(evidence[r['run']],r);assert r['B']==r['v2']['B_values'];new.append(r)
        for scope in ['all','continuous_short']:
            rows=[r for r in new if scope=='all' or r['regime']=='continuous_short' and r['run']=='S']
            for h in (15,45,90):
                group=[r for r in rows if r['h']==h]
                for method in methods:
                    emitted=[r for r in group if method in r['B']];valid_origins=[r for r in emitted if r['v2']['origin_inputs_valid'][method]];answers=[r for r in valid_origins if r['v2']['target_valid']]
                    raw=sum((scope=='all' or s['run']=='S' and s['regime']=='continuous_short') for s in original['accepted'] if s['run'] in targets)
                    waterfall.append(dict(experiment=eid,scope=scope,h=h,method=method,raw_TJ=raw,original_method_origins=len(emitted),method_origins_v2=len(valid_origins),saved_predictions=len(emitted),
                           old_strict_answers=sum(r['label'] is not None for r in emitted),new_trusted_TJ_answers=len(answers),
                           subsets={k:sum(r['v2']['control_context']==k for r in answers) for k in ['confirmed_normal','aux_observation_gap','observed_abnormal_or_changed','unclassified_gap']},
                           no_trusted_answer=len(emitted)-len(answers),A_inputs_complete=sum(r['v2']['A_eligible'] for r in emitted)))
                for context in ['all_emitted_with_valid_truth','confirmed_normal','aux_observation_gap','observed_abnormal_or_changed']:
                    c=[r for r in group if context=='all_emitted_with_valid_truth' or r['v2']['control_context']==context]
                    for layer,ms in [('B0_B1',methods[:2]),('plus_TJ',methods[:3]),('plus_IO',methods[:4]),('all_methods',methods)]:
                        sets.append(dict(experiment=eid,scope=scope,h=h,subset=context,layer=layer,comparison=compare(c,ms)))
        with (a.output/f'{eid}-availability-v2.jsonl').open('x') as f:
            for r in new:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
        all_results+=new
    check=next(r for r in waterfall if r['experiment']=='F-LS' and r['scope']=='continuous_short' and r['h']==45 and r['method']=='B0')
    assert check['raw_TJ']==169 and check['original_method_origins']==166 and check['old_strict_answers']==6
    write(a.output/'waterfall.json',waterfall);write(a.output/'comparisons.json',sets)
    model_rows=jsonl(a.frozen/'runs/main/evaluation/F-POOL/A-long.jsonl');events=[]
    first=evidence['S']['samples'][0];offset=first['t']-datetime.fromisoformat(first['utc']).timestamp()
    for q in sreqs:
        start=datetime.fromisoformat(q['submit_utc']).timestamp()+offset;end=datetime.fromisoformat(q['end_utc']).timestamp()+offset
        event=dict(id=q['request_id'],stage=q['stage'],start=start,end=end,client_submit_mono_s=q['submit_mono_s'],client_end_mono_s=q['end_mono_s'],
                   overlaps_previous=any(datetime.fromisoformat(other['end_utc']).timestamp()+offset+90>start for other in sreqs if other['submit_mono_s']<q['submit_mono_s']))
        events.append(event_metrics(evidence['S']['samples'],evidence['S']['nodes'],event,[r for r in model_rows if r['run']=='S']))
    write(a.output/'event-metrics.json',events)
    write(a.output/'identity.json',dict(rule_version=VERSION,models_refitted=False,missing_predictions_emitted=False,
          old_TTL_counts=old_counts,old_continuous_45_B0=check['old_strict_answers'],frozen_source_sha256=hashlib.sha256((a.frozen/'runs/main/data.json').read_bytes()).hexdigest(),
          models_and_predictions='original bytes unchanged; all new scores use exactly the saved prediction values',live_validation='not_performed'))
    lines=['# A/B评价资格覆盖核对','',f'规则 `{VERSION}`。旧分数保留，新增覆盖不是预测改善；无重新拟合或补发。','',
           '|实验|范围|秒|方法|原始TJ|已存预测|旧答案|新可信答案|正常|辅助缺口|明确异常|无答案|',
           '|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in waterfall:
        if r['scope']=='continuous_short' and r['h']==45:
            sub=r['subsets'];lines.append('|'+ '|'.join(str(v) for v in [r['experiment'],r['scope'],r['h'],r['method'],r['raw_TJ'],r['saved_predictions'],r['old_strict_answers'],r['new_trusted_TJ_answers'],sub['confirmed_normal'],sub['aux_observation_gap'],sub['observed_abnormal_or_changed'],r['no_trusted_answer']])+'|')
    (a.output/'coverage.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(check,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
