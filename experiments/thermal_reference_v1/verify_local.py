"""Read back delivered sidecars and immutable inputs; never contacts GitHub or devices."""
from pathlib import Path
import argparse
import json
from refprep.files import read,write,lines,sha
from refprep.records import latest_records

ROOT=Path(__file__).absolute().parent


def verify(run_output,check_originals=True):
    run_output=Path(run_output);checks={}
    original=read(ROOT/'handoff/SHA256.json')['files']
    for path,entry in original.items():assert sha(ROOT/'handoff'/path)==entry['sha256'],path
    checks['handoff_members_unchanged']=len(original)
    index=read(ROOT/'source-index.json')
    for group in ['local_real_fixture_files','synthetic_fixture_files']:
        for path,digest in index[group].items():assert sha(ROOT/path)==digest,path
    for name,digest in read(ROOT/'stage1-freeze.json')['model_sha256'].items():
        assert sha(ROOT/'frozen/models'/name)==digest
        assert sha(ROOT/'handoff/references/slowstate-snapshot/sources/models'/name)==digest
    assert sha(ROOT/'prep-spec.json')==read(ROOT/'stage1-freeze.json')['spec_sha256']
    checks['three_frozen_models_and_spec']='exact SHA match'
    zero=read(run_output/'zero-report/comparison.json');demo=read(run_output/'synthetic-report/comparison.json')
    assert zero['status']=='not_measured' and zero['numeric_points']==0
    assert demo['status']=='synthetic_demo_only' and demo['real_numeric_points']==0
    assert demo['paired_points']==5 and demo['numeric_points']==5
    assert all(not r['physical_mapping_validated'] for r in [zero,demo])
    checks['zero_and_synthetic_reports_correct']=True
    history=lines(run_output/'reference-sidecar/records.jsonl');latest=latest_records(run_output/'reference-sidecar')
    assert len(history)==7 and len(latest)==6
    bg=[r for r in history if r['record_id']=='fin-bg']
    assert bg[0]['measured_at_raw'] is None and bg[1]['operator_mark_at_utc']==bg[0]['operator_mark_at_utc']
    assert bg[1]['supersedes']==bg[0]['revision_id'] and bg[1]['measured_at_raw']!=bg[1]['recorded_at_utc']
    for r in history:
        if r['artifact']:assert sha(run_output/'reference-sidecar'/r['artifact']['stored_relative_path'])==r['artifact']['sha256']
    checks['append_only_late_entry_and_original_artifact_SHA']=True
    cues=lines(run_output/'synthetic-cues/reminders.jsonl')
    prompts=[r for r in cues if r['status']=='prompt']
    assert len(prompts)==14 and all(r['replay'] and r['prompt_emitted_at_utc'] is None for r in prompts)
    checks['fixed_virtual_prompts']=len(prompts)
    paired=lines(run_output/'synthetic-report/paired-points.jsonl')
    for r in paired:
        assert r['record']['synthetic'] and not r['record']['model_input'] and not r['record']['control_input']
        if r['delta']:
            expected='fin-bg' if r['record']['session_id']=='SYNTH-fin' else 'back-bg'
            assert r['delta']['reference_record_id']==expected
    checks['one_reference_per_site_session_no_model_feedback']=True
    for name in ['zero-report','synthetic-report']:
        for suffix in ['comparison.json','paired-points.jsonl','中文对照报告.html','中文对照报告.md']:
            assert (run_output/name/suffix).is_file()
    checks['reports_read_back']=True
    for path,digest in read(ROOT/'contact-source-index.json')['files'].items():assert sha(ROOT/path)==digest,path
    assert sha(ROOT/'prep-add1-spec.json')==read(ROOT/'stage-add1-freeze.json')['spec_sha256']
    contact=read(run_output/'contact-report/comparison.json')
    assert contact['status']=='synthetic_demo_only' and not contact['real_YET_CSV_mapping_accepted']
    imports=lines(run_output/'contact-sidecar/imports.jsonl');receipt=imports[0]
    assert len(imports)==1 and receipt['rows']==240 and receipt['rejected_rows']==1 and receipt['added']==239
    assert sha(run_output/'contact-sidecar'/receipt['raw_stored_relative_path'])==receipt['input_sha256']
    assert contact['real_numeric_points']==0 and contact['synthetic_numeric_points']==238
    assert contact['unpaired_reasons']['probe_integrity_event_requires_new_session']>0
    assert all(c['positive_interval_median_s']==1 and c['positive_interval_max_s']==2 for c in receipt['cadence'].values())
    checks['ADD1_continuous_CSV_raw_SHA_rows_channels_missing_values_and_probe_events']=True
    if check_originals and ROOT.parent.name=='experiments':
        repo=ROOT.parents[1]
        protected=read(ROOT/'protected-before.json')
        bad=[path for path,digest in protected.items() if not (repo/path).is_file() or sha(repo/path)!=digest]
        assert not bad,bad[:20]
        checks['protected_worktree_file_SHA_unchanged']=len(protected)
    else:checks['protected_worktree_file_SHA_unchanged']='portable archive: original checkout not required'
    write(run_output/'readback.json',dict(status='pass',checks=checks,physical_mapping_validated=False,
        actual_measurement_performed=False,model_refit=False,device_actions=False))
    print(json.dumps(dict(status='pass',checks=checks),ensure_ascii=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run-output',type=Path,required=True)
    ap.add_argument('--skip-original-checkout',action='store_true')
    args=ap.parse_args();verify(args.run_output,not args.skip_original_checkout)
