import numpy,socket
from pathlib import Path
def blocked(*a,**k):
 Path('/Users/massif/Tianshan-thermal-observer/evidence/cpu-runtime-threads-20261020/verification/installed-cli-release/forbidden-network-attempts.txt').write_text('network attempted')
 raise RuntimeError('TEST forbids networking')
socket.create_connection=blocked
socket.socket.connect=blocked
socket.socket.connect_ex=blocked
