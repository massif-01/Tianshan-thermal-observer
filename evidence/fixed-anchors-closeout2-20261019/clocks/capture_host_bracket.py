"""Independent Mac-before / N305 UTC / Mac-after clock bracket, no data collection."""
import datetime,time,subprocess,json,socket,sys
from pathlib import Path
out=Path(sys.argv[1]);assert not out.exists()
before_mono=time.monotonic();before=datetime.datetime.now(datetime.timezone.utc)
cmd=['ssh','-S','/private/tmp/tto-fixed-anchors-closeout2-ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','rm01@10.10.99.99',"python3 -c 'import datetime,time,socket,json;print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic_s=time.monotonic(),host=socket.gethostname())))'"]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=8,check=True)
after=datetime.datetime.now(datetime.timezone.utc);after_mono=time.monotonic();remote=json.loads(r.stdout)
remote_dt=datetime.datetime.fromisoformat(remote['utc'])
result={'kind':'independent_host_clock_bracket','mac_host':socket.gethostname(),'mac_before_utc':before.isoformat(),'n305':remote,'mac_after_utc':after.isoformat(),'mac_mono_before_s':before_mono,'mac_mono_after_s':after_mono,'roundtrip_s':after_mono-before_mono,'n305_minus_mac_offset_bounds_s':[(remote_dt-after).total_seconds(),(remote_dt-before).total_seconds()],'clock_accuracy_absolute_s':None,'timezone_for_instrument_comparison':'Asia/Shanghai UTC+08:00','meaning':'Offset bracket assumes clocks do not jump during exchange; no claim of instrument zero offset or photo exposure simultaneity. This file is evidence, not a live clock display.'}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
