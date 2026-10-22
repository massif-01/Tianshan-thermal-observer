"""Readback final ZIP -> fresh offline install -> real own CLI, never systemd/device."""
import hashlib,json,os,signal,socket,subprocess,sys,time,zipfile
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    archive=ROOT/'TTO-WebUI-v1-rc5-Claude-Sonnet-5.5-审查交接包.zip'
    dest=Path('/private/tmp/tto-web-rc5-zip-readback');dest.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        z.extractall(dest);members=len(z.namelist())
    bundle=dest/'TTO-WebUI-v1.0-rc5'
    payload=json.loads((bundle/'PAYLOAD-MANIFEST.json').read_text())
    for name,digest in payload.items():assert sha(bundle/name)==digest,name
    rootfiles=[n for n in payload if n.startswith(('src/','vendor/','tools/','tests/')) or n in ('pyproject.toml','candidate-identities.json')]
    for n in rootfiles:assert (bundle/n).read_bytes()==(ROOT/'candidate-rc5'/n).read_bytes(),n
    wheel=next((bundle/'wheelhouse').glob('tto_web_ui-*.whl'))
    assert sha(wheel)==sha(ROOT/'dist'/wheel.name)
    with zipfile.ZipFile(wheel) as z:
        sealed=json.loads(z.read('tto_web/web-candidate-files.json'))
        for name,digest in sealed['files'].items():
            source=bundle/('src' if name.startswith('tto_web/') else 'vendor')/name
            assert source.read_bytes()==z.read(name),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
    prefix=Path('/private/tmp/tto-web-rc5-from-final-zip')
    install=subprocess.run([sys.executable,str(bundle/'tools/install.py'),'--prefix',str(prefix),'--service','none','--python','/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12'],capture_output=True,text=True)
    (ROOT/'evidence/self-review-rc5/zip-offline-install.log').write_text(install.stdout+install.stderr);assert install.returncode==0
    py=prefix/'current/env/bin/python'
    identity=json.loads(subprocess.check_output([str(py),'-c','import json,tto_web;from tto_web.identity import verify;print(json.dumps(dict(module=tto_web.__file__,identity=verify())))'],text=True))
    env=dict(os.environ,TTO_WEB_TEST_BOOT_ID='rc5-final-zip')
    cli=subprocess.Popen([str(prefix/'tto-web'),'serve','--config',str(prefix/'web.json')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    opener=build_opener(ProxyHandler({}))
    try:
        end=time.monotonic()+15
        while True:
            if cli.poll() is not None:raise AssertionError(cli.stderr.read())
            try:
                h=json.load(opener.open('http://127.0.0.1:59009/healthz',timeout=.3))
                if h['pid']==cli.pid:break
            except OSError:pass
            assert time.monotonic()<end
            time.sleep(.1)
        assert h['version']=='1.0.0rc5'
        snapshot=json.load(opener.open('http://127.0.0.1:59009/api/v1/snapshot'))
        result=json.load(opener.open('http://127.0.0.1:59009/api/v1/series?ids=temperature.tj,model.Tf_C,model.Ts_C,model.E_C'))
        assert snapshot['mode']=='waiting' and all(not s['points'] for s in result['series'])
    finally:
        cli.send_signal(signal.SIGTERM);stdout,stderr=cli.communicate(timeout=15)
    assert cli.returncode==0
    receipt=dict(version='1.0.0rc5',archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),wheel=wheel.name,wheel_bytes=wheel.stat().st_size,wheel_sha256=sha(wheel),zip_members=members,payload_files_checked=len(payload),source_files_byte_equal=len(rootfiles),wheel_source_files_byte_equal=len(sealed['files']),offline_install_from_exact_zip=True,installed=identity,cli_health=h,cli_exit_code=cli.returncode,waiting_mode=snapshot['mode'],empty_model_history=True,service_none=True,no_device=True)
    (ROOT/'TTO-WebUI-v1-rc5-交付核验回执.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
