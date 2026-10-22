"""Measure the running local service, never a device. Reads only /healthz/snapshot."""
import argparse
import asyncio
import json
import statistics
import time
import signal
from pathlib import Path
import aiohttp
import psutil

async def main(args):
    Path(args.output+'.monitor.json').write_text(json.dumps({'pid':__import__('os').getpid(),'service_pid':args.pid}))
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
    proc=psutil.Process(args.pid);before=proc.cpu_times();start=time.monotonic();rss=[];samples=[];errors=0
    async with aiohttp.ClientSession() as session:
        while time.monotonic()-start<args.seconds and not stop.is_set():
            try:
                async with session.get('http://127.0.0.1:59009/api/v1/snapshot') as r:
                    s=await r.json();rss.append(proc.memory_info().rss/1024**2)
                    samples.append({'elapsed_s':time.monotonic()-start,'rss_MiB':rss[-1],'mode':s['mode'],'run_id':s['run_id'],'model_phase':s['model']['phase']})
            except (OSError,ValueError):errors+=1
            if len(samples)%30==0:
                current_cpu=proc.cpu_times();dt=time.monotonic()-start
                Path(args.output+'.progress.json').write_text(json.dumps(dict(elapsed_s=dt,samples=len(samples),rss_peak_MiB=max(rss,default=0),cpu_mean_single_core_percent=100*(current_cpu.user+current_cpu.system-before.user-before.system)/dt)))
            await asyncio.sleep(1)
    after=proc.cpu_times();elapsed=time.monotonic()-start
    result=dict(scope=args.scope,completed_requested_duration=elapsed>=args.seconds,elapsed_s=elapsed,samples=len(samples),errors=errors,cpu_mean_single_core_percent=100*(after.user+after.system-before.user-before.system)/elapsed,rss_peak_MiB=max(rss,default=0),rss_first_MiB=rss[0] if rss else None,rss_last_MiB=rss[-1] if rss else None,rss_budget_MiB=192,cpu_budget_percent=5,one_browser_required_for_run=True,details=samples)
    Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='details'}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',default='macOS ARM64 installed Web follow process only, separate self-built native source; excludes Chrome; not N305 evidence');p.add_argument('--pid',type=int,required=True);p.add_argument('--seconds',type=int,default=1800);p.add_argument('--output',required=True);asyncio.run(main(p.parse_args()))
