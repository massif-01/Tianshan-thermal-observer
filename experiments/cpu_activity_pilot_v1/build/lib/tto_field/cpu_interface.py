"""Causal analysis interface, no classifier, thermal fitting or control writes.
Arrival mode compares availability in the receiver domain. Source-only files cannot invent arrival.
"""
import math

def available(row,origin,domain,max_age_s):
    if row.get('clock_domain')!=domain:return False
    end=row.get('observed_window_end_s');arrival=row.get('available_at_s');generated=row.get('decision_generated_s')
    return bool(row.get('valid') is True and all(type(x) in (int,float) and math.isfinite(x) for x in (end,arrival,generated)) and
                end<=arrival<=generated<=origin and origin-end<=max_age_s)

def causal_inputs(rows,origin,domain,max_age_s=2.5):
    chosen={}
    for row in rows:
        if available(row,origin,domain,max_age_s) and (row['field'] not in chosen or row['available_at_s']>chosen[row['field']]['available_at_s']):chosen[row['field']]=row
    def view(names):return {name:chosen.get(name) for name in names}
    base=['gpu_percent','vdd_gpu_W','vdd_cpu_soc_mss_W']
    return {'INPUT-BASE':view(base),'INPUT-MEAN':view(base+['cpu_mean_percent']),'INPUT-CORE':view(base+['cpu_mean_percent','cpu_max_percent']),
            'origin_s':origin,'clock_domain':domain,'no_future_plan_input':True,'deployable':False,
            'note':'null means unavailable, not zero; CPU summaries are activity, never added thermal watts'}
