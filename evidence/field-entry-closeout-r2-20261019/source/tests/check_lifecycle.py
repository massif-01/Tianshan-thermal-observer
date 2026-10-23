"""Real CLI child SIGINT, live double-start rejection, and premature native collector exit."""
import asyncio,json,signal,sys
from pathlib import Path
from unittest.mock import patch
from fake_source import FakeSource
from run_loopback import configuration,binding
from tto_field.runtime import run
from tto_field.support import write

async def main(root):
 root.mkdir()
 async with FakeSource() as service:
  c=configuration(service);b=binding(c,'diagnose',root,'LIFECYCLE-CLI-SIGINT')
  cp=root/'config.json';bp=root/'binding.json';write(cp,c);write(bp,b);out=root/'signal-output'
  proc=await asyncio.create_subprocess_exec(sys.executable,'-m','tto_field.cli','diagnose','--config',str(cp),'--binding',str(bp),'--output',str(out),'--duration','30','--allow-network',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
  first=await asyncio.wait_for(proc.stdout.readline(),30)
  await asyncio.sleep(1.);proc.send_signal(signal.SIGINT)
  stdout,stderr=await asyncio.wait_for(proc.communicate(),30);assert proc.returncode==0,(stdout,stderr)
  (root/'signal.stdout.log').write_bytes(first+stdout);(root/'signal.stderr.log').write_bytes(stderr)
  result=json.loads((out/'summary.json').read_text());assert result['collector_summary']['stop_reason']=='SIGINT' and result['own_async_tasks_remaining']==0
  # Hold the actual entry while the second authorized launch is rejected before any collector.
  b=binding(c,'diagnose',root,'LIFECYCLE-FIRST');task=asyncio.create_task(run(c,b,'diagnose',root/'first',duration=3))
  await asyncio.sleep(.5)
  b2=binding(c,'diagnose',root,'LIFECYCLE-SECOND');rejected=False
  try:await run(c,b2,'diagnose',root/'second',duration=1)
  except ValueError:rejected=True
  assert rejected and not (root/'second').exists();await task
  # Reusing the completed command is refused by the persistent ledger, not just the process lock.
  duplicate=False
  try:await run(c,b,'diagnose',root/'reused',duration=1)
  except FileExistsError:duplicate=True
  assert duplicate and not (root/'reused').exists()
  import tto.collector
  native=tto.collector.collect
  async def shortened(config,duration,**kw):return await native(config,1.,**kw)
  b3=binding(c,'diagnose',root,'LIFECYCLE-NATIVE-EXIT')
  with patch('tto.collector.collect',shortened):result2=await run(c,b3,'diagnose',root/'native-exit',duration=10)
  assert result2['reason']=='collector_exited' and result2['own_async_tasks_remaining']==0
  assert service.posts==0
  write(root/'verification.json',dict(SIGINT_native_stop_reason=result['collector_summary']['stop_reason'],CLI_exit_code=proc.returncode,
       actual_concurrent_second_launch_rejected=rejected,persistent_completed_command_rejected=duplicate,
       premature_actual_collector_exit=result2['reason'],actual_requests=service.posts,cleanup_tasks_remaining=0))
 print('Lifecycle checks passed: SIGINT, actual double-start, command reuse, collector exit')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1])))
