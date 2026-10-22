"""Explicit synthetic #8/#9 interface data; never presented as upstream implementation."""
import copy

def snapshot(now,run_id,scenario='healthy',formal=False):
    def fact(value,kind,observed=None,ttl=2.5):
        t=now if observed is None else observed
        return dict(value=value,raw_valid=True,ref=f'SYNTHETIC/{kind}/{t}',observed_at_mono=t,expires_at_mono=t+ttl)
    s={'schema':'TTO-READONLY-STATE-R2','source':'synthetic_fixture_not_device',
       'identity':dict(run_id=run_id,config='fixture-config',firmware='fixture-firmware',collector='candidate024-simulated-feed',
                       model='frozen-fixture-not-fitted',spec='fixture-spec-r2',clock_domain='local_scheduler_monotonic',generated_at_mono=now,observed_until_mono=now),
       'measurement':{'TJ':fact(45.,'TJ'),'rails':{'GPU':fact(2.,'GPU'),'CPU_SOC_MSS':fact(6.,'CPU_SOC_MSS'),
                                                  'VIN_SYS_5V0':fact(4.,'VIN_SYS_5V0-diagnostic')},
                      'successful_PWM':fact(20.,'successful-PWM'),'http_status':'ok'},
       'observer':dict(state='tracking',Tf=44.9,Ts=39.,E_source='synthetic_preregistered_new_run_prior_not_ambient',
                       evidence_ready=True,valid_until_mono=now+2.5,unknown_inputs=[],range_or_uncertainty={'Ts':[35,45]},reasons=[]),
       'safety':dict(guard=False,fault=False,mode='auto',binding='TJ-source',expected_binding='TJ-source',
                     binding_changed=False,observed_at_mono=now,expires_at_mono=now+2.5),
       'permission':dict(run_id=run_id,mode='formal_field' if formal else 'local_demo',current_authorization=True),
       'instrument':dict(recording=True,probe_fixed=True,start_clock_evidence='synthetic-clock-anchor',timezone='UTC+8',
                         display_resolution_s=1,uncertainty_declared=True,uncertainty_s=None),
       'environment':dict(temperature_c=None,source='unknown_not_old_M24')}
    if scenario=='startup' and now<20:
        s['measurement']={};s['observer'].update(state='uninitialized',Tf=None,Ts=None,evidence_ready=False)
        s['safety'].update(guard=None,fault=None,mode=None,binding=None)
    if scenario in ('short_gap','long_gap') and 400<=now<(415 if scenario=='short_gap' else 600):
        s['measurement']['successful_PWM']=fact(20.,'successful-PWM-last',observed=399.)
        s['measurement']['http_status']='timeout';s['observer'].update(state='degraded',unknown_inputs=[{'kind':'PWM','since':401.5,'assumption':'fixture bounded input only','age_s':max(0,now-401.5)}])
    if scenario=='http_timeout' and 400<=now<401:
        s['measurement']['http_status']='timeout';s['measurement']['successful_PWM']=fact(20.,'last-success',observed=399.)
    if scenario in ('mode_change','binding_change','guard','fault','unknown_safety') and now>=400:
        if scenario=='mode_change':s['safety']['mode']='manual'
        elif scenario=='binding_change':s['safety'].update(binding='other-source',binding_changed=True)
        elif scenario=='guard':s['safety']['guard']=True
        elif scenario=='fault':s['safety']['fault']=True
        else:s['safety'].update(guard=None,fault=None,mode=None,binding=None)
    if scenario=='unavailable_observer':s['observer'].update(state='unavailable',Tf=None,Ts=None,evidence_ready=False)
    if scenario=='permission_missing':s['permission']['current_authorization']=False
    return s
