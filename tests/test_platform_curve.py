"""Production schema2 paths, isolated synthetic inputs and preserved schema1."""
import copy
import json
import shutil
from pathlib import Path
import pytest
from tto.cli import main
from tto.dataset import replay, freeze_split, build_dataset, load_dataset, check_split
from tto.demo import packet, fan_packet, temp_packet, record_demo
from tto.engine import engine_for
from tto.features import Features
from tto.model import load_model, eligible_scope
from tto.profiles import PROFILES, FAMILIES, RAILS, platform_contract, uniform_gpu
from tto.platform_quality import PlatformQuality
from tto.storage import Journal, LimitReached
from tto.training import train
from tto.evaluation import evaluate
from tto.report import summarize
from tto.util import read_json, seal, write_json, file_hash, digest


def new_packet(seq, family='jetson_thor', gpu_age=0, outer_age=0):
    p = packet(seq, 46, age=outer_age)
    p['telemetry_meta']['source_sample_interval_ms'] = 1000
    soc, backend = FAMILIES[family]
    p['platform'] = {'schema_version': 1, 'family': family, 'soc': soc, 'gpu_backend': backend,
                     'identification_source': 'device_tree_compatible', 'compatible': ['nvidia,'+soc]}
    p['gpu'] = {'schema_version': 1, 'utilization_pct': 0, 'source': backend, 'status': 'valid',
                'sampled_at_utc': p['telemetry_meta']['received_at'], 'age_at_telemetry_receive_ms': gpu_age,
                'sample_interval_ms': 1000, 'freshness_timeout_ms': 5000,
                'device_uuid': 'GPU-SYNTHETIC' if backend == 'nvml' else None}
    if backend == 'tegrastats': p['gpu']['gr3d_freq'] = 0
    if family == 'jetson_thor':
        p['temperature'].update(soc012=42, soc345=41)
        p['power'] = {name: {'current': 2000+i*1000, 'average': 99999, 'unit': 'mW'} for i, name in enumerate(RAILS[family])}
    return p


def row(seq, t=None, family='jetson_thor', **kwargs):
    return {'observer_run_id': 'synthetic-run', 'episode': 'synthetic-process', 'ref': f'synthetic-run/observation:{seq}',
            'kind': 'orin', 'mono_s': float(seq if t is None else t), 'connection_epoch': 1,
            'received_at_utc': '2026-01-01T00:00:00Z', 'payload': new_packet(seq, family, **kwargs)}


def feed_control(engine, t, scope='curve', duty=0, temp_valid=True):
    f = fan_packet(duty); f['data']['fans'][0]['mode'] = scope
    if scope == 'curve': f['data']['fans'][0].pop('controller_gain')
    d = temp_packet(); d['data']['valid'] = temp_valid
    for kind, p in [('fan', f), ('temp', d)]:
        engine.process({'kind': kind, 'mono_s': float(t), 'payload': p, 'ref': f'synthetic-run/{kind}:{t}'})


@pytest.mark.parametrize('family,scope,size', [('jetson_orin','auto',54), ('jetson_orin','curve',53), ('jetson_thor','auto',51), ('jetson_thor','curve',50)])
def test_finite_profiles_and_curve_zero_success(config, family, scope, size):
    e = engine_for(config, record_schema=2)
    for t in range(186):
        feed_control(e, t, scope)
        out = e.process(row(t+1, t, family))
    origin = out['prediction']['origin']
    assert origin['control_eligible'] and origin['normal_auto'] == (scope == 'auto')
    assert origin['features']['duty'] == 0 and origin['features']['duty_mean_120'] == 0
    assert len(origin['features']) == size <= 64 and origin['history_ready']
    assert len(PROFILES[origin['feature_profile_id']]['columns']) == size
    if scope == 'curve':
        assert 'gain' not in origin['features'] and 'fan_diagnostics' not in origin
        assert out['prediction']['firmware_45s_diagnostic'] is None


@pytest.mark.parametrize('mutation,reason', [
    ('missing_schema','gpu_contract_missing_or_invalid'), ('schema','gpu_contract_missing_or_invalid'),
    ('missing_age','gpu_contract_missing_or_invalid'), ('error','gpu_source_error'),
    ('nan','gpu_value_invalid'), ('same_source','gpu_same_source_value_conflict')])
def test_new_gpu_never_falls_back(config, mutation, reason):
    p = new_packet(1, 'jetson_orin'); g = p['gpu']
    if mutation == 'missing_schema': g.pop('schema_version')
    elif mutation == 'schema': g['schema_version'] = 99
    elif mutation == 'missing_age': g.pop('age_at_telemetry_receive_ms')
    elif mutation == 'error': g.update(status='error', utilization_pct=None, age_at_telemetry_receive_ms=None, sampled_at_utc=None)
    elif mutation == 'nan': g['utilization_pct'] = float('nan')
    else: g['utilization_pct'] = 1
    d = uniform_gpu(p, 'jetson_orin', 0)
    assert d['value'] is None and d['reason'] == reason
    if mutation != 'nan':
        r = row(1, family='jetson_orin'); r['payload'] = p
        q = PlatformQuality(config).accept(r)
        assert q['accepted'] and q['values']['tj'] == 46 and q['values']['gpu_busy'] is None


def test_legacy_gpu_marker_and_unknown_no_guess():
    p = new_packet(1, 'jetson_orin'); p.pop('platform'); p['gpu'] = {'gr3d_freq': 0}
    assert uniform_gpu(p, None, 0)['value'] == 0
    p['hostname'] = 'Thor'; p['model'] = 'Orin'
    assert platform_contract(p, 1000)[0] is None
    assert uniform_gpu(p, None, 0)['value'] == 0


def test_gpu_age_sum_duplicates_utc_and_window_gap(config):
    q = PlatformQuality(config)
    r = row(1, t=0, gpu_age=4500, outer_age=1000)
    out = q.accept(r); assert out['accepted'] and out['gpu']['reason'] == 'gpu_effective_stale'
    assert out['values']['tj'] == 46 and out['values']['gpu_busy'] is None
    r = row(2, t=1, gpu_age=1000, outer_age=500)
    a = q.accept(r); assert a['gpu']['age_lower_bound_ms'] == 1500
    b = copy.deepcopy(r); b['mono_s'] = 2; b['payload']['telemetry_meta']['sample_age_ms'] = 100
    b['received_at_utc'] = '2030-01-01T00:00:00Z'
    out = q.accept(b)
    assert out['reason'] == 'duplicate' and out['gpu']['age_lower_bound_ms'] == 2500
    assert out['gpu']['valid_until'] == a['gpu']['valid_until']
    f = Features(1, PROFILES['thor_curve_v2'])
    for t in range(181):
        f.push({'t': t, 'values': {'tj':46,'duty':0,'gpu_busy':10}, 'gpu_valid_until': t+.5 if t == 150 else t+5, 'ref': str(t)})
    v, _ = f.snapshot(); assert v['gpu_busy'] == 10
    assert v['gpu_busy_mean_30'] is None and v['gpu_busy_mean_120'] is None
    for t in range(181,272):
        f.push({'t':t, 'values': {'tj':46,'duty':0,'gpu_busy':10}, 'gpu_valid_until':t+5, 'ref':str(t)})
    assert f.snapshot()[0]['gpu_busy_mean_120'] == 10


@pytest.mark.parametrize('field', ['platform', 'gpu'])
def test_same_identity_additive_fields_isolate(config, field):
    e = engine_for(config, record_schema=2)
    feed_control(e, 0)
    a = row(1, 0); first = e.process(a)
    b = copy.deepcopy(a); b['mono_s'] = .2
    if field == 'platform': b['payload']['platform']['compatible'].append('synthetic-board')
    else: b['payload']['gpu']['sampled_at_utc'] = '2026-01-01T00:00:09Z'
    conflict = e.process(b)['quality']
    assert conflict['reason'] == 'identity_conflict'
    assert conflict['invalidated_segment'] == first['prediction']['origin']['segment']
    feed_control(e, 1); resumed = e.process(row(2, 1))
    assert resumed['quality']['accepted'] and resumed['prediction']['origin']['segment'] != conflict['invalidated_segment']


@pytest.mark.parametrize('scope', ['manual', 'off', 'curve'])
def test_qualification_does_not_relax_invalid_temperature(config, scope):
    e = engine_for(config, record_schema=2); feed_control(e, 0, scope, temp_valid=False)
    p = e.process(row(1,0))['prediction']
    assert not p['origin']['control_eligible'] and 'control_temperature_invalid' in p['origin']['control_ineligible_reasons']
    assert not p['origin']['normal_auto'] and p['firmware_45s_diagnostic'] is None


def test_profile_unknown_prelude_switches_and_uuid(config):
    e = engine_for(config, record_schema=2); feed_control(e, 0)
    a = row(1,0); a['payload'].pop('platform'); first = e.process(a)['prediction']['origin']
    assert first['feature_profile_id'] is None
    feed_control(e,5); b = e.process(row(2,5))
    assert b['input_profile'] and b['prediction']['origin']['support_start'] == 5
    assert 'control_scope' not in b['input_profile']
    for t, scope in [(10,'auto'),(15,'curve')]:
        feed_control(e,t,scope); e.process(row(t,t))
    assert e.mixed_profiles and len(e.known_scopes) == 2
    e2 = engine_for(config, record_schema=2); feed_control(e2,0)
    a = row(1,0); a['payload']['gpu'].update(status='unavailable',source='unavailable',utilization_pct=None,age_at_telemetry_receive_ms=None,sampled_at_utc=None,device_uuid=None)
    e2.process(a); segment = e2.q.segment
    feed_control(e2,1); e2.process(row(2,1))
    assert e2.q.segment == segment and not e2.mixed_profiles
    c = row(3,2); c['payload']['gpu']['device_uuid'] = 'GPU-SYNTHETIC-OTHER'
    feed_control(e2,2); e2.process(c); assert e2.mixed_profiles and e2.q.segment > segment


@pytest.fixture(scope='module', params=[('jetson_orin','auto'),('jetson_orin','curve'),('jetson_thor','auto'),('jetson_thor','curve')])
def modeled(request, tmp_path_factory):
    family, scope = request.param; root = tmp_path_factory.mktemp(family+'-'+scope)
    runs = record_demo(root/'runs',count=3,seconds=400,record_schema=2,family=family,scope=scope)
    frozen = freeze_split(runs,root/'frozen')
    train(frozen/'dataset.json',frozen/'split.json',root/'model.json')
    return root, runs, load_model(root/'model.json')


def test_full_frozen_chain_and_shadow_offline(modeled, tmp_path):
    root, runs, model = modeled
    d = load_dataset(root/'frozen/dataset.json'); assert d['schema_version'] == model['schema_version'] == 2
    assert d['feature_profile_id'] == model['feature_profile_id']
    result = evaluate(root/'frozen/dataset.json',root/'frozen/split.json',root/'model.json',tmp_path/'evaluation')
    assert result['simulated'] and all(result['comparisons'][k]['horizons']['45']['matched_count'] > 0 for k in ('baseline','m0','m1'))
    m = read_json(runs[0]/'manifest.json'); j = Journal(m['config'],tmp_path/'shadow',simulated=True,run_type='shadow',model_sha256=model['sha256'],record_schema=2)
    e = engine_for(m['config'],model,2)
    for path in sorted(runs[0].glob('observations-*')):
        for line in path.read_text().splitlines():
            r = j.observation(json.loads(line)); j.processing_output(r,e.process(r))
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'elapsed_s':400,'stop_reason':'synthetic_end'})
    hashes = {p.name:file_hash(p) for p in j.path.glob('*.jsonl')}
    assert main(['report','--run',str(j.path),'--output',str(tmp_path/'report')]) == 0
    report = read_json(tmp_path/'report/report.json')
    assert not report['recorded_results']['issues'] and report['recorded_results']['scored_method_horizon_records'] > 0
    assert report['input_diagnostics']['counts']['eligible_origins'] > 0
    assert hashes == {p.name:file_hash(p) for p in j.path.glob('*.jsonl')}


def test_selected_gpu_expiry_keeps_m0_and_unselected_m1(modeled):
    root, runs, model = modeled; c = read_json(runs[0]/'manifest.json')['config']
    e = engine_for(c,model,2); last = None
    for path in sorted(runs[0].glob('observations-*')):
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r['kind']=='orin' and r['mono_s'] >= 200:
                r['payload']['gpu'].update(status='error',utilization_pct=None,age_at_telemetry_receive_ms=None,sampled_at_utc=None)
            out = e.process(r)
            if out['prediction']:last = out['prediction']
    assert 'ridge_tj' in last['values'] and last['origin']['control_eligible']
    assert 'ridge_full' not in last['values'] and last['unavailable']['ridge_full'] == 'missing_selected_features'
    assert not e.mixed_profiles
    # A separately frozen column selection can omit GPU; no imputation occurs.
    m = copy.deepcopy(model); method = m['methods']['ridge_full']; indices = [i for i,c in enumerate(method['columns']) if not c.startswith('gpu_busy')]
    for k in ('columns','mean','scale','minimum','maximum'):method[k] = [method[k][i] for i in indices]
    for head in method['heads'].values():head['coefficients'] = [head['coefficients'][i] for i in indices]
    from tto.model import infer
    assert infer(m,'ridge_full',last['origin']['features'])[0] is not None


def test_missing_profile_separate_from_log_integrity(modeled,tmp_path):
    _,runs,_ = modeled; dst = tmp_path/'copy';shutil.copytree(runs[0],dst)
    (dst/'input-profile.json').rename(dst/'input-profile.saved')
    r = summarize(dst)
    assert 'input_profile_missing' in r['missing_required_metadata'] and not r['missing_required_logs']
    assert r['recorded_results']['log_evidence_complete'] and r['recorded_results']['scored_method_horizon_records'] == 0
    with pytest.raises(ValueError,match='input_profile_missing'):build_dataset([dst])


@pytest.mark.parametrize('mutation', ['profile','units','scope','period','group','dimension'])
def test_model_identity_and_columns_rejected(modeled,tmp_path,mutation):
    _,_,m = modeled; m = copy.deepcopy(m);m.pop('sha256')
    if mutation=='profile':m['feature_profile_id'] = 'unknown_v2'
    elif mutation=='units':m['input_contract']['units']['power']='mW';m['input_contract_sha256']=digest(m['input_contract'])
    elif mutation=='scope':m['control_scope']='manual'
    elif mutation=='period':m['input_contract']['gpu_period_ms']=-1;m['input_contract_sha256']=digest(m['input_contract'])
    elif mutation=='group':m['methods']['ridge_full']['columns'].append('gpu_busy_mean_120')
    else:m['methods']['ridge_tj']['scale'].pop()
    write_json(tmp_path/'model.json',seal(m))
    with pytest.raises(ValueError):load_model(tmp_path/'model.json')


def test_new_record_contract_never_falls_back(tmp_path):
    runs = record_demo(tmp_path/'runs',count=1,seconds=20,record_schema=2)
    p = runs[0]/'manifest.json';m = read_json(p);m.pop('input_schema');p.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='record contract'):replay(runs[0])
    assert main(['report','--run',str(runs[0]),'--output',str(tmp_path/'refused-report')])==0
    refused=read_json(tmp_path/'refused-report/report.json')
    assert refused['report_type']=='diagnostic_evidence_refused' and refused['error_metrics'] is None
    assert '拒绝评分' in refused['conclusion']


def test_formal_never_known_or_mixed_and_forged_dataset_rejected(config,tmp_path):
    j = Journal(config,tmp_path/'runs',simulated=True,record_schema=2);e = engine_for(config,record_schema=2)
    for t in range(30):
        feed_control(e,t);r = row(t+1,t);r['payload'].pop('platform')
        saved=j.observation(r);j.processing_output(saved,e.process(saved))
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'elapsed_s':30})
    r = summarize(j.path);assert 'platform_unconfirmed' in r['platform_state']['evidence_issues']
    assert not r['missing_required_metadata']
    with pytest.raises(ValueError,match='platform_unconfirmed'):build_dataset([j.path])


def test_thor_rails_units_without_alias(config):
    q=PlatformQuality(config);r=row(1);out=q.accept(r)
    v=out['values'];assert v['vdd_gpu']==2 and v['vdd_cpu_soc_mss']==3 and v['vin_sys_5v0']==4
    assert v['temp_soc012']==42 and v['temp_soc345']==41 and 'temp_soc0' not in v
    assert 'vdd_gpu_soc' not in v and 'vdd_cpu_cv' not in v
    r=row(2);r['payload']['power']['vdd_gpu']['unit']='W';r['payload']['power']['vdd_cpu_soc_mss'].pop('current')
    v=q.accept(r)['values'];assert v['vdd_gpu'] is None and v['vdd_cpu_soc_mss'] is None


def test_profile_file_budget_and_write_once(config,tmp_path):
    j=Journal(config,tmp_path,simulated=True,record_schema=2)
    before=j.total;j.metadata('input-profile.json',{'synthetic':True});assert j.total>before
    with pytest.raises(FileExistsError):j.metadata('input-profile.json',{'synthetic':False})
    j.close({'elapsed_s':0});assert read_json(j.path/'files.json')['input-profile.json']==file_hash(j.path/'input-profile.json')


def test_platform_and_cadence_a_b_a_remain_mixed(config):
    for change in ('platform','cadence'):
        e=engine_for(config,record_schema=2)
        for t in range(3):
            feed_control(e,t)
            p=row(t+1,t)
            if t==1:
                if change=='platform':p=row(t+1,t,'jetson_orin')
                elif change=='cadence':p['payload']['gpu'].update(sample_interval_ms=2000,freshness_timeout_ms=6000)
            e.process(p)
        assert e.mixed_profiles and e.counts['mixed_profiles']==1


def test_scope_changes_without_tj_still_mark_mixed(config):
    e=engine_for(config,record_schema=2);feed_control(e,0,'auto');e.process(row(1,0))
    feed_control(e,1,'curve');feed_control(e,2,'auto')
    assert e.mixed_profiles


def test_formal_mixed_rejected_and_rows_cannot_forge_identity(modeled,tmp_path):
    root,runs,m=modeled
    d=load_dataset(root/'frozen/dataset.json');s=read_json(root/'frozen/split.json')
    changed=copy.deepcopy(d);changed.pop('sha256')
    changed['rows'][-1]['feature_profile_id']='thor_auto_v2' if d['feature_profile_id']!='thor_auto_v2' else 'orin_curve_v2'
    changed=seal(changed);write_json(tmp_path/'dataset.json',changed)
    with pytest.raises(ValueError,match='profile'):load_dataset(tmp_path/'dataset.json')
    with pytest.raises(ValueError,match='profile'):check_split(changed,s)
    src=runs[0];manifest=read_json(src/'manifest.json');j=Journal(manifest['config'],tmp_path/'mixed',simulated=True,record_schema=2)
    e=engine_for(manifest['config'],record_schema=2)
    for path in sorted(src.glob('observations-*')):
        for line in path.read_text().splitlines():
            r=json.loads(line)
            if r['kind']=='fan' and 200<=r['mono_s']<250:
                f=r['payload']['data']['fans'][0];f['mode']='curve' if m['control_scope']=='auto' else 'auto';f['controller_gain']=1.1
            saved=j.observation(r);j.processing_output(saved,e.process(saved))
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'elapsed_s':400})
    assert replay(j.path)['platform_state']['mixed_profiles']
    with pytest.raises(ValueError,match='mixed_profiles'):build_dataset([j.path])


@pytest.mark.parametrize('family', ['orin','thor'])
def test_intermediate_monitor_fixture_missing_new_wire_period_detected(config,family):
    payload=read_json(Path(__file__).parent/'fixtures/platform-v2'/f'{family}-contract.json')
    q=PlatformQuality(config);r=row(1,0);r['payload']=payload
    out=q.accept(r)
    assert out['accepted'] and out['input_contract'] is None
    assert out['source_period']['reason']=='source_period_missing_or_invalid' and not out['period_known']


def test_legacy_model_cannot_activate_in_new_run(config):
    fixture=Path(__file__).parent/'fixtures/r3b/synthetic-model.json'
    model=load_model(fixture);assert model['schema_version']==1
    e=engine_for(config,model,2)
    for t in range(186):
        feed_control(e,t,'auto');out=e.process(row(t+1,t,'jetson_orin'))
    p=out['prediction'];assert 'ridge_tj' not in p['values'] and 'ridge_full' not in p['values']
    assert p['unavailable']['ridge_tj']=='legacy_model_requires_legacy_run'


@pytest.mark.parametrize('interval', [1,1000,3000])
def test_wire_period_auto_adopt_without_changing_saved_config(config,interval):
    config['orin']['source_sample_interval_ms']=None
    original=copy.deepcopy(config);e=engine_for(config,record_schema=2)
    feed_control(e,0);r=row(1,0);r['payload']['telemetry_meta']['source_sample_interval_ms']=interval
    p=e.process(r)['prediction'];origin=p['origin']
    assert origin['source_period_evidence']['period_ms']==interval
    assert origin['source_period_evidence']['basis']=='wire_telemetry_meta'
    assert origin['input_contract_eligible'] and e.features.period==interval/1000
    assert config==original
    assert origin['input_contract']['gpu_period_ms']==1000


def test_configured_period_conflict_blocks_modeling_not_tj(config,tmp_path):
    e=engine_for(config,record_schema=2);feed_control(e,0)
    r=row(1,0);r['payload']['telemetry_meta']['source_sample_interval_ms']=3000
    out=e.process(r);p=out['prediction']
    assert out['quality']['accepted'] and p['origin']['features']['tj']==46
    assert p['origin']['source_period_evidence']['reason']=='configured_source_period_conflict'
    assert not p['origin']['input_contract_eligible'] and e.input_conflicts=={'configured_source_period_conflict'}
    j=Journal(config,tmp_path,simulated=True,record_schema=2)
    e=engine_for(config,record_schema=2)
    for kind,payload in [('fan',fan_packet()),('temp',temp_packet()),('orin',r['payload'])]:
        saved=j.observation({'kind':kind,'mono_s':0.,'received_at_utc':'2026-01-01T00:00:00Z','payload':payload})
        j.processing_output(saved,e.process(saved))
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'elapsed_s':1})
    with pytest.raises(ValueError,match='configured_source_period_conflict'):build_dataset([j.path])


def test_source_period_is_immutable_before_duplicate(config):
    q=PlatformQuality(config);a=row(1,0);q.accept(a)
    b=copy.deepcopy(a);b['mono_s']=.1;b['payload']['telemetry_meta']['source_sample_interval_ms']=2000
    assert q.accept(b)['reason']=='identity_conflict'


def test_late_epoch_cannot_change_active_source_period(config):
    config['orin']['source_sample_interval_ms']=None
    q=PlatformQuality(config);q.accept(row(1,0))
    late=row(2,1);late['connection_epoch']=0;late['payload']['telemetry_meta']['source_sample_interval_ms']=3000
    assert q.accept(late)['reason']=='late_connection_callback'
    assert q.c['orin']['source_sample_interval_ms']==1000


def test_operator_evidence_association_keeps_verbatim_and_two_times(tmp_path):
    from tto.report import operator_evidence
    rows=[{'observer_run_id':'run-one','kind':'task_finished','verbatim':'合成任务结束 <script>原文</script>','source':'synthetic_human_marker','approx_event_utc':'2026-01-01T00:00:00Z','recorded_at_utc':'2026-01-01T00:01:00Z'}, {'observer_run_id':'different-run','kind':'task_started'}]
    p=tmp_path/'operator-records.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    before=file_hash(p);result=operator_evidence(tmp_path,'run-one')
    assert result['records'][0]['raw']==rows[0] and len(result['records'])==1
    assert result['issues'][0]['reason']=='operator_run_identity_unconfirmed' and file_hash(p)==before


@pytest.mark.parametrize('setting', ['platform','source_period','gpu_period','gpu_timeout'])
def test_same_stream_lifecycle_change_isolates_old_segment(config,setting):
    config['orin']['source_sample_interval_ms']=None
    e=engine_for(config,record_schema=2);feed_control(e,0);first=e.process(row(1,0))['prediction']['origin']
    b=row(2,1)
    if setting=='platform':b=row(2,1,'jetson_orin')
    elif setting=='source_period':b['payload']['telemetry_meta']['source_sample_interval_ms']=2000
    elif setting=='gpu_period':b['payload']['gpu'].update(sample_interval_ms=2000,freshness_timeout_ms=6000)
    else:b['payload']['gpu']['freshness_timeout_ms']=6000
    feed_control(e,1);out=e.process(b)
    assert out['quality']['accepted'] and out['quality']['lifecycle_violation']
    assert out['quality']['invalidated_segment']==first['segment']
    assert out['prediction']['origin']['segment']!=first['segment'] and e.mixed_profiles


@pytest.mark.parametrize('status', ['error','unavailable','stale'])
def test_sealed_states_keep_settings_no_fake_recovery(config,status):
    e=engine_for(config,record_schema=2);feed_control(e,0);e.process(row(1,0));segment=e.q.segment
    b=row(2,1);g=b['payload']['gpu'];g.update(status=status,utilization_pct=None)
    if status=='stale':g['age_at_telemetry_receive_ms']=5000
    else:g.update(sampled_at_utc=None,age_at_telemetry_receive_ms=None,source='unavailable' if status=='unavailable' else 'nvml')
    feed_control(e,1);out=e.process(b)
    assert out['quality']['gpu']['reason']=='gpu_source_'+status and out['quality']['values']['gpu_busy'] is None
    assert e.q.segment==segment and not e.mixed_profiles and out['prediction'] is None
    duplicate=copy.deepcopy(b);duplicate['mono_s']=2
    assert e.process(duplicate)['prediction'] is None
    feed_control(e,5);restored=e.process(row(3,5))
    assert restored['quality']['values']['gpu_busy']==0 and e.q.segment==segment


@pytest.mark.parametrize('version', [True,1.0,2,None])
def test_bad_gpu_version_only_removes_gpu(config,version):
    e=engine_for(config,record_schema=2);feed_control(e,0);e.process(row(1,0))
    b=row(2,5);b['payload']['gpu']['schema_version']=version;feed_control(e,5)
    out=e.process(b)
    assert out['quality']['accepted'] and out['prediction']['origin']['control_eligible']
    assert out['quality']['values']['gpu_busy'] is None and not e.mixed_profiles


@pytest.mark.parametrize('value', [True,'0',-1,101,None])
def test_bad_gpu_numeric_preserves_real_tj(config,value):
    r=row(1,0);r['payload']['gpu']['utilization_pct']=value
    out=PlatformQuality(config).accept(r)
    assert out['accepted'] and out['values']['tj']==46 and out['values']['gpu_busy'] is None


def test_unknown_valid_contract_and_platform_presence_prevent_legacy_fallback(config):
    r=row(1,0);p=r['payload']
    p['platform'].update(family='unknown',soc=None,identification_source=None,compatible=[],gpu_backend='unavailable')
    p['gpu'].update(status='unavailable',source='unavailable',utilization_pct=None,sampled_at_utc=None,age_at_telemetry_receive_ms=None,sample_interval_ms=None,freshness_timeout_ms=None,device_uuid=None)
    out=PlatformQuality(config).accept(r);assert out['accepted'] and out['platform_reason']=='platform_unconfirmed'
    assert out['period_known'] and out['input_contract'] is None and out['gpu']['reason']=='gpu_source_unavailable'
    p['gpu']={'gr3d_freq':0};assert uniform_gpu(p,None,0)['reason']=='gpu_contract_missing_or_invalid'


def test_lifecycle_isolation_reaches_actual_journal_and_report(tmp_path):
    source=record_demo(tmp_path/'source',count=1,seconds=620,record_schema=2,family='jetson_thor',scope='curve')[0]
    config=read_json(source/'manifest.json')['config']
    j=Journal(config,tmp_path/'shadow',simulated=True,run_type='shadow',record_schema=2);e=engine_for(config,record_schema=2)
    for path in sorted(source.glob('observations-*')):
        for line in path.read_text().splitlines():
            r=json.loads(line)
            if r['kind']=='orin' and r['mono_s']==350:r['payload']['gpu']['freshness_timeout_ms']=6000
            saved=j.observation(r);j.processing_output(saved,e.process(saved))
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'elapsed_s':620})
    before={p.name:file_hash(p) for p in j.path.iterdir() if p.is_file()}
    assert main(['report','--run',str(j.path),'--output',str(tmp_path/'report')])==0
    r=read_json(tmp_path/'report/report.json');rec=r['recorded_results']
    assert rec['log_evidence_complete'] and not rec['issues']
    assert rec['quality_excluded_method_horizon_records']>0 and rec['scored_method_horizon_records']>0
    assert all(x['reason']=='lifecycle_contract_change' for x in rec['quality_isolations'])
    isolated={(x['run_id'],x['segment']) for x in rec['quality_isolations']}
    assert all((p['run_id'],p['segment']) not in isolated for p in rec['scored_records'])
    assert r['platform_state']['mixed_profiles']
    assert before=={p.name:file_hash(p) for p in j.path.iterdir() if p.is_file()}
