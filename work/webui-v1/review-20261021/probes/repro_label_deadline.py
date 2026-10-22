"""No-network check of Web wall-time vs producer-time label completion."""
import os
import json
import sys
import time
from pathlib import Path

ROOT = Path(os.environ["TTO_REVIEW_CANDIDATE"]).resolve()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "tests")]
from producer import Producer, web_config
from tto_web.state import State

p = Producer(time.monotonic() - 120)
s = State(web_config())
for t in range(24):
    s.accept(p.step(t), now=p.start + t + .01)
pred = next(v for v in s.predictions if v["origin_elapsed_ms"] == 9000 and v["horizon_s"] == 15)
assert pred["target_elapsed_ms"] == 24000 and pred["status"] == "pending"
# Last publication remains connected; the next TJ packet takes 1.2 s to reach Web.
s.accept(p.row("fan", 24.5, p.fan()), now=p.start + 24.51)
packet = p.step(25, tj=48)
source_label = next(m for m in packet["metrics"] if m["id"] == "temperature.tj")
s.refresh(p.start + 26.1)
before = pred["status"]
s.accept(packet, now=p.start + 26.2)
after = pred["status"]
assert source_label["as_of_elapsed_ms"] == 25000
assert source_label["status"] == "valid" and packet["source_epoch"] == pred["source_epoch"]
assert before == after == "missing_label" and pred["observed_C"] is None
print(json.dumps({
    "python": sys.version,
    "target_elapsed_ms": pred["target_elapsed_ms"],
    "allowed_label_window_ms": [24000, 26000],
    "actual_source_label_elapsed_ms": source_label["as_of_elapsed_ms"],
    "web_receive_elapsed_ms": 26200,
    "source_transport_delay_ms": 1200,
    "source_label_valid": source_label["status"],
    "same_epoch": packet["source_epoch"] == pred["source_epoch"],
    "publication_gap": packet.get("publication_gap", False),
    "source_connected": s.source_connected,
    "status_before_arrival": before, "status_after_arrival": after,
    "observed_C": pred["observed_C"],
    "effect": "A valid first source label is omitted; no incorrect matched error is generated.",
}, ensure_ascii=False, indent=2))
