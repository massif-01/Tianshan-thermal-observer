"""An occupied candidate must be rejected before sealing or rebuilding any artifact."""
import importlib.util
from pathlib import Path
import pytest


@pytest.mark.parametrize('builder_name',['history','unified'])
@pytest.mark.parametrize('occupied',['stage','artifact'])
def test_existing_candidate_is_read_only_on_rebuild(tmp_path,monkeypatch,occupied,builder_name):
    root=Path(__file__).parents[1]
    script=root/'tools/build_history_candidate.py' if builder_name=='history' else root.parents[1]/'tools/build_unified_candidate.py'
    spec=importlib.util.spec_from_file_location('build_seal_test',script)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    stage=tmp_path/'candidate'
    if builder_name=='history':monkeypatch.setattr(builder,'STAGE',stage)
    else:monkeypatch.setattr(__import__('sys'),'argv',[str(script),'--output',str(stage)])
    manifest=tmp_path/'src/tto_web/web-candidate-files.json';manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b'previous sealed identity')
    artifact=tmp_path/f'dist/tto_web_ui-{builder.VERSION}-py3-none-any.whl' if builder_name=='history' else Path(str(stage)+'.zip')
    if occupied=='stage':stage.mkdir()
    else:artifact.parent.mkdir(exist_ok=True);artifact.write_bytes(b'previous artifact')
    with pytest.raises(SystemExit,match='already exists|fresh output'):
        builder.main()
    assert manifest.read_bytes()==b'previous sealed identity'
    if occupied=='artifact':assert artifact.read_bytes()==b'previous artifact'
