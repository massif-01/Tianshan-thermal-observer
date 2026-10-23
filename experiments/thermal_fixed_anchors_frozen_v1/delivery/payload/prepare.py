"""Copy the minimal current-run replay inputs; verify originals without modifying them."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SHARED = REPO / 'evidence/fixed-anchors-closeout2-20261019'
SEALED = REPO / 'evidence/field-entry-closeout-r2-20261019/source/src'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return h.hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def write(p, d):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def prepare():
    if (ROOT / 'inputs').exists():
        raise FileExistsError('Inputs already prepared; originals must never be replaced')
    run = SHARED / 'remote-result/run'
    native = next((run / 'native').glob('run-*'))
    verified = {}
    for base in (run, SHARED / 'instrument-sidecar'):
        index = read(base / 'files.json')
        for name, item in index.items():
            p = base / name
            assert p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], p
        verified[str(base.relative_to(SHARED))] = len(index)
    for name, digest in read(native / 'files.json').items():
        assert sha(native / name) == digest, name
    manifest = read(native / 'manifest.json')
    for name, digest in manifest['source_identity']['files'].items():
        assert sha(SEALED / 'tto' / name) == digest, name
    spec = read(ROOT / 'spec.json')
    assert manifest['observer_run_id'] == spec['run_id']
    assert manifest['source_identity']['sha256'] == spec['native_source_sha256']
    assert sha(SHARED / 'remote-session-original.tar.gz') == '314822d18ac13b2605c4a66fa586e5be3c9a64012b39885b75190420adf01b59'
    originals = {}

    def copy(src, target):
        src, target = Path(src), ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        originals[str(src.relative_to(REPO))] = dict(bytes=src.stat().st_size, sha256=sha(src))
        assert sha(target) == sha(src)

    # All native Python sources are retained so the installed aggregate can be verified.
    for p in sorted((SEALED / 'tto').iterdir()):
        if p.suffix in ('.py', '.json'):
            copy(p, Path('vendor/src/tto') / p.name)
    names = ['__init__.py', 'projection.py', 'comm_bridge.py', 'research/__init__.py',
             'research/observer.py', 'research/observer-spec.json', 'research/models/primary.json',
             'upstream_comm/source_health.py']
    for name in names:
        copy(SEALED / 'tto_field' / name, Path('vendor/src/tto_field') / name)
    for name in read(native / 'files.json'):
        # Native derived scores are preserved in the original archive, not re-scored as our results.
        if name in ('manifest.json', 'observations-0001.jsonl', 'summary.json', 'input-profile.json'):
            copy(native / name, Path('inputs/native') / name)
    copy(native / 'files.json', 'inputs/native/original-files.json')
    for name in ('states.jsonl', 'scheduler-events.jsonl', 'summary.json', 'native-binding.json', 'launch.json', 'files.json'):
        copy(run / name, Path('inputs/field') / name)
    for p in sorted((SHARED / 'instrument-sidecar').rglob('*')):
        if p.is_file():
            copy(p, Path('inputs/instrument') / p.relative_to(SHARED / 'instrument-sidecar'))
    for p in sorted((SHARED / 'clocks').iterdir()):
        if p.suffix in ('.json', '.HEIC', '.txt'):
            copy(p, Path('inputs/clocks') / p.name)
    for name in ('probe-description.json', 'completed-run-verification.json', 'computer-side-verification.json'):
        copy(SHARED / name, Path('inputs/context') / name)
    copy(SHARED / 'installation/installation-identity.json', 'inputs/context/installation-identity.json')
    assert sha(ROOT / 'vendor/src/tto_field/research/models/primary.json') == spec['model_sha256']
    assert sha(ROOT / 'vendor/src/tto_field/research/observer-spec.json') == spec['observer_spec_sha256']
    write(ROOT / 'source-and-input-originals.json', originals)
    write(ROOT / 'design-freeze.json', dict(spec_sha256=sha(ROOT / 'spec.json'),
          frozen_before_first_replay_or_score=True, original_indexes_verified=verified,
          native_index_verified=7, original_remote_archive=dict(bytes=21123365,
          sha256='314822d18ac13b2605c4a66fa586e5be3c9a64012b39885b75190420adf01b59',
          included=False, reason='no recursive historical bundles; sufficient current-run raw inputs copied'),
          new_data_role='frozen development evaluation only', original_preserved=True))
    write(SHARED / 'modeling-handoff-status.json', dict(stage='inputs_verified_spec_frozen',
          run_id=spec['run_id'], research_directory=str(ROOT), spec_sha256=sha(ROOT / 'spec.json'),
          training=False, device_actions=False, complete=False))
    print(json.dumps(dict(indexes_verified=verified, original_files_copied=len(originals),
                         frozen_spec_sha256=sha(ROOT / 'spec.json'))))


if __name__ == '__main__':
    prepare()
