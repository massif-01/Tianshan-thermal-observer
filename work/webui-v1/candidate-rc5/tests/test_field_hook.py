import json
import time
from tto.engine import engine_for
from tto.storage import Journal,source_identity
from tto_field.runtime import Pipeline
from tto_field.support import Clock,Evidence
from tto_web.common import utc
from producer import Producer,native_config


def test_field_hook_reuses_exact_same_engine_projection_observer_and_no_binding_leak(tmp_path):
    out=tmp_path/'field';out.mkdir();config=native_config();engine=engine_for(config,record_schema=2)
    journal=Journal(config,root=out/'native',simulated=True,record_schema=2)
    evidence=Evidence(out);packets=[]
    binding=dict(command_id='SYNTHETIC-WEB-HOOK',collector_source_sha256=source_identity()['sha256'],synthetic_loopback_only=True,private_headers={'Authorization':'SECRET-DO-NOT-PUBLISH'})
    pipeline=Pipeline(out,config,binding,'diagnose',Clock(),evidence,public_sink=packets.append)
    producer=Producer();start=time.monotonic()-12;count=0
    for t in range(13):
        inputs=[('fan',producer.fan())]+([('temp',producer.temp())] if t%5==0 else [])+[('orin',producer.packet(t))]
        for kind,payload in inputs:
            raw=journal.observation(dict(kind=kind,payload=payload,mono_s=start+t,received_at_utc=utc(),connection_epoch=1))
            processed=engine.process(raw);pipeline.on_record(raw,processed,engine);count+=1
    assert pipeline.web_adapter.observer is pipeline.observer
    assert pipeline.web_adapter.projection is pipeline.projection
    assert pipeline.web_adapter.bridge is pipeline.communication
    assert pipeline.communication.view.process_calls==count==len(packets)
    assert packets[-1]['model']['Tf_C']==pipeline.latest['state']['observer']['Tf_C']
    assert packets[-1]['clock_domain_id'].startswith('host-monotonic:')
    assert pipeline.latest['state']['generated_clock_domain']=='offline_virtual_observer_clock'
    assert 'SECRET' not in json.dumps(packets) and 'private_headers' not in json.dumps(packets)
    assert pipeline.latest['state']['permission']['device_actions'] is False
    evidence.close();journal.close({})
