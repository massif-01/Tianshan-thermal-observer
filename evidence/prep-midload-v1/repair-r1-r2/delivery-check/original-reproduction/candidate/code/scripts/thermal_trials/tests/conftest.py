import ipaddress
import socket
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))


@pytest.fixture(autouse=True)
def owned_loopback_only(monkeypatch):
    original_connect=socket.socket.connect;original_resolve=socket.getaddrinfo
    def check(host):
        if host=='localhost':return
        assert ipaddress.ip_address(host).is_loopback,'offline test attempted non-loopback access'
    def connect(self,address):
        if self.family in (socket.AF_INET,socket.AF_INET6):check(address[0])
        return original_connect(self,address)
    def resolve(host,*args,**kwargs):check(host);return original_resolve(host,*args,**kwargs)
    monkeypatch.setattr(socket.socket,'connect',connect);monkeypatch.setattr(socket,'getaddrinfo',resolve)
