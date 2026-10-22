"""Read two fixed local archives, freeze the study before computing outcomes."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import io
import json
import zipfile

ROOT = Path(__file__).absolute().parent
ARCHIVES = {
    'r2-results-original.zip': '809e90eef398daf34e9cabfd5d4427d35275fc8185541d61810f67943f35aecb',
    'r2-prerequisites-original.zip': '7f52d7cfad66564ff07178bfe14a5a46da83390b0855c28f2b65cad8910c3614',
}
MODELS = {'primary': 'D-LSM', 'old_LS': 'LS-fit-on-LSM', 'A24': 'D-LSM-G2-A24'}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def read(path):
    return json.loads(Path(path).read_text())


def jsonlines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x]


def write_lines(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')


def prepare(input_dir, root=ROOT):
    root = Path(root)
    source = root / 'sources'
    inventory = []
    archives = {}
    for name, expected in ARCHIVES.items():
        path = Path(input_dir) / name
        b = path.read_bytes()
        assert digest(b) == expected, name
        z = zipfile.ZipFile(io.BytesIO(b))
        assert z.testzip() is None
        archives[name] = z
        inventory.append(dict(kind='original_archive', name=name, bytes=len(b), sha256=expected,
                              zip_crc='pass', role='immutable research source'))

    def copy(z, member, dest):
        b = z.read(member)
        path = source / dest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b)
        inventory.append(dict(kind='member', member=member, copied_to=str(path.relative_to(root)),
                              bytes=len(b), sha256=digest(b)))

    rz = archives['r2-results-original.zip']
    for name in ['data.json', 'examples.json', 'evidence-L.json', 'evidence-S.json', 'evidence-M.json']:
        copy(rz, 'runs/main/registered/' + name, 'registered/' + name)
    for model, folder in MODELS.items():
        for name in ['states.jsonl', 'calibrations.json', 'A-long.jsonl', 'predictions.jsonl',
                     'A-long-metrics.json', 'A-roll-metrics.json', 'B-metrics.json', 'coverage.json',
                     'evaluation-identity.json']:
            copy(rz, f'runs/main/evaluation/{folder}/{name}', f'evaluation/{model}/{name}')
    for model, folder in [('primary', 'D-LSM-G2'), ('A24', 'D-LSM-G2-A24')]:
        copy(rz, f'runs/main/fits/{folder}/model.json', f'models/{model}.json')
    pz = archives['r2-prerequisites-original.zip']
    v1 = zipfile.ZipFile(io.BytesIO(pz.read('inputs/greybox-v1-evidence.zip')))
    copy(v1, 'runs/main/fits/F-POOL-G2/model.json', 'models/old_LS.json')
    for name in ['inputs/input-index.json', 'inputs/legacy-input-index.json',
                 'metadata/M-ambient-user-confirmed.json', 'metadata/24C补充说明.md',
                 'references/frozen-old-model-index.json', 'references/source-documents.json']:
        copy(pz, name, 'provenance/' + Path(name).name)
    for run, member in [('L', 'inputs/L-seven-conditions-original.zip'),
                        ('S', 'inputs/S-shortqa-original-complete.zip'),
                        ('M', 'inputs/M-midload-original.zip')]:
        b = pz.read(member)
        z = zipfile.ZipFile(io.BytesIO(b))
        inventory.append(dict(kind='original_nested_archive', run=run, member=member,
                              sha256=digest(b), bytes=len(b), identity='shared archive; not private original'))
        if run == 'M':
            z = zipfile.ZipFile(io.BytesIO(z.read('trial-result.zip')))
        obs = next(n for n in z.namelist() if n.endswith('observations-0001.jsonl'))
        b = z.read(obs)
        # Payloads are copied, never interpreted as commands. No original file is rewritten.
        records = [json.loads(x) for x in b.splitlines()]
        write_lines(source / f'control-{run}.jsonl', [r for r in records if r['kind'] in ('fan', 'temp', 'boundary')])
        inventory.append(dict(kind='original_log', run=run, nested_member=obs, sha256=digest(b),
                              records=len(records), derived_control_only=f'sources/control-{run}.jsonl'))
    write(root / 'source-inventory.json', inventory)

    spec = read(root / 'handoff/templates/slowstate-spec.json')
    spec['implementation_freeze'] = dict(
        frozen_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        parameters='copied immutable model JSON; no dynamic optimization',
        state_replay_tolerance_C=1e-10,
        run_E='sealed first causal 60 s prefix calibration, fixed for run; never training E',
        A_long='exact 2D propagation with saved causal Ts_initial, score only after 60 s; no TJ feedback',
        causal_state='sealed past-60 state[1]; state[0] anchored observed TJ is not prediction',
        LP='union of actual accepted TJ and successful input event nodes, exact left hold; prefix replay only after E known',
        LP_memory='all past in strict segment, compared with fixed 60 s G2 window; no window search',
        all_branches_warmup_s=60,
        comparison='four branches use identical per-horizon (origin ref,h,label ref) inherited from sealed primary',
        main_context='confirmed_normal; every other v2 context and legacy strict separately retained',
        weights='per-origin unweighted metrics plus support seconds; no pooled-win claims across unequal cohorts',
        ablation_model='primary D-LSM G2 only',
        model_sensitivity='old_LS / primary / A24, absolute and one fixed first legal reference per run',
        demand_reference='first legal branch state of each strict segment; not equilibrium or ambient',
        demand_sampling='at actual legal accepted-TJ origins, real dt; fast ledger at every raw node plus known validity expiries',
        demand_invalid='null immediately, clear held output; no cross-gap carry; rebuild existing 60 s qualification',
        reversals='cumulative excursion >=0.02 from last extreme (turning-point hysteresis)',
        saturation='raw<0 or raw>1 duration, plus at-boundary duration; also raw amplitude retained',
        tail_return='first crossing target/output <=0.02 or state <=reference+0.2 C; report censor/recross',
        tail_censor='next request, qualification loss, source/reference change or record end; no extrapolated return',
        event_metadata='posthoc annotation and diagnostics only; never state/filter/demand features',
        resource_policy='CPU single BLAS thread; soft 3600 s budget; own child resource counters',
        runtime_actions='local file reads/writes and CPU kernel only; no network or device functions',
        requested_outputs=['four Chinese figure classes','state/jump/initialization/coverage/q diagnostics',
                           'all four-branch A-roll/B-HOLD point results','fast event ledger and normal demand'])
    for name in MODELS:
        spec.setdefault('model_sha256', {})[name] = digest((source / f'models/{name}.json').read_bytes())
    spec['source_inventory_sha256'] = digest((root / 'source-inventory.json').read_bytes())
    freeze = root / 'slowstate-spec.json'
    if freeze.exists():
        old = read(freeze)
        spec['implementation_freeze']['frozen_at'] = old['implementation_freeze']['frozen_at']
        assert old == spec, 'frozen spec differs; do not silently overwrite'
    else:
        write(freeze, spec)
    write(root / 'stage1-freeze.json', dict(spec_sha256=digest(freeze.read_bytes()),
          source_inventory_sha256=spec['source_inventory_sha256'], models=spec['model_sha256'],
          frozen_at=spec['implementation_freeze']['frozen_at'], all_data_development=True,
          no_fit=True, deployable=False, original_archive_sha256=ARCHIVES))
    # Supplemental historical identity views, already committed by the frozen archive SHA.
    # Kept outside the pre-score inventory so adding a readable index cannot rewrite that seal.
    supplement=[]
    for member in ['runs/main/source-identity-supplement.json','runs/main/source-inventory.json']:
        b=rz.read(member)
        dest=root/'sources/provenance'/('r2-'+Path(member).name)
        dest.write_bytes(b)
        supplement.append(dict(archive='r2-results-original.zip',archive_sha256=ARCHIVES['r2-results-original.zip'],
            member=member, copied_to=str(dest.relative_to(root)), sha256=digest(b),
            role='historical private-original / shared-archive identities, not a newly supplied original'))
    write(root/'historical-provenance-index.json',supplement)
    print('Stage1 frozen; verified original archives and copied immutable source subset.', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', type=Path, default=ROOT / 'handoff/inputs')
    args = ap.parse_args()
    prepare(args.input_dir)
