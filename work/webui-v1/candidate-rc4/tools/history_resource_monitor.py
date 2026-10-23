"""120s installed Web-only measurement; synthetic publisher and Chrome separate."""
import asyncio,json,os,platform,time
from pathlib import Path
import aiohttp,psutil
async def main():
    out=Path(os.environ['TTO_HISTORY_OUT']);meta=json.loads((out/'service.json').read_text());p=psutil.Process(meta['pid']);source=psutil.Process(json.loads((out/'source.json').read_text())['pid'])
    start=time.monotonic();cpu=p.cpu_times();source_cpu=source.cpu_times();samples=[];requests=[]
    async with aiohttp.ClientSession() as c:
        health=await(await c.get('http://127.0.0.1:59009/healthz')).json();assert health['pid']==meta['pid']
        while time.monotonic()-start<120:
            snap=await(await c.get('http://127.0.0.1:59009/api/v1/snapshot')).json()
            assert snap['model']['phase'] in ('tracking','degraded'), 'fixture/model not eligible during measurement'
            samples.append(dict(t=time.monotonic()-start,rss_MiB=p.memory_info().rss/1024**2,source_rss_MiB=source.memory_info().rss/1024**2,model_phase=snap['model']['phase']))
            if meta['version']=='1.0.0rc4' and len(samples)%2==0:
                t=time.perf_counter()
                async with c.get('http://127.0.0.1:59009/api/v1/series?ids=temperature.tj,model.Tf_C,model.Ts_C,model.E_C&max_points=2000') as r:
                    wire=await r.read();assert r.status==200;data=json.loads(wire)
                    requests.append(dict(ms=(time.perf_counter()-t)*1000,bytes=len(wire),rows=data['series'][0]['returned_points']))
            if len(samples)%15==0:(out/'progress.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,samples=len(samples),phase=snap['model']['phase'])))
            await asyncio.sleep(1)
    elapsed=time.monotonic()-start;after=p.cpu_times();sa=source.cpu_times()
    result=dict(version=health['version'],module=meta['module'],identity=meta['identity'],scope='installed Web app_for follow process; synthetic prefill; macOS ARM64; one Chrome page; excludes source and browser from Web budget; not N305',host=platform.platform(),duration_s=elapsed,cpu_mean_single_core_percent=100*(after.user+after.system-cpu.user-cpu.system)/elapsed,rss_peak_MiB=max(s['rss_MiB'] for s in samples),rss_first_MiB=samples[0]['rss_MiB'],rss_last_MiB=samples[-1]['rss_MiB'],source_cpu_percent_separate=100*(sa.user+sa.system-source_cpu.user-source_cpu.system)/elapsed,source_rss_peak_MiB_separate=max(s['source_rss_MiB'] for s in samples),source_rate_Hz=1,preload_rows_per_existing_numeric_series=18002,preload_span_ms=3599800,extra_joint_request_interval_s=2 if requests else None,joint_request_max_ms=max((q['ms'] for q in requests),default=None),joint_request_max_bytes=max((q['bytes'] for q in requests),default=None),joint_request_max_rows=max((q['rows'] for q in requests),default=None),samples=samples,requests=requests)
    result['pass']=result['rss_peak_MiB']<=192 and result['cpu_mean_single_core_percent']<=5
    (out/'resources.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('samples','requests')}),flush=True)
if __name__=='__main__':asyncio.run(main())
