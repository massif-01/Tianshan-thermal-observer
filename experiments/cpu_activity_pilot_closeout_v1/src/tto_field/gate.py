"""Field clock/permission adapter. Native measurement validity and model mathematics stay upstream."""
import math

def number(v):return type(v) in (int,float) and math.isfinite(v)

def fresh(obj,now):
    return bool(obj and obj.get('raw_valid') is True and number(obj.get('observed_mono_s')) and
                number(obj.get('valid_until_mono_s')) and obj['observed_mono_s']<=now<obj['valid_until_mono_s'])

def readiness(envelope,relative_now,run_id,formal=True):
    empty=dict(collection_available=False,model_available=False,field_safety_available=False,
               execution_authorized=False,instrument_clock_ready=False,explicit_stop=False,start_allowed=False,
               reasons=['waiting_for_first_native_record'],observer_state='uninitialized')
    if not envelope:return empty
    s=envelope['state'];clock=envelope['clock'];now=clock['session_origin_mono_s']+relative_now
    i=s['identity'];m=s['measurement'];o=s['observer'];safe=s['safety'];binding=envelope['binding']
    identity_ok=(run_id==i['run_id']==envelope['native_run_id'] and
                 all(i[k]==envelope['expected_identity'][k] for k in ('config_sha256','collector_source_sha256','model_sha256','spec_sha256')))
    temporal=(clock['domain']==envelope['process_clock_domain'] and
              clock['observer_input_mono_s']<=clock['generated_at_mono_s']<=now and
              s['observed_through_ref'].startswith(run_id+'/observation:'))
    tj=m['tj'];p=m['power'];pwm=m['last_successful_pwm'];ctx=m['control_context']
    facts=bool(fresh(tj,now) and number(tj.get('value_C')) and fresh(p,now) and
               p.get('names')==['vdd_gpu','vdd_cpu_soc_mss'] and len(p.get('rails_W',[]))==2 and
               all(number(v) for v in p['rails_W']) and fresh(pwm,now) and number(pwm.get('value_percent')))
    model=bool(temporal and now<clock['model_consumable_until_mono_s'] and o['available'] is True and
               o['phase'] in ('tracking','degraded') and all(number(o[k]) for k in ('Tf_C','Ts_C','E_C')) and
               o['E_source'] and isinstance(o['unknown_input_assumptions'],list) and o['uncertainty'].get('marginal_std_C'))
    ff=fresh(pwm,now);cf=fresh(ctx,now)
    safety=bool(ff and cf and safe['fan_fresh'] and safe['binding_fresh'] and
                safe['guard'] is False and safe['fault'] is False and safe['enabled'] is True and safe['mode']=='auto' and
                safe['temp_stale'] is False and safe['manual_mode'] is False and safe['normalized_valid'] is True and
                safe['active_source']=='variable' and safe['binding']==binding['expected_binding'] and safe['confirmed_normal_now'] is True)
    explicit=bool(not identity_ok or
                  (ff and (safe['guard'] is True or safe['fault'] is True or safe['enabled'] is False or safe['mode'] not in (None,'auto'))) or
                  (cf and (safe['manual_mode'] is True or safe['binding'] not in (None,binding['expected_binding']) or
                           safe['active_source'] not in (None,'variable'))))
    permit=bool(envelope['mode']=='execute' and binding['authorization']['action']=='fixed-anchors' and
                binding['authorization']['explicit_user_start'] is True and binding['authorization']['command_id']==binding['command_id'])
    ins=binding.get('instrument',{})
    instrument=bool(ins.get('recording') is True and ins.get('probe_fixed') is True and
                    ins.get('clock_start',{}).get('verified_file_sha256') and ins['clock_start'].get('timezone') and
                    ins['clock_start'].get('display_resolution_s') and 'uncertainty_s' in ins['clock_start'])
    if binding.get('cpu_pilot_verified') is True:
        permit=bool(envelope['mode']=='execute' and binding['authorization']['action']=='cpu-activity-pilot' and
                    binding['authorization']['explicit_user_start'] is True and binding['authorization']['command_id']==binding['command_id'])
        if not ins.get('used',True):instrument=True
    reasons=[]
    for ok,reason in [(identity_ok and temporal,'identity_or_clock_unverified'),(facts,'measurement_unusable'),
                      (model,'model_unavailable_or_state_expired'),(safety,'control_context_unready'),
                      (permit,'current_load_authorization_absent'),(instrument,'instrument_or_clock_missing')]:
        if not ok:reasons.append(reason)
    return dict(collection_available=bool(identity_ok and temporal and facts),model_available=model,
                field_safety_available=safety,execution_authorized=permit,instrument_clock_ready=instrument,
                explicit_stop=explicit,start_allowed=bool(identity_ok and temporal and facts and model and safety and permit and instrument),
                reasons=reasons,observer_state=o['phase'],successful_PWM_age_s=now-pwm['observed_mono_s'] if pwm else None,
                measurement_current={k:fresh(v,now) for k,v in m.items()},
                source_ages_s={k:now-v['observed_mono_s'] if v else None for k,v in m.items()},
                source_expiry_mono_s={k:v['valid_until_mono_s'] if v else None for k,v in m.items()},
                model_state_age_s=now-clock['generated_at_mono_s'],model_consumable_until_mono_s=clock['model_consumable_until_mono_s'],
                safety_status='fresh' if ff and cf else 'unknown',observation_cutoff=s['observed_through_ref'],
                native_quality_preserved=True,model_permission=s['permission'])
