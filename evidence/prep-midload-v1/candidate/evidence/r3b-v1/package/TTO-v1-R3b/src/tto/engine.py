"""Ordered causal processor. Outputs are immutable and append-only."""
from collections import Counter
from .features import Features, TJ_COLUMNS
from .model import HORIZONS, infer
from .quality import Quality, fan_data, temp_data
from .util import finite


class Engine:
    def __init__(self, config, model=None):
        self.c = config
        period = config['orin']['source_sample_interval_ms']
        self.features = Features(period / 1000 if period else None)
        self.q = Quality(config)
        self.model = model
        self.fan = None
        self.temp = None
        self.pending = []
        self.pred_seq = 0
        self.last_prediction = None
        self.active_segment = None
        self.context = None
        self.last_normal = None
        self.has_cooled = False
        self.counts = Counter()
        self.origins = []  # used only by replay with retain_origins=True
        self.retain_origins = False

    @property
    def tolerance(self):
        p = self.c['orin']['source_sample_interval_ms']
        return min(5, max(2, p / 1000)) if p else 2

    def invalidate(self, reason):
        self.q.boundary(reason)
        self.features.clear()
        self.has_cooled = False
        self.last_prediction = None
        out = [dict(prediction_id=p['id'], model_sha256=p['model_sha256'], horizon_s=h, status='cross_segment', reason=reason) for p in self.pending for h in p['waiting']]
        self.pending.clear()
        return out

    def expire(self, now):
        out = []
        for p in self.pending:
            for h in list(p['waiting']):
                if now > p['origin']['t'] + h + self.tolerance:
                    out.append(dict(prediction_id=p['id'], model_sha256=p['model_sha256'], horizon_s=h, status='no_future_label', reason='deadline'))
                    p['waiting'].remove(h)
        self.pending = [p for p in self.pending if p['waiting']]
        return out

    def process(self, r):
        scores = self.expire(r['mono_s'])
        result = {'quality': None, 'prediction': None, 'scores': scores}
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
        if q['reason'] in ('identity_conflict', 'sequence_regression'):
            q['invalidated_segment'] = previous_active
        if self.q.segment != previous_segment or self.active_segment != self.q.segment:
            result['scores'] += self.invalidate('input_boundary')
            self.active_segment = self.q.segment
            q['segment'] = self.q.segment
        if not q['accepted']:
            return result
        normal = self.normal(t)
        if self.last_normal is not None and normal != self.last_normal:
            result['scores'] += self.invalidate('normal_scope_change')
            q['segment'] = self.q.segment
            self.active_segment = self.q.segment
        self.last_normal = normal
        v = dict(q['values'])
        aux_refs = []
        if self.fan and t - self.fan['t'] <= self.c['features']['fan_max_age_s']:
            f = self.fan['data']
            v['duty'] = f['successful_duty'] if normal else None
            v['gain'] = f.get('controller_gain') if normal and finite(f.get('controller_gain')) else None
            aux_refs.append(self.fan['ref'])
        if self.temp:
            aux_refs.append(self.temp['ref'])
        sample = {'t': t, 'values': v, 'ref': r['ref'], 'aux_refs': aux_refs, 'key': q['key'], 'segment': q['segment'], 'normal_auto': normal}
        # First causal label at or after each target, never nearest neighbour before it.
        for p in self.pending:
            for h in list(p['waiting']):
                target = p['origin']['t'] + h
                if target <= t <= target + self.tolerance:
                    status = 'scored' if normal and p['origin']['normal_auto'] else 'abnormal_scope'
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
            elif not q['period_known']:
                reasons[name] = 'source_period_unknown'
            elif abs(self.model['source_period_s'] - self.features.period) > 1e-9:
                reasons[name] = 'source_period_mismatch'
            elif not normal or not all(s['normal_auto'] for s in self.features.history):
                reasons[name] = 'normal_auto_unconfirmed'
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
        origin = {'t': t, 'available_at': t, 'run_id': r['observer_run_id'], 'episode': r.get('episode', r['observer_run_id']), 'segment': q['segment'], 'key': q['key'], 'ref': r['ref'], 'raw_refs': refs, 'features': features, 'normal_auto': normal, 'support_start': min(s['t'] for s in self.features.history), 'support_end': t + 90 + self.tolerance, 'history_ready': all(finite(features.get(c)) for c in TJ_COLUMNS), 'phase': phase, 'high_temperature': v['tj'] >= 60}
        if self.fan:
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

    def control_context(self):
        f = self.fan['data'] if self.fan else {}
        d = self.temp['data'] if self.temp else {}
        return (f.get('mode'), f.get('enabled'), f.get('fault'), f.get('guard_active'), f.get('temp_stale'), f.get('duty_valid'), d.get('active_source'), d.get('bound_variable'), d.get('preferred_source'), d.get('manual_mode'), d.get('normalized_valid'))

    def normal(self, t):
        if not self.fan or not self.temp or t < self.fan['t'] or t < self.temp['t']:
            return False
        f, d = self.fan['data'], self.temp['data']
        return (t - self.fan['t'] <= 2.5 and t - self.temp['t'] <= max(7.5, self.c['tianshan']['temp_poll_interval_s'] + self.c['network']['request_timeout_s']) and f.get('mode') == 'auto' and f.get('enabled') is True and f.get('fault') is False and f.get('guard_active') is False and f.get('temp_stale') is False and f.get('successful_duty') is not None and d.get('manual_mode') is False and d.get('normalized_valid') is True and d.get('active_source') in ('agx', 'variable') and bool(d.get('bound_variable') or d.get('active_source') == 'agx'))
