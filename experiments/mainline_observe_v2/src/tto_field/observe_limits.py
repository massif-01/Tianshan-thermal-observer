"""Observe-only bounded diagnostics. Full poll/raw/resource events stay on disk."""
from collections import deque
class Samples(deque):
    def __init__(self):super().__init__(maxlen=4096);self.total=0
    def append(self,value):self.total+=1;super().append(value)
    def __getitem__(self,item):return list(self)[item] if isinstance(item,slice) else super().__getitem__(item)

class ReceiverBudget:
    """Predeclared observe policy: 5% target, rolling10s >8% for30s, RSS128MiB, unknown10s."""
    def __init__(self):self.samples=deque();self.over=None;self.unknown=None;self.mean=None
    def sample(self,row,t,*,enforce=True):
        cpu=row['cpu_pct_single_core'];rss=row['rss_bytes']
        if cpu is not None:self.samples.append((t,cpu))
        while self.samples and t-self.samples[0][0]>10:self.samples.popleft()
        self.mean=sum(v for _,v in self.samples)/len(self.samples) if self.samples else None
        if not enforce:return None
        if rss is None or (cpu is None and t>2):
            if self.unknown is None:self.unknown=t
        else:self.unknown=None
        exceeded=self.mean is not None and len(self.samples)>=8 and self.mean>8
        if exceeded and self.over is None:self.over=t
        if not exceeded:self.over=None
        if rss is not None and rss>128*1024**2:return 'receiver_RSS_budget'
        if self.over is not None and t-self.over>=30:return 'receiver_sustained_CPU_budget'
        if self.unknown is not None and t-self.unknown>=10:return 'resource_unavailable'
        return None
