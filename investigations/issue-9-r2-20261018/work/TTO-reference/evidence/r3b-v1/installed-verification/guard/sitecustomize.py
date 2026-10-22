import ipaddress,socket
_real=socket.socket.connect
_dns=socket.getaddrinfo
def _ok(host):
 if host in ('localhost',None): return
 try:
  if ipaddress.ip_address(host).is_loopback: return
 except ValueError: pass
 raise RuntimeError('loopback-only offline verification')
def _connect(self,address):
 if self.family in (socket.AF_INET,socket.AF_INET6): _ok(address[0])
 return _real(self,address)
def _resolve(host,*a,**k):
 _ok(host)
 return _dns(host,*a,**k)
socket.socket.connect=_connect
socket.getaddrinfo=_resolve
