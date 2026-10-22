"""Classify declarations, never infer verified field hardware from missing flags."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(run_dir, adapted):
    run_dir, adapted = Path(run_dir), Path(adapted)
    reasons, identities, declarations = [], {}, []
    result = dict(category='unknown', label_zh='未知', synthetic_only=None,
                  identity_association_verified=False, physical_source_verified=False,
                  Thor_N305_verified=False, source_timing_verified=False,
                  reasons=reasons, metadata_sha256=identities, declarations=declarations)

    def load(path, name):
        identities[name] = sha(path)
        return json.loads(path.read_text())

    try:
        launch = load(run_dir/'launch.json', 'launch.json')
        binding = load(run_dir/'native-binding.json', 'native-binding.json')
        manifest_rel = binding['native_manifest']
        manifest_path = (run_dir/manifest_rel).resolve()
        manifest_path.relative_to(run_dir.resolve())
        manifest = load(manifest_path, manifest_rel)
        registration = load(adapted/'registration.json', 'adapted/registration.json')
        sources = load(adapted/'sources.json', 'adapted/sources.json')
        recorded_root = Path(sources['run_dir'])
        indexed = {}
        for item in sources['files']:
            try:
                rel = Path(item['path']).relative_to(recorded_root)
            except ValueError:
                continue  # External config is retained in original provenance, not remapped here.
            if rel in indexed:
                reasons.append('duplicate_provenance_path:'+str(rel))
            indexed[rel] = item
        required = {'launch.json', 'native-binding.json', manifest_rel,
                    'cpu-sidecar-wire.jsonl', 'cpu-sidecar-arrivals.jsonl',
                    'sidecar-events.jsonl', 'states.jsonl'}
        for rel in sorted(required):
            item = indexed.get(Path(rel))
            if item is None or sha(run_dir/rel) != item['sha256']:
                reasons.append('provenance_missing_or_changed:'+rel)
        run_ids = [binding['native_run_id'], manifest['observer_run_id'], registration['run_id']]
        command_ids = [binding['command_id'], launch['command_id'],
                       manifest['field_command_id'], registration['command_id']]
        if not run_ids[0] or len(set(run_ids)) != 1:
            reasons.append('run_identity_unassociated')
        if not command_ids[0] or len(set(command_ids)) != 1:
            reasons.append('command_identity_unassociated')
        if not launch.get('config_sha256') or launch['config_sha256'] != manifest.get('config_sha256'):
            reasons.append('native_launch_config_unassociated')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reasons.append('metadata_unavailable:'+type(exc).__name__+':'+str(exc))
        return result
    result.update(run_id=run_ids[0], command_id=command_ids[0],
                  declared_role=registration.get('declared_role'),
                  saw_new_data_for_parameter_selection=registration.get('saw_new_data_for_parameter_selection'))
    if reasons:
        return result
    result['identity_association_verified'] = True
    scopes = [('launch', launch), ('launch.binding', launch.get('binding', {})),
              ('launch.binding.sidecar', launch.get('binding', {}).get('sidecar', {})),
              ('manifest', manifest)]
    for origin, obj in scopes:
        for key in ('synthetic_loopback_only', 'synthetic', 'simulated'):
            if key in obj:
                declarations.append(dict(source=origin, field=key, value=obj[key]))
    role = registration.get('declared_role')
    declarations.append(dict(source='registration', field='declared_role', value=role))
    synthetic = any(d['value'] is True for d in declarations)
    synthetic = synthetic or role == 'synthetic_actual_sender_receiver_integration'
    field = role == 'targeted_recorded_arrival_research'
    if synthetic and field:
        reasons.append('synthetic_and_field_role_conflict')
    elif synthetic:
        result.update(category='synthetic', label_zh='合成', synthetic_only=True)
    elif (field and launch.get('synthetic_loopback_only') is False
          and manifest.get('simulated') is False):
        result.update(category='declared_field_unverified', label_zh='声明现场，证据另核', synthetic_only=False)
        reasons.append('field_declaration_is_not_hardware_or_timing_verification')
    else:
        reasons.append('no_explicit_associated_source_declaration')
    return result
