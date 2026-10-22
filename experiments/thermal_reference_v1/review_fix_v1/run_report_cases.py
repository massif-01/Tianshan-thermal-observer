"""Export four source-category reports. Every input is constructed test material."""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import json
import sys

ROOT=Path(__file__).absolute().parent.parent
sys.path.insert(0,str(ROOT))
from refprep.files import read,write,sha
spec=importlib.util.spec_from_file_location('report_source_cases',ROOT/'tests/test_report_sources.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
if args.output.exists():raise ValueError("Use a fresh output directory")
result=[]
for name,flags,expected in module.CASES:
    dest=args.output/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    with (dest.parent/(name+'-cli.log')).open('w') as log,contextlib.redirect_stdout(log):
        output=module.generate_case(dest,flags)
    summary=read(output/'comparison.json')
    assert summary['report_text']['source_status']==expected
    result.append(dict(name=name,classification=expected,total=summary['numeric_points'],
        declared_external=summary['real_numeric_points'],synthetic=summary['synthetic_numeric_points'],
        all_values_constructed_test_only=True,new_field_measurement=False,
        report_text=summary['report_text'],report_directory=str(output),
        YET_format_validated=summary['real_YET_CSV_mapping_accepted'],physical_mapping_validated=summary['physical_mapping_validated']))
write(args.output/'source-cases-receipt.json',dict(status='pass',cases=result,
    note='false metadata exercises the declared-external branch only; no real new CSV or field measurement'))
print(json.dumps(dict(status='pass',cases=len(result),all_inputs_test_only=True),ensure_ascii=False))
