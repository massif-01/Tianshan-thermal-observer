"""Offline tests: deny non-loopback sockets and subprocess/device/service tools."""
import ipaddress
import socket
import subprocess
import pytest
from tto.config import load_config
from tto.demo import packet, fan_packet, temp_packet


@pytest.fixture(autouse=True)
def offline_guard(monkeypatch):
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo
    def loopback(host):
        if host in ('localhost', None):
            return
        try:
            if ipaddress.ip_address(host).is_loopback:
                return
        except ValueError:
            pass
        raise AssertionError('offline suite blocked non-loopback access')
    def connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            loopback(address[0])
        return real_connect(self, address)
    def connect_ex(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            loopback(address[0])
        return real_connect_ex(self, address)
    def resolve(host, *args, **kwargs):
        loopback(host)
        return real_getaddrinfo(host, *args, **kwargs)
    def popen(*args, **kwargs):
        raise AssertionError('unit suite blocked process/service/device launch')
    monkeypatch.setattr(socket.socket, 'connect', connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', connect_ex)
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    monkeypatch.setattr(subprocess, 'Popen', popen)


@pytest.fixture
def config():
    c = load_config(environ={})
    c['orin'].update(source_sample_interval_ms=1000, source_interval_evidence='synthetic_fixture')
    return c


def record(seq, t=None, **kwargs):
    return {'observer_run_id': 'test-run', 'episode': 'test-process', 'ref': f'test-run/observation:{seq}', 'kind': 'orin', 'mono_s': float(seq if t is None else t), 'received_at_utc': '2026-01-01T00:00:00+00:00', 'connection_epoch': 1, 'payload': packet(seq, 40.0, **kwargs)}


def aux(kind, t):
    return {'observer_run_id': 'test-run', 'episode': 'test-process', 'ref': f'test-run/{kind}:{t}', 'kind': kind, 'mono_s': float(t), 'payload': fan_packet() if kind == 'fan' else temp_packet()}
