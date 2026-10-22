"""Real CLI rapid restart: old TCP connections must not block the next listener."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import build_opener,ProxyHandler


def test_real_cli_rapid_restart_preserves_port_conflict_and_waiting_semantics(tmp_path):
    root=Path(__file__).parents[1];config=tmp_path/'web.json';config.write_bytes((root/'config/web.json').read_bytes())
    env=dict(os.environ) if os.environ.get('TTO_WEB_TEST_INSTALLED') else dict(os.environ,PYTHONPATH=os.pathsep.join([str(root/'src'),str(root/'vendor')]))
    opener=build_opener(ProxyHandler({}))
    for iteration in range(2):
        child=subprocess.Popen([sys.executable,'-m','tto_web.cli','serve','--config',str(config)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        connection=None
        try:
            deadline=time.monotonic()+10
            while True:
                if child.poll() is not None:raise AssertionError(child.stderr.read())
                try:
                    with opener.open('http://127.0.0.1:59009/healthz',timeout=.3) as r:health=json.load(r)
                    if health['pid']==child.pid:break
                except OSError:pass
                assert time.monotonic()<deadline,'own waiting service never ready'
                time.sleep(.05)
            conflict=subprocess.run([sys.executable,'-m','tto_web.cli','serve','--config',str(config)],env=env,capture_output=True,text=True,timeout=10)
            assert conflict.returncode==2 and '59009' in conflict.stderr
            connection=http.client.HTTPConnection('127.0.0.1',59009,timeout=2)
            connection.request('GET','/api/v1/snapshot');response=connection.getresponse();snapshot=json.loads(response.read())
            assert snapshot['mode']=='waiting' and snapshot['model']['phase']=='not_loaded'
            child.terminate();assert child.wait(timeout=10)==0
        finally:
            if connection:connection.close()
            if child.poll() is None:child.terminate();child.wait(timeout=10)
