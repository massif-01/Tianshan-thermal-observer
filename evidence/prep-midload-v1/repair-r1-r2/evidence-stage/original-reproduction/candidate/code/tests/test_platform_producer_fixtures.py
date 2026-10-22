"""Frozen producer output consumed by TTO's actual Quality/Journal/report path."""
import hashlib
import json
from pathlib import Path
import pytest
from tto.cli import main
from tto.demo import fan_packet,temp_packet
from tto.engine import engine_for
from tto.platform_quality import PlatformQuality
from tto.storage import Journal
from tto.util import file_hash,read_json
from conftest import record

FIXTURES=Path(__file__).parent/'fixtures/platform-v2/producer'
MANIFEST_SHA256='59798e9e93fdc6b9968ef6f2e88847fdd238514c52ed43eb50f06d02432aacf2'


def frozen_fixtures():
    manifest_path=FIXTURES/'manifest.json'
    assert file_hash(manifest_path)==MANIFEST_SHA256
    manifest=read_json(manifest_path)
    assert manifest['contract']=='TTO-PLATFORM-CURVE-v2.0'
    assert manifest['producer_version']=='1.1.1' and manifest['live_device_test'] is False
    for name,digest in manifest['files'].items():
        assert file_hash(FIXTURES/name)==digest,name
    return manifest


def test_frozen_producer_cases_reach_tto_quality(config):
    manifest=frozen_fixtures()
    config['orin']['source_sample_interval_ms']=None
    checks={'orin-zero':('jetson_orin',0,None),
            'orin-nonzero':('jetson_orin','positive',None),
            'orin-missing':('jetson_orin',None,'gpu_source_unavailable'),
            'thor-zero':('jetson_thor',0,None),
            'thor-nonzero':('jetson_thor','positive',None),
            'thor-error':('jetson_thor',None,'gpu_source_error'),
            'thor-error-with-legacy-zero':('jetson_thor',None,'gpu_source_error'),
            'thor-stale':('jetson_thor',None,'gpu_source_stale'),
            'thor-unavailable':('jetson_thor',None,'gpu_source_unavailable'),
            'unknown':(None,None,'gpu_source_unavailable')}
    for name,(family,value,reason) in checks.items():
        p=read_json(FIXTURES/(name+'.json'))
        assert p['telemetry_meta']['source_sample_interval_ms']==3000
        e=engine_for(config,record_schema=2)
        fan=fan_packet(0);fan['data']['fans'][0]['mode']='curve';fan['data']['fans'][0].pop('controller_gain')
        for kind,payload in (('fan',fan),('temp',temp_packet())):
            e.process({'kind':kind,'mono_s':1.,'payload':payload,'ref':'fixture/'+name+'/'+kind})
        r=record(p['telemetry_meta']['sample_seq'],t=3,stream=p['telemetry_meta']['stream_id'])
        r.update(observer_run_id='fixture-run',episode='fixture',ref='fixture/'+name)
        r['payload']=p
        out=e.process(r)
        assert p['telemetry_meta']['schema_version']==1
        q=out['quality']
        assert q['accepted'] and q['values']['tj']==p['temperature']['tj'],name
        assert q['platform_reason'] == ('platform_unconfirmed' if family is None else None),name
        if value=='positive':assert q['gpu']['value']>0,name
        else:assert q['gpu']['value']==value,name
        assert q['gpu']['reason']==reason,name
        if family=='jetson_thor':
            assert q['values']['temp_soc012']==p['temperature']['soc012'],name
            assert q['values']['temp_soc345']==p['temperature']['soc345'],name
            assert q['values']['vdd_gpu']==p['power']['vdd_gpu']['current']/1000,name
            assert q['values']['vdd_cpu_soc_mss']==p['power']['vdd_cpu_soc_mss']['current']/1000,name
    from tto.quality import numbers
    for name, expected_value, expected_reason in (('legacy-zero.json',0,None),('legacy-empty-gpu.json',None,'legacy_gpu_missing_or_invalid')):
        p=read_json(FIXTURES/name)
        assert numbers(p)['gpu_busy']==expected_value
    # Same cached seq and an identical-valued new seq have distinct contracts.
    q=PlatformQuality(config)
    first=read_json(FIXTURES/'thor-zero.json')
    r=dict(observer_run_id='fixture-run',episode='fixture',ref='fixture/1',kind='orin',mono_s=1.,received_at_utc='2026-01-01T00:00:01Z',connection_epoch=1,payload=first)
    assert q.accept(r)['accepted']
    duplicate=dict(r,ref='fixture/2',mono_s=2.,payload=read_json(FIXTURES/'thor-repeat.json'))
    assert q.accept(duplicate)['reason']=='duplicate'
    fresh=dict(r,ref='fixture/3',mono_s=3.,payload=read_json(FIXTURES/'thor-same-value-new-input.json'))
    assert q.accept(fresh)['accepted']


def test_frozen_producer_report_uses_formal_journal(tmp_path,config):
    config['orin']['source_sample_interval_ms']=None
    frozen_fixtures()
    p=read_json(FIXTURES/'thor-error.json')
    j=Journal(config,tmp_path/'journal',simulated=True,episode='producer-contract-fixture',run_type='collect',record_schema=2)
    e=engine_for(config,record_schema=2)
    for kind,payload in (('fan',fan_packet(0)),('temp',temp_packet())):
        row=j.observation({'kind':kind,'mono_s':1.,'received_at_utc':'2026-01-01T00:00:01Z','payload':payload})
        j.processing_output(row,e.process(row))
    row=j.observation({'kind':'orin','mono_s':2.,'received_at_utc':'2026-01-01T00:00:02Z','payload':p})
    j.processing_output(row,e.process(row))
    j.close({'elapsed_s':2.,'synthetic_fixture':'monitor service 1.1.1 Thor error'})
    before={f.name:file_hash(f) for f in j.path.iterdir() if f.is_file()}
    out=tmp_path/'report'
    assert main(['report','--run',str(j.path),'--output',str(out)])==0
    report=read_json(out/'report.json')
    assert report['simulated'] is True
    assert report['input_diagnostics']['platform_declaration']['platform']['family']=='jetson_thor'
    assert report['input_diagnostics']['source_period_evidence']['period_ms']==3000
    assert report['input_diagnostics']['gpu_unavailable_reasons']['gpu_source_error']>0
    assert report['input_diagnostics']['counts']['eligible_origins']>0
    assert '模拟' in report['conclusion']
    assert before=={f.name:file_hash(f) for f in j.path.iterdir() if f.is_file()}


@pytest.mark.parametrize('name,expected',[
    ('identity-conflict-platform.json','identity_conflict'),
    ('lifecycle-conflict-source-period.json','lifecycle_contract_change')])
def test_consumer_negative_probes_conflict_before_duplicate(config,name,expected):
    frozen_fixtures();base=read_json(FIXTURES/'thor-zero.json');mutant=read_json(FIXTURES/name)
    config['orin']['source_sample_interval_ms']=None
    e=engine_for(config,record_schema=2)
    r=dict(observer_run_id='fixture-run',episode='fixture',ref='fixture/1',kind='orin',mono_s=1.,received_at_utc='2026-01-01T00:00:01Z',connection_epoch=1,payload=base)
    first=e.process(r)
    assert first['quality']['accepted']
    bad=dict(r,ref='fixture/2',mono_s=2.,payload=mutant)
    out=e.process(bad)
    assert out['quality']['reason']==expected and out['quality']['invalidated_segment']==first['prediction']['origin']['segment']
