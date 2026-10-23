"""One native engine + I-02 + frozen observer. The public allowlist has no raw binding."""
import copy
import hashlib
import json
import time
from collections import deque
from pathlib import Path
from tto_field.comm_bridge import CommunicationBridge
from tto_field.projection import SavedStream
from .common import finite, short, boot_id, utc

SPEC_PATH = Path(__import__('tto_field').__file__).parent / 'research/observer-spec.json'
SPEC = json.loads(SPEC_PATH.read_text())
SPEC_ID = hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()
TOPOLOGY = json.loads((Path(__file__).parent / 'contracts/model-topology.json').read_text())


class Adapter:
    def __init__(self, manifest, engine, observed_device=None, test_replay=False, owner=None):
        self.projection = owner.projection if owner else SavedStream(manifest, SPEC, engine)
        self.projection.quality = deque(maxlen=128)
        self.bridge = owner.communication if owner else CommunicationBridge(manifest, engine)
        if owner:
            self.observer = owner.observer
        else:
            from tto_field.research.observer import ThermalObserver
            self.observer = ThermalObserver(SPEC)
        self.run_id = short(manifest['observer_run_id'])
        self.config_id=manifest['config_sha256']
        if boot_id().startswith('test:') and not test_replay:raise ValueError('test clock requires test_replay')
        self.domain = 'host-monotonic:' + boot_id()
        self.origin = None
        self.metrics = {}
        self.observed_device = observed_device
        self.test_replay = test_replay
        self.tj_sample = None
        self.platform = None
        self.source_health={}

    def feed(self, raw, processed):
        comm = self.bridge.feed(raw, processed)
        frame = self.projection.feed(raw, processed)
        if not comm['measurement']['TJ_and_rails']['raw_valid']:
            for k in ['tj', 'power']:
                if frame['measurement'][k]:
                    frame['measurement'][k]['raw_valid'] = False
            frame['new_TJ'] = False
        state = self.observer.step(frame)
        return self.encode(raw, processed, frame, comm, state)

    def encode(self, raw, processed, frame, comm, state):
        t = raw['mono_s']
        if self.origin is None:
            self.origin = t
        epoch = frame['identity']['source_epoch']
        if frame['source_reset']:
            self.metrics.clear()
            self.tj_sample = None
        elapsed = (t - self.origin) * 1000
        payload = raw.get('payload') or {}
        quality = processed['quality'] or {}
        diagnostic=raw.get('poll_diagnostics') or {}
        if raw['kind'] in ('fan','temp','orin','boundary'):
            source=raw['kind'] if raw['kind']!='boundary' else 'orin'
            self.source_health[source]=dict(source=source,last_received_at_utc=raw['received_at_utc'],elapsed_ms=elapsed,quality_reason=quality.get('reason'),error_class=raw.get('error_class') if raw.get('error_class') in ('TimeoutError','ValueError','ClientError','ClientConnectorError','ServerDisconnectedError') else None,timeout_phase=diagnostic.get('last_phase') if diagnostic.get('last_phase') in ('before_request','connection_queued','dns','connect','response_headers','response_body','complete','request_sent','response_headers_received','connection_create_start') else None,round_trip_ms=raw.get('round_trip_ms'))
        ref = self.run_id + ':' + short(raw['ref'])
        sample = str(epoch) + ':' + ref

        def metric(id, label, value, unit, valid, expiry, *, age=0., kind='observed', reason=None, source=None, sample_id=sample, source_time=None):
            # A newly invalid event withdraws the old current value; no backward search.
            prior = self.metrics.get(id)
            last = prior.get('last_observation') if prior else None
            if prior and prior['value'] is not None:
                last = {'value': prior['value'], 'observed_at_utc': prior['received_at_utc']}
            scalar = value if isinstance(value, (str, bool)) or finite(value) else None
            good = valid and scalar is not None
            self.metrics[id] = dict(id=id, label=label, kind=kind, unit=unit, value=scalar if good else None,
                status='valid' if good else 'invalid', reason_code=(reason or raw.get('error_class') or 'native_field_invalid_or_missing') if not good else None,
                source_id=source or raw['kind'], source_ref=ref, sample_id=sample_id,
                received_at_utc=raw['received_at_utc'], source_time_utc=source_time,
                as_of_elapsed_ms=elapsed, age_lower_bound_ms=max(0., age),
                remaining_valid_ms=max(0., (expiry-t)*1000), time_quality='receive_approximation',
                last_observation=last, _expiry=expiry, _at=t)

        if raw['kind'] == 'orin' and quality.get('accepted'):
            meta = payload['telemetry_meta']
            expiry = t + (meta['freshness_timeout_ms'] - quality['age_lower_bound_ms'])/1000
            valid = bool(frame['measurement']['tj'] and frame['measurement']['tj']['raw_valid'])
            for k, v in payload.get('temperature', {}).items():
                if k in ('tj','cpu','gpu','soc012','soc345','soc0','soc1','soc2'):
                    metric('temperature.'+k, k.upper()+'温度', v, '°C', valid, expiry, age=quality['age_lower_bound_ms'])
            for k, rail in payload.get('power', {}).items():
                if k not in ('vdd_gpu','vdd_cpu_soc_mss','vin_sys_5v0','vdd_gpu_soc','vdd_cpu_cv','vdd_in'):
                    continue
                id = {'vdd_gpu':'gpu','vdd_cpu_soc_mss':'cpu_soc_mss'}.get(k, 'other.'+k)
                for field in ('current','average'):
                    value = rail.get(field)
                    unit_ok = rail.get('unit') in ('mW','W')
                    if finite(value) and rail.get('unit') == 'mW':
                        value /= 1000
                    metric('power.'+id+('' if field=='current' else '.average'), k.upper()+(' 瞬时' if field=='current' else ' 平均（平均窗未知）'), value, 'W', valid and unit_ok, expiry)
            cores = payload.get('cpu', {}).get('cores', [])
            usage = []
            for core in cores[:128]:
                if not isinstance(core.get('id'), int):
                    continue
                online = core.get('online') is not False
                for k, unit in [('usage','%'),('freq','MHz')]:
                    v = core.get(k)
                    metric(f'cpu.cores.{core["id"]}.{k}', f'CPU {core["id"]} '+k, v, unit, valid and online and finite(v), expiry)
                if online and finite(core.get('usage')):
                    usage.append(core['usage'])
            coverage = len(usage) == len(cores) and len(usage)>0
            metric('usage.cpu.mean', 'Jetson CPU均值'+('（覆盖不完整）' if not coverage else ''), sum(usage)/len(usage) if usage else None, '%', valid and bool(usage), expiry, kind='derived')
            metric('usage.cpu.max', 'Jetson CPU最大核心', max(usage) if usage else None, '%', valid and bool(usage), expiry, kind='derived')
            metric('cpu.valid_cores', '有效CPU核心数', len(usage), 'cores', valid, expiry, kind='derived')
            for group in ('ram','swap'):
                mem = payload.get('memory', {}).get(group, {})
                for field in ('used','total','cached'):
                    metric(f'memory.{group}'+('' if field=='used' else '.'+field), group.upper()+' '+field, mem.get(field), mem.get('unit') if mem.get('unit') in ('MB','MiB','GB') else None, valid and finite(mem.get(field)) and mem.get('unit') in ('MB','MiB','GB'), expiry)
            # NVML has its own sample identity and expiry. A WS sample cannot renew it.
            gpu = payload.get('gpu', {})
            gq = quality.get('gpu', {})
            gpuid = str(epoch)+':gpu:'+short((gpu.get('device_uuid'),gpu.get('sampled_at_utc')))
            age = gpu.get('age_at_telemetry_receive_ms')
            timeout = gpu.get('freshness_timeout_ms')
            gvalid = valid and gpu.get('status')=='valid' and gq.get('contract_valid') is True and finite(age) and finite(timeout) and age<timeout
            old = self.metrics.get('usage.gpu')
            gexpiry = t + (timeout-age)/1000 if finite(age) and finite(timeout) else t
            if old and old['sample_id']==gpuid:
                # Same cache can be explicitly revoked, and its expiry may only shrink.
                gexpiry = min(gexpiry, old['_expiry'])
                if not gvalid:
                    old.update(value=None,status='invalid',reason_code='gpu_source_invalid')
                old['_expiry'] = gexpiry
            else:
                metric('usage.gpu','GPU利用率（NVML独立期限）',gpu.get('utilization_pct'),'%',gvalid,gexpiry,age=age if finite(age) else 0,source='nvml',sample_id=gpuid,source_time=gpu.get('sampled_at_utc'))
            self.platform = {k:payload.get('platform', {}).get(k) for k in ('family','soc','gpu_backend')}
            if frame['new_TJ']:
                self.tj_sample = sample
        if raw['kind'] in ('fan','temp'):
            group = raw['kind']
            if group == 'fan':
                fans = payload.get('data', {}).get('fans', [])
                fan = next((v for v in fans if v.get('id')==0), {})
                fm = frame['measurement']['last_successful_pwm']
                valid = bool(fm and fm['raw_valid'] and fm['source_ref']==raw['ref'])
                expiry = t + SPEC['input_policy']['fan_raw_TTL_s']
                metric('fan.pwm.actual','成功PWM',fm['value_percent'] if fm else None,'%',valid,expiry)
                metric('fan.pwm.target','天山OS目标PWM',fan.get('target_duty'),'%',valid,expiry)
                metric('fan.rpm','风扇RPM',None,'RPM',False,expiry,reason='tachometer_validity_not_confirmed')
                self.metrics['fan.rpm'].update(status='unverified', last_observation={'value':fan['rpm'],'observed_at_utc':raw['received_at_utc']} if finite(fan.get('rpm')) else None)
                for key, label, unit in [('mode','控制模式',None),('enabled','风扇启用',None),('running','主板running',None),('auto_state','自动状态',None),('controller_gain','主板gain',None),('slope_c_per_min','主板温度斜率','°C/min'),('predicted_temperature','主板预测诊断','°C'),('cooling_response','主板cooling_response（单位未核实）',None),('control_temperature','主板控制温度','°C'),('guard_active','主板guard',None),('fault','主板fault',None),('temp_stale','主板失温',None)]:
                    metric('fan.'+key,label,fan.get(key),unit,valid,expiry)
            else:
                data = payload.get('data', {})
                cm = frame['measurement']['control_context']
                valid = bool(cm and cm['raw_valid'] and cm['source_ref']==raw['ref'])
                expiry = t + SPEC['input_policy']['temp_raw_TTL_s']
                for key in ('temperature_c','valid','manual_mode','active_source','initialized'):
                    metric('control.'+key,'主板 '+key,data.get(key),'°C' if key=='temperature_c' else None,valid,expiry)
        # I-02 has precedence, even if a previous accepted raw sample is cached.
        for id, m in self.metrics.items():
            if id.startswith(('temperature.','power.','usage.','cpu.','memory.')) and not comm['measurement']['TJ_and_rails']['raw_valid']:
                if m['value'] is not None:
                    m['last_observation'] = {'value':m['value'],'observed_at_utc':m['received_at_utc']}
                m.update(value=None,status='invalid',reason_code='I02_source_withdrawn')
        model = state['observer']
        return dict(schema='TTO-WEB-PUBLICATION-v1', run_id=self.run_id, source_epoch=epoch,
            clock_domain_id=self.domain, boot_id=boot_id(), origin_mono_s=self.origin,
            input_mono_s=t, generated_mono_s=time.monotonic(), consumable_until_mono_s=min(t+2.5,time.monotonic()+2.5),
            mode='test_replay' if self.test_replay else 'live',config_id=self.config_id,
            metrics=copy.deepcopy(list(self.metrics.values())), model=copy.deepcopy(model),
            model_id=SPEC['model_sha256'], spec_id=SPEC_ID,
            new_tj=frame['new_TJ'], tj_sample_id=self.tj_sample,
            safety={k:frame['safety'].get(k) for k in ('guard','fault','mode','enabled','temp_stale','manual_mode','normalized_valid','fan_fresh','binding_fresh','confirmed_normal_now')},
            observed_device=self.observed_device or (self.platform or {}).get('family'),
            platform=self.platform, source_health=copy.deepcopy(self.source_health), event_reason=raw.get('reason') if raw['kind']=='boundary' else None)
