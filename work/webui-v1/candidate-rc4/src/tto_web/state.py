"""Atomic display snapshots and causal, immutable G2-HOLD issuance, independent of clients."""
import copy
import math
import socket
import time
import uuid
from itertools import islice
from collections import deque, namedtuple
from .adapter import SPEC, SPEC_ID, TOPOLOGY
from .common import utc, finite, boot_id, load, short

HORIZONS = (15,45,90)
MODEL_IDS = ('model.Tf_C', 'model.Ts_C', 'model.E_C')
MODEL_LABELS = ('快热状态估计', '慢热状态估计', '等效边界估计')
MODEL_GROUP = ('temperature.tj',) + MODEL_IDS
# Shared lineage and one four-value row, rather than three dict histories.
ModelRow = namedtuple('ModelRow', 't values sample_id received_at_utc source_ref phase reason')


class State:
    def __init__(self, config):
        self.config = config
        self.epoch = str(uuid.uuid4())
        self.seq = 0
        self.packet = None
        self.host_values={}
        self.host_sample_mono=0.
        self.host_sample_utc=None
        self.source_status = '尚未配置观察来源'
        self.source_connected = False
        self.history = {}
        self.history_seen = {}
        self.model_history = deque(maxlen=18002)
        self.model_history_sample = None
        self.model_gap_t = -math.inf
        self.model_history_disposition = None
        self.predictions = deque(maxlen=11070)
        self.prediction_labels={}
        self.events = deque(maxlen=1000)
        self.event_seq = 0
        self.task_event_seq=0
        self.last_signature = None
        self.last_origin = -math.inf
        self.last_tj = None
        self.solver = None
        self.clients = set()
        self.dropped = 0
        self.last_advisory_basis = None
        self.curve = load(config['advisory']['curve_manifest']) if config.get('advisory',{}).get('curve_manifest') else None
        if self.curve:
            self.validate_curve(self.curve)
        self._snapshot = self.empty()

    def prepare_model(self):
        if self.solver is None:
            from tto_field.research.observer import ThermalObserver
            self.solver = ThermalObserver(SPEC)

    @staticmethod
    def validate_curve(c):
        if c.get('method_id') != 'CURVE-REFERENCE-v1' or not c.get('verified') or c.get('temperature_binding')!='agx_info.temperature.tj' or not c.get('device_id') or not c.get('curve_id') or not isinstance(c.get('source_config_sha256'),str) or len(c['source_config_sha256'])!=64 or c.get('fan_id')!=0:
            raise ValueError('curve manifest requires verified identity/binding/method')
        points=c.get('points',[])
        if len(points)<2 or any(len(p)!=2 or not all(finite(x) for x in p) or not 0<=p[1]<=100 for p in points) or any(a[0]>=b[0] for a,b in zip(points,points[1:])):
            raise ValueError('curve must contain ordered in-domain temperature/PWM points')
        body={k:v for k,v in c.items() if k!='sha256'}
        from tto.util import digest
        if c.get('sha256')!=digest(body):
            raise ValueError('curve hash mismatch')

    def empty(self):
        return dict(schema_version='TTO-WEB-SNAPSHOT-v1',snapshot_seq=self.seq,service_epoch=self.epoch,
            run_id=None,source_epoch=None,mode='waiting',server_time_utc=utc(),clock_domain_id=None,run_elapsed_ms=None,
            metrics=[],model=dict(model_id=None,spec_id=None,phase='not_loaded',remaining_valid_ms=0.,Tf_C=None,Ts_C=None,E_C=None,
                calibrated_confidence=None,nodes=copy.deepcopy(TOPOLOGY['nodes']),edges=copy.deepcopy(TOPOLOGY['edges'])),
            predictions=[],advisory=dict(status='not_configured',remaining_valid_ms=0.,provider_id=None,value_percent=None,reason='暂无可用建议映射',device_write_permitted=False),
            context=dict(observed_device=None,tto_host=socket.gethostname(),task_metadata_available=False,active_requests=None,control_owner='TianshanOS',tto_role='read_only'),
            health=dict(web_connected=True,measurement_status='waiting',protection_status='unknown',protection_remaining_valid_ms=0.),event_cursor=None)

    def event(self, source, reason, t=None, severity='info'):
        now=utc()
        p=self.packet if t is not None else None
        identity=dict(service_epoch=self.epoch,run_id=p['run_id'] if p else None,source_epoch=p['source_epoch'] if p else None)
        if self.events and (self.events[-1]['source'],self.events[-1]['reason'])==(source,reason) and all(self.events[-1].get(k)==v for k,v in identity.items()):
            self.events[-1].update(last_at_utc=now,count=self.events[-1]['count']+1)
            return
        self.event_seq+=1
        self.events.append(dict(id=str(self.event_seq),source=source,reason=reason,severity=severity,
            elapsed_ms=t if p else None,first_at_utc=now,last_at_utc=now,count=1,**identity))

    def current_events(self):
        p=self.packet
        return [e for e in self.events if e['run_id'] is None or p and (e['run_id'],e['source_epoch'])==(p['run_id'],p['source_epoch'])]

    def accept(self, packet, now=None):
        accepted_at = time.perf_counter()
        now = time.monotonic() if now is None else now
        if packet.get('schema')=='TTO-WEB-DISPLAY-GAP-v1':
            if packet.get('boot_id')!=boot_id() or packet.get('clock_domain_id')!='host-monotonic:'+boot_id():
                raise ValueError('unverified display gap')
            self.event('publication','显示编码或发布失败；当前显示已撤销',severity='warning')
            self.disconnect('显示发布暂断；等待下一份合格快照')
            return
        if packet.get('schema')!='TTO-WEB-PUBLICATION-v1' or packet.get('boot_id')!=boot_id() or packet.get('clock_domain_id')!='host-monotonic:'+boot_id():
            raise ValueError('unverified producer clock domain')
        if boot_id().startswith('test:') and packet.get('mode')!='test_replay':raise ValueError('test clock cannot be live')
        if packet['model_id']!=SPEC['model_sha256'] or packet['spec_id']!=SPEC_ID:
            raise ValueError('frozen model/spec mismatch')
        if not (finite(packet['input_mono_s']) and finite(packet['origin_mono_s']) and packet['origin_mono_s']<=packet['input_mono_s']<=now+.05):
            raise ValueError('producer monotonic time is not comparable')
        old=self.packet
        signature=(packet['run_id'],packet['source_epoch'],packet['model_id'],packet['spec_id'])
        old_signature=None if not old else (old['run_id'],old['source_epoch'],old['model_id'],old['spec_id'])
        if old_signature!=signature:
            self.history.clear(); self.history_seen.clear(); self.last_origin=-math.inf; self.last_tj=None;self.task_event_seq=0
            self.model_history.clear(); self.model_history_sample=None
            self.model_gap_t=-math.inf; self.model_history_disposition=None
            self.last_signature=None
            self.events=deque((e for e in self.events if e['run_id'] is None),maxlen=1000)
            for p in self.predictions:
                if p['status']=='pending':p['status']='not_comparable'
        elif packet['input_mono_s']<old['input_mono_s']:
            raise ValueError('producer time regression')
        if old_signature==signature:
            self.expire_model_history(now)
        self.packet=copy.deepcopy(packet)
        if old_signature!=signature:self.event('source','已切换观察过程，曲线从新过程开始',0)
        self.source_connected=True;self.source_status='正在观察'
        elapsed=(packet['input_mono_s']-packet['origin_mono_s'])*1000
        if packet.get('publication_gap'):
            self.event('publication','显示发布流丢帧，未跨缺口匹配预测',elapsed,'warning')
            for pred in self.predictions:
                if pred['status']=='pending':pred['status']='not_comparable'
            for series in self.history.values():
                series.append(dict(t=elapsed,value=None,sample_id=None,received_at_utc=None,status='unknown',source_ref=None))
        metrics={m['id']:m for m in packet['metrics']}
        tj=metrics.get('temperature.tj')
        self.record_model_history(packet, tj, now, elapsed)
        fresh_tj=bool(packet['new_tj'] and packet['tj_sample_id']!=self.last_tj and tj and tj['status']=='valid' and tj['value'] is not None)
        if fresh_tj:
            self.last_tj=packet['tj_sample_id']
            label_time=tj['as_of_elapsed_ms']
            for p in self.predictions:
                if p['status']!='pending' or (p['run_id'],p['source_epoch'],p['model_id'],p['spec_id'])!=signature:
                    continue
                if p['target_elapsed_ms']<=label_time<=p['target_elapsed_ms']+2000:
                    p.update(status='matched',observed_C=tj['value'],error_C=p['value_C']-tj['value'],settled_elapsed_ms=(now-packet['origin_mono_s'])*1000)
                    self.prediction_labels[p['prediction_id']]={'label_elapsed_ms':label_time,'received_at_utc':tj['received_at_utc'],'sample_id':tj['sample_id'],'source_ref':tj['source_ref']}
            observer=packet['model']
            inputs=observer.get('conditional_inputs_rails_W_PWM')
            eligible=observer['phase'] in ('tracking','degraded') and packet['consumable_until_mono_s']>now and inputs and all(finite(v) for v in inputs) and packet['input_mono_s']-self.last_origin>=1.
            if eligible:
                # The frozen comparison anchors Tf to real TJ, retaining causal Ts/E.
                start=[tj['value'],observer['Ts_C'],observer['E_C']]
                self.prepare_model()
                values=[float(self.solver.mean_step(start,inputs,h)[0]) for h in HORIZONS]
                issued=(now+time.perf_counter()-accepted_at-packet['origin_mono_s'])*1000
                for horizon,value in zip(HORIZONS,values):
                    if len(self.predictions)==self.predictions.maxlen:
                        removed=self.predictions.popleft();self.prediction_labels.pop(removed['prediction_id'],None)
                    target=label_time+horizon*1000
                    self.predictions.append(dict(prediction_id=str(uuid.uuid4()),run_id=packet['run_id'],source_epoch=packet['source_epoch'],
                        model_id=packet['model_id'],spec_id=packet['spec_id'],scenario='HOLD',horizon_s=horizon,
                        origin_elapsed_ms=label_time,issued_elapsed_ms=issued,target_elapsed_ms=target,input_cutoff_elapsed_ms=label_time,
                        value_C=value,phase_at_origin=observer['phase'],evidence_mode='test_replay' if packet['mode']=='test_replay' else 'issued_online',
                        status='late_publication' if issued>=target else 'pending',observed_C=None,error_C=None))
                self.last_origin=packet['input_mono_s']
        # Input timestamps advance only after consuming the ordered source stream.
        # Web wall time cannot seal a window ahead of a delayed legal source label.
        for pred in self.predictions:
            if pred['status']=='pending' and (pred['run_id'],pred['source_epoch'],pred['model_id'],pred['spec_id'])==signature and elapsed>pred['target_elapsed_ms']+2000:
                pred.update(status='missing_label',settled_elapsed_ms=(now-packet['origin_mono_s'])*1000)
        for m in packet['metrics']:
            id=m['id']
            if not id.startswith(('temperature.','power.','fan.pwm.','fan.rpm')):
                continue
            if id.endswith('.average'):
                continue
            key=(m['sample_id'],m['status'])
            if self.history_seen.get(id)!=key:
                series=self.history.setdefault(id,deque(maxlen=18002))
                series.append(dict(t=elapsed if m['value'] is None else m['as_of_elapsed_ms'],value=m['value'],sample_id=m['sample_id'],
                    received_at_utc=m['received_at_utc'],status=m['status'],source_ref=m['source_ref']))
                self.history_seen[id]=key
        for event in packet.get('task',{}).get('events',[]):
            if event['seq']>self.task_event_seq:
                self.event('runner',event['label'],max(0.,(event['at_mono_s']-packet['origin_mono_s'])*1000))
                self.task_event_seq=event['seq']
        phase=packet['model']['phase']
        safety=packet['safety']
        signature_state=(phase,tuple(safety.get(k) for k in ('guard','fault','temp_stale','fan_fresh','binding_fresh')))
        if signature_state!=self.last_signature:
            self.event('observer','模型阶段：'+phase,elapsed)
            if any(safety.get(k) is True for k in ('guard','fault','temp_stale')):
                self.event('board','主板明确保护或失温，观察建议已暂停',elapsed,'warning')
            self.last_signature=signature_state
        if packet.get('event_reason'):
            self.event('source',packet['event_reason'],elapsed,'warning')
        self.refresh(now)

    def disconnect(self, reason='数据暂断', ended=False):
        if self.source_connected:self.event('web-source',reason,severity='warning')
        if self.packet:
            self.model_gap('source_ended' if ended else 'source_disconnected',
                           (time.monotonic()-self.packet['origin_mono_s'])*1000)
        self.source_connected=False;self.source_status=reason
        if not ended:
            for pred in self.predictions:
                if pred['status']=='pending':pred['status']='not_comparable'
        if ended and self.packet and self.packet['mode']!='test_replay':self.packet["mode"]="ended"
        self.refresh()

    def advisory(self, snapshot):
        result=dict(status='not_configured',provider_id=None,value_percent=None,reason='暂无可用建议映射',device_write_permitted=False)
        self.last_advisory_basis=None
        if not self.curve:return result
        result.update(provider_id='CURVE-REFERENCE-v1',status='withheld',reason='数据/模式/保护上下文不满足；天山OS继续负责保护')
        p=self.packet
        if not p:return result
        s=p['safety'];metrics={m['id']:m for m in snapshot['metrics']}
        tj=metrics.get('temperature.tj',{})
        preds=[v for v in snapshot['predictions'] if v['horizon_s']==45 and v['status']=='pending' and v['origin_elapsed_ms']==(tj.get('as_of_elapsed_ms'))]
        good=all(s.get(k) is False for k in ('guard','fault','temp_stale','manual_mode')) and s.get('mode')=='auto' and s.get('enabled') is True and s.get('normalized_valid') is True and s.get('fan_fresh') and s.get('binding_fresh') and s.get('confirmed_normal_now')
        if self.curve['device_id']!=p['observed_device'] or self.curve['source_config_sha256']!=p.get('config_id') or not good or tj.get('value') is None or not preds or snapshot['health']['protection_status']!='no_reported_protection' or snapshot['model']['phase'] not in ('tracking','degraded') or metrics.get('fan.pwm.actual',{}).get('value') is None:
            return result
        tref=max(tj['value'],preds[-1]['value_C']);points=self.curve['points']
        if tref<points[0][0] or tref>points[-1][0]:
            result.update(status='out_of_domain',reason='温度超出核实曲线取值域，禁止外推');return result
        lo,hi=next((a,b) for a,b in zip(points,points[1:]) if a[0]<=tref<=b[0])
        value=lo[1]+(hi[1]-lo[1])*(tref-lo[0])/(hi[0]-lo[0])
        result.update(status='available',value_percent=value,reason='实验观察参考，无设备写权限')
        self.last_advisory_basis=dict(method_id='CURVE-REFERENCE-v1',provider_version=1,T_ref_C=tref,curve_id=self.curve['curve_id'],curve_sha256=self.curve['sha256'],device_id=self.curve['device_id'],source_config_sha256=self.curve['source_config_sha256'],fan_id=0,identity_evidence_kind='verified_local_endpoint_config_and_current_binding',temperature_binding=self.curve['temperature_binding'],prediction_id=preds[-1]['prediction_id'],scenario='HOLD',horizon_s=45,input_refs=[tj['source_ref']],value_domain=[points[0][0],points[-1][0]],device_write_permitted=False)
        return result

    def refresh(self, now=None):
        now=time.monotonic() if now is None else now
        snapshot=self.empty();self.seq+=1;snapshot['snapshot_seq']=self.seq
        if self.packet:
            p=self.packet
            elapsed=max(0.,(now-p['origin_mono_s'])*1000)
            snapshot.update(run_id=p['run_id'],source_epoch=p['source_epoch'],mode=p['mode'],clock_domain_id=p['clock_domain_id'],run_elapsed_ms=elapsed)
            snapshot['context']['observed_device']=p['observed_device']
            task=p.get('task',{}).get('context',{})
            if task.get('task_metadata_available'):
                snapshot['context'].update(task_metadata_available=True,active_requests=task.get('active_requests') if self.source_connected else None)
            for raw in p['metrics']:
                m={k:copy.deepcopy(v) for k,v in raw.items() if not k.startswith('_')}
                m['age_lower_bound_ms']=(raw.get('age_lower_bound_ms') or 0)+max(0,now-raw['_at'])*1000
                m['remaining_valid_ms']=max(0.,(raw['_expiry']-now)*1000)
                if (not self.source_connected and m['status']!='unverified') or (raw['_expiry']<=now and m['status']=='valid'):
                    if m['value'] is not None:m['last_observation']={'value':m['value'],'observed_at_utc':m['received_at_utc']}
                    m.update(value=None,status='stale',reason_code='source_disconnected' if not self.source_connected else 'source_expired')
                snapshot['metrics'].append(m)
                # Explicit gap when a previously valid sample expires with no new messages.
                if m['value'] is None and m['id'] in self.history and self.history[m['id']] and self.history[m['id']][-1]['value'] is not None:
                    self.history[m['id']].append(dict(t=min(elapsed,(raw['_expiry']-p['origin_mono_s'])*1000),value=None,sample_id=None,received_at_utc=None,status=m['status'],source_ref=m['source_ref']))
            metrics={m['id']:m for m in snapshot['metrics']}
            tj=next((m for m in p['metrics'] if m['id']=='temperature.tj'),{})
            model_until=self.model_until(p, now)
            self.expire_model_history(now)
            current=now<model_until and self.source_connected and metrics.get('temperature.tj',{}).get('status')=='valid'
            o=p['model'];model=snapshot['model'];model.update(model_id=p['model_id'],spec_id=p['spec_id'],phase=o['phase'] if current else 'unavailable')
            model['remaining_valid_ms']=max(0.,(model_until-now)*1000) if current else 0.
            for key in ('Tf_C','Ts_C','E_C'):model[key]=o[key] if current else None
            metrics={m['id']:m for m in snapshot['metrics']}
            safety=p['safety'];fans=metrics.get('fan.pwm.actual',{});control=metrics.get('control.valid',{})
            protection='unknown'
            if fans.get('status')=='valid' and control.get('status')=='valid':
                if any(safety.get(k) is True for k in ('guard','fault','temp_stale','manual_mode')):protection='active'
                elif all(safety.get(k) is False for k in ('guard','fault','temp_stale','manual_mode')) and safety.get('normalized_valid') is True:protection='no_reported_protection'
            status='valid' if metrics.get('temperature.tj',{}).get('value') is not None else 'unavailable'
            snapshot['health'].update(measurement_status=status,protection_status=protection)
            protection_until=min((m['_expiry'] for m in p['metrics'] if m['id'] in ('fan.pwm.actual','control.valid')),default=now)
            snapshot['health']['protection_remaining_valid_ms']=max(0.,(protection_until-now)*1000) if protection!='unknown' else 0.
            signature=(p['run_id'],p['source_epoch'],p['model_id'],p['spec_id'])
            while self.predictions and (self.predictions[0]['run_id']!=p['run_id'] or self.predictions[0]['origin_elapsed_ms']<elapsed-3690000):
                removed=self.predictions.popleft();self.prediction_labels.pop(removed['prediction_id'],None)
            snapshot['predictions']=list(reversed([copy.deepcopy(v) for v in islice((v for v in reversed(self.predictions) if (v['run_id'],v['source_epoch'],v['model_id'],v['spec_id'])==signature),6)]))
            for node in model['nodes']:
                if 'metric_id' in node:node['status']=metrics.get(node['metric_id'],{}).get('status','unknown')
                elif node['role']=='estimate':node['status']='valid' if model.get(node['state_path']) is not None and current else 'unknown'
                elif node['id']=='forecast':node['status']='valid' if current and any(v['status']=='pending' for v in snapshot['predictions']) else 'unknown'
                elif node['id']=='risk':node['status']='valid' if protection!='unknown' else 'unknown'
                else:node['status']='unknown'
            by_id={n['id']:n for n in model['nodes']}
            for e in model['edges']:
                e['animate_allowed']=bool(current and by_id[e['from']].get('status')=='valid' and by_id[e['to']].get('status')=='valid')
            for series in self.history.values():
                while series and series[0]['t']<elapsed-3600000:series.popleft()
            while self.model_history and self.model_history[0].t<elapsed-3600000:
                self.model_history.popleft()
            snapshot['advisory']=self.advisory(snapshot)
            snapshot['advisory']['remaining_valid_ms']=min(model['remaining_valid_ms'],snapshot['health']['protection_remaining_valid_ms']) if snapshot['advisory']['value_percent'] is not None else 0.
        for id,value in self.host_values.items():
            snapshot['metrics'].append(dict(id=id,label='Web进程单核等效CPU' if id=='host.cpu' else 'Web进程RSS',kind='observed',unit='%' if id=='host.cpu' else 'MiB',value=value,status='valid',reason_code=None,source_id='tto-web-process',source_ref='process:'+self.epoch,sample_id=str(self.host_sample_mono),received_at_utc=self.host_sample_utc,source_time_utc=None,as_of_elapsed_ms=snapshot['run_elapsed_ms'],age_lower_bound_ms=max(0.,(now-self.host_sample_mono)*1000),remaining_valid_ms=max(0.,2000-(now-self.host_sample_mono)*1000),time_quality='same_clock',last_observation=None))
        snapshot['event_cursor']=str(self.event_seq) if self.events else None
        self._snapshot=snapshot
        return snapshot

    def snapshot(self):
        return copy.deepcopy(self._snapshot)

    def prediction_view(self, horizon=45, start=0, end=math.inf, records_after=None):
        s=self._snapshot
        selected=[p for p in self.predictions if (p['run_id'],p['source_epoch'],p['model_id'],p['spec_id'],p['horizon_s'])==(s['run_id'],s['source_epoch'],s['model']['model_id'],s['model']['spec_id'],horizon) and start<=p['origin_elapsed_ms']<=end]
        matched=[p for p in selected if p['status']=='matched'];errors=[abs(p['error_C']) for p in matched]
        elapsed=s['run_elapsed_ms'] or 0
        ordered=sorted(errors);rank=.95*(len(ordered)-1) if ordered else 0
        p95=(ordered[math.floor(rank)]*(1-(rank%1))+ordered[math.ceil(rank)]*(rank%1)) if ordered else None
        summary=dict(issued_count=len(selected),due_count=sum(p['target_elapsed_ms']<=elapsed and p['status'] not in ('late_publication','not_comparable') for p in selected),matched_count=len(matched),missing_label_count=sum(p['status']=='missing_label' for p in selected),unmatched_future_count=sum(p['target_elapsed_ms']>elapsed and p['status']=='pending' for p in selected),late_publication_count=sum(p['status']=='late_publication' for p in selected),not_comparable_count=sum(p['status']=='not_comparable' for p in selected),MAE_C=sum(errors)/len(errors) if errors else None,P95_absolute_C=p95 if errors else None,max_underprediction_C=max((max(-p['error_C'],0) for p in matched),default=None))
        records=[copy.deepcopy(p) for p in selected if records_after is None or p['target_elapsed_ms']>=records_after-2000 or p.get('settled_elapsed_ms',-math.inf)>=records_after]
        return dict(horizon_s=horizon,scenario='HOLD',records=records,records_complete=records_after is None,summary=summary,labels={v['prediction_id']:self.prediction_labels[v['prediction_id']] for v in records if v['prediction_id'] in self.prediction_labels})

    @staticmethod
    def model_until(packet, now):
        tj=next((m for m in packet['metrics'] if m['id']=='temperature.tj'),{})
        return min(packet['consumable_until_mono_s'],tj.get('_expiry',now))

    def model_gap(self, reason, t):
        self.model_history_disposition=reason
        # One break per continuous invalid interval. Keep the barrier even after trim.
        self.model_gap_t=max(self.model_gap_t,t)
        if self.model_history and self.model_history[-1].reason is not None:
            return
        if self.model_history:
            t=max(t,self.model_history[-1].t)
            if t==self.model_history[-1].t:
                self.model_history.pop()
        self.model_gap_t=max(self.model_gap_t,t)
        self.model_history.append(ModelRow(t,(None,None,None,None),None,None,None,None,reason))

    def expire_model_history(self, now):
        if self.packet and self.source_connected:
            until=self.model_until(self.packet,now)
            if now>=until:
                self.model_gap('model_expired',(until-self.packet['origin_mono_s'])*1000)

    def record_model_history(self, packet, tj, now, elapsed):
        if packet.get('publication_gap'):
            self.model_gap('publication_gap',elapsed)
            return
        o=packet['model']
        fresh=bool(packet['new_tj'] and packet['tj_sample_id']!=self.model_history_sample)
        if packet['new_tj']:self.model_history_sample=packet['tj_sample_id']
        reason=None
        if not tj or tj['status']!='valid' or not finite(tj['value']):reason='tj_invalid'
        elif now>=self.model_until(packet,now):reason='model_expired'
        elif o['phase'] not in ('tracking','degraded'):reason='phase_unavailable'
        elif not all(finite(o.get(k)) for k in ('Tf_C','Ts_C','E_C')):reason='nonfinite_state'
        if reason:
            t=(self.model_until(packet,now)-packet['origin_mono_s'])*1000 if reason=='model_expired' else elapsed
            self.model_gap(reason,t)
            return
        if not fresh:
            return
        t=tj['as_of_elapsed_ms']
        # Both values are the same source mono timestamp; tolerate float subtraction only.
        if tj['sample_id']!=packet['tj_sample_id'] or not finite(t) or not math.isclose(t,elapsed,rel_tol=0.,abs_tol=1e-3):
            self.model_gap('alignment_mismatch',elapsed)
            return
        if t<=self.model_gap_t:
            self.model_history_disposition='arrived_after_gap'
            return
        if self.model_history and t<=self.model_history[-1].t:
            return
        self.model_history.append(ModelRow(t,(tj['value'],o['Tf_C'],o['Ts_C'],o['E_C']),
            tj['sample_id'],tj['received_at_utc'],tj['source_ref'],o['phase'],None))
        self.model_history_disposition='accepted'

    def model_series(self, ids, start, end, max_points):
        rows=[r for r in self.model_history if start<=r.t<=end]
        original=len(rows)
        sampled=original>max_points
        if sampled:
            # Four components + three signed differences: at most 14 extrema,
            # plus bucket endpoints. Mandatory breaks/segment edges are extra.
            width=max(1,math.ceil(original/max(1,max_points//16)))
            indices={0,original-1}
            for i,r in enumerate(rows):
                if r.reason is not None:
                    indices.update(j for j in (i-1,i,i+1) if 0<=j<original)
            for offset in range(0,original,width):
                bucket=rows[offset:offset+width]
                indices.update((offset,offset+len(bucket)-1))
                features=[(*r.values,r.values[0]-r.values[1],r.values[2]-r.values[3],r.values[1]-r.values[2])
                          if r.reason is None else (None,)*7 for r in bucket]
                for column in range(7):
                    valid=[j for j,f in enumerate(features) if f[column] is not None]
                    if valid:
                        indices.add(offset+min(valid,key=lambda j:features[j][column]))
                        indices.add(offset+max(valid,key=lambda j:features[j][column]))
            rows=[rows[i] for i in sorted(indices)]
        result={}
        for id in ids:
            if id not in MODEL_GROUP:continue
            column=MODEL_GROUP.index(id)
            result[id]=dict(id=id,label='实测结温（模型采样对齐）' if column==0 else MODEL_LABELS[column-1],
                kind='observed' if column==0 else 'estimate',unit='°C',
                alignment_group='tj_model',time_basis='tj_sample',anchor_metric_id='temperature.tj',
                estimate_stage=None if column==0 else 'posterior',
                sampling='joint_bucket_extrema_and_gaps' if sampled else 'actual_samples',
                original_points=original,returned_points=len(rows),soft_budget_exceeded=len(rows)>max_points,
                points=[dict(t=r.t,value=r.values[column],status='valid' if r.reason is None else 'unknown',
                    sample_id=r.sample_id,received_at_utc=r.received_at_utc,source_ref=r.source_ref,
                    phase_at_sample=r.phase,reason_code=r.reason) for r in rows])
        return result

    def series(self, ids, start, end, max_points):
        joint=self.model_series(ids[:32],start,end,max_points) if any(id in MODEL_IDS for id in ids[:32]) else {}
        result=[]
        for id in ids[:32]:
            if id in joint:
                result.append(joint[id]);continue
            points=[p for p in self.history.get(id,()) if start<=p['t']<=end]
            sampled=False
            if len(points)>max_points:
                # Preserve first/last and extrema per bucket, plus null gaps. Gap-dense
                # inputs may exceed the render budget; never erase a gap to meet it.
                width=max(1,math.ceil(len(points)/max(1,max_points//4)))
                output=[]
                for i in range(0,len(points),width):
                    bucket=points[i:i+width];valid=[(j,p) for j,p in enumerate(bucket) if finite(p['value'])]
                    indices={0,len(bucket)-1}
                    if valid:indices|={min(valid,key=lambda v:v[1]['value'])[0],max(valid,key=lambda v:v[1]['value'])[0]}
                    indices|={j for j,p in enumerate(bucket) if p['value'] is None}
                    output.extend(bucket[j] for j in sorted(indices))
                points=output;sampled=True
            metric=next((m for m in self._snapshot['metrics'] if m['id']==id),{})
            result.append(dict(id=id,label=metric.get('label',id),unit=metric.get('unit'),sampling='bucket_first_last_min_max_and_gaps' if sampled else 'actual_samples',points=points))
        return result
