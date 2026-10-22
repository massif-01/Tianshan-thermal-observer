"""Schema2 causal processing. Legacy Engine remains the schema1 replay path."""
from .engine import Engine
from .features import Features, TJ_COLUMNS
from .platform_quality import PlatformQuality
from .profiles import CONTRACT, PROFILES, profile_id, compatible_contract
from .model import HORIZONS, infer
from .quality import fan_data, temp_data
from .util import digest, finite


class PlatformEngine(Engine):
    def __init__(self, config, model=None):
        super().__init__(config, model)
        self.q = PlatformQuality(config)
        self.c = self.q.c
        self.features.independent_gpu = True
        self.contract = None
        self.profile_id = None
        self.first_profile = None
        self.known_contracts = []
        self.known_scopes = set()
        self.known_uuid = None
        self.mixed_profiles = False
        self.input_conflicts = set()

    def update_profile(self, q, record, result):
        current = q['input_contract']
        if q['source_period']['reason'] == 'configured_source_period_conflict':
            self.input_conflicts.add('configured_source_period_conflict')
        if q.get('lifecycle_violation'):
            self.mixed_profiles = True
        scope = self.control_qualification(record['mono_s'])[0]
        # Retain the last evidenced setting as trace. Quality separately flags
        # a changed/missing fixed wire setting; GPU methods still need current
        # valid cadence and samples, so this does not restore their eligibility.
        if current and self.contract and compatible_contract(current, self.contract, False):
            current = dict(current)
            if current['gpu_period_ms'] is None:
                current['gpu_period_ms'] = self.contract['gpu_period_ms']
                current['gpu_timeout_ms'] = self.contract['gpu_timeout_ms']
        incompatible = self.contract is not None and current is not None and not compatible_contract(self.contract, current, False)
        period_change = bool(current and self.contract and current['gpu_period_ms'] is not None and self.contract['gpu_period_ms'] is not None and current['gpu_period_ms'] != self.contract['gpu_period_ms'])
        uuid = q['gpu'].get('device_uuid') if q['gpu']['contract_valid'] else None
        uuid_change = bool(uuid and self.known_uuid and uuid != self.known_uuid)
        if current:
            if any(not compatible_contract(old, current, False) or (old['gpu_period_ms'] and current['gpu_period_ms'] and old['gpu_period_ms'] != current['gpu_period_ms']) for old in self.known_contracts):
                self.mixed_profiles = True
            # Two representative contracts suffice to retain the permanent
            # mixed flag; the complete sequence remains in raw/profile events.
            if len(self.known_contracts) < 2 and (not self.known_contracts or not compatible_contract(self.known_contracts[-1], current)):
                self.known_contracts.append(current)
            if scope in ('auto', 'curve'):
                self.known_scopes.add(scope)
                self.mixed_profiles |= len(self.known_scopes) > 1
        if uuid_change:
            self.mixed_profiles = True
        if uuid:
            self.known_uuid = uuid
        next_id = profile_id(current, scope)
        if incompatible or period_change or uuid_change or (self.contract is None) != (current is None) or next_id != self.profile_id:
            result['scores'] += self.invalidate('input_profile_change')
            self.active_segment = self.q.segment
            q['segment'] = self.q.segment
            result['events'].append({'reason': 'input_profile_change', 'ref': record['ref'], 'run_id': record['observer_run_id'], 'segment': self.q.segment, 'previous_contract': self.contract, 'input_contract': current, 'feature_profile_id': next_id, 'control_scope': scope, 'mixed_profiles': self.mixed_profiles, 'device_uuid': uuid})
        self.contract, self.profile_id = current, next_id
        selected = PROFILES.get(next_id)
        if self.features.profile != selected:
            self.features.profile = selected
        if current and self.first_profile is None:
            self.first_profile = {'schema_version': 2, 'run_id': record['observer_run_id'], 'input_contract': current, 'input_contract_sha256': digest(current), 'identification_ref': record['ref'], 'source_period_evidence': dict(q['source_period'], ref=record['ref']), 'platform_evidence': record['payload']['platform']}
            result['input_profile'] = self.first_profile
        if self.mixed_profiles:
            self.counts['mixed_profiles'] = 1

    def control_qualification(self, t):
        f = self.fan['data'] if self.fan else {}
        d = self.temp['data'] if self.temp else {}
        mode = f.get('mode')
        scope = mode if mode in ('auto', 'curve', 'manual', 'off') else 'unknown'
        checks = {
            'unsupported_control_scope': scope in ('auto', 'curve'),
            'fan_missing_or_stale': bool(self.fan and 0 <= t-self.fan['t'] <= 2.5),
            'temperature_status_missing_or_stale': bool(self.temp and 0 <= t-self.temp['t'] <= max(7.5, self.c['tianshan']['temp_poll_interval_s']+self.c['network']['request_timeout_s'])),
            'fan_not_enabled': f.get('enabled') is True,
            'fan_fault': f.get('fault') is False,
            'guard_active': f.get('guard_active') is False,
            'control_temperature_stale': f.get('temp_stale') is False,
            'successful_duty_unavailable': f.get('successful_duty') is not None,
            'manual_temperature': d.get('manual_mode') is False,
            'control_temperature_invalid': d.get('normalized_valid') is True,
            'active_temperature_source_untrusted': d.get('active_source') in ('agx', 'variable'),
            'temperature_binding_unconfirmed': bool(d.get('bound_variable') or d.get('active_source') == 'agx')}
        reasons = [reason for reason, valid in checks.items() if not valid]
        return scope, not reasons, reasons

    def process(self, r):
        scores = self.expire(r['mono_s'])
        result = {'quality': None, 'prediction': None, 'scores': scores, 'events': [], 'input_profile': None}
        if r.get('preceding_queue_gap'):
            result['scores'] += self.invalidate('queue_drop')
        kind, t = r['kind'], r['mono_s']
        if kind == 'boundary':
            result['scores'] += self.invalidate(r.get('reason', 'connection'))
            self.fan = self.temp = None
            return result
        if kind in ('fan', 'temp'):
            try:
                d = fan_data(r['payload']) if kind == 'fan' else temp_data(r['payload'])
                setattr(self, kind, {'t': t, 'data': d, 'ref': r['ref']})
                context = self.control_context()
                if self.context is not None and context != self.context:
                    result['scores'] += self.invalidate('control_context_change')
                self.context = context
                self.counts[kind + '_ok'] += 1
                if kind == 'fan' and self.contract and d.get('mode') in ('auto', 'curve'):
                    self.known_scopes.add(d['mode'])
                    if len(self.known_scopes) > 1 and not self.mixed_profiles:
                        self.mixed_profiles = True
                        self.counts['mixed_profiles'] = 1
                        result['events'].append({'reason': 'mixed_control_profiles', 'ref': r['ref'], 'run_id': r.get('observer_run_id'), 'control_scope': d['mode'], 'mixed_profiles': True})
            except (ValueError, TypeError, AttributeError):
                setattr(self, kind, None)
                self.context = self.control_context()
                result['scores'] += self.invalidate(kind + '_unavailable')
                self.counts[kind + '_unavailable'] += 1
            return result
        if kind != 'orin':
            return result
        previous_segment = self.q.segment
        previous_active = self.active_segment
        q = self.q.accept(r)
        result['quality'] = q
        if q.get('lifecycle_violation'):
            self.mixed_profiles = True
            self.counts['mixed_profiles'] = 1
        if q['reason'] in ('identity_conflict', 'sequence_regression') or q.get('lifecycle_violation') and q.get('isolation_required'):
            q['invalidated_segment'] = previous_active
        if self.q.segment != previous_segment or self.active_segment != self.q.segment:
            result['scores'] += self.invalidate('input_boundary')
            self.active_segment = self.q.segment
            q['segment'] = self.q.segment
        if not q['accepted']:
            if q['reason'] == 'duplicate' and q.get('gpu'):
                for sample in self.features.history:
                    if sample['key'] == self.q.key and sample.get('gpu_valid_until') is not None:
                        deadline = q['gpu'].get('valid_until')
                        sample['gpu_valid_until'] = min(sample['gpu_valid_until'], deadline if deadline is not None else t)
            return result
        period = self.c['orin']['source_sample_interval_ms']
        period_s = period/1000 if period else None
        if self.features.period != period_s:
            self.features = Features(period_s, independent_gpu=True)
        self.update_profile(q, r, result)
        scope, eligible, scope_reasons = self.control_qualification(t)
        normal = eligible and scope == 'auto'
        if self.last_normal is not None and eligible != self.last_normal:
            result['scores'] += self.invalidate('normal_scope_change')
            q['segment'] = self.q.segment
            self.active_segment = self.q.segment
        self.last_normal = eligible
        v = dict(q['values'])
        aux_refs = []
        if self.fan and t - self.fan['t'] <= self.c['features']['fan_max_age_s']:
            f = self.fan['data']
            v['duty'] = f['successful_duty'] if eligible else None
            v['gain'] = f.get('controller_gain') if normal and finite(f.get('controller_gain')) else None
            aux_refs.append(self.fan['ref'])
        if self.temp:
            aux_refs.append(self.temp['ref'])
        sample = {'t': t, 'values': v, 'ref': r['ref'], 'aux_refs': aux_refs, 'key': q['key'], 'segment': q['segment'], 'normal_auto': normal, 'control_eligible': eligible, 'gpu_valid_until': q['gpu']['valid_until']}
        # First causal label at or after each target, never nearest neighbour before it.
        for p in self.pending:
            for h in list(p['waiting']):
                target = p['origin']['t'] + h
                if target <= t <= target + self.tolerance:
                    status = 'scored' if eligible and p['origin']['control_eligible'] else 'abnormal_scope'
                    row = {'prediction_id': p['id'], 'model_sha256': p['model_sha256'], 'horizon_s': h, 'status': status, 'label_ref': r['ref'], 'label_t': t, 'target_t': target, 'offset_s': t - target, 'truth': v['tj']}
                    if status == 'scored':
                        row['errors'] = {name: values[str(h)] - v['tj'] for name, values in p['values'].items()}
                    result['scores'].append(row)
                    p['waiting'].remove(h)
        self.pending = [p for p in self.pending if p['waiting']]
        self.features.push(sample)
        if self.last_prediction is not None and t - self.last_prediction < 5:
            return result
        self.last_prediction = t
        features, refs = self.features.snapshot()
        methods = {'persist': {str(h): v['tj'] for h in HORIZONS}}
        reasons = {}
        slope = self.features.slope(30)
        if slope is not None:
            methods['trend30'] = {str(h): v['tj'] + slope * h for h in HORIZONS}
        else:
            reasons['trend30'] = 'warming_up_10s'
        outside = {}
        for name in ('ridge_tj', 'ridge_full'):
            if not self.model:
                reasons[name] = 'model_not_loaded'
            elif self.model.get('schema_version') != 2:
                reasons[name] = 'legacy_model_requires_legacy_run'
            elif not self.profile_id:
                reasons[name] = 'platform_or_scope_unconfirmed'
            elif self.model.get('feature_profile_id') != self.profile_id or self.model.get('control_scope') != scope:
                reasons[name] = 'model_profile_scope_mismatch'
            elif not compatible_contract(self.model.get('input_contract'), self.contract, 'gpu_busy' in self.model['methods'][name]['columns']):
                reasons[name] = 'model_input_contract_mismatch'
            elif 'gpu_busy' in self.model['methods'][name]['columns'] and not q['gpu']['sample_interval_ms']:
                reasons[name] = 'gpu_period_unknown'
            elif not q['period_known']:
                reasons[name] = q['source_period']['reason'] or 'source_period_unknown'
            elif abs(self.model['source_period_s'] - self.features.period) > 1e-9:
                reasons[name] = 'source_period_mismatch'
            elif not eligible or not all(s['control_eligible'] for s in self.features.history):
                reasons[name] = 'control_eligibility_unconfirmed'
            else:
                pred, reason, extrapolated = infer(self.model, name, features)
                if pred:
                    methods[name] = pred
                    outside[name] = extrapolated
                else:
                    reasons[name] = reason
        if slope is not None and slope < -0.005:
            self.has_cooled = True
        phase = 'stable' if slope is None or abs(slope) < 0.005 else (('rewarming' if self.has_cooled else 'warming') if slope > 0 else 'cooling')
        actual = next((name for name in ('ridge_full', 'ridge_tj', 'trend30', 'persist') if name in methods), None)
        self.pred_seq += 1
        origin = {'t': t, 'available_at': t, 'run_id': r['observer_run_id'], 'episode': r.get('episode', r['observer_run_id']), 'segment': q['segment'], 'key': q['key'], 'ref': r['ref'], 'raw_refs': refs, 'features': features, 'normal_auto': normal, 'support_start': min(s['t'] for s in self.features.history), 'support_end': t + 90 + self.tolerance, 'history_ready': all(finite(features.get(c)) for c in TJ_COLUMNS), 'phase': phase, 'high_temperature': v['tj'] >= 60, 'feature_schema': 2, 'feature_profile_id': self.profile_id, 'control_scope': scope, 'control_eligible': eligible, 'control_ineligible_reasons': scope_reasons, 'input_contract_sha256': digest(self.contract) if self.contract else None, 'input_contract': self.contract, 'platform_reason': q['platform_reason'], 'gpu_diagnostics': q['gpu'], 'source_period_evidence': q['source_period'], 'input_contract_eligible': q['period_known'] and self.profile_id is not None}
        if self.fan and scope == 'auto':
            origin['fan_diagnostics'] = {k: self.fan['data'].get(k) for k in ('control_temperature', 'guard_temperature', 'cooling_response', 'auto_state')}
            origin['fan_diagnostics'].update(fan_return_age_s=t-self.fan['t'], ref=self.fan['ref'])
        diagnostic = self.fan['data'].get('predicted_temperature') if normal and self.fan else None
        prediction = {'id': f"{r['observer_run_id']}:{self.pred_seq}", 'origin': origin, 'model_sha256': self.model['sha256'] if self.model else None, 'values': methods, 'actual_method': actual, 'fallback': actual != 'ridge_full', 'unavailable': reasons, 'outside_training_range': outside, 'firmware_45s_diagnostic': diagnostic if finite(diagnostic) else None}
        result['prediction'] = prediction
        self.pending.append({'id': prediction['id'], 'model_sha256': prediction['model_sha256'], 'origin': origin, 'values': methods, 'waiting': list(HORIZONS)})
        if len(self.pending) > 20:
            raise ValueError('pending scoring queue exceeded bound')
        if self.retain_origins:
            self.origins.append(prediction)
        self.counts['origins'] += 1
        return result

