"""One frozen activity rule and one future-input conversion. No source acquisition."""
import math
from functools import lru_cache
import numpy as np
from scipy.linalg import expm
from common import ROOT, read, sha


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class Activity:
    def __init__(self, config, variant):
        self.config, self.variant = config, variant
        self.names = config['variants'][variant]
        self.epoch = self.clock = self.last_t = None
        self.state = 'UNKNOWN'
        self.low_since = None
        self.latest = {}
        self.supported_until = None

    def step(self, frame, cutoff=None):
        t = frame.get('arrival_mono_s')
        if not finite(t):
            return self._unknown('arrival_time_unknown')
        if cutoff is not None and t > cutoff:
            raise ValueError('future frame cannot be consumed at cutoff')
        if self.last_t is not None and t < self.last_t:
            raise ValueError('arrival monotonic regression')
        self.last_t = t
        identity = (frame.get('epoch'), frame.get('arrival_clock_id'))
        if identity != (self.epoch, self.clock):
            self.epoch, self.clock = identity
            self.state, self.low_since, self.latest = 'UNKNOWN', None, {}
            self.supported_until = None
        if self.supported_until is not None and t >= self.supported_until:
            self.state, self.low_since = 'UNKNOWN', None
        if frame.get('source_only') or not self.clock or self.epoch is None:
            return self._unknown('no_observed_receiver_clock_or_arrival')
        values, deadlines, new = {}, [], False
        problems = []
        for name in self.names:
            f = frame.get('features', {}).get(name, {})
            v, at, until = (f.get(k) for k in ('value', 'available_at_mono_s', 'valid_until_mono_s'))
            if (not finite(v) or not finite(at) or not finite(until) or at > t or t >= until
                    or f.get('valid') is not True or not f.get('update_id')):
                problems.append(name + ':missing_invalid_expired_or_not_arrived')
                continue
            if v < 0 or (name.endswith('_pct') and v > 100):
                problems.append(name + ':out_of_range')
                continue
            previous = self.latest.get(name)
            if previous and previous['update_id'] == f['update_id']:
                # Reading an old buffer again does not renew its support or become new evidence.
                until = min(until, previous['until'])
                if v != previous['value'] or t >= until:
                    problems.append(name + ':repeated_identity_changed_or_expired')
                    continue
                previous['until'] = until
            else:
                if previous and finite(f.get('source_order')) and finite(previous.get('source_order')) and f['source_order'] <= previous['source_order']:
                    problems.append(name + ':source_order_regression')
                    continue
                new = True
                self.latest[name] = dict(update_id=f['update_id'], value=v, until=until,
                                          source_order=f.get('source_order'))
            values[name] = v
            deadlines.append(until)
        if problems:
            return self._unknown(';'.join(problems))
        lo, hi = self.config['levels']['idle'], self.config['levels']['active']
        scores = {n:(values[n]-lo[n])/(hi[n]-lo[n]) for n in self.names}
        score = max(scores.values())
        before = self.state
        if new:
            if score >= self.config['on']:
                self.state, self.low_since = 'ACTIVE', None
            elif score <= self.config['off']:
                if self.state == 'UNKNOWN':
                    self.state = 'IDLE'
                if self.state == 'ACTIVE':
                    if self.low_since is None:
                        self.low_since = t
                    if t-self.low_since >= self.config['low_confirmation_s']:
                        self.state, self.low_since = 'IDLE', None
            else:
                self.low_since = None
        self.supported_until = min(deadlines)
        return dict(variant=self.variant, state=self.state, score=score, feature_scores=scores,
                    new_evidence=new, transition=before != self.state,
                    supported_until_mono_s=min(deadlines), reason=None,
                    deployable=False, control_permission=False)

    def _unknown(self, reason):
        changed = self.state != 'UNKNOWN'
        self.state, self.low_since = 'UNKNOWN', None
        self.supported_until = None
        return dict(variant=self.variant, state='UNKNOWN', score=None, feature_scores={},
                    new_evidence=False, transition=changed, supported_until_mono_s=None,
                    reason=reason, deployable=False, control_permission=False)


class FutureInputs:
    """Analytic affine propagation with constant or exponentially relaxing rail inputs."""
    def __init__(self, config, dynamic):
        self.config, self.p = config, dynamic

    @lru_cache(maxsize=4096)
    def operator(self, mode, h, pwm):
        p = self.p
        d = p['d0'] + p['d1']*pwm
        m = np.zeros((6,6))
        m[0,0], m[0,1] = -p['a'], p['a']
        m[1,0], m[1,1], m[1,2] = p['c'], -p['c']-d, d
        m[0,3], m[0,4] = p['b_g'], p['b_c']
        if mode == 'IDLE':
            m[3,3] = m[4,4] = -1/self.config['relaxation_tau_s']
            idle = self.config['levels']['idle']
            m[0,5] = p['b_g']*idle['gpu_W'] + p['b_c']*idle['cpu_soc_mss_W']
        return expm(m*h)

    def predict(self, thermal, state, horizon):
        if state == 'UNKNOWN' or not thermal or not thermal.get('available'):
            return None
        if thermal.get('model_sha256') != self.config['immutable']['model_sha256'] or thermal.get('observer_spec_sha256') != self.config['immutable']['observer_spec_sha256']:
            raise ValueError('frozen thermal identity mismatch')
        x = [thermal.get(k) for k in ('current_TJ_C','Ts_C','E_C')]
        u = thermal.get('conditional_inputs_rails_W_PWM')
        if not all(finite(v) for v in x) or not isinstance(u,list) or len(u)!=3 or not all(finite(v) for v in u) or not 0 <= u[2] <= 1:
            raise ValueError('invalid thermal state or original conditional inputs')
        if horizon not in (15,45,90):
            raise ValueError('only frozen 15/45/90-second horizons')
        if state == 'ACTIVE':
            level = self.config['levels']['active']
            powers = [max(u[0],level['gpu_W']), max(u[1],level['cpu_soc_mss_W'])]
        elif state == 'IDLE':
            level = self.config['levels']['idle']
            powers = [u[0]-level['gpu_W'],u[1]-level['cpu_soc_mss_W']]
        elif state == 'HOLD':
            powers = u[:2]
        else:
            raise ValueError('unknown input scenario')
        result = self.operator(state,float(horizon),float(u[2])) @ np.array(x+powers+[1.])
        return float(result[0])

    def scenario(self, thermal, state):
        if state == 'UNKNOWN' or not thermal or not thermal.get('available'):
            return None
        return dict(name='ACTIVE-FLOOR-IDLE-RELAX30-v1', state=state,
            current_rails_W=thermal['conditional_inputs_rails_W_PWM'][:2],
            active_rail_floor_W=[self.config['levels']['active'][n] for n in ('gpu_W','cpu_soc_mss_W')],
            idle_rails_W=[self.config['levels']['idle'][n] for n in ('gpu_W','cpu_soc_mss_W')],
            idle_relaxation_tau_s=self.config['relaxation_tau_s'],
            conditional_held_PWM_fraction=thermal['conditional_inputs_rails_W_PWM'][2],
            observed_future_inputs_used=False, future_end_known=False)


def load_candidate(root=ROOT):
    freeze=read(root/'freeze.json')
    if sha(root/'candidate.json') != freeze['candidate_sha256'] or sha(root/'analysis-spec.json') != freeze['spec_sha256']:
        raise ValueError('frozen candidate/spec changed')
    c=read(root/'candidate.json')
    p=root/c['dynamic_spec_path']
    if sha(p) != c['immutable']['observer_spec_sha256']:
        raise ValueError('observer spec changed')
    return c, FutureInputs(c, read(p)['dynamic'])


class Processor:
    def __init__(self, config, forecast):
        self.models={k:Activity(config,k) for k in config['variants']}
        self.forecast=forecast

    def process(self, frame):
        variants={}
        for name, model in self.models.items():
            state=model.step(frame)
            variants[name]=dict(activity=state,
                future_inputs=self.forecast.scenario(frame.get('thermal'),state['state']),
                temperature_C={str(h):self.forecast.predict(frame.get('thermal'),state['state'],h) for h in (15,45,90)})
        return dict(native_ref=frame.get('native_ref'), arrival_mono_s=frame.get('arrival_mono_s'),
            variants=variants, deployable=False, field_safety_available=False,
            note='research candidate; activity is not inference/GPU ground truth or control permission')
