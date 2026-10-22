"""#10 consumer of one upstream stream. Does not repair quality, renew TTL, or estimate states."""
import copy,math,json
from pathlib import Path

SCHEMA='TTO-READONLY-STATE-R2'
IDENTITIES=('config','firmware','collector','model','spec')

def readiness(s,now,run_id,formal=True):
    reasons=[]
    identity=s.get('identity',{})
    identity_ok=(s.get('schema')==SCHEMA and identity.get('clock_domain')=='local_scheduler_monotonic' and identity.get('run_id')==run_id and all(identity.get(k) for k in IDENTITIES)
                 and isinstance(identity.get('generated_at_mono'),(int,float))
                 and isinstance(identity.get('observed_until_mono'),(int,float))
                 and identity['observed_until_mono']<=identity['generated_at_mono']<=now)
    if not identity_ok:reasons.append('identity_or_observation_cutoff_unverified')
    def fresh(v):
        return (isinstance(v.get('value'),(float,int)) and math.isfinite(v['value']) and v.get('raw_valid') is True and isinstance(v.get('observed_at_mono'),(int,float))
                and isinstance(v.get('expires_at_mono'),(int,float))
                and v['observed_at_mono']<=now<=v['expires_at_mono'] and bool(v.get('ref')))
    measurement=s.get('measurement',{})
    tj=measurement.get('TJ',{});rails=measurement.get('rails',{});pwm=measurement.get('successful_PWM',{})
    fact_ready=fresh(tj) and all(fresh(rails.get(k,{})) for k in ('GPU','CPU_SOC_MSS')) and fresh(pwm)
    if not fact_ready:reasons.append('current_raw_measurements_unusable')
    observer=s.get('observer',{})
    state=observer.get('state','unavailable')
    observer_ready=(state in ('tracking','degraded') and observer.get('evidence_ready') is True
                    and observer.get('valid_until_mono',-1)>=now
                    and all(isinstance(observer.get(k),(float,int)) and math.isfinite(observer[k]) for k in ('Tf','Ts'))
                    and observer.get('E_source') is not None and bool(observer.get('range_or_uncertainty'))
                    and isinstance(observer.get('unknown_inputs'),list))
    if not observer_ready:reasons.append('observer_evidence_unready')
    safety=s.get('safety',{})
    safety_fresh=(isinstance(safety.get('observed_at_mono'),(int,float)) and isinstance(safety.get('expires_at_mono'),(int,float))
                  and safety['observed_at_mono']<=now<=safety['expires_at_mono'])
    safety_ready=(safety_fresh and safety.get('guard') is False and safety.get('fault') is False
                  and safety.get('mode')=='auto' and safety.get('binding')==safety.get('expected_binding')
                  and safety.get('binding') is not None)
    explicit_stop=(safety_fresh and (safety.get('guard') is True or safety.get('fault') is True
                   or safety.get('mode') not in (None,'auto') or safety.get('binding_changed') is True
                   or (safety.get('binding') is not None and safety.get('expected_binding') is not None
                       and safety['binding']!=safety['expected_binding'])))
    if not safety_ready:reasons.append('safety_unready_or_explicit_stop')
    permission=s.get('permission',{})
    permission_ok=(permission.get('run_id')==run_id and permission.get('current_authorization') is True
                    and permission.get('mode')==('formal_field' if formal else 'local_demo'))
    if not permission_ok:reasons.append('execution_authorization_absent')
    instrument=s.get('instrument',{})
    instrument_ok=(instrument.get('recording') is True and instrument.get('probe_fixed') is True
                   and instrument.get('start_clock_evidence') is not None and instrument.get('timezone') is not None
                   and instrument.get('display_resolution_s') is not None
                   and instrument.get('uncertainty_declared') is True)
    if formal and not instrument_ok:reasons.append('instrument_or_clock_evidence_missing')
    return dict(collection_available=bool(identity_ok and fact_ready),model_available=bool(observer_ready),
                field_safety_available=bool(safety_ready),execution_authorized=bool(permission_ok),
                instrument_clock_ready=bool(instrument_ok),explicit_stop=bool(explicit_stop),
                start_allowed=bool(identity_ok and fact_ready and observer_ready and safety_ready and permission_ok
                                   and (instrument_ok or not formal)),reasons=reasons,
                raw_valid_preserved=copy.deepcopy(measurement),observer_state=state,
                successful_PWM_age_s=now-pwm['observed_at_mono'] if pwm.get('observed_at_mono') is not None else None,
                safety_status='observed_fresh' if safety_fresh else 'unknown',
                state_generated_at=identity.get('generated_at_mono'),observation_cutoff=identity.get('observed_until_mono'))

class StateConsumer:
    """One ordered local JSONL stream; source algorithms belong to #8/#9."""
    def __init__(self,rows):
        self.rows=list(rows);self.index=-1
        ts=[s['identity']['generated_at_mono'] for s in self.rows]
        if ts!=sorted(ts):raise ValueError('state stream must be in generation order')
    @classmethod
    def from_jsonl(cls,path):
        return cls(json.loads(line) for line in Path(path).read_text().splitlines() if line.strip())
    def at(self,now):
        while self.index+1<len(self.rows) and self.rows[self.index+1]['identity']['generated_at_mono']<=now:self.index+=1
        return self.rows[self.index] if self.index>=0 else {}
