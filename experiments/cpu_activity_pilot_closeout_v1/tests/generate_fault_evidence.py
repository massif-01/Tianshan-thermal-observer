"""Actual local child, receiver and file writer; no network/native collector or model request."""
import asyncio,json,sys
from pathlib import Path
from tto_field.cpu_transport import Sidecar
from tto_field.support import Clock,Evidence,write
class Pipeline:run_id='SYNTHETIC-CHILD-ONLY-NO-NATIVE-RUN';fan_success_times=[]
async def main(root):
    for name,code in [('rejected_bytes',"import sys;sys.stderr.buffer.write(b'E'*5000);sys.stderr.flush();sys.stdout.buffer.write(b'bad-row-\\xff\\n');sys.stdout.flush()"),('source_exit7',"import sys;sys.stderr.write('SYNTHETIC SOURCE START FAILURE\\n');sys.exit(7)")]:
        out=root/name;out.mkdir(parents=True,exist_ok=False);ev=Evidence(out);clock=Clock();clock.origin-=30
        s=Sidecar(dict(command_id='SYNTHETIC-'+name,argv=[sys.executable,'-c',code]),out,clock,Pipeline(),ev)
        await s.tick(clock.now(),None);await s.startup_task
        if s.reader:await s.reader
        await asyncio.sleep(.05);await s.close();ev.close()
        write(out/'scope.json',dict(synthetic=True,own_local_child_only=True,native_collection=False,devices=0,requests=0,status=s.status))
    print('actual local rejected-wire/stderr/exit evidence saved')
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1])))
