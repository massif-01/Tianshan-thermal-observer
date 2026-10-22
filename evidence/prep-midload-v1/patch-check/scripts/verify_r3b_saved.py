#!/usr/bin/env python3
"""Apply repaired formal reports to the SAME preserved before-repair runs.
The --runs-root is output of the original independent review reproduction.
No writes inside runs, no network or model loading. New output only.
"""
import argparse
import json
from pathlib import Path
from tto.cli import main
from tto.util import read_json
from verify_r3b import log_hashes


def verify(root, output):
    root=Path(root).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    findings={}
    for mode,facts in read_json(root/'findings.json').items():
        run=root/facts['run_relative'];before=log_hashes(run)
        assert main(['report','--run',str(run),'--output',str(output/(mode+'-report'))])==0
        rec=read_json(output/(mode+'-report/report.json'))['recorded_results']
        assert rec['historical_scored_method_horizon_records']==facts['reported_scored_method_horizon_records']
        assert rec['quality_excluded_method_horizon_records']==facts['reported_records_from_invalid_segments']
        assert rec['scored_method_horizon_records']==facts['reported_records_from_other_segments']
        assert rec['log_evidence_complete']
        assert before==log_hashes(run)
        old=read_json(root/(mode+'-report/report.json'))['recorded_results']
        for key,group in rec['models'].items():
            assert group['model_sha256']==old['models'][key]['model_sha256']
            for h,counts in group['horizons'].items():
                for method,mc in counts['methods'].items():
                    original=old['models'][key]['horizons'][h]['methods'][method]
                    assert mc['issued']==original['issued']
                    assert mc['coverage_denominator']==old['models'][key]['horizons'][h]['issued_origins']
                    if mode=='normal':
                        assert mc['metrics']==original['metrics']
                        assert mc['coverage_fraction']==original['coverage_fraction']
        findings[mode]={'run_id':next(iter(rec['prediction_references'])).split(':')[0], 'historical_scored':rec['historical_scored_method_horizon_records'],'currently_eligible':rec['scored_method_horizon_records'],'quality_excluded':rec['quality_excluded_method_horizon_records'],'sha256_before':before,'sha256_after':log_hashes(run),'original_logs_byte_unchanged':True,'normal_identity_metrics_coverage_unchanged':mode=='normal'}
    (output/'findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':True,'findings':findings},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs-root',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();verify(a.runs_root,a.output)
