"""One native collector; raw quality and bounded pure model consumption are independent."""
import asyncio, copy, json, os, queue, socket, threading, time, subprocess
from collections import deque
from pathlib import Path
from datetime import datetime, timezone
from .support import Clock, utc
from .observe_storage import SessionStore, expire_history
from .observe_predictions import Ledger
from .receiver_resources import read_sample
from . import __version__

def boot_identity():
    p=Path('/proc/sys/kernel/random/boot_id')
    if p.exists():return p.read_text().strip()
    if os.uname().sysname=='Darwin':
        r=subprocess.run(['/usr/sbin/sysctl','-n','kern.bootsessionuuid'],capture_output=True,text=True,timeout=1)
        if r.returncode==0:return r.stdout.strip() or None
    return None

class StopObservation(RuntimeError):
    """Identity or native recording loss; stop only this program."""

class Consumer:
    def __init__(self,store,registration,clock,stop,loop,*,lag_limit=.25,publication=None,prediction_view=None):
        self.publication=publication;self.publication_errors=0;self.prediction_view=prediction_view
        self.store=store;self.registration=registration;self.clock=clock;self.stop=stop;self.loop=loop
        self.queue=queue.Queue(maxsize=64);self.lag_limit=lag_limit;self.closed=threading.Event()
        self.projection=self.communication=None;self.latest_ref=None;self.engine_id=None;self.native_run_id=None;self.device_uuid=registration.get('expected_gpu_uuid')
        self.callbacks=0;self.valid_TJ=0;self.projection_disabled=False;self.dropped=0;self.seen_dropped=0;self.fatal=None;self.model_errors=0;self.history=deque(maxlen=181)
        self.stateful_observers=0;self.ledger=None;self.observer=None;self.predictor=None;self.model_reinitialize=False
        self.thread=threading.Thread(target=self._work,name='frozen-model-consumer',daemon=True);self.thread.start()
    def emit(self,name,row):
        self.store.append(self.store.root,name,row)
        if self.prediction_view and name in ('predictions','scores'):self.prediction_view.committed(name,row)
    def event(self,reason,**extra):self.emit('events',dict(reason=reason,mono_s=time.monotonic(),utc=utc(),**extra))
    def block(self,reason):
        self.fatal=reason;self.loop.call_soon_threadsafe(self.stop.set)
    def publication_gap(self):
        if self.publication:
            try:self.publication.invalidate()
            except Exception:self.publication_errors+=1
    def publish(self, inputs, frame, state, deadline):
        if self.publication and inputs is not None:
            try:self.publication.submit(*inputs,frame,state,deadline)
            except Exception:
                self.publication_errors+=1;self.publication_gap()
    def on_record(self,raw,processed,engine):
        from .projection import SavedStream
        from .comm_bridge import CommunicationBridge
        self.callbacks+=1
        try:
            if raw.get('preceding_queue_gap'):raise StopObservation('native_queue_loss_raw_incomplete')
            if self.projection is None:
                paths=list((self.store.root/'native').glob('run-*/manifest.json'))
                if len(paths)!=1:raise StopObservation('native_manifest_identity_conflict')
                manifest=json.loads(paths[0].read_text())
                if manifest['observer_run_id']!=raw['observer_run_id']:raise StopObservation('native_run_identity_conflict')
                spec=json.loads((Path(__file__).parent/'research/observer-spec.json').read_text())
                self.projection=SavedStream(manifest,spec,engine,retain_quality_history=False);self.communication=CommunicationBridge(manifest,engine)
                self.native_run_id=raw['observer_run_id'];self.engine_id=id(engine)
                self.store.metadata(self.store.root/'native-binding.json',dict(native_run_id=self.native_run_id,
                    native_manifest=str(paths[0].relative_to(self.store.root)),collector_engine_instance_id=id(engine),
                    I02_shared_engine_instance_id=id(self.communication.view.engine),registration=self.registration))
            if raw['observer_run_id']!=self.native_run_id or id(engine)!=self.engine_id:raise StopObservation('second_engine_or_run_identity')
            platform=(raw.get('payload')or{}).get('platform',{}) if raw['kind']=='orin' else {}
            gpu_uuid=(raw.get('payload')or{}).get('gpu',{}).get('device_uuid') if raw['kind']=='orin' else None
            if gpu_uuid:
                if self.device_uuid is not None and gpu_uuid!=self.device_uuid:raise StopObservation('device_gpu_identity_conflict')
                if self.device_uuid is None:
                    self.device_uuid=gpu_uuid
                    self.store.metadata(self.store.root/'source-device-identity.json',dict(device_uuid=gpu_uuid,first_ref=raw['ref'],device_id=self.registration['device_id'],scope='observed stable GPU identity; operator thermal configuration remains separate'))
            for k,v in (self.registration.get('expected_platform') or {}).items():
                if v is not None and platform and platform.get(k)!=v:raise StopObservation('device_platform_identity_conflict')
            comm=self.communication.feed(raw,processed)
            if raw['kind']=='orin' and processed.get('quality',{}).get('accepted') and comm['measurement']['TJ_and_rails']['raw_valid']:
                self.valid_TJ+=1
            if self.projection_disabled:
                self.emit('observations',dict(ref=raw['ref'],native_run_id=self.native_run_id,mono_s=raw['mono_s'],received_at_utc=raw['received_at_utc'],kind=raw['kind'],
                    measurement=None,raw_quality=processed['quality'],model_component='projection_disabled'))
                self.publication_gap()
                return
            frame=self.projection.feed(raw,processed)
            if not comm['measurement']['TJ_and_rails']['raw_valid']:
                for k in ('tj','power'):
                    if frame['measurement'][k]:frame['measurement'][k]['raw_valid']=False
                frame['new_TJ']=False
            frame['_communication']=comm
            # The raw native record and original quality were flushed before this callback.
            self.emit('observations',dict(ref=raw['ref'],native_run_id=self.native_run_id,mono_s=raw['mono_s'],
                received_at_utc=raw['received_at_utc'],kind=raw['kind'],source_epoch=frame['identity']['source_epoch'],measurement=frame['measurement'],
                raw_quality=processed['quality']))
            queued=copy.deepcopy(frame)
            if self.publication:
                try:queued['_web_input']=copy.deepcopy((raw,dict(quality=processed['quality'])))
                except Exception:
                    self.publication_errors+=1;self.publication_gap()
            try:self.queue.put_nowait(queued)
            except queue.Full:
                self.dropped+=1;self.event('model_queue_full_raw_preserved',ref=raw['ref'],dropped_frames=self.dropped);self.publication_gap()
        except StopObservation as exc:self.event(str(exc),ref=raw['ref']);self.block(str(exc))
        except OSError as exc:self.block('recorder_error:'+type(exc).__name__)
        except Exception as exc:
            from tto.storage import LimitReached
            if isinstance(exc,LimitReached):self.block('recorder_limit:'+str(exc));return
            self.publication_gap()
            self.projection_disabled=True;self.model_errors+=1
            self.event('projection_error_model_disabled_raw_continues',error=type(exc).__name__,ref=raw['ref'])
    def _model_import(self):
        from .g2_model.g2_runtime import Predictor,ThermalObserver
        self.predictor=Predictor();self.observer=ThermalObserver(self.predictor.spec);self.stateful_observers=1
    def _reset(self,frame,reason):
        if self.ledger:self.ledger.finish(frame['t'],reason)
        self.history.clear()
        if self.observer is not None:self.observer.x=self.observer.P=None
        frame['source_reset']=True;frame['reset_reason']=reason
    def _work(self):
        try:
            try:self._model_import()
            except Exception as exc:self.model_errors+=1;self.event('model_initialization_failed_raw_continues',error=type(exc).__name__)
            while not self.closed.is_set() or not self.queue.empty():
                try:frame=self.queue.get(timeout=.1)
                except queue.Empty:continue
                try:
                    inputs=frame.pop('_web_input',None)
                    if self.projection_disabled:
                        if self.ledger:self.ledger.finish(frame['t'],'projection_disabled')
                        continue
                    if self.ledger is None:
                        ident=dict(self.registration,session_id=self.registration['session_id'],run_id=frame['identity']['run_id'],
                            model_id=self.predictor.manifest['model_id'] if self.predictor else None,software_version=__version__,model_sha256=frame['identity']['model_sha256'],spec_sha256=frame['identity']['spec_sha256'],clock_domain=self.clock.domain)
                        self.ledger=Ledger(self.emit,ident)
                    dropped=self.dropped
                    if dropped!=self.seen_dropped:self._reset(frame,'model_consumer_gap_raw_preserved');self.seen_dropped=dropped
                    if time.monotonic()-frame['t']>self.lag_limit:
                        self.event('model_consumer_late_raw_preserved',ref=frame['ref']);self._reset(frame,'model_consumer_lag');self.publication_gap();continue
                    try:
                        if self.observer is None:raise ValueError('model_not_initialized')
                        state=self.observer.step(frame)
                    except Exception as exc:
                        self.model_errors+=1;self.model_reinitialize=True
                        self.event('model_computation_error_raw_continues',error=type(exc).__name__,ref=frame['ref'])
                        state=dict(identity=frame['identity'],generated_at_mono_s=frame['t'],observed_through_ref=frame['ref'],
                            measurement=frame['measurement'],safety=frame['safety'],observer=dict(phase='unavailable',available=False,reasons=['model_error']))
                    if self.model_reinitialize:
                        # Next successful step must cold-start; no fabricated continuity through an exception.
                        frame['source_reset']=True;frame['reset_reason']='model_computation_error';self.model_reinitialize=False
                        if self.observer:self.observer.x=self.observer.P=None
                    outputs=[];tj=frame['measurement']['tj']
                    valid=frame['new_TJ'] and tj and tj['raw_valid']
                    if valid:
                        origin=dict(ref=tj['source_ref'],received_at_mono_s=tj['observed_mono_s'],value_C=tj['value_C'],raw_valid=True,
                            source_epoch=frame['identity']['source_epoch'],clock_domain=self.clock.domain)
                        self.history.append(origin)
                        if self.ledger.last_anchor is None or frame['t']-self.ledger.last_anchor>=self.ledger.stride:
                            try:
                                if self.predictor is None:raise ValueError('predictor_unavailable')
                                calc=time.monotonic()
                                rows=self.predictor.predict(state,origin=origin,observed_through=dict(ref=frame['ref'],mono_s=frame['t'],clock_domain=self.clock.domain),
                                    issued_at=dict(mono_s=calc,utc=utc(),clock_domain=self.clock.domain),identity=self.ledger.identity,publication_mode='live',history=list(self.history))
                                outputs=[dict(method=x['method'],horizon_s=x['horizon_s'],value_C=x['value_C'],reason=x['unavailable_reasons'],
                                    assumptions=x.get('condition'),computation_id=x['prediction_id'],calculation_started_at=x['issued_at'],state_used=x.get('state_used'),history_refs=x.get('history_refs')) for x in rows]
                            except Exception as exc:
                                self.model_errors+=1;self.event('prediction_error_raw_continues',error=type(exc).__name__,ref=frame['ref'])
                                outputs=[dict(method='B0',horizon_s=h,value_C=tj['value_C']) for h in (15,45,90)]
                    issued=time.monotonic()
                    if issued-frame['t']>self.lag_limit:
                        self._reset(frame,'model_computation_late');outputs=[];state['observer']=dict(phase='unavailable',available=False,reasons=['computation_late'])
                    self.ledger.consume(frame,issued,outputs,state_status=state['observer']['phase'],wall_clock=dict(utc=utc(),mono_s=issued))
                    deadline=min(issued+2.5,frame['t']+2.5)
                    self.latest_ref=frame['ref']
                    if self.prediction_view:self.prediction_view.committed('context',(frame,state,deadline))
                    self.publish(inputs,frame,state,deadline)
                except (OSError,ValueError) as exc:self.block('derived_recorder_error:'+type(exc).__name__)
                except Exception as exc:
                    self.model_errors+=1;self.event('model_consumer_error_raw_continues',error=type(exc).__name__)
                finally:self.queue.task_done()
        except Exception as exc:self.block('consumer_worker_failure:'+type(exc).__name__)
    def close(self):self.closed.set();self.thread.join(timeout=2);return not self.thread.is_alive()

async def run_observe(config,registration,out,duration,*,local_loopback=False,storage_options=None,grant=None,publication_descriptor=None):
    from .numeric_policy import initialize
    from tto.collector import collect
    from tto.config import public_config
    from tto.util import digest
    import psutil
    policy=initialize();clock=Clock();stop=asyncio.Event();loop=asyncio.get_running_loop()
    registration=dict(registration,session_id=registration['session_id'],source_scope='self_owned_loopback' if local_loopback else 'operator_registered_device',observer_host_actual=socket.gethostname(),
        boot_id=boot_identity(),clock_domain=clock.domain)
    from .scheduler import Registry
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Registry(Path(out).parent/'.tto-observe-ledger').claim(registration['session_id'],registration['session_id'])
    store=SessionStore(out,**(storage_options or {}))
    publication=None;publication_error=None
    from .prediction_view import PredictionView
    prediction_view=PredictionView(clock.origin) if publication_descriptor is not None else None
    if publication_descriptor is not None:
        try:
            from .web_publication import Publication
            publication=Publication(publication_descriptor,registration['boot_id'],registration['device_id'],process_clock_domain=clock.domain,prediction_view=prediction_view).start()
        except Exception as exc:publication_error=dict(phase='initialization',error_class=type(exc).__name__)
    consumer=Consumer(store,registration,clock,stop,loop,publication=publication,prediction_view=prediction_view)
    proc=psutil.Process();creation=proc.create_time();reason='duration';native=None;error=None
    retention_day=None;start=last_status=None
    def prepare_recording():
        nonlocal retention_day,start,last_status
        retention_day=datetime.now(timezone.utc).date()
        expired=expire_history(store.root,registration['device_id'],socket.gethostname(),retention_day)
        store.metadata(store.root/'history-retention.json',dict(contract='TTO-OBSERVE-RETENTION-v1',retention_days=30,
            day=retention_day.isoformat(),device_id=registration['device_id'],host=socket.gethostname()))
        store.metadata(store.root/'thread-policy.json',policy)
        store.metadata(store.root/'launch.json',dict(version=__version__,publication_requested=publication_descriptor is not None,mode='observe',registration=registration,clock_start=clock.bracket(),
            authorization=grant,duration_s=duration,session_max_s=86400,storage_budget=dict(total_bytes=store.budget,segment_bytes=store.segment_bytes,chunk_bytes=store.chunk_bytes),
            recording=dict(contract='TTO-OBSERVE-HISTORY-v2',encoding='gzip-jsonl-level1-sync-flush',
                observations='measurements, validity and source references; full native input retained',states_persisted=False),
            legacy_native_config=public_config(config),config_sha256=digest(public_config(config)),local_loopback=local_loopback,
            Requester_count=0,sidecar_count=0,experiment_authorization=False,control_permission=False,process_created=creation))
        if expired:consumer.event('history_days_expired',days=expired,retention_days=30)
        start=time.monotonic();last_status=start-10
    task=asyncio.create_task(collect(config,duration,data_root=store.root/'native',episode=registration['session_id'],run_type='observe',
        deployment=dict(observe_contract='TTO-OBSERVE-v1',device_registration=registration,simulated=local_loopback,synthetic_loopback_only=local_loopback),stop_event=stop,on_record=consumer.on_record,observe_store=store,on_locked=prepare_recording))
    workload=None
    if registration.get('workload_event_source'):
        from .observe_workload import EventTail
        source=registration['workload_event_source'];workload=EventTail(source['path'],source,clock.domain,consumer.emit)
    checkpoint=False
    from .observe_limits import ReceiverBudget
    budget=ReceiverBudget();prev=None;resource_state=None
    try:
        while not task.done():
            await asyncio.sleep(1)
            if task.done():break
            now=time.monotonic();sample,prev=read_sample(now-start,prev)
            sample.update(sampled_at_mono_s=now,clock_domain=clock.domain,interval_origin_mono_s=start)
            store.append(store.root,'resources',sample)
            budget_reason=budget.sample(sample,now-start)
            resource_state=dict(cpu_single_core_rolling10s=budget.mean,mean_target_pct=5,hard_mean_pct=8,hard_sustain_s=30,rss_limit_bytes=128*1024**2)
            if budget_reason:reason=budget_reason;stop.set()
            if workload:workload.tick()
            today=datetime.now(timezone.utc).date()
            # Only after the native collector has acquired its exclusive lock.
            if consumer.native_run_id and today!=retention_day:
                expired=await asyncio.to_thread(expire_history,store.root,registration['device_id'],socket.gethostname(),today)
                if expired:consumer.event('history_days_expired',days=expired,retention_days=30)
                retention_day=today
            if not checkpoint and now-start>=7200:
                store.metadata(store.root/'two-hour-checkpoint.json',dict(elapsed_s=now-start,blocking_reason=consumer.fatal,valid_TJ_observed=consumer.valid_TJ,
                    model_trial='insufficient_observations_diagnostic_only' if not consumer.valid_TJ else 'conditional_observation',continue_within_same_authorized_window=not stop.is_set()))
                checkpoint=True
            if now-last_status>=10 or stop.is_set():
                store.metadata(store.root/'status.json',dict(running=not stop.is_set(),pid=os.getpid(),process_created=creation,
                    clock_domain=clock.domain,elapsed_s=now-start,reason=reason if stop.is_set() else None,native_run_id=consumer.native_run_id,
                    collection=True,latest_observed_ref=consumer.latest_ref,model_component='disabled_projection_error' if consumer.projection_disabled else 'consuming',model_queue_frames=consumer.queue.qsize(),model_dropped_frames=consumer.dropped,
                    resource=resource_state,experiment_authorization=False,control_permission=False,business_events=dict(last_event=workload.current,source_health='unknown_without_heartbeat',scope='counts_at_event_only') if workload else 'unknown'))
                last_status=now
        native=await task
        if consumer.fatal:reason=consumer.fatal
        elif reason=='duration':reason=native[1]['stop_reason']
    except Exception as exc:
        error=type(exc).__name__+':'+str(exc)[:200];reason='observe_software_error';stop.set()
    finally:
        stop.set()
        if not task.done():
            try:native=await asyncio.wait_for(asyncio.shield(task),3)
            except (asyncio.TimeoutError,Exception) as exc:reason='native_cleanup_unconfirmed';error=type(exc).__name__
        closed=await asyncio.to_thread(consumer.close)
        if not closed:reason='model_cleanup_unconfirmed'
        end=time.monotonic()
        if consumer.ledger and closed:consumer.ledger.finish(end,'projection_disabled' if consumer.projection_disabled else 'session_end')
        scores=consumer.ledger.summary() if consumer.ledger and closed else dict(reason='model_consumer_not_available_or_not_closed')
        scores['all_native_valid_TJ_denominator']=consumer.valid_TJ
        publication_status=None
        if publication:
            try:publication_status=await asyncio.to_thread(publication.close,completed=closed and consumer.ledger is not None)
            except Exception as exc:publication_error=dict(phase='close',error_class=type(exc).__name__)
        summary=dict(version=__version__,publication=publication_status,publication_lifecycle_error=publication_error,publication_callback_errors=consumer.publication_errors,reason=reason,error=error,elapsed_s=end-clock.origin,clock_end=clock.bracket(),pid=os.getpid(),
            native_run_id=consumer.native_run_id,collector_invocation_count=1,collector_count=len(list((store.root/'native').glob('run-*/manifest.json'))),stateful_observer_count=consumer.stateful_observers,
            valid_TJ_observed=consumer.valid_TJ,model_trial='insufficient_observations_diagnostic_only' if not consumer.valid_TJ else 'conditional_observation',
            native_callbacks=consumer.callbacks,I02_processed_views=consumer.communication.view.process_calls if consumer.communication else 0,
            projection_diagnostics=dict(retain_history=False,retained=len(consumer.projection.quality) if consumer.projection else 0,quality_seen=consumer.projection.quality_seen if consumer.projection else 0,complete_quality_stream='observations'),
            shared_native_engine_id=consumer.engine_id,projection_disabled=consumer.projection_disabled,model_errors=consumer.model_errors,model_dropped_frames=consumer.dropped,consumer_stopped=closed,
            Requester_count=0,sidecar_count=0,control_permission=False,experiment_authorization=False,scoring=scores,
            native_summary=native[1] if native else None,thread_policy_same_pid=policy['pid']==os.getpid())
        try:
            store.metadata(store.root/'summary.json',summary,final=True)
            store.metadata(store.root/'status.json',dict(running=False,pid=os.getpid(),reason=reason,summary='summary.json',native_run_id=consumer.native_run_id),final=True)
            store.close()
        except (OSError,ValueError) as exc:
            raise RuntimeError('recording_finalize_failed:'+type(exc).__name__) from exc
    return summary
