"""Immutable local model versions; selections affect only new observation sessions."""
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone
from .util import read, write, sha, safe_id, load_bundle


def now():
    return datetime.now(timezone.utc).isoformat()


def load(root):
    root = Path(root)
    path = root/'registry.json'
    return read(path) if path.exists() else dict(schema='TTO-LOCAL-MODEL-REGISTRY-v1', models={},
                selected_for_next_session=None, previous_selection=None, sessions={}, frozen_reference_model_id=None,
                device_id=None, thermal_config_id=None,
                selection_effect='next new session only; existing session pins never change', control_permission=False)


def save(root, state, event):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root/'registry.json'
    temporary = root/'registry.json.tmp'
    write(temporary, state)
    os.replace(temporary, path)
    with (root/'events.jsonl').open('a') as f:
        f.write(json.dumps(dict(at=now(), **event), ensure_ascii=False)+'\n')


def register(root, manifest, *, device_id=None, thermal_config_id=None):
    root, manifest = Path(root), Path(manifest).resolve()
    record, model, _ = load_bundle(manifest)
    state = load(root)
    if state['device_id'] is None:
        if not device_id or not thermal_config_id:
            raise ValueError('first registration requires explicit device_id and thermal_config_id')
        state.update(device_id=device_id, thermal_config_id=thermal_config_id)
    elif ((device_id is not None and device_id != state['device_id']) or
          (thermal_config_id is not None and thermal_config_id != state['thermal_config_id'])):
        raise ValueError('registry belongs to another device/configuration')
    if record.get('device_id', state['device_id']) != state['device_id'] or record.get('thermal_config_id', state['thermal_config_id']) != state['thermal_config_id']:
        raise ValueError('candidate belongs to another device/configuration')
    ident, digest = record['model_id'], sha(manifest)
    if ident in state['models']:
        if state['models'][ident]['manifest_sha256'] != digest:
            raise ValueError('model_id already registered with different bytes')
        return state['models'][ident]
    dest = root/'models'/safe_id(ident)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(manifest.parent, dest)
    copied = dest/manifest.name
    load_bundle(copied)
    entry = dict(manifest=str(copied.resolve()), manifest_sha256=digest, model_sha256=record['model_sha256'],
                 parent_model_id=record.get('parent_model_id'), numerical_convergence=model.get('converged', False),
                 data_role=record.get('data_role', 'frozen previously examined development reference'),
                 registered_at=now(), automatic_activation=False, control_permission=False)
    state['models'][ident] = entry
    if state['frozen_reference_model_id'] is None and ident == 'G2-FROZEN-RM01-v1':
        state['frozen_reference_model_id'] = ident
        state['selected_for_next_session'] = ident
    save(root, state, dict(action='register', model_id=ident, activated=False))
    return entry


def select(root, ident, *, confirm, reason, action='activate'):
    if not confirm or not reason:
        raise ValueError('explicit --confirm and a recorded reason are required')
    state = load(root)
    entry = state['models'][ident]
    if sha(entry['manifest']) != entry['manifest_sha256']:
        raise ValueError('registered manifest changed')
    manifest, model, _ = load_bundle(entry['manifest'])
    if state['frozen_reference_model_id'] not in state['models']:
        raise ValueError('register the original frozen reference before selecting a candidate')
    rollback = manifest.get('rollback_model_id') or manifest.get('parent_model_id')
    if rollback is not None and rollback not in state['models']:
        raise ValueError('rollback model must be retained before candidate selection')
    if not model.get('converged'):
        raise ValueError('nonconverged numerical diagnostic cannot be selected')
    before = state['selected_for_next_session']
    state.update(previous_selection=before, selected_for_next_session=ident)
    save(root, state, dict(action=action, before=before, after=ident, reason=reason,
                           effective='next_new_observation_session', control_permission=False))
    return dict(selected_for_next_session=ident, previous_selection=before, existing_sessions_unchanged=True,
                frozen_reference_model_id=state['frozen_reference_model_id'], control_permission=False)


def open_session(root, session_id):
    safe_id(session_id)
    state = load(root)
    if session_id in state['sessions']:
        return state['sessions'][session_id]  # An existing session cannot be hot-switched.
    ident = state['selected_for_next_session']
    if ident is None:
        raise ValueError('no explicitly selected version')
    entry = state['models'][ident]
    if sha(entry['manifest']) != entry['manifest_sha256']:
        raise ValueError('session model manifest changed')
    load_bundle(entry['manifest'])
    pin = dict(session_id=session_id, model_id=ident, manifest_sha256=entry['manifest_sha256'],
               manifest=entry['manifest'], model_sha256=entry['model_sha256'], opened_at=now(), control_permission=False)
    pin.update(device_id=state['device_id'], thermal_config_id=state['thermal_config_id'],
               state_initialization='new observer for this device/model/session; never copy another thermal state')
    state['sessions'][session_id] = pin
    save(root, state, dict(action='open_session', **pin))
    return pin
