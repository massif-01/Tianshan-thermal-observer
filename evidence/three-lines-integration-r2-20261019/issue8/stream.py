"""Read-only projection of saved events through the manifest-matching native processor."""
from pathlib import Path
import copy, hashlib, json, sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
from tto.config import load_config, merge, validate
from tto.engine import engine_for


def load_lines(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s]


def jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')


def visible_rows(rows, windows, first_mono):
    """Remove the WHOLE hidden fan payload. Nothing from it reaches native quality or observer."""
    result, hidden = [], []
    for r in rows:
        offset = r['mono_s'] - first_mono
        if r['kind'] == 'fan' and any(lo <= offset < hi for lo, hi in windows):
            hidden.append(r['ref'])
            r = {k: v for k, v in r.items() if k not in ['payload', 'error', 'response_body', 'reason']}
            r.update(payload=None, error='OFFLINE_MASK_WHOLE_FAN_RESPONSE')
        result.append(copy.deepcopy(r))
    return result, hidden


class SavedStream:
    def __init__(self, manifest, spec):
        self.manifest, self.spec = manifest, spec
        c = load_config(environ={})
        saved = copy.deepcopy(manifest['config'])
        for section in ['orin', 'tianshan']:
            saved[section]['headers_file'] = saved[section]['ca_file'] = None
        merge(c, saved)
        validate(c)
        self.engine = engine_for(c, record_schema=2)
        self.tj = self.power = self.fan = self.temp = None
        self.source_identity = None
        self.epoch = 0
        self.start = self.context = self.context_since = None
        self.context_supported_until = None
        self.quality = []

    def feed(self, raw):
        t = raw['mono_s']
        if self.start is None:
            self.start = t
        e = self.engine
        previous_gap = e.q.counts['boundary_long_gap']
        out = e.process(raw)
        q = out['quality']
        reset = raw['kind'] == 'boundary'
        reason = raw.get('reason') if reset else None
        new = None
        if q:
            self.quality.append(dict(ref=raw['ref'], t=t, quality=q))
            if q.get('lifecycle_violation') or q['reason'] in ['identity_conflict', 'sequence_regression', 'retired_stream', 'invalid_numeric_contract']:
                reset = True
                reason = 'native_source_identity_or_numeric_boundary'
            if q['accepted']:
                ident = (tuple(q['key'][:2]), raw.get('connection_epoch'), repr(e.q.lifecycle_settings), e.q.lifecycle_uuid)
                if self.source_identity is not None and ident != self.source_identity:
                    reset = True
                    reason = 'source_epoch_changed'
                self.source_identity = ident
                s = e.features.history[-1]
                valid = bool(q.get('period_known') and q.get('input_contract') is not None and not e.q.blocked and not e.q.quarantined)
                until = t + (raw['payload']['telemetry_meta']['freshness_timeout_ms'] - q['age_lower_bound_ms']) / 1000
                new = dict(value_C=s['values']['tj'], observed_mono_s=t, observed_utc=raw['received_at_utc'], source_ref=raw['ref'],
                           source_age_lower_bound_ms=q['age_lower_bound_ms'], valid_until_mono_s=until, native_source_valid=valid)
                self.tj = new
                self.power = dict(rails_W=[s['values']['vdd_gpu'], s['values']['vdd_cpu_soc_mss']],
                                  names=['vdd_gpu', 'vdd_cpu_soc_mss'], observed_mono_s=t, source_ref=raw['ref'],
                                  valid_until_mono_s=until, native_source_valid=valid)
                assert new['value_C'] == raw['payload']['temperature']['tj']
                assert all(abs(v - raw['payload']['power'][n]['current'] / 1000) < 1e-10 for n, v in zip(self.power['names'], self.power['rails_W']))
        if e.q.counts['boundary_long_gap'] > previous_gap:
            reset, reason = True, 'native_source_long_gap_boundary'
        if reset:
            self.epoch += 1
            if new is None:
                self.tj = self.power = None
        if e.fan and e.fan['ref'] == raw['ref']:
            self.fan = dict(value_percent=e.fan['data']['successful_duty'], observed_mono_s=e.fan['t'],
                            observed_utc=raw['received_at_utc'], source_ref=raw['ref'],
                            valid_until_mono_s=e.fan['t'] + self.spec['input_policy']['fan_raw_TTL_s'],
                            last_observed_flags=copy.deepcopy(e.fan['data']))
        if e.temp and e.temp['ref'] == raw['ref']:
            self.temp = dict(observed_mono_s=e.temp['t'], observed_utc=raw['received_at_utc'], source_ref=raw['ref'],
                             valid_until_mono_s=e.temp['t'] + self.spec['input_policy']['temp_raw_TTL_s'],
                             last_observed_flags=copy.deepcopy(e.temp['data']))
        fan, temp, tj, power = [copy.deepcopy(x) for x in [self.fan, self.temp, self.tj, self.power]]
        for obj, current in [(fan, bool(e.fan)), (temp, bool(e.temp)), (tj, not e.q.blocked and not e.q.quarantined), (power, not e.q.blocked and not e.q.quarantined)]:
            if obj is not None:
                obj['age_s'] = t - obj['observed_mono_s']
                obj['raw_valid'] = bool(current and t < obj['valid_until_mono_s'] and obj.get('native_source_valid', True))
        f = fan['last_observed_flags'] if fan and fan['raw_valid'] else {}
        v = temp['last_observed_flags'] if temp and temp['raw_valid'] else {}
        signature = (f.get('mode'), f.get('enabled'), v.get('manual_mode'), v.get('active_source'), v.get('bound_variable'))
        complete_context = all(x is not None for x in signature)
        changed = complete_context and self.context is not None and signature != self.context
        if complete_context:
            if self.context != signature or self.context_since is None or (
                self.context_supported_until is not None and t > self.context_supported_until
            ):
                self.context_since = t
            self.context = signature
            self.context_supported_until = min(fan['valid_until_mono_s'],temp['valid_until_mono_s'])
        else:
            # Fresh recovery only proves the current observation, never the missing interval.
            self.context_since = self.context_supported_until = None
        safety = dict(guard=f.get('guard_active'), fault=f.get('fault'), mode=f.get('mode'), enabled=f.get('enabled'),
                      temp_stale=f.get('temp_stale'), manual_mode=v.get('manual_mode'), normalized_valid=v.get('normalized_valid'),
                      active_source=v.get('active_source'), binding=v.get('bound_variable'),
                      fan_fresh=bool(fan and fan['raw_valid']), binding_fresh=bool(temp and temp['raw_valid']),
                      context_changed_this_event=bool(changed),
                      context_stable_s=t - self.context_since if complete_context and self.context_since is not None else None,
                      unknown_is_normal=False)
        expected = self.spec['phase_gates']
        safety['confirmed_normal_now'] = bool(safety['fan_fresh'] and safety['binding_fresh'] and
            safety['guard'] is False and safety['fault'] is False and safety['mode'] == expected['expected_mode'] and safety['enabled'] is True and
            safety['temp_stale'] is False and safety['manual_mode'] is False and safety['normalized_valid'] is True and
            safety['active_source'] == 'variable' and safety['binding'] == expected['expected_binding'] and
            not changed and safety['context_stable_s'] >= expected['normal_context_stable_s'])
        identity = dict(run_id=self.manifest['observer_run_id'], config_sha256=self.manifest['config_sha256'],
                        firmware_identity=self.manifest.get('firmware_identity'),
                        collector_source_sha256=self.manifest['source_identity']['sha256'],
                        model_sha256=self.spec['model_sha256'], spec_sha256=hashlib.sha256((ROOT / 'observer-spec.json').read_bytes()).hexdigest(),
                        source_epoch=self.epoch)
        return dict(t=t, utc=raw['received_at_utc'], ref=raw['ref'], stream_started_mono_s=self.start, identity=identity,
                    source_reset=bool(reset), reset_reason=reason, new_TJ=bool(new and new['native_source_valid']),
                    measurement=dict(tj=tj, power=power, last_successful_pwm=fan, control_context=temp), safety=safety)


def make_frames(rows, manifest, spec):
    adapter = SavedStream(manifest, spec)
    return [adapter.feed(r) for r in rows], adapter.quality
