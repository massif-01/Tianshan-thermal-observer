"""Only consumes the ONE observer's existing output; no sensors, model, or API clients."""
import math

def number(x):return type(x) in (int,float) and math.isfinite(x)
def fresh(x,now):
    return bool(x and x.get('raw_valid') is True and number(x.get('observed_mono_s')) and number(x.get('valid_until_mono_s')) and x['observed_mono_s']<=now<x['valid_until_mono_s'])

def evaluate(launch,status,now,identity,*,alive,process_created):
    """No model score/tracking or instrument dependency; permission is checked separately."""
    if not launch or not status:return dict(action='pause',reasons=['observer_starting'],software_healthy=False)
    reg=launch['registration'];clock=launch['clock_start'];env=status.get('latest_state')
    expected={k:identity[k] for k in ('device_id','thermal_config_id','session_id','observer_host_id','boot_id')}
    if any(reg.get(k)!=v for k,v in expected.items()) or launch.get('version')!='0.2.4+observe.2':
        return dict(action='stop',reasons=['observer_identity_mismatch'],software_healthy=False)
    if not alive or status.get('running') is not True:
        return dict(action='stop',reasons=['observer_exited'],software_healthy=False)
    if status.get('process_created')!=process_created or status.get('pid')!=launch['clock_start']['pid']:
        return dict(action='stop',reasons=['observer_process_replaced'],software_healthy=False)
    age=now-(clock['mono_before_s']+status['elapsed_s'])
    if not -.1<=age<=3:return dict(action='pause',reasons=['observer_heartbeat_stale'],software_healthy=False)
    healthy=bool(status.get('collection') and not status.get('reason'))
    if not env:return dict(action='pause',reasons=['no_current_measurement_view'],software_healthy=healthy)
    actual=env['identity']
    if any(actual.get(k)!=v for k,v in expected.items()) or actual.get('run_id')!=status.get('native_run_id') or env['process_clock_domain']!=clock['domain'] or env['clock']['domain']!=clock['domain']:
        return dict(action='stop',reasons=['state_session_or_clock_mismatch'],software_healthy=False)
    if any(actual.get(k)!=identity[k] for k in ('model_sha256','spec_sha256')) or env['expected_identity']['config_sha256']!=launch['authorization']['config_sha256']:
        return dict(action='stop',reasons=['state_model_or_config_mismatch'],software_healthy=False)
    if not env['clock']['observer_input_mono_s']<=env['clock']['generated_at_mono_s']<=now:
        return dict(action='stop',reasons=['state_clock_invalid'],software_healthy=False)
    m=env['measurement'];s=env['safety'];pwm=m.get('last_successful_pwm');context=m.get('control_context');tj=m.get('tj');power=m.get('power')
    ff=fresh(pwm,now);cf=fresh(context,now)
    if ((ff and (s.get('guard') is True or s.get('fault') is True or s.get('enabled') is False or s.get('mode') not in (None,'auto'))) or
        (cf and (s.get('manual_mode') is True or s.get('binding') not in (None,'agx_info.temperature.tj') or s.get('active_source') not in (None,'variable')))):
        return dict(action='stop',reasons=['explicit_protection_or_mode_binding'],software_healthy=healthy)
    facts=bool(fresh(tj,now) and number(tj.get('value_C')) and fresh(power,now) and power.get('names')==['vdd_gpu','vdd_cpu_soc_mss'] and len(power.get('rails_W',[]))==2 and all(number(v) for v in power['rails_W']) and ff and number(pwm.get('value_percent')))
    safety=bool(ff and cf and s.get('fan_fresh') and s.get('binding_fresh') and s.get('guard') is False and s.get('fault') is False and s.get('enabled') is True and s.get('mode')=='auto' and s.get('temp_stale') is False and s.get('manual_mode') is False and s.get('normalized_valid') is True and s.get('active_source')=='variable' and s.get('binding')=='agx_info.temperature.tj' and s.get('confirmed_normal_now') is True and number(s.get('context_stable_s')) and s['context_stable_s']>=5)
    reasons=[]
    if not healthy:reasons.append('observer_not_recording')
    if not facts:reasons.append('measurement_unusable')
    if not safety:reasons.append('control_context_unready')
    return dict(action='allow' if not reasons else 'pause',reasons=reasons,software_healthy=healthy,model_available=env.get('model',{}).get('available'),model_used_as_permission=False,instrument_required=False,raw_expiry_unchanged=True,observation_ref=env['native_ref'],native_run_id=status['native_run_id'])
