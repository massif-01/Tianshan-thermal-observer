"""Local immutable bundles and explicit whole-run data roles."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    def cast(x):
        if hasattr(x, 'tolist'): return x.tolist()
        if isinstance(x, Path): return str(x)
        raise TypeError(type(x).__name__)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=cast, allow_nan=False)+'\n')


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', value):
        raise ValueError('invalid local model/session identifier')
    return value


def legacy_identity():
    expected = read(ROOT/'tool/legacy-identity.json')
    for name, digest in expected.items():
        if sha(ROOT/'tool/legacy'/name) != digest:
            raise ValueError('accepted legacy source changed: '+name)
    return expected


def load_bundle(path):
    path = Path(path).resolve()
    manifest = read(path)
    safe_id(manifest['model_id'])
    for name, digest in manifest['files'].items():
        file = (path.parent/name).resolve()
        file.relative_to(path.parent)
        if sha(file) != digest:
            raise ValueError('model bundle checksum mismatch: '+name)
    model = read(path.parent/manifest['model_file'])
    spec = read(path.parent/manifest['observer_spec_file'])
    if model.get('model') != 'G2' or model.get('deployable') is not False or model['dynamic'] != spec['dynamic']:
        raise ValueError('only consistent read-only G2 bundles are accepted')
    if sha(path.parent/manifest['model_file']) != manifest['model_sha256'] or sha(path.parent/manifest['observer_spec_file']) != manifest['observer_spec_sha256']:
        raise ValueError('model/spec identity mismatch')
    bounds = read(ROOT/'config/solver-spec.json')['models']['G2']['bounds']
    for name, (lo, hi) in bounds.items():
        value = model['dynamic'][name]
        if type(value) not in (float, int) or not lo <= value <= hi:
            raise ValueError('outside accepted G2 bounds: '+name)
    return manifest, model, spec


def validate_roles(data, train, validation, *, device_id, thermal_config_id, all_seen):
    if data.get('schema') != 'TTO-G2-MODELING-DATA-v1':
        raise ValueError('explicit modeling-data schema required; vendor fields are not guessed')
    runs = {r['run']: r for r in data['runs']}
    if len(runs) != len(data['runs']) or len({r['run_id'] for r in runs.values()}) != len(runs):
        raise ValueError('duplicate run identity: field/modeling are one process')
    if not train or set(train) & set(validation):
        raise ValueError('train/validation must be nonempty train and disjoint complete runs')
    for name in set(train+validation):
        record = runs[name]
        if record['device_id'] != device_id or record['thermal_config_id'] != thermal_config_id:
            raise ValueError('device or thermal configuration mismatch')
        if record['role'] == 'seen_development' and not all_seen:
            raise ValueError('seen development data cannot be relabelled blind')
    return runs


def parent_actual_fit_runs(manifest):
    """Actual UUID lineage, including the two retained pre-UUID example bundles."""
    ids = manifest.get('parameter_fit_actual_run_ids')
    if ids is not None:
        return set(ids)
    # Legacy examples have an exact dataset/model SHA. Resolve only that known
    # identity; never infer a parent's UUIDs from a newly supplied alias table.
    source = ROOT/'inputs/dataset.json'
    known = read(source)
    frozen = read(ROOT/'baseline/frozen-model-manifest.json')
    if manifest.get('training_dataset_sha256') == sha(source):
        aliases = manifest['parameter_fit_train_runs']
    elif manifest.get('model_sha256') == frozen['model_sha256']:
        aliases = frozen['fit_runs']
    else:
        raise ValueError('parent actual run lineage unknown; explicit UUID lineage required')
    mapping = {r['run']:r['run_id'] for r in known['runs']}
    return {mapping[name] for name in aliases}


def load_job(path, operation, parent):
    path = Path(path).resolve()
    job = read(path)
    if job['operation'] != operation:
        raise ValueError('operation differs from registered job')
    safe_id(job['model_id'])
    dataset = (path.parent/job['dataset']).resolve()
    solver = (path.parent/job['solver_spec']).resolve()
    if sha(dataset) != job['dataset_sha256'] or sha(solver) != job['solver_spec_sha256']:
        raise ValueError('registered dataset/solver SHA mismatch')
    data, spec = read(dataset), read(solver)
    runs = validate_roles(data, job['train_runs'], job['validation_runs'], device_id=job['device_id'],
                          thermal_config_id=job['thermal_config_id'], all_seen=job['all_data_seen'])
    manifest, model, _ = load_bundle(parent)
    if manifest['model_id'] != job['parent_model_id']:
        raise ValueError('parent model differs from preregistration')
    spec = dict(spec, initializations=[dict(s, G2=dict(s['G2'])) for s in spec['initializations']])
    if len(spec['initializations']) > 6:
        raise ValueError('at most six registered starts')
    if operation == 'calibrate':
        previous = parent_actual_fit_runs(manifest)
        if previous & {runs[n]['run_id'] for n in job['train_runs']}:
            raise ValueError('calibration data must be additional actual runs relative to parent fit data')
        spec['initializations'][0] = dict(id='PARENT', G2=dict(model['dynamic']))
    frozen = dict(job, dataset=str(dataset), solver_spec=str(solver), job_file_sha256=sha(path),
                  parent_manifest=str(Path(parent).resolve()), parent_manifest_sha256=sha(parent),
                  actual_run_ids={n:runs[n]['run_id'] for n in set(job['train_runs']+job['validation_runs'])},
                  legacy_sources=legacy_identity())
    return frozen, data, spec


def create_bundle(model, job, dest, *, parent_id, fit_report):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT/'baseline/g2_runtime', dest/'g2_runtime', ignore=shutil.ignore_patterns('__pycache__'))
    model = dict(model, model_id=job['model_id'], parent_model_id=parent_id, deployable=False)
    write(dest/'g2_runtime/frozen/primary.json', model)
    spec = read(ROOT/'baseline/g2_runtime/frozen/observer-spec.json')
    spec.update(contract='TTO-MAINLINE-CANDIDATE-OBSERVER-v1', scope='new candidate only; not activated or control qualified',
                model_sha256=sha(dest/'g2_runtime/frozen/primary.json'), dynamic=dict(model['dynamic']))
    # Same broad causal prior/information budget; validation future/nuisance fit is never imported.
    write(dest/'g2_runtime/frozen/observer-spec.json', spec)
    manifest = dict(schema='TTO-READONLY-MODEL-MANIFEST-v1', model_id=job['model_id'], parent_model_id=parent_id,
                    model_file='g2_runtime/frozen/primary.json', observer_spec_file='g2_runtime/frozen/observer-spec.json',
                    observer_code_file='g2_runtime/frozen/observer.py',
                    files={str(p.relative_to(dest)):sha(p) for p in (dest/'g2_runtime').rglob('*') if p.is_file()},
                    model_sha256=sha(dest/'g2_runtime/frozen/primary.json'),
                    observer_spec_sha256=sha(dest/'g2_runtime/frozen/observer-spec.json'),
                    observer_code_sha256=sha(dest/'g2_runtime/frozen/observer.py'),
                    parameter_fit_train_runs=job['train_runs'], validation_runs=job['validation_runs'],
                    parameter_fit_actual_run_ids=[job['actual_run_ids'][n] for n in job['train_runs']],
                    validation_actual_run_ids=[job['actual_run_ids'][n] for n in job['validation_runs']],
                    training_dataset_sha256=job['dataset_sha256'], data_role=job['data_role'], all_data_seen=job['all_data_seen'],
                    device_id=job['device_id'], thermal_config_id=job['thermal_config_id'],
                    numerical_convergence=model['converged'], fit_report=fit_report, rollback_model_id=parent_id,
                    source_model_deployable=False, automatic_activation=False, control_permission=False,
                    time_contract='TTO-RECEIVE-ANCHOR-v1')
    write(dest/'model-manifest.json', manifest)
    load_bundle(dest/'model-manifest.json')
    return manifest
