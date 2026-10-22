"""Bounded local tail of an explicitly supplied existing event log. No polling endpoints."""
import json,time
from pathlib import Path
from .business_events import Adapter
from .support import utc
class EventTail:
    def __init__(self,path,binding,domain,emit):
        self.path=Path(path);self.emit=emit;self.offset=0;self.inode=None;self.buffer=b'';self.last_problem=None
        self.adapter=Adapter(session_id=binding['session_id'],source_clock_domain=binding['clock_domain'],
            observer_clock_domain=domain,complete_from_session_start=binding.get('complete_from_session_start',False),publication_mode='live')
        self.complete=binding.get('complete_from_session_start',False);self.current=None
    def unknown(self,reason):
        self.current=self.adapter.unavailable(reason,received_mono_s=time.monotonic())
        if reason!=self.last_problem:self.emit('workload-events',self.current)
        self.last_problem=reason
    def tick(self):
        try:
            info=self.path.stat();key=(info.st_dev,info.st_ino)
            if self.inode is None:
                self.inode=key;self.offset=info.st_size
                if self.complete and self.offset:raise ValueError('not_attached_from_empty_session_start')
                if not self.complete:self.unknown('mid_session_attachment')
            if self.inode!=key or info.st_size<self.offset:
                self.inode=key;self.offset=info.st_size;self.buffer=b'';self.unknown('event_file_rotated_or_truncated');return
            with self.path.open('rb') as f:f.seek(self.offset);data=f.read(65537)
            if len(data)>65536:
                self.offset=info.st_size;self.buffer=b'';self.unknown('event_read_budget_gap');return
            self.offset+=len(data);self.buffer+=data
            if len(self.buffer)>65536:self.buffer=b'';self.unknown('event_line_budget');return
            while b'\n' in self.buffer:
                line,self.buffer=self.buffer.split(b'\n',1)
                if not line:continue
                def invalid_constant(value):raise ValueError('nonfinite event JSON')
                parsed=json.loads(line,parse_constant=invalid_constant)
                if not isinstance(parsed,dict):raise ValueError('event row is not an object')
                row=self.adapter.feed(parsed,received_mono_s=time.monotonic(),received_at_utc=utc())
                if row is not None:self.last_problem=None;self.current=row;self.emit('workload-events',row)
        except (OSError,ValueError,KeyError,TypeError):self.unknown('event_source_unavailable_or_invalid')
