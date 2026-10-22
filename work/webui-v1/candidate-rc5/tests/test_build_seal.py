"""An occupied candidate must be rejected before sealing or rebuilding any artifact."""
import importlib.util
from pathlib import Path
import pytest


@pytest.mark.parametrize('occupied',['stage','wheel'])
def test_existing_candidate_is_read_only_on_rebuild(tmp_path,monkeypatch,occupied):
    script=Path(__file__).parents[1]/'tools/build_history_candidate.py'
    spec=importlib.util.spec_from_file_location('build_seal_test',script)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    monkeypatch.setattr(builder,'STAGE',tmp_path/'candidate')
    manifest=tmp_path/'src/tto_web/web-candidate-files.json';manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b'previous sealed identity')
    wheel=tmp_path/f'dist/tto_web_ui-{builder.VERSION}-py3-none-any.whl'
    if occupied=='stage':builder.STAGE.mkdir()
    else:wheel.parent.mkdir();wheel.write_bytes(b'previous wheel')
    with pytest.raises(SystemExit,match='already exists'):
        builder.main()
    assert manifest.read_bytes()==b'previous sealed identity'
    if occupied=='wheel':assert wheel.read_bytes()==b'previous wheel'
