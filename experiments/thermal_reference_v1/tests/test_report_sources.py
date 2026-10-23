"""P3 report regression. All inputs are constructed tests, including synthetic=False cases."""
from pathlib import Path
import html
import sys
import pytest

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT))
from ref import main as cli
from refprep.files import read,write,sha

CASES=[('zero',[],'no_numeric_records'),
       ('synthetic',[True,True],'synthetic_only'),
       ('declared-external',[False,False],'declared_external_only'),
       ('mixed',[True,False],'mixed_declared_external_and_synthetic')]


def generate_case(directory,flags):
    directory=Path(directory);directory.mkdir(parents=True)
    store=directory/'sidecar';output=directory/'report'
    session=read(ROOT/'fixtures/synthetic/fin-session.json')
    session['session_id']='TEST-ONLY-NOT-A-REAL-MEASUREMENT'
    session['reference_record_id']=None
    session_file=directory/'session.json';write(session_file,session)
    assert cli(['init-session','--store',str(store),'--session',str(session_file)])==0
    times=read(ROOT/'fixtures/synthetic/point-times.json')
    rows=[dict(id='test-'+str(i),value=41+i,unit='C',sample_time=times['background'],synthetic=flag,
               note='TEST-ONLY-NOT-A-REAL-MEASUREMENT: constructed data; false flag exercises declared category only')
          for i,flag in enumerate(flags)]
    path=directory/'TEST-ONLY-NOT-A-REAL-MEASUREMENT.json';write(path,rows)
    mapping=dict(input_path='numeric_export',columns=dict(record_id='id',original_value='value',original_unit='unit',
                 measured_at_raw='sample_time',synthetic='synthetic',note='note'),
                 constants=dict(session_id=session['session_id'],time_source='TEST-CONSTRUCTED',time_uncertainty_s=0))
    mapping_path=directory/'mapping.json';write(mapping_path,mapping)
    assert cli(['import','--store',str(store),'--file',str(path),'--mapping',str(mapping_path)])==0
    trajectory=ROOT/'fixtures/real/M-frozen.jsonl';before=sha(trajectory)
    assert cli(['compare','--store',str(store),'--trajectory',str(trajectory),'--output',str(output),'--no-plots'])==0
    assert sha(trajectory)==before
    return output


@pytest.mark.parametrize('name,flags,expected',CASES,ids=[r[0] for r in CASES])
def test_P3_result_owned_source_text_agrees_in_JSON_MD_HTML(tmp_path,name,flags,expected):
    output=generate_case(tmp_path/name,flags)
    summary=read(output/'comparison.json');wording=summary['report_text']
    md=(output/'中文对照报告.md').read_text()
    rendered=html.unescape((output/'中文对照报告.html').read_text())
    assert wording['source_status']==expected
    assert summary['numeric_points']==len(flags)
    assert summary['real_numeric_points']==flags.count(False)
    assert summary['synthetic_numeric_points']==flags.count(True)
    for key in ['measurement_status','counts','format_status','validation_status']:
        assert wording[key] in md and wording[key] in rendered
    assert '现场测温未执行' not in md and '现场测温未执行' not in rendered
    assert not summary['real_YET_CSV_mapping_accepted'] and not summary['physical_mapping_validated']
    assert not summary['instrument_profile_confirmed'] and not summary['model_refit']
    if False in flags:
        assert summary['surface_measurement_performed'] is True
        assert '按输入声明分类' in wording['measurement_status']
    if True in flags:assert '合成' in wording['measurement_status']
