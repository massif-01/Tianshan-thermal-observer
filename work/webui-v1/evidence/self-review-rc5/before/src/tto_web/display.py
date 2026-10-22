"""Failure boundary for the optional display encoder and publisher only."""
from collections import deque
from .common import boot_id


class DisplayPublisher:
    def __init__(self, sink):
        self.sink = sink
        self.errors = deque(maxlen=32)
        self.gap_pending = False

    def publish(self, encode):
        try:
            packet = encode()
            if self.gap_pending:
                packet = dict(packet, publication_gap=True)
            self.sink(packet)
            self.gap_pending = False
        except Exception as exc:
            # No payload, exception text, credentials, or native processing here.
            self.errors.append(type(exc).__name__)
            self.gap_pending = True
            try:
                self.sink(dict(schema='TTO-WEB-DISPLAY-GAP-v1', boot_id=boot_id(),
                    clock_domain_id='host-monotonic:'+boot_id(), error_class=type(exc).__name__))
            except Exception:
                # A broken display sink cannot affect the original evidence commit.
                # Its receivers expire on their existing deadlines; next delivery is a gap.
                pass
