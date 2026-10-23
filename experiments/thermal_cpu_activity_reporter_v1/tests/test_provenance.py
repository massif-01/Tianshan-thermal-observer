"""Three metadata classes; declared-field fixtures are never physical-field evidence."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provenance import classify, sha

OLD = ROOT.parent/'thermal_cpu_activity_bridge_v1'


def fixture(tmp_path):
    run, adapted = tmp_path/'run', tmp_path/'adapted'
    shutil.copytree(OLD/'inputs/joint-complete/run', run)
    shutil.copytree(OLD/'results/final-v2', adapted)
    return run, adapted


def update_json(path, obj):
    path.write_text(json.dumps(obj))


def reindex(run, adapted):
    sources = json.loads((adapted/'sources.json').read_text())
    old_root = Path(sources['run_dir'])
    for item in sources['files']:
        try:
            rel = Path(item['path']).relative_to(old_root)
        except ValueError:
            continue
        item['sha256'] = sha(run/rel)
    update_json(adapted/'sources.json', sources)


def test_synthetic_from_actual_sender_receiver_metadata(tmp_path):
    run, adapted = fixture(tmp_path)
    result = classify(run, adapted)
    assert result['category'] == 'synthetic' and result['synthetic_only'] is True
    assert result['identity_association_verified'] is True
    assert result['physical_source_verified'] is False


def test_declared_field_does_not_verify_hardware_or_time(tmp_path):
    run, adapted = fixture(tmp_path)
    launch = json.loads((run/'launch.json').read_text())
    launch['synthetic_loopback_only'] = False
    launch['binding']['synthetic_loopback_only'] = False
    launch['binding']['sidecar'].pop('synthetic')
    update_json(run/'launch.json', launch)
    reg = json.loads((adapted/'registration.json').read_text())
    reg['declared_role'] = 'targeted_recorded_arrival_research'
    update_json(adapted/'registration.json', reg)
    reindex(run, adapted)
    result = classify(run, adapted)
    assert result['category'] == 'declared_field_unverified' and result['synthetic_only'] is False
    assert result['identity_association_verified'] is True
    assert result['physical_source_verified'] is False and result['Thor_N305_verified'] is False
    assert result['source_timing_verified'] is False


def test_unknown_missing_flags_conflict_or_unassociated(tmp_path):
    run, adapted = fixture(tmp_path)
    reg = json.loads((adapted/'registration.json').read_text())
    reg['declared_role'] = 'targeted_recorded_arrival_research'
    update_json(adapted/'registration.json', reg)
    conflict = classify(run, adapted)
    assert conflict['category'] == 'unknown' and conflict['synthetic_only'] is None
    assert 'synthetic_and_field_role_conflict' in conflict['reasons']
    launch = json.loads((run/'launch.json').read_text())
    for obj in [launch, launch['binding'], launch['binding']['sidecar']]:
        obj.pop('synthetic_loopback_only', None)
        obj.pop('synthetic', None)
    update_json(run/'launch.json', launch)
    reindex(run, adapted)
    assert classify(run, adapted)['category'] == 'unknown'  # Absence is not field proof.
    launch['command_id'] = 'FOREIGN-COMMAND'
    update_json(run/'launch.json', launch)
    reindex(run, adapted)
    foreign = classify(run, adapted)
    assert foreign['identity_association_verified'] is False and foreign['category'] == 'unknown'
    assert 'command_identity_unassociated' in foreign['reasons']
    launch['command_id'] = reg['command_id']
    update_json(run/'launch.json', launch)  # Do not reindex: changed evidence must remain unresolved.
    assert classify(run, adapted)['identity_association_verified'] is False
    (run/'launch.json').unlink()
    assert classify(run, adapted)['category'] == 'unknown'
