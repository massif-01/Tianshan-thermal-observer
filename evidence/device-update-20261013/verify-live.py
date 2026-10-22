import collections,hashlib,json,subprocess,time,threading,urllib.request
from pathlib import Path
import psutil,socketio
root=Path.home()/'rmstatus-update-20261013'
expected=Path.home()/'.venvs/tegrastats-api-1.1.1-2c356a1-20261013'
pid=int(subprocess.check_output(['systemctl','show','tegrastats-api','-p','MainPID','--value'],text=True))
proc=psutil.Process(pid);proc.cpu_percent()
rows=[];seen={};conflicts=[];mutex=threading.Lock()
def accept(p,transport):
    m=p['telemetry_meta'];key=(m['stream_id'],m['sample_seq'])
    immutable={k:p.get(k) for k in ('platform','gpu','temperature','cpu','memory','power')}
    immutable['source_sample_interval_ms']=m.get('source_sample_interval_ms')
    fingerprint=hashlib.sha256(json.dumps(immutable,sort_keys=True,allow_nan=False).encode()).hexdigest()
    with mutex:
        if key in seen and seen[key]!=fingerprint:conflicts.append(list(key))
        seen[key]=fingerprint
        rows.append({'transport':transport,'key':list(key),'gpu':p['gpu'],'fresh':m['fresh'],'tj':p['temperature']['tj']})
client=socketio.Client(reconnection=False)
@client.on('tegrastats_update')
def update(p):accept(p,'websocket')
client.connect('http://10.10.99.98:58090',transports=['websocket'])
resources=[];http_errors=[];start=time.monotonic()
try:
    for i in range(180):
        try:
            with urllib.request.urlopen('http://127.0.0.1:58090/api/status',timeout=3) as response:p=json.load(response)
            accept(p,'http')
            if i==0:(root/'first-status.json').write_text(json.dumps(p,indent=2)+'\n')
        except Exception as error:http_errors.append(type(error).__name__)
        resources.append({'rss_mib':proc.memory_info().rss/1024**2,'cpu_pct_one_core':proc.cpu_percent()})
        time.sleep(max(0,start+i+1-time.monotonic()))
finally:client.disconnect()
with urllib.request.urlopen('http://127.0.0.1:58090/api/health',timeout=3) as response:health=json.load(response)
(root/'health.json').write_text(json.dumps(health,indent=2)+'\n')
assert health['package_version']=='1.1.1'
assert str(expected) in health['parser_file']
assert psutil.Process(pid).is_running()
assert not conflicts and not http_errors
assert any(r['transport']=='websocket' for r in rows)
assert len(seen)>=150
assert all(r['gpu']['status']=='valid' and r['gpu']['source']=='nvml' and r['fresh'] for r in rows)
first=json.loads((root/'first-status.json').read_text());assert first['platform']['family']=='jetson_thor'
assert first['platform']['soc']=='tegra264'
result={'passed':True,'duration_s':time.monotonic()-start,'pid':pid,'cmdline':proc.cmdline(),'health':health,'unique_samples':len(seen),'records_by_transport':dict(collections.Counter(r['transport'] for r in rows)),'immutable_conflicts':conflicts,'http_errors':http_errors,'gpu_statuses':dict(collections.Counter(r['gpu']['status'] for r in rows)),'gpu_min_pct':min(r['gpu']['utilization_pct'] for r in rows),'gpu_max_pct':max(r['gpu']['utilization_pct'] for r in rows),'service_rss_max_mib':max(r['rss_mib'] for r in resources),'service_cpu_mean_pct_one_core':sum(r['cpu_pct_one_core'] for r in resources)/len(resources),'service_cpu_max_pct_one_core':max(r['cpu_pct_one_core'] for r in resources),'workload_started_by_assistant':False}
(root/'live-verification.json').write_text(json.dumps(result,indent=2)+'\n')
(root/'live-samples.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
print(json.dumps(result,indent=2))
