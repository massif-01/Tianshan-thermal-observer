"""Pure read-only forecast facade; all G2 propagation uses the unchanged observer."""
import copy
import hashlib
import json
import math
from pathlib import Path

from .frozen.observer import ThermalObserver

HORIZONS = (15, 45, 90)
TIME_CONTRACT = 'TTO-RECEIVE-ANCHOR-v1'


def finite(x):
    return type(x) in (float, int) and math.isfinite(x)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Predictor:
    def __init__(self, manifest=None):
        self.path = Path(manifest) if manifest else Path(__file__).resolve().parents[1]/'frozen-model-manifest.json'
        self.manifest = json.loads(self.path.read_text())
        for name, expected in self.manifest['files'].items():
            if digest(self.path.parent/name) != expected:
                raise ValueError('model package SHA mismatch: '+name)
        self.model = json.loads((self.path.parent/self.manifest['model_file']).read_text())
        self.spec = json.loads((self.path.parent/self.manifest['observer_spec_file']).read_text())
        if self.model['dynamic'] != self.spec['dynamic'] or self.model['deployable'] is not False:
            raise ValueError('model/spec dynamics or read-only scope mismatch')
        self.engine = ThermalObserver(self.spec)

    def _trend(self, history, origin):
        # A caller supplies only original quality-engine accepted TJ entries.
        past = [p for p in history if finite(p.get('received_at_mono_s')) and p['received_at_mono_s'] <= origin['received_at_mono_s']]
        if any(b['received_at_mono_s'] < a['received_at_mono_s'] for a, b in zip(past, past[1:])):
            return None, []
        if not past or past[-1].get('ref') != origin['ref']:
            past.append(origin)
        active = []
        for p in past:
            if (p.get('raw_valid') is not True or not finite(p.get('value_C'))
                    or p.get('source_epoch') != origin['source_epoch'] or p.get('clock_domain') != origin['clock_domain']):
                active = []
                continue
            if active and p['received_at_mono_s']-active[-1]['received_at_mono_s'] > 5:
                active = []
            active.append(p)
        chosen = [p for p in active if p['received_at_mono_s'] >= origin['received_at_mono_s']-30]
        if not chosen or origin['received_at_mono_s']-chosen[0]['received_at_mono_s'] < 10:
            return None, []
        first = chosen[0]
        return ((origin['value_C']-first['value_C'])/(origin['received_at_mono_s']-first['received_at_mono_s']),
                [first['ref'], origin['ref']])

    def predict(self, state, *, origin, observed_through, issued_at, identity, publication_mode, history=()):
        """No mutation, sampling, fitting or future inputs. Returns nine ledger items."""
        reasons = []
        required = ('device_id', 'thermal_config_id', 'observer_host_id', 'run_id', 'clock_domain')
        if any(not identity.get(k) for k in required):
            reasons.append('identity_incomplete')
        if publication_mode not in ('live', 'replay'):
            reasons.append('publication_mode_invalid')
        si = state.get('identity', {})
        model_sha = self.manifest['model_sha256']
        spec_sha = self.manifest['observer_spec_sha256']
        if (si.get('run_id') != identity.get('run_id') or si.get('model_sha256') != model_sha
                or si.get('spec_sha256') != spec_sha or si.get('source_epoch') != origin.get('source_epoch')):
            reasons.append('state_model_run_or_epoch_mismatch')
        clocks = [identity.get('clock_domain'), origin.get('clock_domain'), observed_through.get('clock_domain'), issued_at.get('clock_domain')]
        if not clocks[0] or len(set(clocks)) != 1:
            reasons.append('clock_domain_unassociated')
        anchor, cutoff, issue = origin.get('received_at_mono_s'), observed_through.get('mono_s'), issued_at.get('mono_s')
        timing = all(finite(v) for v in (anchor, cutoff, issue))
        if not timing or not finite(state.get('generated_at_mono_s')):
            reasons.append('time_unknown')
        elif abs(cutoff-anchor) > 1e-8 or abs(state['generated_at_mono_s']-cutoff) > 1e-8:
            reasons.append('state_not_at_TJ_origin')
        elif issue < cutoff:
            reasons.append('publication_before_information_arrival')
        if observed_through.get('ref') != state.get('observed_through_ref'):
            reasons.append('observed_through_ref_mismatch')
        tj = state.get('measurement', {}).get('tj') or {}
        if (origin.get('raw_valid') is not True or tj.get('raw_valid') is not True or not finite(origin.get('value_C'))
                or origin.get('ref') != tj.get('source_ref') or origin.get('value_C') != tj.get('value_C')
                or not finite(tj.get('valid_until_mono_s')) or not finite(tj.get('observed_mono_s'))
                or not timing or abs(anchor-tj['observed_mono_s']) > 1e-8 or anchor >= tj['valid_until_mono_s']):
            reasons.append('original_TJ_unavailable_or_unassociated')
        observer = state.get('observer', {})
        phase = observer.get('phase')
        model_reasons = []
        u = observer.get('conditional_inputs_rails_W_PWM')
        x = [origin.get('value_C'), observer.get('Ts_C'), observer.get('E_C')]
        if observer.get('available') is not True or phase not in ('provisional', 'tracking', 'degraded'):
            model_reasons += ['observer_unavailable']+observer.get('reasons', [])
        elif not (all(finite(v) for v in x) and isinstance(u, list) and len(u) == 3 and all(finite(v) for v in u)
                  and u[0] >= 0 and u[1] >= 0 and 0 <= u[2] <= 1):
            model_reasons.append('conditional_state_or_inputs_invalid')
        slope, slope_refs = (self._trend(history, origin) if not reasons else (None, []))
        results = []
        for h in HORIZONS:
            target = anchor+h if finite(anchor) else None
            late = bool(timing and issue >= target)
            for method in ('G2-HOLD', 'B0', 'B1'):
                unavailable = list(reasons)
                if late:
                    unavailable.append('issued_at_or_after_target')
                if method == 'G2-HOLD':
                    unavailable += model_reasons
                if method == 'B1' and slope is None:
                    unavailable.append('past_trend_unavailable')
                value = None
                if not unavailable:
                    if method == 'G2-HOLD':
                        value = float(self.engine.mean_step(x, u, h)[0])
                    elif method == 'B0':
                        value = origin['value_C']
                    else:
                        value = origin['value_C']+h*slope
                    if not finite(value):
                        value = None
                        unavailable.append('nonfinite_prediction')
                fan = state.get('measurement', {}).get('last_successful_pwm') or {}
                metadata = dict(identity, model_id=self.manifest['model_id'], model_sha256=model_sha, observer_spec_sha256=spec_sha)
                key = [metadata, origin.get('ref'), h, method, publication_mode, issued_at]
                prediction_id = hashlib.sha256(json.dumps(key, sort_keys=True, allow_nan=False).encode()).hexdigest()
                results.append(dict(schema='TTO-CAUSAL-PREDICTION-v1', prediction_id=prediction_id, identity=metadata,
                    time_contract=TIME_CONTRACT, origin=copy.deepcopy(origin), observed_through=copy.deepcopy(observed_through),
                    issued_at=copy.deepcopy(issued_at), target_mono_s=target, horizon_s=h,
                    effective_lead_s=target-issue if timing else None, late=late, publication_mode=publication_mode,
                    time_evidence='caller actual monotonic/UTC publication' if publication_mode == 'live' else 'explicit replay clock; never live evidence',
                    method=method, value_C=value, unavailable_reasons=unavailable, origin_phase=phase,
                    condition=dict(kind='constant current independent rails and declared PWM', rails_W=u[:2], pwm_fraction=u[2],
                                   PWM_is_current_raw_measurement=bool(fan.get('raw_valid') and finite(fan.get('valid_until_mono_s')) and timing and anchor < fan['valid_until_mono_s']),
                                   assumptions=copy.deepcopy(observer.get('unknown_input_assumptions', []))) if method == 'G2-HOLD' and isinstance(u, list) and len(u) == 3 else None,
                    state_used=dict(current_TJ_C=x[0], Ts_C=x[1], E_C=x[2]) if method == 'G2-HOLD' else None,
                    history_refs=slope_refs if method == 'B1' else [], original_safety=copy.deepcopy(state.get('safety', {})),
                    dynamic_parameter_updates=0, external_temperature_used=False, is_measured_Ts=False, control_permission=False))
        return results
