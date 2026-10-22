import tto.storage as s
from pathlib import Path
original=s.InstanceLock
def isolated(path=None):
 return original(Path('/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/verification/installed-cli-loopback-final/private-locks')/('native.lock' if path is None else Path(path).name))
s.InstanceLock=isolated
