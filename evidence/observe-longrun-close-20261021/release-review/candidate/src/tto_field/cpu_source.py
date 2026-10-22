"""Bounded read-only Linux side recorder. No jtop client, service, WS or control connection."""
import argparse,json,os,resource,socket,sys,time,uuid,hashlib,platform,importlib.metadata
from datetime import datetime,timezone
from pathlib import Path
FIELDS=['user','nice','system','idle','iowait','irq','softirq','steal','guest','guest_nice']

def utc():return datetime.now(timezone.utc).isoformat()
def bracket():
    a=time.monotonic();u=utc();b=time.monotonic()
    return dict(mono_before_s=a,utc=u,mono_after_s=b,clock='CLOCK_MONOTONIC')

def read_cpu(root='/'):
    a=time.monotonic();p=Path(root)
    raw='\n'.join(x for x in (p/'proc/stat').read_text().splitlines() if x.split() and x.split()[0].startswith('cpu'))+'\n';online=(p/'sys/devices/system/cpu/online').read_text().strip()
    counts={x.split()[0]:[int(y) for y in x.split()[1:]] for x in raw.splitlines() if x.split() and x.split()[0].startswith('cpu')}
    possible=(p/'sys/devices/system/cpu/possible').read_text().strip()
    cpus=set();all_cpus=set()
    for part in possible.split(','):
        pair=part.split('-');all_cpus.update(range(int(pair[0]),int(pair[-1])+1))
    for part in online.split(','):
        pair=part.split('-');cpus.update(range(int(pair[0]),int(pair[-1])+1))
    return dict(read_start_mono_s=a,read_end_mono_s=time.monotonic(),raw_proc_stat=raw,counters=counts,online_text=online,
                possible_text=possible,per_core_online={'cpu'+str(k):k in cpus for k in sorted(all_cpus)},SC_CLK_TCK=os.sysconf('SC_CLK_TCK'),fields=FIELDS)

def utilization(previous,current):
    values={};reason={}
    for k,new in current['counters'].items():
        if k=='cpu':continue
        old=previous['counters'].get(k)
        if not old or not current['per_core_online'].get(k) or not previous['per_core_online'].get(k):reason[k]='offline_or_no_predecessor';continue
        # First 8 already include guest in user/nice: never add guest a second time.
        delta=[b-a for a,b in zip(old[:8],new[:8])]
        if len(delta)!=8 or any(x<0 for x in delta) or sum(delta)<=0:reason[k]='counter_reset_iowait_decrease_or_zero_window';continue
        values[k]=100*(sum(delta)-delta[3]-delta[4])/sum(delta)
    complete=len(values)==sum(current['per_core_online'].values()) and bool(values)
    return dict(per_core_percent=values,complete_online_set=complete,valid_core_count=len(values),mean_percent=sum(values.values())/len(values) if complete else None,max_percent=max(values.values()) if complete else None,
                unavailable=reason,window_start_read=previous['read_start_mono_s'],window_start_read_end=previous['read_end_mono_s'],
                window_end_read_start=current['read_start_mono_s'],window_end_read=current['read_end_mono_s'],
                semantics='busy=total-idle-iowait; total=sum first8; guest included once; negative delta unavailable; unweighted online-core mean')

class Sensors:
    def __init__(self,config):
        self.rails=config.get('rails',[]);self.nv=None;self.error=None;self.identity=None;self.driver_version=None;self.binding_version=None
        if config.get('nvml',False):
            try:
                import pynvml
                self.nv=pynvml;self.nv.nvmlInit();self.driver_version=str(self.nv.nvmlSystemGetDriverVersion());self.binding_version=importlib.metadata.version('nvidia-ml-py')
                if self.nv.nvmlDeviceGetCount()!=1:raise ValueError('single GPU required')
                self.handle=self.nv.nvmlDeviceGetHandleByIndex(0);self.identity=str(self.nv.nvmlDeviceGetUUID(self.handle))
            except Exception as e:self.error=type(e).__name__
    def read(self):
        a=time.monotonic();value=None;error=self.error
        if self.nv and not error:
            try:value=self.nv.nvmlDeviceGetUtilizationRates(self.handle).gpu
            except Exception as e:error=type(e).__name__
        gpu=dict(value=value,unit='percent',read_start_mono_s=a,read_end_mono_s=time.monotonic(),device_uuid=self.identity,driver_version=self.driver_version,binding_version=self.binding_version,
                 source='NVML',status='query_ok_window_unknown' if value is not None else 'unavailable',error=error,
                 generation_id=None,source_window=None,source_age_s=None,new_independent_sample=None)
        rails=[]
        for c in self.rails:
            a=time.monotonic();raw=None;error=None
            try:raw=Path(c['path']).read_text().strip();value=float(raw)
            except Exception as e:value=None;error=type(e).__name__
            rails.append(dict(name=c['name'],path=c['path'],unit=c['unit'],raw=raw,value=value,
                              read_start_mono_s=a,read_end_mono_s=time.monotonic(),error=error,source='explicit_readonly_sysfs',
                              source_window=None,source_age_s=None,generation_id=None,new_independent_sample=None))
        return dict(gpu=gpu,rails=rails)
    def close(self):
        if self.nv:self.nv.nvmlShutdown()

def stream(config,permission,duration):
    if not 0<duration<=1200:raise ValueError('bounded duration required')
    if permission.get('action')!='cpu-sidecar-readonly' or permission.get('explicit_user_start') is not True or not permission.get('evidence') or not permission.get('command_id'):
        raise ValueError('current read-only sidecar permission required')
    if config.get('query_target_s')!=.2:raise ValueError('first candidate is 200ms only')
    for r in config.get('rails',[]):
        if r['name'] not in ('vdd_gpu','vdd_cpu_soc_mss') or not r['path'].startswith('/sys/') or r['unit'] not in ('mW','uW','W'):
            raise ValueError('only explicitly identified independent rail read paths')
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();session=str(uuid.uuid4())
    identity=dict(host=socket.gethostname(),boot_id=boot,source_session=session,pid=os.getpid(),clock='CLOCK_MONOTONIC',clock_resolution_s=time.get_clock_info('monotonic').resolution,utc_correspondence=bracket(),command_id=permission['command_id'],python=sys.version,kernel=platform.release(),source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    sensors=Sensors(config);start=time.monotonic();due=start;prev=None;seq=0;bytes_total=0;cpu_start=time.process_time();recent_read=[];recent_jitter=[]
    try:
        while time.monotonic()-start<duration:
            t=time.monotonic();current=read_cpu();metrics=sensors.read();end=time.monotonic();seq+=1
            cpu=None if prev is None else utilization(prev,current)
            row=dict(schema='TTO-CPU-SOURCE-v1',identity=identity,seq=seq,query_target_s=.2,utc=utc(),
                     read_start_mono_s=t,read_end_mono_s=end,clock_correspondence=bracket(),raw_cpu=current,previous_raw_cpu=prev,cpu=cpu,**metrics,
                     resources=dict(cpu_seconds=time.process_time()-cpu_start,elapsed_s=end-start,rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                                    read_duration_s=end-t,deadline_jitter_s=max(0,t-due),bytes_preceding=bytes_total),
                     precision_note='200ms query, not asserted GPU/rail source resolution; unrelated processes and monitor CPU included')
            recent_read=(recent_read+[end-t])[-25:];recent_jitter=(recent_jitter+[max(0,t-due)])[-25:]
            reasons=[]
            if end-t>.1:reasons.append('single_read_over_100ms')
            if row['resources']['rss_bytes']>64*1024**2:reasons.append('source_RSS_over_64MiB')
            if end-start>=5:
                if (time.process_time()-cpu_start)/(end-start)>.05:reasons.append('source_CPU_over_5percent_one_core')
                if sorted(recent_read)[int(.95*(len(recent_read)-1))]>.02:reasons.append('read_p95_over_20ms')
                if sorted(recent_jitter)[int(.95*(len(recent_jitter)-1))]>.1:reasons.append('jitter_p95_over_100ms')
            row['stop_reasons']=reasons
            encoded=json.dumps(row,separators=(',',':'));bytes_total+=len(encoded.encode())+1
            print(encoded,flush=True);prev=current
            if reasons:break
            due+=.2
            if due<end:due=end+.2  # skip missed slots, no catch-up burst
            time.sleep(max(0,due-time.monotonic()))
    finally:sensors.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--permission',required=True,type=Path);p.add_argument('--duration',type=float,required=True)
    a=p.parse_args();stream(json.loads(a.config.read_text()),json.loads(a.permission.read_text()),a.duration)
if __name__=='__main__':main()
