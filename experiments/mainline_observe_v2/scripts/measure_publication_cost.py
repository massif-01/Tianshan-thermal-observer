"""Local synthetic-source cost comparison in separate, sequential processes.

Includes the owned fixture's cost; not an N305 budget or device result.
"""
import argparse
import asyncio
import json
import os
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'experiments/mainline_observe_v2/src'),str(ROOT/'experiments/mainline_observe_v2/tests'),str(ROOT/'work/webui-v1/src')]


def sample(mode,duration):
    from tto_field.numeric_policy import initialize
    initialize()
    from tto_field.g2_model.g2_runtime import Predictor
    Predictor()  # Same numerical import warmup, outside all measurement windows.
    import psutil
    from fake_source import FakeSource
    from tto.config import load_config
    from tto_field.observe_runtime import run_observe,Consumer
    import tto_field.observe_runtime as runtime
    runtime.boot_identity=lambda:'owned-local-cost-fixture'  # Fixture identity, never live evidence.
    times=[]
    original=Consumer.on_record
    def measured(self,*args):
        begin=time.perf_counter()
        try:return original(self,*args)
        finally:times.append((time.perf_counter()-begin)*1000)
    Consumer.on_record=measured
    async def go():
        with tempfile.TemporaryDirectory(dir='/tmp',prefix='pc-') as directory:
            root=Path(directory);descriptor=root/'pub'/'active.json'
            async with FakeSource() as source:
                config=load_config(environ={})
                config['orin'].update(base_url=source.url,source_sample_interval_ms=1000,source_interval_evidence='owned local cost fixture')
                config['tianshan']['base_url']=source.url
                reg=dict(device_id='synthetic',thermal_config_id='synthetic',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()))
                slow=None
                async def connect():
                    nonlocal slow
                    while not descriptor.exists():await asyncio.sleep(.01)
                    slow=socket.socket(socket.AF_UNIX);slow.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024);slow.connect(str(descriptor.parent/'publication.sock'))
                task=asyncio.create_task(connect()) if mode=='unread' else None
                ledger_stop=asyncio.Event()
                if mode=='ledger-client':
                    from tto_web.state import State
                    from tto_web.predictions import follow_predictions
                    import tto_web.predictions as subscription
                    import tto_web.state as web_state
                    subscription.boot_id=web_state.boot_id=lambda:'owned-local-cost-fixture'
                    web_config={'source':{'active_descriptor':str(descriptor)},'advisory':{}}
                    ledger_state=State(web_config)
                    task=asyncio.create_task(follow_predictions(web_config,ledger_state,ledger_stop))
                proc=psutil.Process();cpu0=sum(proc.cpu_times()[:2]);start=time.perf_counter()
                try:
                    result=await run_observe(config,reg,root/'session',duration,local_loopback=True,
                        storage_options={'min_free':0},publication_descriptor=None if mode=='off' else descriptor)
                finally:
                    if task:task.cancel();await asyncio.gather(task,return_exceptions=True)
                    if slow:slow.close()
                wall=time.perf_counter()-start;cpu=sum(proc.cpu_times()[:2])-cpu0
                resources=[json.loads(line) for file in sorted((root/'session').glob('resources*.jsonl')) for line in file.read_text().splitlines()]
                assert result['reason']=='duration' and result['model_dropped_frames']==0 and result['model_errors']==0
                assert result['native_summary']['dropped']==0 and source.posts==source.model_gets==0
                if mode!='off':assert result['publication']['errors']==0 and result['publication']['worker_stopped'], result['publication']
                if mode=='ledger-client':assert ledger_state.prediction_cursor>0
                ordered=sorted(times)
                return dict(mode=mode,wall_s=wall,cpu_s=cpu,cpu_single_core_pct=100*cpu/wall,
                    peak_sampled_rss_bytes=max(x['rss_bytes'] for x in resources),callbacks=len(times),
                    callback_mean_ms=statistics.mean(times),callback_p95_ms=ordered[int(.95*(len(ordered)-1))],
                    model_drops=result['model_dropped_frames'],native_drops=result['native_summary']['dropped'],
                    publication=result['publication'])
    return asyncio.run(go())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('off','unread','no-client','ledger-client'))
    p.add_argument('--duration',type=float,default=10);p.add_argument('--output',type=Path);p.add_argument('--repetitions',type=int,default=3);a=p.parse_args()
    if a.mode:print(json.dumps(sample(a.mode,a.duration)))
    else:
        rows=[]
        for n in range(a.repetitions):
            for mode in ('off','no-client','unread','ledger-client'):
                command=[sys.executable,__file__,'--mode',mode,'--duration',str(a.duration)]
                row=json.loads(subprocess.check_output(command,text=True).splitlines()[-1]);rows.append(row)
                print(json.dumps(dict(repetition=n,**row)),flush=True)
        result=dict(scope='Mac local synthetic loopback, fixture cost included, no Web service/N305; sequential subprocesses',
            duration_s=a.duration,repetitions=a.repetitions,python=sys.version,samples=rows,
            medians={mode:{k:statistics.median(x[k] for x in rows if x['mode']==mode)
                for k in ('cpu_single_core_pct','peak_sampled_rss_bytes','callback_mean_ms','callback_p95_ms')}
                for mode in ('off','no-client','unread','ledger-client')})
        a.output.write_text(json.dumps(result,indent=2)+'\n')
