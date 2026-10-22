"""Consume the owner's byte-exact I02 generator using already processed native records.
Dependency injection supplies a read-only view, so export_records never processes quality twice.
The generator's lifecycle latch is the owner's implementation, not another local repair.
"""
from collections import deque
import importlib.util
from pathlib import Path

class PreparedEngine:
    def __init__(self,engine):self.engine=engine;self.record=None;self.result=None;self.process_calls=0
    def __getattr__(self,key):return getattr(self.engine,key)
    def process(self,raw):
        if raw is not self.record:raise ValueError('I02 requested a record outside the native callback')
        self.process_calls+=1
        return self.result

class Records:
    def __init__(self):self.items=deque()
    def __iter__(self):return self
    def __next__(self):return self.items.popleft()

class CommunicationBridge:
    def __init__(self,manifest,engine):
        path=Path(__file__).parent/'upstream_comm/source_health.py'
        spec=importlib.util.spec_from_file_location('_owned_I02_'+str(id(self)),path)
        owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
        self.view=PreparedEngine(engine);self.records=Records()
        # The only seam: substitute construction of a second engine with the existing result view.
        owner.engine_for=lambda *args,**kwargs:self.view
        self.generator=owner.export_records(manifest,self.records)
    def feed(self,raw,processed):
        self.view.record=raw;self.view.result=processed;self.records.items.append(raw)
        return next(self.generator)
