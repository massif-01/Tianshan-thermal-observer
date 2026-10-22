"""Review-only deterministic probe; no network and no collector locks."""
import os
import json
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(os.environ['TTO_REVIEW_CANDIDATE']).resolve()
OUT = Path(os.environ.get("TTO_REVIEW_OUTPUT", str(Path(__file__).parent)))
OUT.mkdir(parents=True,exist_ok=True)
sys.path[:0] = [str(BASE/'src'), str(BASE/'vendor'), str(BASE/'tests')]

from tto.engine import engine_for
from tto.storage import Journal, source_identity
from tto_field.runtime import Pipeline
from tto_field.support import Clock, Evidence
from tto_web.common import utc
from producer import Producer, native_config


def field_case(web_enabled, case):
    with tempfile.TemporaryDirectory(prefix='field-probe-', dir=OUT) as directory:
        out = Path(directory)
        config = native_config()
        engine = engine_for(config, record_schema=2)
        journal = Journal(config, root=out/'native', simulated=True, record_schema=2)
        evidence = Evidence(out)
        packets = []
        binding = dict(command_id='SYNTHETIC-REVIEW', collector_source_sha256=source_identity()['sha256'], synthetic_loopback_only=True)
        pipeline = Pipeline(out, config, binding, 'diagnose', Clock(), evidence,
                            public_sink=packets.append if web_enabled else None)
        producer = Producer()
        start = time.monotonic() - 12
        try:
            for t in range(13):
                inputs = [('fan', producer.fan())]
                if t % 5 == 0:
                    inputs.append(('temp', producer.temp()))
                inputs.append(('orin', producer.packet(t)))
                for kind, payload in inputs:
                    raw = journal.observation(dict(kind=kind, payload=payload, mono_s=start+t, received_at_utc=utc(), connection_epoch=1))
                    processed = engine.process(raw)
                    pipeline.on_record(raw, processed, engine)
            if case == 'fan_data_null':
                kind, payload = 'fan', {'code': 0, 'data': None}
            elif case == 'memory_null':
                kind, payload = 'orin', producer.packet(13)
                payload['memory'] = None
            else:
                raise ValueError(case)
            raw = journal.observation(dict(kind=kind, payload=payload, mono_s=start+13, received_at_utc=utc(), connection_epoch=1))
            processed = engine.process(raw)
            result = {'case': case, 'web_hook_enabled': web_enabled,
                      'native_processing_returned': True,
                      'native_fan_invalidated': engine.fan is None,
                      'native_tj_accepted': (processed.get('quality') or {}).get('accepted'),
                      'callbacks_before': pipeline.callbacks}
            try:
                pipeline.on_record(raw, processed, engine)
                result.update(field_callback='returned', error=None, cause=None)
            except Exception as exc:
                result.update(field_callback='raised', error=type(exc).__name__+': '+str(exc),
                              cause=type(exc.__cause__).__name__+': '+str(exc.__cause__) if exc.__cause__ else None)
            result['callbacks_after'] = pipeline.callbacks
            return result
        finally:
            evidence.close()
            journal.close({})


results = [field_case(enabled, case) for case in ('fan_data_null', 'memory_null') for enabled in (False, True)]
print(json.dumps(results, ensure_ascii=False, indent=2))
(OUT/'optional_source_fields_result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
