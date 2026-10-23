import copy,json
from pathlib import Path
import pytest
from tto_field.receiver_resources import baseline_admission

def sample():return dict(interval_start_mono_s=28.5,mono_s=29.5,cpu_pct_single_core=2.,rss_bytes=80*1024**2,resource_seq=29)
@pytest.mark.parametrize('change,reason',[
 ({'cpu_pct_single_core':8.01},'baseline_receiver_resource_budget_exceeded'),
 ({'rss_bytes':128*1024**2+1},'baseline_receiver_resource_budget_exceeded'),
 ({'cpu_pct_single_core':None},'baseline_receiver_resources_unavailable'),
 ({'cpu_pct_single_core':float('nan')},'baseline_receiver_resources_unavailable'),
 ({'mono_s':28.},'baseline_receiver_resources_unavailable'),
 ({'interval_start_mono_s':0.},'baseline_receiver_resources_unavailable')])
def test_unqualified_baseline_is_not_a_sidecar_green_light(change,reason):
 x=sample();x.update(change);r=baseline_admission(x,30);assert not r['allowed'] and r['reason']==reason

def test_missing_and_exact_limits():
 assert not baseline_admission(None,30)['allowed']
 x=sample();x.update(cpu_pct_single_core=8.,rss_bytes=128*1024**2)
 assert baseline_admission(x,30)['allowed']

def test_unreadable_counter_revokes_previous_sample(monkeypatch):
 import psutil
 from tto_field.receiver_resources import read_sample
 class Denied:
  def cpu_times(self):raise psutil.AccessDenied(123)
 monkeypatch.setattr(psutil,'Process',lambda:Denied())
 row,prev=read_sample(30.,(29.,1.))
 assert prev is None and row['cpu_pct_single_core'] is None and row['rss_bytes'] is None and row['resource_error']=='AccessDenied'
 assert not baseline_admission(row,30)['allowed']
