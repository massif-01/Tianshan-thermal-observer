"""Replay one synthetic measurement conflict through installed, unmodified TTO.
Only creates NEW local test records; no device/network/subprocess access.
Usage: python scripts/check_shadow_quality.py --output NEW_DIRECTORY
Requires the supplied candidate wheel, not an edited source checkout.
"""
import argparse, copy, json
from pathlib import Path
from datetime import datetime,timedelta
from tto.storage import Journal
from tto.engine import Engine
from tto.dataset import replay
from tto.model import load_model
from tto.report import run_report
from tto.util import read_json,file_hash

def verify(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    fixture=Path(__file__).resolve().parent.parent/'fixtures'
    config=read_json(fixture/'config.json'); model=load_model(fixture/'synthetic-model.json')
    source=[json.loads(l) for l in (fixture/'synthetic-observations.jsonl').read_text().splitlines()]
    results={}
    for mode in ('normal','conflict','conflict_then_recovery'):
        conflict=mode!='normal';limit=620 if mode=='conflict_then_recovery' else 350
        j=Journal(config,output/mode,simulated=True,episode='review-synthetic-shadow',run_type='shadow',model_sha256=model['sha256'])
        e=Engine(config,model);last=None;collision=None; label_ref=None
        def process(row):
            r=j.observation(row);out=e.process(r)
            if out['quality']:j.append('events',dict(ref=r['ref'],**out['quality']))
            if out['prediction']:j.append('predictions',out['prediction'])
            for s in out['scores']:j.append('scores',s)
            return r,out
        for r in source:
            if r['mono_s']>limit:break
            saved,out=process(r)
            if r['kind']=='orin' and r['mono_s']==350:
                last=saved; label_ref=saved['ref']
                if conflict:
                    bad=copy.deepcopy(saved);bad['mono_s']+=.2
                    bad['received_at_utc']=(datetime.fromisoformat(bad['received_at_utc'])+timedelta(seconds=.2)).isoformat()
                    bad['payload']['telemetry_meta']['sample_age_ms']=200
                    bad['payload']['temperature']['tj']+=10
                    _,out=process(bad);collision=out['quality']
        for s in e.invalidate('run_end'):j.append('scores',s)
        j.close({'stop_reason':'synthetic_run_end','elapsed_s':limit+.2})
        names=['observations-0001.jsonl','predictions.jsonl','scores.jsonl','events.jsonl']
        before={n:file_hash(j.path/n) for n in names}
        rp=replay(j.path);report=run_report(j.path,output/(mode+'-report')); rec=report['recorded_results']
        invalid={r['segment'] for r in rp['rows'] if r.get('invalid_segment_reason')}
        affected=[p for p in rec['scored_records'] if p['segment'] in invalid]
        suspect_label=[p for p in rec['scored_records'] if p['label_ref']==label_ref]
        clean=[p for p in rec['scored_records'] if p['segment'] not in invalid]
        results[mode]={
            'run_relative':str(j.path.relative_to(output)),'simulated':True,'quality_result':collision,
            'normal_auto_origins_after_quality':report['normal_auto_origins'],'replay_eligible_label_counts':report['label_counts'],
            'invalidated_segments':sorted(invalid),'reported_scored_method_horizon_records':rec['scored_method_horizon_records'],
            'reported_records_from_invalid_segments':len(affected),'reported_records_using_sample_at_350s':len(suspect_label),
            'model_records_using_sample_at_350s':[p for p in suspect_label if p['method']=='ridge_full'],
            'reported_records_from_other_segments':len(clean),
            'log_evidence_complete':rec['log_evidence_complete'],'report_conclusion':report['conclusion'],
            'logs_unchanged_by_report':before=={n:file_hash(j.path/n) for n in names},
        }
    # These assertions describe the defect in candidate 0.1.1, not a repair pass.
    assert results['normal']['reported_records_from_invalid_segments']==0
    assert results['conflict']['quality_result']['reason']=='identity_conflict'
    assert results['conflict']['replay_eligible_label_counts']=={'15':0,'45':0,'90':0}
    assert results['conflict']['reported_records_from_invalid_segments']==510
    assert results['conflict']['reported_records_using_sample_at_350s']==12
    assert results['conflict_then_recovery']['reported_records_from_other_segments']>0
    (output/'findings.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);verify(p.parse_args().output)
