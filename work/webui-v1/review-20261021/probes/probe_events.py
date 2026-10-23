"""Two-run event identity probe using installed candidate, no source/network."""
import os
import json,time
from pathlib import Path
from tto_web.state import State
from tto_web.adapter import SPEC,SPEC_ID
from tto_web.common import boot_id
out=Path(os.environ.get('TTO_REVIEW_OUTPUT', str(Path(__file__).parent)))
out.mkdir(parents=True,exist_ok=True)
now=time.monotonic()
def packet(run,origin,t):
 return dict(schema='TTO-WEB-PUBLICATION-v1',boot_id=boot_id(),clock_domain_id='host-monotonic:'+boot_id(),run_id=run,source_epoch=1,model_id=SPEC['model_sha256'],spec_id=SPEC_ID,origin_mono_s=origin,input_mono_s=t,mode='test_replay',observed_device='SYNTHETIC',metrics=[],new_tj=False,model=dict(phase='uninitialized',Tf_C=None,Ts_C=None,E_C=None),consumable_until_mono_s=t+10,safety={})
s=State({'advisory':{'curve_manifest':None}})
s.accept(packet('old-run-A',now-600,now-560),now=now-560)
s.event('runner','OLD-RUN-A task started',20000)
old_id=s.events[-1]['id']
s.accept(packet('new-run-B',now-30,now),now=now)
snap=s.snapshot();events=list(s.events)
visible=[e for e in events if e['elapsed_ms'] is not None and 0<=e['elapsed_ms']<=snap['run_elapsed_ms']]
result=dict(current_run=snap['run_id'],current_epoch=snap['source_epoch'],current_elapsed_ms=snap['run_elapsed_ms'],old_event_id=old_id,visible_event_reasons=[e['reason'] for e in visible],old_event_still_visible=any(e['id']==old_id for e in visible),old_event=next(e for e in events if e['id']==old_id),events=events,snapshot=snap)
assert result['old_event_still_visible']
assert 'run_id' not in result['old_event'] and 'source_epoch' not in result['old_event']
(out/'events-probe-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('snapshot','events')},ensure_ascii=False,indent=2))
