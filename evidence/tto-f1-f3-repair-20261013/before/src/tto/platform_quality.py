"""Schema2 uses the established identity/isolation rules with additive fields."""
from .quality import Quality
import copy
from .profiles import platform_contract, platform_numbers, uniform_gpu, source_period, identified_family, lifecycle_signature, lifecycle_evidenced
from .util import digest, finite


class PlatformQuality(Quality):
    def __init__(self, config):
        self.configured_period = config['orin']['source_sample_interval_ms']
        super().__init__(copy.deepcopy(config))
        self.lifecycle_stream = None
        self.lifecycle_settings = None
        self.lifecycle_uuid = None

    def measurement_fingerprint(self, payload):
        body = {k: payload.get(k) for k in ('temperature', 'cpu', 'gpu', 'power', 'memory', 'platform')}
        body['source_sample_interval_ms'] = payload['telemetry_meta'].get('source_sample_interval_ms')
        body['source_received_at'] = payload['telemetry_meta'].get('received_at')
        return digest(body)

    def extract_values(self, payload):
        family, _ = identified_family(payload)
        return platform_numbers(payload, family)

    def accept(self, record):
        payload = record['payload']
        previous_segment = self.segment
        previous_period = self.c['orin']['source_sample_interval_ms']
        info = None
        if isinstance(payload, dict) and isinstance(payload.get('telemetry_meta'), dict):
            info = source_period(payload, self.configured_period)
            self.c['orin']['source_sample_interval_ms'] = info['period_ms']
        out = super().accept(record)
        if not isinstance(record['payload'], dict) or out['reason'] not in ('new_sample', 'duplicate'):
            self.c['orin']['source_sample_interval_ms'] = previous_period
            return out
        out['source_period'] = info
        out['period_known'] = info is not None and info['period_ms'] is not None and info['reason'] is None
        if info and info['reason']:
            self.counts[info['reason']] += 1
        contract, reason = platform_contract(record['payload'], self.c['orin']['source_sample_interval_ms'])
        out['platform_reason'] = reason
        out['input_contract'] = contract
        # Source age can rise on retransmission. Use the quality layer's single
        # monotonic anchor, never add local elapsed time a second time.
        payload = dict(record['payload'])
        meta = dict(payload.get('telemetry_meta') or {})
        if out['reason'] in ('new_sample', 'duplicate') and finite(self.anchor_age):
            meta['sample_age_ms'] = self.anchor_age
        payload['telemetry_meta'] = meta
        gpu = uniform_gpu(payload, contract['family'] if contract else None, record['mono_s'])
        if contract is None:
            family, _ = identified_family(payload)
            gpu = uniform_gpu(payload, family, record['mono_s'])
        out['gpu'] = gpu
        if out['accepted']:
            if self.lifecycle_stream != self.stream:
                self.lifecycle_stream, self.lifecycle_settings = self.stream, None
                self.lifecycle_uuid = None
            signature = lifecycle_signature(payload)
            uuid = gpu.get('device_uuid') if gpu['contract_valid'] else None
            settings_change = self.lifecycle_settings is not None and signature != self.lifecycle_settings
            device_change = bool(uuid and self.lifecycle_uuid and uuid != self.lifecycle_uuid)
            if settings_change or device_change:
                self.boundary('lifecycle_contract_change')
                out.update(reason='lifecycle_contract_change', lifecycle_violation=True, segment=self.segment, invalidated_segment=previous_segment, lifecycle_changes={'settings': settings_change, 'device_uuid': device_change})
                self.counts['lifecycle_contract_change'] += 1
            if uuid:
                self.lifecycle_uuid = uuid
            if lifecycle_evidenced(payload):
                self.lifecycle_settings = signature
            out['values']['gpu_busy'] = gpu['value']
        return out
