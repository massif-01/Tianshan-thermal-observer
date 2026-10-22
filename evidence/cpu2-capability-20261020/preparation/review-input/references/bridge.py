"""Only offline adapter: actual sidecar envelopes/native states -> frozen FRAME/origins."""
import argparse
import copy
import math
from pathlib import Path
from io_utils import ROOT,read,lines,write,jsonl,sha

CPU_NAMES=('cpu_mean_pct','cpu_max_pct')
BASE_NAMES=('gpu_pct','gpu_W','cpu_soc_mss_W')
FIELDS=['user','nice','system','idle','iowait','irq','softirq','steal','guest','guest_nice']


def finite(x):
    return type(x) in (int,float) and math.isfinite(x)


def cpu_list(text):
    if not isinstance(text,str) or not text:raise ValueError('CPU_set_text_unknown')
    result=set()
    for part in text.split(','):
        pair=[int(v) for v in part.split('-')]
        if len(pair) not in (1,2) or pair[0]<0 or pair[-1]<pair[0]:raise ValueError('CPU_set_text_invalid')
        result.update('cpu'+str(k) for k in range(pair[0],pair[-1]+1))
    return result


def cpu_window(source):
    """Recompute only complete actual online sets; never trust summary-only input."""
    current,previous=source.get('raw_cpu'),source.get('previous_raw_cpu')
    if not current or not previous:raise ValueError('missing_complete_raw_counter_window')
    for obj in (previous,current):
        if obj.get('fields',[])[:8]!=FIELDS[:8] or not finite(obj.get('SC_CLK_TCK')) or obj['SC_CLK_TCK']<=0:
            raise ValueError('counter_units_or_fields_unknown')
        if not isinstance(obj.get('per_core_online'),dict) or not obj['per_core_online']:
            raise ValueError('online_set_unknown')
        if any(type(v) is not bool for v in obj['per_core_online'].values()):raise ValueError('online_status_unknown')
        possible=cpu_list(obj.get('possible_text'));online=cpu_list(obj.get('online_text'))
        if (set(obj['per_core_online'])!=possible or not online<=possible
            or {k for k,v in obj['per_core_online'].items() if v}!=online):
            raise ValueError('incomplete_possible_or_online_set')
        parsed={x.split()[0]:[int(v) for v in x.split()[1:]] for x in obj.get('raw_proc_stat','').splitlines() if x.split()}
        if parsed!=obj.get('counters'):raise ValueError('raw_counter_text_mismatch')
    if previous['SC_CLK_TCK']!=current['SC_CLK_TCK']:raise ValueError('counter_tick_unit_changed')
    prev_online={k for k,v in previous['per_core_online'].items() if v}
    online={k for k,v in current['per_core_online'].items() if v}
    if online!=prev_online:raise ValueError('online_set_changed')
    if not online:raise ValueError('no_online_cores')
    window=[previous.get('read_start_mono_s'),previous.get('read_end_mono_s'),current.get('read_start_mono_s'),current.get('read_end_mono_s')]
    if not all(finite(v) for v in window) or not window[0]<=window[1]<window[2]<=window[3]:raise ValueError('invalid_source_read_window')
    if not finite(source.get('read_end_mono_s')) or window[3]>source['read_end_mono_s']:raise ValueError('counter_window_after_source_read')
    values={}
    for name in sorted(online):
        a=previous.get('counters',{}).get(name,[]);b=current.get('counters',{}).get(name,[])
        if len(a)<8 or len(b)<8 or not all(type(v) is int and v>=0 for v in a[:8]+b[:8]):raise ValueError('incomplete_online_counter_set')
        delta=[y-x for x,y in zip(a[:8],b[:8])]
        if any(v<0 for v in delta) or sum(delta)<=0:raise ValueError('counter_reset_iowait_decrease_or_zero_window')
        values[name]=100*(sum(delta)-delta[3]-delta[4])/sum(delta)
    reported=source.get('cpu')
    if not isinstance(reported,dict) or reported.get('complete_online_set') is not True:
        raise ValueError('source_explicit_incomplete_CPU')
    if set(reported.get('per_core_percent',{}))!=online:
        raise ValueError('reported_online_core_set_incomplete')
    if any(not finite(reported['per_core_percent'][k]) or abs(reported['per_core_percent'][k]-v)>1e-8 for k,v in values.items()):
        raise ValueError('reported_counter_summary_mismatch')
    if source.get('stop_reasons'):raise ValueError('source_stop_reasons')
    return dict(per_core_percent=values,online=sorted(online),possible_online_map=current['per_core_online'],
        mean_percent=sum(values.values())/len(values),max_percent=max(values.values()),
        source_read_window=window,SC_CLK_TCK=current['SC_CLK_TCK'])


class Bridge:
    def __init__(self,manifest,binding,launch,source_config):
        self.manifest,self.binding,self.launch=manifest,binding,launch
        self.run=binding['native_run_id'];self.command=binding['command_id']
        self.domain=binding['clock']['domain'];self.source_config=source_config
        self.immutable=read(ROOT/'frozen/candidate.json')['immutable']
        assert manifest['observer_run_id']==self.run and manifest['field_command_id']==self.command
        assert launch['command_id']==self.command and manifest['field_clock_domain']==self.domain
        assert launch['clock_start']['domain']==self.domain
        assert binding['expected_identity']['model_sha256']==self.immutable['model_sha256']
        assert binding['expected_identity']['spec_sha256']==self.immutable['observer_spec_sha256']
        self.epoch=None;self.native=None;self.features={};self.cpu_identity=None;self.cpu_seq=None
        self.last_source=None;self.retired=set();self.audit=[];self.diagnostic=[]
        self.receiver_identity=dict(binding['clock'],boot_id=binding['clock'].get('boot_id'))

    def revoke_cpu(self,reason,ref,t):
        for name in CPU_NAMES:self.features[name]=dict(value=None,valid=False,reason=reason,original_ref=ref,available_at_mono_s=t)
        self.audit.append(dict(event='CPU_qualification_revoked',reason=reason,ref=ref,available_at_mono_s=t))

    def feature(self,name,value,t,until,uid,ref,**metadata):
        old=self.features.get(name)
        if old and old.get('update_id')==uid:
            if value!=old.get('value'):
                return dict(value=None,valid=False,reason='same_source_identity_changed_value',original_ref=ref,available_at_mono_s=t)
            until=min(until,old['valid_until_mono_s']);available=old['available_at_mono_s']
        else:available=t
        return dict(value=value,valid=finite(value) and finite(until) and until>t,
            available_at_mono_s=available,valid_until_mono_s=until,update_id=uid,source_order=None,
            original_ref=ref,**metadata)

    def native_event(self,env,raw,t):
        ident=env['state']['identity'];clock=env['clock'];ref=raw['ref']
        if (env['native_run_id']!=self.run or ident['run_id']!=self.run or raw['observer_run_id']!=self.run
            or env['process_clock_domain']!=self.domain or clock['domain']!=self.domain
            or env['generation_evidence']['native_ref']!=ref):raise ValueError('native_run_clock_or_ref_mismatch')
        if ident['model_sha256']!=self.immutable['model_sha256'] or ident['spec_sha256']!=self.immutable['observer_spec_sha256']:
            raise ValueError('frozen_model_identity_mismatch')
        if t<raw['mono_s']:raise ValueError('native_generation_before_input')
        epoch=ident['source_epoch']
        if self.epoch!=epoch:
            self.features={};self.epoch=epoch;self.revoke_cpu('native_epoch_changed',ref,t)
        self.native=(env,raw)
        m=env['state']['measurement'];power=m.get('power');tj=m.get('tj')
        valid=bool(power and power.get('raw_valid') and env['communication']['measurement']['TJ_and_rails']['raw_valid'])
        if valid:
            source_ref=power['source_ref'];u=power['rails_W'];until=power['valid_until_mono_s']
            for name,v in zip(BASE_NAMES[1:],u):
                self.features[name]=self.feature(name,v,t,until,source_ref+':'+name,source_ref,
                    feature_source='saved original native independent rail',raw_unit='W',
                    original_observed_mono_s=power['observed_mono_s'],source_age_s=None,transport_delay_ms=None,
                    validity_basis='original native power eligibility/expiry, unchanged')
            source_raw=self.raw_by_ref[source_ref];g=source_raw['payload'].get('gpu',{})
            age=(tj or {}).get('source_age_lower_bound_ms')
            gpu_age=g.get('age_at_telemetry_receive_ms');timeout=g.get('freshness_timeout_ms')
            good=bool(g.get('status')=='valid' and finite(g.get('utilization_pct')) and 0<=g['utilization_pct']<=100
                and finite(age) and finite(gpu_age) and gpu_age>=0 and finite(timeout) and timeout>0
                and g.get('sampled_at_utc') and g.get('device_uuid'))
            if good:
                expiry=source_raw['mono_s']+(timeout-age-gpu_age)/1000
                self.features['gpu_pct']=self.feature('gpu_pct',g['utilization_pct'],t,expiry,
                    str(g['device_uuid'])+':'+g['sampled_at_utc'],source_ref,feature_source='saved original GPU record',
                    source_sampled_at_utc=g['sampled_at_utc'],source_age_lower_bound_ms=age+gpu_age,
                    source_window=None,transport_delay_ms=None,validity_basis='original GPU source age lower bound and expiry')
            else:self.features['gpu_pct']=dict(value=None,valid=False,reason='native_GPU_unavailable',original_ref=ref,available_at_mono_s=t)
        else:
            for name in BASE_NAMES:self.features[name]=dict(value=None,valid=False,reason='latest_native_source_invalid',original_ref=ref,available_at_mono_s=t)
        is_origin=bool(tj and tj.get('source_ref')==ref and raw['kind']=='orin')
        origin=None
        if is_origin:
            ob=env['state']['observer'];source_valid=bool(valid and tj.get('raw_valid'))
            thermal=dict(available=bool(source_valid and ob['available']),current_TJ_C=tj['value_C'],Ts_C=ob['Ts_C'],E_C=ob['E_C'],
                conditional_inputs_rails_W_PWM=ob['conditional_inputs_rails_W_PWM'],state_native_ref=ref,
                model_sha256=ident['model_sha256'],observer_spec_sha256=ident['spec_sha256'],
                saved_state_generated_mono_s=t,original_PWM=m.get('last_successful_pwm'),safety=env['state']['safety'])
            source_key=env['communication']['measurement']['TJ_and_rails'].get('source') or {}
            key=source_key.get('key')
            if key is None:key=[self.manifest['config']['orin']['source_id'],raw['payload']['telemetry_meta']['stream_id']]
            origin=dict(ref=ref,t=t,measurement_received_mono_s=raw['mono_s'],current=tj['value_C'],source_valid=source_valid,
                source_key=key[:2],epoch=self.epoch,arrival_clock_id=self.domain,thermal=thermal,
                decision_time_basis='actual saved state generation; original raw receive retained, no backdating',
                synthetic=self.launch.get('synthetic_loopback_only',False))
        return origin

    def cpu_event(self,row,ref,t):
        if row.get('receiver_domain')!=self.domain:raise ValueError('receiver_clock_unmapped: cannot place foreign mono time')
        if row.get('native_run_id')!=self.run or row.get('command_id')!=self.command:
            self.revoke_cpu('sidecar_foreign_run_or_command',ref,t);return
        if row.get('receiver_identity'):
            self.receiver_identity=copy.deepcopy(row['receiver_identity'])
            if self.receiver_identity.get('domain')!=self.domain:
                raise ValueError('receiver_identity_domain_mismatch')
        s=row.get('source') or {};ident=s.get('identity') or {}
        if (s.get('schema')!='TTO-CPU-SOURCE-v1' or ident.get('command_id')!=self.command
            or not all(ident.get(k) for k in ['host','boot_id','source_session']) or ident.get('clock')!='CLOCK_MONOTONIC'):
            self.revoke_cpu('source_identity_or_clock_unknown',ref,t);return
        received=row.get('received_at_mono_s')
        if not finite(received) or received>t:
            self.revoke_cpu('receiver_decision_before_arrival',ref,t);return
        identity=tuple(ident[k] for k in ['host','boot_id','source_session','clock'])
        seq=s.get('seq')
        if type(seq) is not int or seq<=0:self.revoke_cpu('source_seq_unknown',ref,t);return
        changed=self.cpu_identity is not None and self.cpu_identity!=identity
        if changed:
            self.retired.add(self.cpu_identity);self.cpu_seq=None;self.last_source=None
        if identity in self.retired:
            self.revoke_cpu('retired_source_identity',ref,t);return
        self.cpu_identity=identity
        if self.cpu_seq is not None and seq==self.cpu_seq and self.last_source==s:
            self.audit.append(dict(event='duplicate_buffer_no_renewal',ref=ref,available_at_mono_s=t));return
        if self.cpu_seq is not None and seq<=self.cpu_seq:
            self.revoke_cpu('source_sequence_regression',ref,t);return
        self.cpu_seq=seq;self.last_source=copy.deepcopy(s)
        self.diagnostic.append(dict(ref=ref,source_GPU=s.get('gpu'),source_rails=s.get('rails'),
            use='diagnostic_only; unknown independent generation/window never substituted into BASE',
            network_latency_s=row.get('network_latency_s'),source_identity=ident,receiver_identity=row.get('receiver_identity')))
        if changed:self.revoke_cpu('source_identity_changed',ref,t);return
        try:values=cpu_window(s)
        except ValueError as e:self.revoke_cpu(str(e),ref,t);return
        uid='|'.join(map(str,identity))+'|'+str(seq)+'|'+repr(values['source_read_window'])
        for name,key in zip(CPU_NAMES,('mean_percent','max_percent')):
            self.features[name]=self.feature(name,values[key],t,received+1.,uid+':'+name,ref,
                feature_source='actual CPU cumulative-counter window, all online cores',source_identity=ident,
                receiver_received_at_mono_s=received,receiver_decision_generated_mono_s=t,
                source_read_window=values['source_read_window'],source_clock_mapping='unknown',
                per_core_percent=values['per_core_percent'],online=values['online'],possible_online_map=values['possible_online_map'],
                source_age_s=None,transport_delay_ms=None,network_latency_s=None,
                source_order_original=seq,validity_basis='receiver research support <=received_at+1s, NOT source freshness')

    def frame(self,t,ref,kind,thermal=None):
        return dict(schema='TTO-CPU-ACTIVITY-FRAME-v1',native_ref=ref,arrival_mono_s=t,
            arrival_clock_id=self.domain,arrival_host=self.receiver_identity.get('host'),
            arrival_boot_id=self.receiver_identity.get('boot_id'),epoch=self.epoch,source_only=False,
            synthetic=self.launch.get('synthetic_loopback_only',False),features=copy.deepcopy(self.features),
            thermal=thermal,adapter_event=kind,receiver_domain=self.domain,
            evaluation_scope='receiver_arrival_order_research; source age/physical lead unknown',
            latest_native_state_ref=self.native[0]['generation_evidence']['native_ref'] if self.native else None,
            deployable=False)


def adapt(run,config):
    binding=read(run/'native-binding.json');launch=read(run/'launch.json')
    mp=run/binding['native_manifest'];manifest=read(mp)
    b=Bridge(manifest,binding,launch,config)
    raw=list(lines(mp.parent/'observations-0001.jsonl'));b.raw_by_ref={r['ref']:r for r in raw}
    envs=lines(run/'states.jsonl');arrivals=lines(run/'cpu-sidecar-arrivals.jsonl')
    origins_clock={e['clock']['session_origin_mono_s'] for e in envs}
    if len(origins_clock)!=1:raise ValueError('receiver session origin changed within run')
    origin_clock=next(iter(origins_clock))
    events=[]
    for i,e in enumerate(envs,1):
        ref=e['generation_evidence']['native_ref'];events.append((e['clock']['generated_at_mono_s'],0,i,'native',(e,b.raw_by_ref[ref])))
    for i,r in enumerate(arrivals,1):
        t=r.get('decision_generated_mono_s')
        if not finite(t):raise ValueError('missing_actual_receiver_decision_time')
        if r.get('receiver_domain')!=b.domain:raise ValueError('receiver_clock_unmapped: cannot compare foreign clocks')
        events.append((t,1,i,'cpu',r))
    for i,e in enumerate(lines(run/'sidecar-events.jsonl'),1):
        if e.get('event') in ('source_error','source_rejected','source_eof','stop_sidecar_only','connection_missing','connection_invalid','missing_source'):
            t=e.get('decision_generated_mono_s',e.get('received_at_mono_s'))
            if not finite(t):t=origin_clock+e['mono_s']
            events.append((t,2,i,'revoke',e))
    frames=[];origins=[]
    for t,_,i,kind,payload in sorted(events,key=lambda x:x[:3]):
        if kind=='native':
            e,r=payload;o=b.native_event(e,r,t);ref=r['ref']
            if o:origins.append(o)
            frames.append(b.frame(t,ref,kind,o['thermal'] if o else None))
        elif kind=='cpu':
            ref=b.run+'/cpu-sidecar-arrivals.jsonl:'+str(i);b.cpu_event(payload,ref,t)
            frames.append(b.frame(t,ref,kind))
        else:
            ref=b.run+'/sidecar-events.jsonl:'+str(i)
            b.revoke_cpu('transport_'+payload.get('status',payload['event']),ref,t)
            b.audit[-1]['original_transport_event']=copy.deepcopy(payload)
            frames.append(b.frame(t,ref,kind))
    return b,frames,origins


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--source-config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    try:b,frames,origins=adapt(a.run_dir.resolve(),read(a.source_config))
    except (ValueError,KeyError,AssertionError) as e:
        write(a.output/'failure.json',dict(status='unavailable',error=str(e),no_clock_mapping_invented=True));raise
    jsonl(a.output/'frames.jsonl',frames);jsonl(a.output/'thermal-origins.jsonl',origins)
    jsonl(a.output/'revocations.jsonl',b.audit);jsonl(a.output/'source-query-diagnostics.jsonl',b.diagnostic)
    write(a.output/'registration.json',dict(run_id=b.run,command_id=b.command,
        declared_role='synthetic_actual_sender_receiver_integration' if b.launch.get('synthetic_loopback_only') else 'targeted_recorded_arrival_research',
        saw_new_data_for_parameter_selection=False,candidate_sha256=sha(ROOT/'frozen/candidate.json'),
        analysis_spec_sha256=sha(ROOT/'frozen/analysis-spec.json'),adapter_spec_sha256=sha(ROOT/'adapter-spec.json'),
        physical_CPU_GPU_lead_validated=False,source_to_receiver_latency_s=None,
        origin_time_basis='actual state decision readiness; one per original TJ, original measurement time retained',
        decimation='200ms counter-window values selected every1s, not reconstructed1s statistics'))
    sources=[p for p in a.run_dir.rglob('*') if p.is_file()]+[a.source_config]
    write(a.output/'sources.json',dict(run_dir=str(a.run_dir.resolve()),
        files=[dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(sources)],
        frames=len(frames),original_TJ_origins=len(origins),source_config_binding='explicit supplied file SHA; retain original launch/source config bindings separately'))
    print('Adapted',len(frames),'real-shaped arrival events;',len(origins),'original TJ decision origins; parameters unchanged.')


if __name__=='__main__':main()
