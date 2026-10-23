import copy
import json
import pytest
from tto.demo import record_demo
from tto.dataset import freeze_split, build_dataset, check_split, load_dataset
from tto.util import read_json, seal, write_json
from tto.training import train
from tto.evaluation import evaluate


@pytest.fixture(scope='module')
def grouped_runs(tmp_path_factory):
    root = tmp_path_factory.mktemp('r1')
    runs = record_demo(root / 'runs', count=6, seconds=400)
    return root, runs


def set_groups(runs, names):
    # Test copies only; the original review used the same receive-date sequence.
    for path, ep in zip(runs, names):
        m = read_json(path / 'manifest.json'); m['episode'] = ep
        (path / 'manifest.json').write_text(json.dumps(m))
        for file in path.glob('observations-*'):
            data = [dict(json.loads(line), episode=ep) for line in file.read_text().splitlines()]
            file.write_text(''.join(json.dumps(r) + '\n' for r in data))


def test_noncontiguous_reuse_rejected_at_creation_and_consumption(grouped_runs, tmp_path):
    import shutil
    _, original = grouped_runs
    runs = []
    for i, src in enumerate(original):
        dst = tmp_path / str(i); shutil.copytree(src, dst); runs.append(dst)
    set_groups(runs, 'ABCDEA')
    with pytest.raises(ValueError, match='非连续.*A'):
        freeze_split(runs, tmp_path / 'frozen')
    d = build_dataset(runs)
    mapping = dict(A='train', B='train', C='validation', D='test', E='test')
    bad = seal({'schema_version': 1, 'dataset_sha256': d['sha256'], 'sources': d['sources'], 'scope': 'chronological_episodes', 'episodes_order': list('ABCDE'), 'partitions': {p: [r['id'] for r in d['rows'] if mapping[r['episode']] == p] for p in ('train','validation','test')}})
    with pytest.raises(ValueError, match='非连续.*A'):
        check_split(d, bad)
    write_json(tmp_path / 'd.json', d); write_json(tmp_path / 's.json', bad)
    with pytest.raises(ValueError, match='非连续'):
        train(tmp_path / 'd.json', tmp_path / 's.json', tmp_path / 'model.json')
    with pytest.raises(ValueError, match='非连续'):
        evaluate(tmp_path / 'd.json', tmp_path / 's.json', None, tmp_path / 'eval')
    assert not (tmp_path / 'test-used.json').exists()


def test_adjacent_same_group_allowed_and_hand_changed_partition_rejected(grouped_runs, tmp_path):
    import shutil
    _, original = grouped_runs
    runs = []
    for i, src in enumerate(original):
        dst = tmp_path / str(i); shutil.copytree(src, dst); runs.append(dst)
    set_groups(runs, 'AABCDE')
    frozen = freeze_split(runs[::-1], tmp_path / 'frozen')
    d, s = load_dataset(frozen / 'dataset.json'), read_json(frozen / 'split.json')
    check_split(d, s)
    assert s['episodes_order'] == list('ABCDE')
    assert {r['run_id'] for r in d['rows'] if r['id'] in s['partitions']['train'] and r['episode']=='A'} == {run['observer_run_id'] for run in d['runs'] if run['episode'] == 'A'}
    s.pop('sha256'); s['partitions']['train'],s['partitions']['test'] = s['partitions']['test'],s['partitions']['train']
    with pytest.raises(ValueError, match='not chronological'):
        check_split(d, seal(s))


def test_missing_time_evidence_and_overlapping_runs_are_explicit(grouped_runs, tmp_path):
    _, runs = grouped_runs
    d = build_dataset(runs)
    from tto.dataset import chronological_runs
    damaged = copy.deepcopy(d); damaged['runs'][0].pop('time_evidence')
    with pytest.raises(ValueError, match='时间证据不足'):
        chronological_runs(damaged)
    damaged = copy.deepcopy(d); damaged['runs'][1]['time_evidence'] = damaged['runs'][0]['time_evidence']
    with pytest.raises(ValueError, match='时间范围交错'):
        chronological_runs(damaged)


def test_single_process_exploratory_purge_is_preserved(tmp_path):
    runs = record_demo(tmp_path / 'runs', count=1, seconds=1800)
    frozen = freeze_split(runs, tmp_path / 'frozen', exploratory=True)
    d,s = load_dataset(frozen / 'dataset.json'),read_json(frozen / 'split.json')
    check_split(d,s)
    assert s['scope'] == 'same_thermal_process_time_extrapolation'
    assert s['discarded']


def test_cross_run_support_purge_checked_independently(grouped_runs,tmp_path):
    import shutil
    from datetime import datetime,timezone,timedelta
    _,original=grouped_runs; runs=[]
    for i,source in enumerate(original[:5]):
        dst=tmp_path/str(i);shutil.copytree(source,dst);runs.append(dst)
        for file in dst.glob('observations-*'):
            rows=[json.loads(l) for l in file.read_text().splitlines()]
            for row in rows:
                row['received_at_utc']=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=i*400+row['mono_s'])).isoformat()
            file.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    frozen=freeze_split(runs,tmp_path/'frozen')
    d,s=load_dataset(frozen/'dataset.json'),read_json(frozen/'split.json')
    assert s['discarded']
    check_split(d,s)
    # A handcrafted list that assigns all origins skips the required boundary purge.
    episode_part={r['episode']:p for p,ids in s['partitions'].items() for r in d['rows'] if r['id'] in ids}
    s.pop('sha256');s['partitions']={p:[r['id'] for r in d['rows'] if episode_part[r['episode']]==p] for p in ('train','validation','test')}
    with pytest.raises(ValueError,match='cross-run raw temporal support'):
        check_split(d,seal(s))


def test_single_run_exploration_uses_monotonic_time_even_when_utc_jumps(tmp_path):
    runs=record_demo(tmp_path/'runs',count=1,seconds=1800)
    for file in runs[0].glob('observations-*'):
        rows=[json.loads(l) for l in file.read_text().splitlines()]
        for r in rows:
            if r['mono_s']>900:r['received_at_utc']='1990-01-01T00:00:00+00:00'
        file.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    frozen=freeze_split(runs,tmp_path/'exploration',exploratory=True)
    d,s=load_dataset(frozen/'dataset.json'),read_json(frozen/'split.json')
    assert not d['runs'][0]['time_evidence']['clock_consistent']
    check_split(d,s)
    assert s['scope']=='same_thermal_process_time_extrapolation'
