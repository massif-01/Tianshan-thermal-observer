"""One native collector, its processed output, one observer, one scheduling/request executor.
This module contains no device defaults. Only an explicit CLI invocation with a current bound grant
constructs network clients. Diagnostic runs never instantiate Requester.
"""
import asyncio,copy,hashlib,json,os,threading,time
from pathlib import Path
from .support import Clock,Evidence,write,utc,digest_file
from .gate import readiness
from .scheduler import Scheduler,resolve_plan
from . import __version__

ROOT=Path(__file__).resolve().parent
ACTOR='01a1331a-f937-7d91-aef0-ac4f5e50bd8a'
MODEL_STATE_MAX_AGE_S=2.5


def profile():
    return resolve_plan(json.loads((ROOT/'plans/mix-plan.json').read_text()),'fixed-anchors')


def verify_grant(c,binding,mode,duration):
    from tto.config import public_config
    from tto.util import digest
    from tto.storage import source_identity
    a=binding['authorization']
    if binding.get('old_overrides') is not False:raise ValueError('old overrides are forbidden')
    if not binding.get('command_id') or a.get('command_id')!=binding['command_id']:raise ValueError('current command authorization missing')
    action='readonly-diagnostic' if mode=='diagnose' else 'fixed-anchors'
    if a.get('action')!=action or a.get('explicit_user_start') is not True or not a.get('evidence'):
        raise ValueError('explicit current-run mode authorization required')
    if binding.get('config_sha256')!=digest(public_config(c)):raise ValueError('configuration identity mismatch')
    if binding.get('collector_source_sha256')!=source_identity()['sha256']:raise ValueError('installed runtime identity mismatch')
    if binding.get('observer_model_sha256')!=digest_file(ROOT/'research/models/primary.json') or binding.get('observer_spec_sha256')!=digest_file(ROOT/'research/observer-spec.json'):
        raise ValueError('frozen observer identity mismatch')
    if binding.get('expected_binding')!='agx_info.temperature.tj':raise ValueError('unexpected control binding')
    if (c['network']['request_timeout_s'],c['tianshan']['fan_poll_interval_s'],c['tianshan']['temp_poll_interval_s'],c['features']['fan_max_age_s'])!=(2.,1.,5.,2.5):
        raise ValueError('original timeout/poll/TTL contract must be preserved')
    if binding.get('synthetic_loopback_only'):
        import ipaddress
        from urllib.parse import urlsplit
        origins=[c[k]['base_url'] for k in ('orin','tianshan')]
        if mode=='execute':origins.append(binding['inference']['base_url'])
        if not all(ipaddress.ip_address(urlsplit(u).hostname).is_loopback for u in origins):raise ValueError('synthetic mode is numeric loopback only')
    if mode=='diagnose':
        if not 0<duration<=300:raise ValueError('diagnostic record duration must be <=300s')
    else:
        if binding.get('request_actor_thread')!=ACTOR:raise ValueError('only the designated inference actor launches execute')
        m=binding['inference']
        if m.get('model')!='RM-01 VLM' and not binding.get('synthetic_loopback_only'):raise ValueError('first profile uses original resident RM-01 VLM')
        if not binding.get('synthetic_loopback_only') and (not m.get('identity_evidence') or m.get('confirmed_client_slots')!=4):
            raise ValueError('current model identity and client slot capacity evidence required')
        if m.get('max_tokens')!=256 or m.get('request_timeout_s')!=30:raise ValueError('request contract changed')
        if not binding.get('synthetic_loopback_only'):
            original=json.loads((ROOT/'plans/model-profiles.json').read_text())['existing-dense-27b-confirm-before-live']
            if m.get('messages')!=original['payload']['messages'] or m.get('stream') is not True or m.get('sampling',{})!=original['sampling']:
                raise ValueError('frozen inference payload changed')
        ins=binding['instrument'];anchor=ins['clock_start'];p=Path(anchor['path'])
        if not ins.get('recording') or not ins.get('probe_fixed') or anchor.get('command_id')!=binding['command_id'] or digest_file(p)!=anchor['sha256']:
            raise ValueError('current instrument/clock evidence missing or mismatched')
        anchor['verified_file_sha256']=anchor['sha256']
        if not anchor.get('timezone') or not anchor.get('display_resolution_s') or 'uncertainty_s' not in anchor:
            raise ValueError('clock timezone/resolution/unknown error must be explicit')
    return binding


class Pipeline:
    """Called only from the native collector's single writer thread, after native processing."""
    def __init__(self,out,config,binding,mode,clock,evidence):
        self.out=out;self.config=config;self.binding=binding;self.mode=mode;self.clock=clock;self.evidence=evidence
        self.projection=self.observer=self.communication=None;self.latest=None;self.lock=threading.Lock();self.engine_id=None;self.callbacks=0;self.run_id=None;self.fan_success_times=[]
    def on_record(self,raw,processed,engine):
        from .projection import SavedStream
        from .research.observer import ThermalObserver
        try:
            if self.projection is None:
                manifests=list((self.out/'native').glob('run-*/manifest.json'))
                if len(manifests)!=1:raise ValueError('expected exactly one native collector journal')
                manifest=json.loads(manifests[0].read_text())
                if manifest['observer_run_id']!=raw['observer_run_id']:raise ValueError('native run mismatch')
                spec=json.loads((ROOT/'research/observer-spec.json').read_text())
                self.projection=SavedStream(manifest,spec,engine);self.observer=ThermalObserver(spec);self.engine_id=id(engine);self.run_id=raw['observer_run_id']
                from .comm_bridge import CommunicationBridge
                self.communication=CommunicationBridge(manifest,engine)
                self.expected=dict(run_id=self.run_id,config_sha256=manifest['config_sha256'],collector_source_sha256=manifest['source_identity']['sha256'],
                                   model_sha256=spec['model_sha256'],spec_sha256=digest_file(ROOT/'research/observer-spec.json'))
                if self.expected['collector_source_sha256']!=self.binding['collector_source_sha256']:raise ValueError('native collector source identity drift')
                write(self.out/'native-binding.json',dict(command_id=self.binding['command_id'],native_run_id=self.run_id,native_manifest=str(manifests[0].relative_to(self.out)),
                      expected_identity=self.expected,clock=self.clock.bracket(),collector_engine_instance_id=self.engine_id,
                      observer_instance_id=id(self.observer),projection_instance_id=id(self.projection),native_writer_thread_id=threading.get_ident()))
            if id(engine)!=self.engine_id or raw['observer_run_id']!=self.run_id:raise ValueError('second engine/run prohibited')
            comm=self.communication.feed(raw,processed)
            frame=self.projection.feed(raw,processed)
            before_validity={k:(v or {}).get('raw_valid',False) for k,v in frame['measurement'].items()}
            if not comm['measurement']['TJ_and_rails']['raw_valid']:
                for name in ['tj','power']:
                    if frame['measurement'][name]:frame['measurement'][name]['raw_valid']=False
                frame['new_TJ']=False
            s=self.observer.step(frame);generated=time.monotonic()
            if raw['kind']=='fan' and engine.fan and engine.fan['ref']==raw['ref']:self.fan_success_times.append(raw['mono_s'])
            env=dict(schema='TTO-FIELD-CONSUMABLE-STATE-v1',state=s,mode=self.mode,binding=self.binding,
                     native_run_id=self.run_id,expected_identity=self.expected,process_clock_domain=self.clock.domain,
                     communication=comm,native_projected_validity_before_I02=before_validity,
                     clock=dict(domain=self.clock.domain,session_origin_mono_s=self.clock.origin,observer_input_mono_s=raw['mono_s'],
                                generated_at_mono_s=generated,generated_at_utc=utc(),
                                model_consumable_until_mono_s=min(generated+MODEL_STATE_MAX_AGE_S,raw['mono_s']+MODEL_STATE_MAX_AGE_S)),
                     generation_evidence=dict(origin='actual native on_record callback after engine.process',native_ref=raw['ref'],
                                              native_engine_instance_id=id(engine),I02_shared_native_engine_instance_id=id(self.communication.view.engine),
                                              I02_processed_views=self.communication.view.process_calls,model_math_source_unchanged=True,
                                              research_snapshot_clock_label='upstream literal retained; actual clocks are in this envelope'))
            self.evidence.append('states.jsonl',env)
            with self.lock:self.latest=env
            self.callbacks+=1
        except Exception as exc:
            # Native writer already handles ValueError, preserving its raw journal on a projection failure.
            raise ValueError('field_projection_failed:'+type(exc).__name__) from exc
    def get(self):
        with self.lock:return self.latest


async def run(config,binding,mode,out,duration=300,probe_profile=None):
    from tto.collector import collect
    from tto.storage import InstanceLock,source_identity
    from tto.config import public_config
    from tto.util import digest
    out=Path(out);binding=copy.deepcopy(binding);verify_grant(config,binding,mode,duration)
    # Load numerical dependencies before constructing any network client.
    from .research.observer import ThermalObserver
    chosen=profile()
    if probe_profile is not None:
        # Internal integration tests only. There is no CLI plan override, and nonloopback is rejected.
        import ipaddress
        from urllib.parse import urlsplit
        origins=[config[k]['base_url'] for k in ('orin','tianshan')]+[binding['inference']['base_url']]
        if not binding.get('synthetic_loopback_only') or not all(ipaddress.ip_address(urlsplit(x).hostname).is_loopback for x in origins):
            raise ValueError('probe profile allowed only on own numeric loopback services')
        chosen=probe_profile
    clock=Clock();stop=asyncio.Event();tasks={};clients=[];scheduler=None;native_task=None
    # Same user-wide native lock still guards collector instances. This lock also covers preparation and drain.
    with InstanceLock(f'/tmp/tto-field-entry-{os.getuid()}.lock'):
        out.parent.mkdir(parents=True,exist_ok=True)
        from .scheduler import Registry
        Registry(out.parent/'.tto-command-ledger').claim(binding['command_id'],binding['command_id'])
        out.mkdir(mode=0o700)
        ev=Evidence(out);pipeline=Pipeline(out,config,binding,mode,clock,ev)
        stopped_reason=None;scheduler_event_cursor=0;clock_reminder_sent=False;totals={k:0. for k in ['observed_s','measurement_usable_s','model_usable_s','context_ready_s','joint_ready_s','work_paused_s','tj_usable_s','rail_usable_s','PWM_usable_s','temp_context_usable_s']}
        phase_seconds={};resource_prev=None
        previous=None;previous_gate=None;previous_work=False;last_resources=0.;protocol_records=[]
        def emit(name,**details):
            row=dict(event=name,mono_s=clock.now(),at_utc=utc(),command_id=binding['command_id'],native_run_id=pipeline.run_id,**details)
            ev.append('protocol.jsonl',row)
            if name=='request_end':protocol_records.append(row)
        write(out/'launch.json',dict(version=__version__,mode=mode,command_id=binding['command_id'],authorization=binding['authorization'],
              clock_start=clock.bracket(),config=public_config(config),config_sha256=digest(public_config(config)),
              collector_source_identity=source_identity(),binding=binding,profile=chosen if mode=='execute' else None,
              diagnostics_seconds=duration if mode=='diagnose' else None,control_changes=False,
              synthetic_loopback_only=binding.get('synthetic_loopback_only',False),firmware_identity=binding.get('firmware_identity')))
        if mode=='execute':
            p=Path(binding['instrument']['clock_start']['path']);(out/'clock-evidence').mkdir();(out/'clock-evidence/start.original').write_bytes(p.read_bytes())
        collector_duration=duration if mode=='diagnose' else chosen['hard_limit_seconds']
        native_task=asyncio.create_task(collect(config,collector_duration,data_root=out/'native',episode=binding['command_id'],
                   deployment=dict(field_entry_version=__version__,field_command_id=binding['command_id'],field_clock_domain=clock.domain,
                                   firmware_identity=binding.get('firmware_identity')),stop_event=stop,on_record=pipeline.on_record),name='ONLY-native-collector')
        emit('native_collector_task_started',task_identity=id(native_task),collector_instances_created=1)
        result=None;error=None
        try:
            if mode=='execute':
                from .requester import Requester
                # One executor owns up to four per-slot sessions; no other request producer exists.
                clients=[Requester(binding['inference'],out,clock,emit) for _ in range(4)]
                for client in clients:await client.open()
                resident=await asyncio.wait_for(clients[0].check_resident_idle(),min(30.,chosen['preparation_reserve_seconds']))
                write(out/'resident-idle-check.json',resident)
            while True:
                now=clock.now();latest=pipeline.get();run_id=pipeline.run_id or 'PENDING-NATIVE-UUID'
                gate=readiness(latest,now,run_id,formal=True)
                if previous is not None:
                    dt=now-previous;totals['observed_s']+=dt
                    for key,layer in [('measurement_usable_s','collection_available'),('model_usable_s','model_available'),('context_ready_s','field_safety_available')]:
                        totals[key]+=dt*bool(previous_gate[layer])
                    totals['joint_ready_s']+=dt*bool(previous_gate['collection_available'] and previous_gate['model_available'] and previous_gate['field_safety_available'])
                    totals['work_paused_s']+=dt*bool(previous_work and not previous_gate['start_allowed'])
                    phase_seconds[previous_gate['observer_state']]=phase_seconds.get(previous_gate['observer_state'],0.)+dt
                    for label,key in [('tj_usable_s','tj'),('rail_usable_s','power'),('PWM_usable_s','last_successful_pwm'),('temp_context_usable_s','control_context')]:
                        totals[label]+=dt*bool(previous_gate.get('measurement_current',{}).get(key,False))
                previous=now;previous_gate=gate
                ev.append('admission.jsonl',dict(evaluated_mono_s=time.monotonic(),scheduler_mono_s=now,at_utc=utc(),command_id=binding['command_id'],native_run_id=pipeline.run_id,**gate))
                user_stop=(out/'STOP').exists()
                if mode=='diagnose':
                    if user_stop:stopped_reason='user_stop';break
                    if now>=duration:stopped_reason='diagnostic_duration';break
                    if native_task.done():stopped_reason='collector_exited';break
                else:
                    if scheduler is None and pipeline.run_id:
                        scheduler=Scheduler(chosen,dict(max_data_unready_seconds=60,max_request_seconds=60,max_total_requests=4096),pipeline.run_id,binding['command_id'],formal=True)
                    if scheduler is not None:
                        if native_task.done():scheduler.stop('collector_exited')
                        if stop.is_set():scheduler.stop('collector_or_signal_stop')
                        completed=[]
                        for ident,task in list(tasks.items()):
                            if task.done():
                                completed.append(task.result());del tasks[ident]
                        actions,gate=scheduler.tick(now,latest,completed,user_stop=user_stop)
                        previous_work=(scheduler.state=='stage' and scheduler.profile['stages'][scheduler.index]['kind']=='work' and now<scheduler.window_end)
                        for action in actions:
                            ident=action['request_id']
                            if action['kind']=='submit':
                                tasks[ident]=asyncio.create_task(clients[action['slot']].request(ident,action['timeout_s']),name='ONLY-executor-'+ident)
                            else:
                                task=tasks.pop(ident);task.cancel();await asyncio.gather(task,return_exceptions=True)
                        for event in scheduler.events[scheduler_event_cursor:]:
                            ev.append('scheduler-events.jsonl',dict(event,recorded_at_utc=utc()))
                        scheduler_event_cursor=len(scheduler.events)
                        if 0<=scheduler.index<len(scheduler.profile['stages']) and scheduler.profile['stages'][scheduler.index]['kind']=='final_recovery' and not clock_reminder_sent and now>=scheduler.window_end-120:
                            emit('instrument_clock_end_reminder',remaining_s=max(0.,scheduler.window_end-now))
                            clock_reminder_sent=True
                        if scheduler.terminal:stopped_reason=scheduler.reason;break
                    elif user_stop or native_task.done() or now>=chosen['preparation_reserve_seconds']:
                        stopped_reason='user_stop' if user_stop else 'collector_exited' if native_task.done() else 'preparation_budget_exhausted';break
                if now-last_resources>=1:
                    import psutil
                    p=psutil.Process();ct=p.cpu_times();cpu_total=ct.user+ct.system
                    cpu_pct=None if resource_prev is None else 100*(cpu_total-resource_prev[1])/(now-resource_prev[0])
                    resource_prev=(now,cpu_total)
                    ev.append('resources.jsonl',dict(mono_s=now,rss_bytes=p.memory_info().rss,cpu_times=ct._asdict(),cpu_pct_single_core=cpu_pct,
                                                field_log_bytes=ev.bytes,native_log_bytes=sum(f.stat().st_size for f in (out/'native').rglob('*') if f.is_file())))
                    last_resources=now
                await asyncio.sleep(.1)
        except BaseException as exc:
            error=exc;stopped_reason='entry_error:'+type(exc).__name__
        finally:
            stop.set()
            for task in tasks.values():task.cancel()
            await asyncio.gather(*tasks.values(),return_exceptions=True)
            for client in clients:await client.close()
            try:
                result=await asyncio.wait_for(asyncio.shield(native_task),chosen['cleanup_reserve_seconds'] if mode=='execute' else 30.)
            except BaseException as exc:
                native_task.cancel();await asyncio.gather(native_task,return_exceptions=True)
                error=error or exc;stopped_reason='collector_cleanup_failed:'+type(exc).__name__
            if scheduler:
                for row in scheduler.events[scheduler_event_cursor:]:ev.append('scheduler-events.jsonl',dict(row,recorded_at_utc=utc()))
                recorded=set()
                for row in scheduler.requests:
                    ev.append('requests.jsonl',row);recorded.add(row['request_id'])
                for row in protocol_records:
                    if row['request_id'] not in recorded:ev.append('requests.jsonl',row)
            if not scheduler:
                # Diagnostic mode gets an explicit empty request ledger, never a Requester.
                (out/'requests.jsonl').touch(mode=0o600,exist_ok=False)
            ev.close()
            success_gaps=[b-a for a,b in zip(pipeline.fan_success_times,pipeline.fan_success_times[1:])]
            if mode=='diagnose':
                write(out/'diagnostic-precheck.json',dict(last_evaluation=previous_gate,time_coverage=totals,phase_seconds=phase_seconds,
                      current_measurement_model_context_ready=bool(previous_gate and all(previous_gate[k] for k in ['collection_available','model_available','field_safety_available'])),
                      load_authorized=False,automatic_upgrade_to_mixed=False,
                      note='Snapshot/time coverage only. New current authorization, instrument and fresh preflight remain required; not a root cause fix.'))
            write(out/'summary.json',dict(mode=mode,command_id=binding['command_id'],native_run_id=pipeline.run_id,reason=stopped_reason,
                  elapsed_s=clock.now(),time_coverage=totals,phase_seconds=phase_seconds,
                  fan_success_intervals=dict(count=len(success_gaps),max_s=max(success_gaps) if success_gaps else None,
                                             over_original_2_5s=sum(x>2.5 for x in success_gaps)),protocol_requests=len(protocol_records),
                  successful_requests=sum(r['status']=='completed' for r in protocol_records),
                  server_completion_unknown=any(r['status']!='completed' for r in protocol_records),
                  schedule_completed=bool(scheduler and scheduler.reason=='completed'),
                  workload_intent='completed_with_pauses_review_exposure' if totals['work_paused_s']>0 else 'evaluate_actual_protocol_GPU_rails_not_client_slots',
                  collector_task_identity=id(native_task),collector_engine_instance_id=pipeline.engine_id,observer_instances_created=int(pipeline.observer is not None),
                  native_callbacks=pipeline.callbacks,native_run_directories=len(list((out/'native').glob('run-*'))),
                  I02_shared_engine_instance_id=id(pipeline.communication.view.engine) if pipeline.communication else None,
                  I02_preprocessed_views=pipeline.communication.view.process_calls if pipeline.communication else 0,
                  requester_sessions_all_closed=all(client.session.closed for client in clients if client.session is not None),
                  requester_instances_created=len(clients),request_executor_instances_created=int(bool(clients)),
                  own_async_tasks_remaining=sum(not t.done() for t in [native_task,*tasks.values()]),
                  collector_summary=result[1] if result else None,clock_end=clock.bracket(),control_changes=False,
                  field_proven=False,synthetic_loopback_only=binding.get('synthetic_loopback_only',False)))
            write(out/'instrument-link.pending.json',dict(native_run_id=pipeline.run_id,command_id=binding['command_id'],
                  mode=mode,original_csv_sha256=None,end_clock_evidence=None,
                  note='Diagnostic needs no instrument. Mixed attachments use a fresh sidecar directory and keep original run index unchanged.'))
            write(out/'files.json',{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':digest_file(p)} for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'files.json'})
        if error:raise error
        return json.loads((out/'summary.json').read_text())
