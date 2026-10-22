"""Offline-only consumption of actual Issue 8 JSONL; no IO, no device authority.
Original source clock/expiry and research flags are never renamed or renewed.
The replay origin is an explicit clock translation, not a live monotonic binding.
"""
import math

def finite(v):
    return type(v) in (int,float) and math.isfinite(v)

def fresh(obj, now):
    return bool(obj and obj.get('raw_valid') is True and
                finite(obj.get('observed_mono_s')) and finite(obj.get('valid_until_mono_s')) and
                obj['observed_mono_s'] <= now < obj['valid_until_mono_s'])

def readiness(envelope, now, run_id, formal=False):
    s=envelope['upstream']; expected=envelope['expected_identity']; i=s['identity']
    source_now=now+envelope['replay_origin_mono_s']
    same_identity=(i==expected and i['run_id']==run_id)
    clock_ok=(s['schema']=='TTO-STATE-READONLY-R2-v1' and
              s['generated_clock_domain']=='offline_virtual_observer_clock' and
              finite(s['generated_at_mono_s']) and s['generated_at_mono_s']<=source_now and
              s['observed_through_ref'].startswith(run_id+'/observation:'))
    identity_ok=same_identity and clock_ok
    m=s['measurement']; tj=m['tj']; power=m['power']; pwm=m['last_successful_pwm']; context=m['control_context']
    values_ok=bool(tj and finite(tj.get('value_C')) and power and
                   power.get('names')==['vdd_gpu','vdd_cpu_soc_mss'] and
                   len(power.get('rails_W',[]))==2 and all(finite(v) for v in power['rails_W']) and
                   pwm and finite(pwm.get('value_percent')))
    measurements_ok=values_ok and all(fresh(x,source_now) for x in [tj,power,pwm])
    ob=s['observer']; phase=ob['phase']
    # No synthetic "evidence_ready". Preserve actual phase, conditional inputs and uncertainty.
    model_ok=bool(clock_ok and ob['available'] is True and phase in ('tracking','degraded') and
                  all(finite(ob[k]) for k in ('Tf_C','Ts_C','E_C')) and ob['E_source'] and
                  isinstance(ob['unknown_input_assumptions'],list) and ob['uncertainty'].get('marginal_std_C') and
                  s['generated_at_mono_s']==source_now)
    safe=s['safety']; fan_fresh=fresh(pwm,source_now); context_fresh=fresh(context,source_now)
    safety_ok=bool(fan_fresh and context_fresh and safe['fan_fresh'] and safe['binding_fresh'] and
                   safe['guard'] is False and safe['fault'] is False and safe['enabled'] is True and
                   safe['mode']=='auto' and safe.get('manual_mode') is False and
                   safe.get('normalized_valid') is True and safe.get('temp_stale') is False and
                   safe.get('binding')==envelope['expected_binding'] and safe.get('active_source')=='variable' and
                   safe.get('confirmed_normal_now') is True)
    explicit_stop=bool(not same_identity or
        (fan_fresh and (safe['guard'] is True or safe['fault'] is True or safe['enabled'] is False or
                        safe['mode'] not in (None,'auto'))) or
        (context_fresh and (safe.get('manual_mode') is True or
          safe.get('binding') not in (None,envelope['expected_binding']) or
          safe.get('active_source') not in (None,'variable'))))
    # An offline demo grant is local harness input, never promoted from the observer's permission.
    authorized=bool(not formal and envelope.get('offline_demo_authorized') is True and
                    envelope.get('transport')=='no_requests_virtual_replay' and
                    s['permission']==dict(local_demo=True,formal_field_authorized=False,device_actions=False))
    reasons=[]
    for ok,reason in [(identity_ok,'identity_or_replay_clock_unverified'),(measurements_ok,'current_raw_measurements_unusable'),
                      (model_ok,'observer_evidence_unready'),(safety_ok,'safety_unready_or_explicit_stop'),
                      (authorized,'execution_authorization_absent')]:
        if not ok:reasons.append(reason)
    return dict(collection_available=bool(identity_ok and measurements_ok),model_available=model_ok,
                field_safety_available=safety_ok,execution_authorized=authorized,instrument_clock_ready=False,
                explicit_stop=explicit_stop,start_allowed=bool(identity_ok and measurements_ok and model_ok and safety_ok and authorized),
                reasons=reasons,raw_valid_preserved=m,observer_state=phase,
                successful_PWM_age_s=source_now-pwm['observed_mono_s'] if pwm else None,
                safety_status='observed_fresh' if fan_fresh and context_fresh else 'unknown',
                state_generated_at=s['generated_at_mono_s'],observation_cutoff=s['observed_through_ref'],
                formal_start_allowed=False,clock_domain=s['generated_clock_domain'],
                model_permission_unchanged=s['permission'],firmware_identity=i['firmware_identity'])
