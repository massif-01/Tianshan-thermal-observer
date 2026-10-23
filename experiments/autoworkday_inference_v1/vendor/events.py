"""Passive protocol.jsonl adapter. No networking, collectors, or Requester imports."""
import argparse
from collections import deque
import hashlib
import json

CONTRACT = 'TTO-WORKLOAD-EVENTS-v1'
EVENTS = {'request_submit', 'first_content', 'request_end', 'request_cancel'}

class Adapter:
    def __init__(self, *, session_id, source_clock_domain, observer_clock_domain,
                 complete_from_session_start=False, publication_mode='replay'):
        self.session_id = session_id
        self.source_clock_domain = source_clock_domain
        self.observer_clock_domain = observer_clock_domain
        self.mode = publication_mode
        self.known = complete_from_session_start
        self.active = set()
        self.seen = set()
        self.recent = deque()
        self.last_source_mono = None
        self.sequence = 0

    def unavailable(self, reason, *, received_mono_s=None):
        self.known = False
        return dict(contract=CONTRACT, event='source_unknown', reason=reason,
                    session_id=self.session_id, client_inflight=None,
                    received_mono_s=received_mono_s,
                    observer_clock_domain=self.observer_clock_domain,
                    gpu_kernel_start=None, gpu_kernel_end=None)

    def feed(self, row, *, received_mono_s=None, received_at_utc=None):
        if row.get('event') not in EVENTS:
            return None
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        if digest in self.seen:
            return None
        self.seen.add(digest)
        self.recent.append(digest)
        if len(self.recent) > 4096:
            self.seen.remove(self.recent.popleft())
        event, rid = row['event'], row.get('request_id')
        mono = row.get('mono_s')
        if (row.get('native_run_id') != self.session_id or not rid or
                not isinstance(mono, (int, float))):
            return self.unavailable('identity_or_source_time_missing', received_mono_s=received_mono_s)
        if self.last_source_mono is not None and mono < self.last_source_mono:
            return self.unavailable('out_of_order_source_event', received_mono_s=received_mono_s)
        self.last_source_mono = mono
        terminal = None
        if event == 'request_submit':
            if rid in self.active or len(self.active) >= 256:
                return self.unavailable('duplicate_submit_or_state_budget', received_mono_s=received_mono_s)
            self.active.add(rid)
        elif event == 'request_end':
            if rid not in self.active:
                self.known = False  # A terminal record cannot invent an earlier live submit.
            self.active.discard(rid)
            if row.get('status') == 'completed' and row.get('done') and row.get('finish_reason') is not None:
                terminal = 'protocol_completed'
            elif row.get('error_class') == 'CancelledError':
                terminal = 'client_cancelled_server_end_unknown'
            else:
                terminal = 'client_ended_server_end_unknown'
        elif rid not in self.active:
            self.known = False
        self.sequence += 1
        return dict(contract=CONTRACT, event=event, sequence=self.sequence,
                    session_id=self.session_id, request_id=rid,
                    source_event_utc=row.get('at_utc'), source_event_mono_s=mono,
                    source_clock_domain=self.source_clock_domain,
                    received_mono_s=received_mono_s, received_at_utc=received_at_utc,
                    observer_clock_domain=self.observer_clock_domain,
                    publication_mode=self.mode, client_inflight=len(self.active) if self.known else None,
                    inflight_scope='this_requester_session_only',
                    terminal=terminal, finish_reason=row.get('finish_reason'),
                    done=row.get('done'), usage=row.get('usage'),
                    server_request_id=row.get('server_request_id'),
                    content_semantics=row.get('semantics') if event == 'first_content' else None,
                    gpu_kernel_start=None, gpu_kernel_end=None)

def main():
    p = argparse.ArgumentParser(description='Offline local JSONL replay; never opens a network connection.')
    p.add_argument('input'); p.add_argument('--session-id', required=True)
    p.add_argument('--source-clock-domain', required=True)
    p.add_argument('--complete-from-session-start', action='store_true')
    a = p.parse_args()
    adapter = Adapter(session_id=a.session_id, source_clock_domain=a.source_clock_domain,
                      observer_clock_domain='offline-replay-arrival-unknown',
                      complete_from_session_start=a.complete_from_session_start)
    with open(a.input, encoding='utf8') as f:
        for line in f:
            if len(line) > 1048576:
                raise ValueError('line_budget_exceeded')
            out = adapter.feed(json.loads(line))
            if out is not None:
                print(json.dumps(out, ensure_ascii=False))

if __name__ == '__main__':
    main()
