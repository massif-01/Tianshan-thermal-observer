"""Exercise installer filesystem and service command construction. Does not run systemd."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def test_install_system_unit_enables_and_restarts_new_release_without_touching_old_tto(tmp_path,monkeypatch):
    source=Path(__file__).parents[1]/'tools/install.py'
    spec=importlib.util.spec_from_file_location('web_installer_test',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    root=tmp_path/'bundle';(root/'config').mkdir(parents=True);(root/'wheelhouse').mkdir()
    (root/'config/web.json').write_text(json.dumps({'web':{'port':59009,'bind':'127.0.0.1','access_mode':'local'},'source':{},'advisory':{}}))
    (root/'wheelhouse/tto_web_ui-1.0.0rc1-py3-none-any.whl').write_bytes(b'SYNTHETIC command construction test only')
    (root/'requirements.runtime.lock').write_text('')
    files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    (root/'candidate-identities.json').write_text(json.dumps(files))
    prefix=tmp_path/'independent Web prefix';commands=[]
    monkeypatch.setattr(m,'wait_ready',lambda *args:commands.append(['ready-check']))
    monkeypatch.setattr(m,'ROOT',root);monkeypatch.setattr(m,'run',lambda *args:commands.append([str(a) for a in args]))
    monkeypatch.setattr(m.getpass,'getuser',lambda:'synthetic-user');monkeypatch.setattr(m.sys,'platform','linux');monkeypatch.setattr(m.os,'getuid',lambda:501)
    monkeypatch.setattr(sys,'argv',['install.py','--prefix',str(prefix),'--service','system'])
    m.main()
    assert any(command[-2:]==['enable','tto-web.service'] for command in commands)
    assert any(command[-2:]==['restart','tto-web.service'] for command in commands)
    assert commands[-1]==['ready-check']
    unit=(prefix/'tto-web.service').read_text()
    assert 'WantedBy=multi-user.target' in unit and 'User=' in unit
    assert '59009' in unit and 'ExecStart="'+str(prefix/'tto-web')+'"' in unit
    assert (prefix/'current').is_symlink() and (prefix/'web.json').exists()


def test_service_ready_check_rejects_other_listener_pid(tmp_path,monkeypatch):
    import io,pytest
    source=Path(__file__).parents[1]/'tools/install.py'
    spec=importlib.util.spec_from_file_location('ready_installer_test',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    config=tmp_path/'web.json';config.write_text(json.dumps(dict(web=dict(bind='127.0.0.1',access_mode='local'))))
    monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**k:'12345')
    monkeypatch.setattr(m,'urlopen',lambda *a,**k:io.StringIO('{"pid":54321,"web":"running"}'))
    with pytest.raises(SystemExit,match='未在期限内就绪'):m.wait_ready(config,['systemctl'],timeout_s=.02)
    monkeypatch.setattr(m,'urlopen',lambda *a,**k:io.StringIO('{"pid":12345,"web":"running"}'))
    m.wait_ready(config,['systemctl'],timeout_s=.1)
