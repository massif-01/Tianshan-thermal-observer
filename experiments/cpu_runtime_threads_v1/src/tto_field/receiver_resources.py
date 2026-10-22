"""Pre-sidecar admission of the existing one-second process resource sample."""
import math
CPU_LIMIT=8.0
RSS_LIMIT=128*1024**2

def baseline_admission(sample,now):
    r=dict(evaluated_mono_s=now,resource_sample=sample,cpu_limit_single_core_percent=CPU_LIMIT,
           rss_limit_bytes=RSS_LIMIT,allowed=False,reason='baseline_receiver_resources_unavailable',
           interval_contract='latest actual1s interval; start>=1s, span0.5..2s, age0..1.5s; no averaging or host-core normalization')
    if sample is None:return r
    vals=[sample.get(k) for k in ('interval_start_mono_s','mono_s','cpu_pct_single_core','rss_bytes')]
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in vals):return r
    start,end,cpu,rss=vals;r['sample_age_s']=now-end
    if not (start>=1 and .5<=end-start<=2 and 0<=now-end<=1.5 and cpu>=0 and rss>=0):return r
    if cpu>CPU_LIMIT or rss>RSS_LIMIT:r['reason']='baseline_receiver_resource_budget_exceeded';return r
    r.update(allowed=True,reason='baseline_receiver_resources_qualified');return r


def read_sample(now,previous):
    """Unknown resource observations revoke the sample; never reuse an older good reading."""
    import psutil
    start=previous[0] if previous else None
    try:
        process=psutil.Process();ct=process.cpu_times();total=ct.user+ct.system;rss=process.memory_info().rss
        cpu=None if previous is None else 100*(total-previous[1])/(now-start)
        if not math.isfinite(total) or rss<0 or (cpu is not None and (not math.isfinite(cpu) or cpu<0)):
            raise ValueError('invalid_process_resource_counters')
        return dict(mono_s=now,interval_start_mono_s=start,cpu_pct_single_core=cpu,rss_bytes=rss,cpu_times=ct._asdict(),resource_error=None),(now,total)
    except (psutil.Error,OSError,ValueError,ZeroDivisionError) as exc:
        return dict(mono_s=now,interval_start_mono_s=start,cpu_pct_single_core=None,rss_bytes=None,cpu_times=None,resource_error=type(exc).__name__),None
