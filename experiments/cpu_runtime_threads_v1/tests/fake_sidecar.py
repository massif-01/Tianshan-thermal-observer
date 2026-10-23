"""Synthetic stream for own-process transport tests, no /proc or GPU access."""
import json,sys,time,socket
command=sys.argv[1];start=time.monotonic();seq=0
while time.monotonic()-start<70:
    seq+=1;t=time.monotonic()
    r=dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host=socket.gethostname(),boot_id='SYNTHETIC-BOOT',source_session='SYNTHETIC-SOURCE',clock='CLOCK_MONOTONIC',command_id=command),seq=seq,
           read_start_mono_s=t,read_end_mono_s=t+.0001,cpu=dict(mean_percent=4,max_percent=40),gpu=dict(value=0,unit='percent',source_window=None),rails=[],
           resources=dict(elapsed_s=t-start,cpu_seconds=.0001,rss_bytes=1000000,read_duration_s=.0001,deadline_jitter_s=0))
    print(json.dumps(r),flush=True);time.sleep(.2)
