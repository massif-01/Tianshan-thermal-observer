"""Frozen G2 augmented-state KF and identical-policy conditional-hold reference. No IO/control."""
import copy
from functools import lru_cache
import numpy as np
from scipy.linalg import expm


class ThermalObserver:
    def __init__(self, spec, method='AUGMENTED-KF'):
        assert method in ['AUGMENTED-KF', 'CONDITIONAL-HOLD']
        self.spec, self.method = copy.deepcopy(spec), method
        self.x = self.P = self.last = None
        self.updates = self.starts = 0
        self.last_ref = None
        self.projected = False
        self.innovation = None
        self.last_stop = None

    def matrices(self, u):
        p = self.spec['dynamic']
        d = p['d0'] + p['d1'] * u[2]
        A = np.array([[-p['a'], p['a'], 0], [p['c'], -p['c'] - d, d], [0, 0, 0]], float)
        b = np.array([p['b_g'] * u[0] + p['b_c'] * u[1], 0, 0], float)
        return A, b

    def _input(self, frame, t):
        m = frame['measurement']
        fan, power = m['last_successful_pwm'], m['power']
        u = [*(power['rails_W'] if power else [0., 0.]), fan['value_percent'] / 100 if fan else 0.5]
        assumptions = []
        for kind, obj, method in [('PWM', fan, 'last_successful_hold' if fan else 'startup_half_scale'), ('rails', power, 'last_observed_hold')]:
            known = bool(obj and obj['raw_valid'] and t < obj['valid_until_mono_s'])
            if not known:
                assumptions.append(dict(input=kind, method=method, age_s=t - (obj['observed_mono_s'] if obj else frame['stream_started_mono_s']),
                                        last_real_ref=obj['source_ref'] if obj else None,
                                        real_expiry_mono_s=obj['valid_until_mono_s'] if obj else None,
                                        range=[0., 1.] if kind == 'PWM' else None,
                                        renewed_raw_measurement=False))
        return np.array(u, float), assumptions

    def _supported(self, frame, t):
        policy = self.spec['input_policy']
        limits = [('last_successful_pwm', policy['fan_max_actual_age_s']), ('tj', policy['power_or_TJ_max_actual_age_s']),
                  ('power', policy['power_or_TJ_max_actual_age_s']), ('control_context', policy['control_context_max_actual_age_s'])]
        reasons = []
        for name, limit in limits:
            obj = frame['measurement'][name]
            age = t - (obj['observed_mono_s'] if obj else frame['stream_started_mono_s'])
            if age > limit:
                reasons.append('long_missing_' + name)
        return reasons

    @lru_cache(maxsize=4096)
    def _transition(self, dt, pwm):
        A, _ = self.matrices([0., 0., pwm])
        Q = np.diag(np.square(self.spec['numerical']['process_std_C_per_sqrt_s']))
        V = np.block([[A, Q], [np.zeros((3, 3)), -A.T]])
        e = expm(V * dt)
        F = e[:3, :3]
        return F, e[:3, 3:] @ F.T

    def mean_step(self, state, u, dt):
        A, b = self.matrices(u)
        M = np.zeros((4, 4))
        M[:3, :3], M[:3, 3] = A, b
        return (expm(M * dt) @ np.r_[state, 1.])[:3]

    def _advance(self, frame, end):
        start = self.last['t']
        edges = [start, end]
        for obj in self.last['measurement'].values():
            if obj and start < obj['valid_until_mono_s'] < end:
                edges.append(obj['valid_until_mono_s'])
        edges = sorted(set(edges))
        for left, right in zip(edges, edges[1:]):
            dt = right - left
            if dt <= 0:
                continue
            u, assumptions = self._input(self.last, (left + right) / 2)
            before = self.x.copy()
            F, Q = self._transition(dt, u[2])
            self.x = self.mean_step(before, u, dt)
            self.P = F @ self.P @ F.T + Q
            for a in assumptions:
                if a['input'] == 'PWM':
                    lo, hi = u.copy(), u.copy()
                    lo[2], hi[2] = 0., 1.
                    g = self.mean_step(before, hi, dt) - self.mean_step(before, lo, dt)
                    self.P += np.outer(g, g) / 12
                else:
                    b = self.spec['dynamic']
                    scale = self.spec['numerical']['power_unknown_relative_std'] * (b['b_g'] * abs(u[0]) + b['b_c'] * abs(u[1]))
                    self.P[0, 0] += (scale * dt) ** 2
            self.P = (self.P + self.P.T) / 2

    def _initialize(self, frame):
        tj = frame['measurement']['tj']
        prior = self.spec['prior']
        vE, vo = prior['E_std_C'] ** 2, prior['Ts_minus_E_std_C'] ** 2
        self.x = np.array([tj['value_C'], prior['E_mean_C'] + prior['Ts_minus_E_mean_C'], prior['E_mean_C']])
        self.P = np.array([[self.spec['numerical']['TJ_noise_std_C'] ** 2, 0., 0.], [0., vE + vo, vE], [0., vE, vE]])
        self.updates, self.starts = 1, self.starts + 1
        self.last_ref, self.projected = tj['source_ref'], False

    def step(self, frame):
        assert self.last is None or frame['t'] >= self.last['t']
        if self.x is not None and self.last is not None:
            # A fresh recovery response does not retroactively fill a silent interval.
            elapsed_stop = self._supported(self.last, frame['t'])
            if elapsed_stop:
                self.x = self.P = None
                self.last_stop = 'input_support_elapsed_between_events:' + ','.join(elapsed_stop)
            else:
                self._advance(frame, frame['t'])
        if frame['source_reset']:
            self.x = self.P = None
            self.last_stop = frame['reset_reason']
        stop = self._supported(frame, frame['t'])
        if stop:
            self.x = self.P = None
            self.last_stop = ','.join(stop)
        tj, power = frame['measurement']['tj'], frame['measurement']['power']
        if self.x is None and not stop and tj and tj['raw_valid'] and power and power['raw_valid']:
            self._initialize(frame)
        if self.x is not None and frame['new_TJ'] and tj['source_ref'] != self.last_ref:
            R = self.spec['numerical']['TJ_noise_std_C'] ** 2
            self.innovation = float(tj['value_C'] - self.x[0])
            if self.method == 'AUGMENTED-KF':
                K = self.P[:, 0] / (self.P[0, 0] + R)
                self.x += K * self.innovation
                I = np.eye(3)
                I[:, 0] -= K
                self.P = I @ self.P @ I.T + R * np.outer(K, K)
            else:
                self.x[0] = tj['value_C']
                self.P[0, :] = self.P[:, 0] = 0.
                self.P[0, 0] = R
            self.P = (self.P + self.P.T) / 2
            self.updates += 1
            self.last_ref = tj['source_ref']
            self.projected = False
            self.unprojected = self.x.tolist()
            for k, bounds in [(1, self.spec['prior']['Ts_bounds_C']), (2, self.spec['prior']['E_bounds_C'])]:
                clipped = float(np.clip(self.x[k], *bounds))
                if clipped != self.x[k]:
                    self.x[k], self.projected = clipped, True
                    self.P[k, k] = max(self.P[k, k], 4.)
        u, assumptions = self._input(frame, frame['t'])
        reasons, phase = [], 'uninitialized'
        s = frame['safety']
        hard = s['guard'] is True or s['fault'] is True or s['mode'] not in [None, 'auto'] or s['enabled'] is False or s['manual_mode'] is True
        if stop:
            phase, reasons = 'unavailable', stop
        elif self.x is None:
            reasons = ['waiting_for_current_source_valid_TJ_and_rails', self.last_stop]
        elif hard:
            phase, reasons = 'unavailable', ['explicit_guard_fault_mode_or_manual_state']
        else:
            std = np.sqrt(np.maximum(np.diag(self.P), 0))
            if not np.isfinite(self.x).all() or not np.isfinite(self.P).all() or np.any(std > self.spec['phase_gates']['max_output_std_C']):
                phase, reasons = 'unavailable', ['outside_internal_uncertainty_support']
            else:
                warm = self.updates >= self.spec['phase_gates']['min_TJ_updates_for_tracking']
                confident = bool(np.all(std <= self.spec['phase_gates']['max_tracking_std_C']))
                current = bool(tj and tj['raw_valid'] and power and power['raw_valid'])
                if warm and confident and current and s['confirmed_normal_now'] and not assumptions and not self.projected:
                    phase = 'tracking'
                elif not warm or not confident:
                    phase = 'provisional'
                    reasons.append('cold_or_prior_uncertainty_not_resolved')
                else:
                    phase = 'degraded'
                if not s['confirmed_normal_now']:
                    reasons.append('observed_abnormal_or_unknown_control_context')
                if assumptions:
                    reasons.append('conditional_input_assumption')
                if self.projected:
                    reasons.append('posterior_boundary_projection')
                    phase = 'degraded'
        available = phase in ['provisional', 'tracking', 'degraded']
        observer = dict(method=self.method, phase=phase, available=available, reasons=[r for r in reasons if r],
                        Tf_C=float(self.x[0]) if available else None, Ts_C=float(self.x[1]) if available else None,
                        E_C=float(self.x[2]) if available else None, E_source='L/S training prior plus past TJ sequential inference' if self.method == 'AUGMENTED-KF' else 'L/S training prior, unchanged',
                        TJ_updates_since_cold_start=self.updates if self.x is not None else 0, cold_starts=self.starts,
                        unknown_input_assumptions=assumptions, conditional_inputs_rails_W_PWM=u.tolist() if available else None,
                        uncertainty=dict(meaning=self.spec['numerical']['uncertainty'],
                                         covariance_C2=self.P.tolist() if available else None,
                                         marginal_std_C=np.sqrt(np.maximum(np.diag(self.P), 0)).tolist() if available else None,
                                         includes_theta_error=False, calibrated=False),
                        latest_innovation_C=self.innovation, boundary_projected=self.projected,
                        unprojected_state_C=getattr(self, 'unprojected', None) if self.projected else None,
                        dynamic_parameter_updates=0, external_temperature_used=False, is_measured_Ts=False,
                        instruction='conditional research state; finite or tracking is not field permission')
        record = dict(schema='TTO-STATE-READONLY-R2-v1', identity=copy.deepcopy(frame['identity']),
                      generated_at_mono_s=frame['t'], generated_clock_domain='offline_virtual_observer_clock',
                      generated_at_utc=frame['utc'], observed_through_ref=frame['ref'], observed_through_utc=frame['utc'],
                      measurement=copy.deepcopy(frame['measurement']), observer=observer, safety=copy.deepcopy(s),
                      permission=dict(local_demo=True, formal_field_authorized=False, device_actions=False))
        self.last = frame
        return record
