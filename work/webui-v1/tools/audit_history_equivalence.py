"""Audit rc4 vs installed candidate public history on deterministic source transitions."""
import copy,importlib.util,json,os,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from producer import Producer,web_config
from tto_web.state import State,MODEL_GROUP
oldfile=ROOT/'evidence/self-review-rc5/before/src/tto_web/state.py'
spec=importlib.util.spec_from_file_location('tto_web._audit_rc4',oldfile)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
p=Producer(1000.)
for t in range(31):template=p.step(t)
a=old.State(web_config());b=State(web_config());rng=random.Random(514);t=0.;sample=0;checks=0
for i in range(300):
    t+=rng.choice((.1,.5,1.,3.));packet=copy.deepcopy(template)
    packet.update(origin_mono_s=1000.,input_mono_s=1000.+t,consumable_until_mono_s=1002.5+t,new_tj=rng.random()>.15,publication_gap=rng.random()<.05)
    if packet['new_tj']:sample+=1
    packet['tj_sample_id']=str(sample)
    packet['model'].update(phase=rng.choice(('tracking','tracking','degraded','provisional','unavailable')),conditional_inputs_rails_W_PWM=None)
    for m in packet['metrics']:
        m.update(as_of_elapsed_ms=t*1000,_at=1000.+t,_expiry=1005.+t)
        if m['id']=='temperature.tj':m.update(sample_id=str(sample),source_ref='audit/'+str(sample))
    packet['source_epoch']=i//75
    now=1000.+t+rng.choice((.01,.2,3.))
    a.accept(packet,now=now);b.accept(packet,now=now)
    for ids in (list(MODEL_GROUP),['model.Ts_C'],['temperature.tj']):
        assert a.series(ids,0,1e9,16)==b.series(ids,0,1e9,16),(i,ids)
        checks+=1
    assert list(a.model_history)==list(b.model_history)
result=dict(seed=514,source_transitions=300,public_series_comparisons=checks,all_equal=True,scope='deterministic synthetic packets; same frozen observer input template, no training/device')
(ROOT/'evidence/self-review-rc5/history-equivalence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
