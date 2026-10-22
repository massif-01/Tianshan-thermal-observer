"""Replay one new archived run through its exact native TTO processor, never live IO."""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).absolute().parent
sys.path.insert(0,str(ROOT/'vendor'))
from common import read,write,sha,seconds
from tto.config import load_config,merge,validate
from tto.engine import engine_for
from tto.dataset import replay as native_replay
from data_views import index_evidence,strict_segments,make_examples


def replay(evidence,output):
    evidence=Path(evidence);run=next((evidence/'remote-result/collection').glob('run-*'));manifest=read(run/'manifest.json')
    assert manifest['observer_run_id']==read(ROOT/'spec.json')['run_id']
    for name,digest in read(run/'files.json').items():assert sha(run/name)==digest,name
    source={n:sha(ROOT/'vendor/tto'/n) for n in manifest['source_identity']['files']}
    assert source==manifest['source_identity']['files']
    native=native_replay(run)
    assert not native['platform_state']['mixed_profiles'] and not native['platform_state']['evidence_issues']
    isolated={x['segment'] for x in native['quality_eligibility']['isolations']}
    config=load_config(environ={});saved=copy.deepcopy(manifest['config'])
    for section in ['orin','tianshan']:saved[section]['headers_file']=saved[section]['ca_file']=None
    merge(config,saved);validate(config);engine=engine_for(config,record_schema=2)
    phases=read(evidence/'checks/computer-side-verification.json')['phases']
    for p in phases:p['start']=seconds(p['start_utc']);p['end']=seconds(p['end_utc']);p['id']=p['name']
    def classify(wall):
        p=next((p for p in phases if p['start']<=wall<p['end']),None)
        phase=p['name'] if p else 'outside_phases'
        macro='work' if phase in ['sparse','continuous'] else 'background' if phase in ['resident-baseline','outside_phases'] else 'recovery'
        return macro,phase,phase
    rawrows=[json.loads(x) for x in (run/'observations-0001.jsonl').read_text().splitlines()]
    samples=[];nodes=[];latest=None;epoch=0;identity=None;context_last=None;quality=[]
    for count,raw in enumerate(rawrows,1):
        assert raw['ref']==f"{manifest['observer_run_id']}/observation:{count}"
        blocked=engine.q.blocked;longgap=engine.q.counts['boundary_long_gap']
        out=engine.process(raw);q=out['quality'];t=raw['mono_s']
        if (engine.q.blocked and not blocked) or engine.q.counts['boundary_long_gap']>longgap:epoch+=1
        if raw['kind']=='boundary' or raw.get('preceding_queue_gap'):epoch+=1
        if q:
            quality.append(dict(ref=raw['ref'],t=t,utc=raw['received_at_utc'],quality=q))
            if q.get('lifecycle_violation') or q['reason'] in ['identity_conflict','sequence_regression','retired_stream','stale_or_missing_tj','stale_duplicate','invalid_numeric_contract']:epoch+=1
            if q['accepted']:
                ident=(tuple(q['key'][:2]),raw.get('connection_epoch'),repr(engine.q.lifecycle_settings),engine.q.lifecycle_uuid)
                if identity is not None and ident!=identity:epoch+=1
                identity=ident;s=engine.features.history[-1]
                until=t+(raw['payload']['telemetry_meta']['freshness_timeout_ms']-q['age_lower_bound_ms'])/1000
                latest=dict(ref=raw['ref'],t=t,mono_s=t,utc=raw['received_at_utc'],wall=seconds(raw['received_at_utc']),
                    run='YET',run_id=manifest['observer_run_id'],values=dict(s['values']),segment=s['segment'],source_epoch=epoch,
                    source_identity=repr(ident),sample_seq=raw['payload']['telemetry_meta']['sample_seq'],source_valid_until=until,
                    source_age_ms=q['age_lower_bound_ms'],target_valid=bool(q.get('period_known',False) and q.get('input_contract') is not None and s['segment'] not in isolated),
                    control_eligible=s['control_eligible'],node_index=len(nodes))
                latest['macro'],latest['phase'],latest['regime']=classify(latest['wall'])
                assert latest['values']['tj']==raw['payload']['temperature']['tj']
                for rail in ['vdd_gpu','vdd_cpu_soc_mss','vin_sys_5v0']:assert latest['values'][rail]==raw['payload']['power'][rail]['current']/1000
                samples.append(latest)
        fan=engine.fan['data'] if engine.fan else {};temp=engine.temp['data'] if engine.temp else {}
        _,eligible,reasons=engine.control_qualification(t)
        context=(fan.get('mode'),fan.get('enabled'),temp.get('manual_mode'),temp.get('active_source'),temp.get('bound_variable'))
        known=engine.fan is not None and engine.temp is not None and all(v is not None for v in context[:4])
        changed=bool(known and context_last is not None and context!=context_last)
        if known:context_last=context
        abnormal=bool(any(fan.get(k) is True for k in ['temp_stale','guard_active','fault']) or
            fan.get('mode') is not None and fan.get('mode')!='auto' or fan.get('enabled') is False or
            temp.get('manual_mode') is True or temp.get('normalized_valid') is False or changed)
        source_until=latest['source_valid_until'] if latest else t
        power_ok=bool(latest and latest['target_valid'] and not engine.q.blocked and not engine.q.quarantined and latest['segment']==engine.q.segment)
        deadline=min(source_until,engine.fan['t']+2.5 if engine.fan else t,engine.temp['t']+7.5 if engine.temp else t)
        complete=bool(power_ok and eligible and fan.get('mode')=='auto' and not abnormal)
        inputs=[latest['values']['vdd_gpu'],latest['values']['vdd_cpu_soc_mss'],fan['successful_duty']/100] if complete else None
        nodes.append(dict(t=t,utc=raw['received_at_utc'],wall=seconds(raw['received_at_utc']),ref=raw['ref'],trigger_ref=raw['ref'],
            complete=complete,good=complete,valid_until=deadline,source_until=source_until,power_ok=power_ok,
            control_eligible=eligible,mode=fan.get('mode'),observed_abnormal_or_changed=abnormal,
            context_known=known,context_change=changed,reasons=reasons,fan_ref=engine.fan['ref'] if engine.fan else None,
            temp_ref=engine.temp['ref'] if engine.temp else None,power_ref=latest['ref'] if latest else None,
            source_epoch=epoch,segment=engine.q.segment,inputs=inputs,raw_flags=dict(temp_stale=fan.get('temp_stale'),
            normalized_valid=temp.get('normalized_valid'),active_source=temp.get('active_source'),bound_variable=temp.get('bound_variable'),
            guard_active=fan.get('guard_active'),fault=fan.get('fault'))))
    assert [a['ref'] for a in samples]==native['accepted_refs']
    evidence_data=index_evidence(dict(run='YET',run_id=manifest['observer_run_id'],samples=samples,nodes=nodes,
        phases=phases,isolated_segments=sorted(isolated),quality=native['quality'],quality_eligibility=native['quality_eligibility'],
        native_platform=native['platform_state'],native_time_evidence=native['time_evidence'],source_hashes=source,
        execution_policy_used_for_model_qualification=False))
    segments,coverage=strict_segments(evidence_data);examples=make_examples(evidence_data,segments)
    evidence_data['segments']=segments;evidence_data['coverage']=coverage;evidence_data['examples']=examples;evidence_data['quality_decisions']=quality
    write(output,{k:v for k,v in evidence_data.items() if not k.startswith('_')})
    print('Replay',len(rawrows),'raw',len(samples),'accepted',len(segments),'strict segments',flush=True)
    return evidence_data

if __name__=='__main__':replay(Path(sys.argv[1]),Path(sys.argv[2]))
