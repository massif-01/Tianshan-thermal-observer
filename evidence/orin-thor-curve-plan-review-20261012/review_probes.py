"""Offline plan-review probes; no production edits or real connections.

The monkeypatches below emulate incomplete migration strategies, not the full
proposed schema2 implementation. All original records remain byte unchanged.
"""
import collections
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from tto.config import load_config, merge
from tto.dataset import replay
from tto.demo import fan_packet, packet, temp_packet
from tto.engine import Engine
from tto.quality import Quality, fan_data, temp_data
from tto.recorded import recorded_results

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
REAL = ROOT / 'evidence/device-install-20261012/runs/run-2026-10-12T113943.639076_0000-7113c960'
LEGACY = ROOT / 'evidence/r3b-v1/before/reproduction/normal/run-2026-10-10T191150.922292_0000-18c4564d'


def hashes(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()}


def main():
    before = {str(path.relative_to(ROOT)): hashes(path) for path in (REAL, LEGACY)}
    c = load_config(environ={})
    c['orin'].update(source_sample_interval_ms=1000, source_interval_evidence='synthetic_review')
    payload = packet(1, 40)
    payload['platform'] = dict(schema_version=1, family='jetson_orin', soc='tegra234', identification_source='device_tree_compatible', gpu_backend='tegrastats')
    q = Quality(c)
    initial = q.accept(dict(mono_s=0, payload=payload, connection_epoch=1))
    changed = copy.deepcopy(payload)
    changed['telemetry_meta']['sample_age_ms'] = 200
    changed['platform'].update(family='jetson_thor', soc='tegra264', gpu_backend='nvml')
    duplicate = q.accept(dict(mono_s=.2, payload=changed, connection_epoch=1))
    assert initial['accepted'] and duplicate['reason'] == 'duplicate' and not q.quarantined

    raw = [json.loads(line) for line in (REAL / 'observations-0001.jsonl').read_text().splitlines()]
    temps = [temp_data(r['payload']) for r in raw if r['kind'] == 'temp']
    fans = [fan_data(r['payload']) for r in raw if r['kind'] == 'fan']
    old_normal = Engine.normal

    def widened(self, t):
        if self.fan and self.fan['data'].get('mode') == 'curve':
            self.fan['data']['mode'] = 'auto'
            try:
                return old_normal(self, t)
            finally:
                self.fan['data']['mode'] = 'curve'
        return old_normal(self, t)

    with patch.object(Engine, 'normal', widened):
        mode_only = replay(REAL)
    assert sum(r['normal_auto'] for r in mode_only['rows']) == 0

    # Independent synthetic, valid control-temperature fixture: widening the
    # old bool also widens the AUTO-only firmware diagnostic downstream.
    with patch.object(Engine, 'normal', widened):
        e = Engine(c)
        f = fan_packet()
        f['data']['fans'][0]['mode'] = 'curve'
        e.process(dict(kind='fan', mono_s=0, payload=f, ref='synthetic/fan'))
        e.process(dict(kind='temp', mono_s=0, payload=temp_packet(), ref='synthetic/temp'))
        p = e.process(dict(kind='orin', mono_s=0, payload=packet(1, 40), ref='synthetic/tj', observer_run_id='synthetic', connection_epoch=1))['prediction']
    assert p['origin']['normal_auto'] is True and p['firmware_45s_diagnostic'] == 47.5

    original = replay(LEGACY)
    original_rec, _ = recorded_results(LEGACY, original['manifest'], original['quality_eligibility'])
    old_process = Engine.process

    def profile_boundary(self, r):
        # Emulate a new initial profile-resolution boundary without historical
        # schema dispatch. Segment identity changes even with unchanged files.
        if r['kind'] == 'orin' and not getattr(self, '_review_profile_set', False):
            self._review_profile_set = True
            self.invalidate('review_profile_resolved')
        return old_process(self, r)

    with patch.object(Engine, 'process', profile_boundary):
        shifted = replay(LEGACY)
    shifted_rec, _ = recorded_results(LEGACY, shifted['manifest'], shifted['quality_eligibility'])
    assert original_rec['scored_method_horizon_records'] == 510
    assert shifted_rec['scored_method_horizon_records'] == 0 and shifted_rec['issues']

    legacy_base = copy.deepcopy(c)
    del legacy_base['features']['power_current_rails']
    try:
        merge(legacy_base, c)
    except ValueError as error:
        migration_error = str(error)
    else:
        raise AssertionError('probe expected closed-config failure')
    after = {str(path.relative_to(ROOT)): hashes(path) for path in (REAL, LEGACY)}
    assert before == after
    result = {
        'scope': '离线方案审查；负向模拟不完整改法，不是新合同完整实现',
        'real_connections': False,
        'original_records_sha256_unchanged': before == after,
        'platform_only_change_same_seq': {'reason': duplicate['reason'], 'quarantined': q.quarantined},
        'real_control_state': {
            'fan_modes': dict(collections.Counter(f['mode'] for f in fans)),
            'temp_valid': dict(collections.Counter(str(d['normalized_valid']) for d in temps)),
            'active_sources': dict(collections.Counter(d['active_source'] for d in temps)),
            'timestamps_ms': sorted({d['timestamp_ms'] for d in temps}),
            'mode_only_normal_origins': sum(r['normal_auto'] for r in mode_only['rows']),
        },
        'synthetic_widened_bool': {'actual_mode': 'curve', 'old_normal_auto_relabelled': p['origin']['normal_auto'], 'auto_firmware_diagnostic_emitted': p['firmware_45s_diagnostic']},
        'synthetic_legacy_replay_boundary': {
            'original_valid_scores': original_rec['scored_method_horizon_records'],
            'after_incomplete_migration_valid_scores': shifted_rec['scored_method_horizon_records'],
            'issues': dict(collections.Counter(x['reason'] for x in shifted_rec['issues'])),
            'logs_missing': shifted_rec['missing_logs'],
        },
        'remove_config_key_without_migration': migration_error,
        'proposed_profile_counts': {'orin_auto': 54, 'orin_curve': 53, 'thor_auto': 51, 'thor_curve': 50},
        'original_record_sha256': before,
    }
    (OUTPUT / 'review-probes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'original_record_sha256'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
