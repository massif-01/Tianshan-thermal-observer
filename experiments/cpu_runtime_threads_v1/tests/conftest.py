"""Test-only lock namespace: preserve flock semantics without colliding with unrelated local observers."""
import pytest
@pytest.fixture(autouse=True)
def private_collector_locks(tmp_path,monkeypatch):
    import tto.storage as storage
    import tto.collector as collector
    original=storage.InstanceLock
    def isolated(path=None):
        from pathlib import Path
        return original(tmp_path/('native.lock' if path is None else Path(path).name))
    monkeypatch.setattr(storage,'InstanceLock',isolated)
    monkeypatch.setattr(collector,'InstanceLock',isolated)
