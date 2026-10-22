"""Read-only synthetic replay through candidate production Engine and TrialHealth."""
import sys, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
code=root/'candidate/code'
sys.path[:0]=[str(code/'scripts/thermal_trials'),str(code/'tests')]
from health import TrialHealth
from test_platform_curve import new_packet
from tto.config import load_config
from tto.engine import engine_for
from tto.demo import fan_packet,temp_packet
c=load_config(environ={});e=engine_for(c,record_schema=2);h=TrialHealth()
accepted=[];decisions=[]
for t in range(133):
    rows=[('fan',fan_packet(19)),('temp',temp_packet())]
    p=new_packet(t+1)
    if 71<=t<=131:p['temperature'].pop('tj')
    rows.append(('orin',p))
    for kind,payload in rows:
        r=dict(kind=kind,payload=payload,mono_s=float(t),ref=f'review/{kind}:{t}',connection_epoch=1,observer_run_id='review-synthetic')
        out=e.process(r);h.observe(r,out,e)
        if out['quality'] and out['quality']['accepted']:accepted.append(t)
        if kind=='orin' and t in (70,71,80,131,132):
            s=h.snapshot(t)
            decisions.append(dict(t=t,quality=out['quality']['reason'],accepted=out['quality']['accepted'],last_actual_accepted_t=accepted[-1],
                    current_ready=s['current_ready'],continuous_60s=s['continuous_60s'],abnormal=s['abnormal'],
                    reported_latest=s['latest'],gaps_180s=s['gaps_180s']))
result=dict(simulated=True,real_device_access=False,production_engine=e.__class__.__name__,decisions=decisions)
(root/'results/health-missing-tj.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps([{k:r[k] for k in ('t','quality','accepted','last_actual_accepted_t','current_ready','continuous_60s','abnormal')} for r in decisions],indent=2))
assert decisions[1]['quality']=='stale_or_missing_tj' and not decisions[1]['accepted']
assert decisions[-2]['last_actual_accepted_t']==70 and decisions[-2]['current_ready'] and decisions[-2]['continuous_60s']
print('COUNTEREXAMPLE CONFIRMED: absent TJ for 61 seconds still marked ready and continuous.')
