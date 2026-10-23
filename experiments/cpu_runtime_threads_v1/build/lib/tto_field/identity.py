"""Installed source verification; checks bytes without network or credential contents."""
import importlib.metadata,json,platform,sys
from pathlib import Path
from .support import digest_file
from . import __version__

def verify(target=False):
    from .numeric_policy import initialize
    numeric=initialize()
    import tto
    root=Path(__file__).resolve().parent;packages=root.parent
    if Path(tto.__file__).resolve().parent != packages/'tto':raise ValueError('TTO import is outside the isolated candidate')
    manifest=json.loads((root/'candidate-files.json').read_text())
    for name,value in manifest['files'].items():
        if digest_file(packages/name)!=value:raise ValueError('installed candidate bytes differ: '+name)
    if tto.__version__!='0.2.4':raise ValueError('native 0.2.4 version contract changed')
    if target and (sys.version_info[:2]!=(3,10) or platform.system()!='Linux' or platform.machine()!='x86_64'):
        raise ValueError('field target is Linux x86_64 CPython3.10; use isolated target environment')
    from tto.storage import source_identity
    return dict(candidate_version=__version__,native_version=tto.__version__,native_source_identity=source_identity(),
                checked_files=len(manifest['files']),python=sys.version,platform=platform.platform(),machine=platform.machine(),
                dependencies={x:importlib.metadata.version(x) for x in ['aiohttp','python-socketio','psutil','numpy','scipy','threadpoolctl']},
                target_environment_checked=target,numeric_thread_policy=numeric)
