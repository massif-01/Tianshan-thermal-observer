"""Offline semantic probe using the candidate native processor and public adapter.

No socket client/server is created. The fixture's outer source age and NVML base
age are varied independently; all published values come from real candidate code.
"""
import os
import json
import sys
import time
from pathlib import Path

ROOT = Path(os.environ["TTO_REVIEW_CANDIDATE"]).resolve()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "tests")]

from producer import Producer, web_config
from tto_web.common import utc
from tto_web.state import State


def case(outer_age_ms):
    producer = Producer(time.monotonic() - 10)
    state = State(web_config())
    producer.row("fan", 0, producer.fan())
    producer.row("temp", 0, producer.temp())
    payload = producer.packet(1, gpu_age=2000)
    payload["telemetry_meta"]["sample_age_ms"] = outer_age_ms
    raw = dict(
        kind="orin", payload=payload, mono_s=producer.start + 1,
        received_at_utc=utc(), observer_run_id=producer.manifest["observer_run_id"],
        ref=producer.manifest["observer_run_id"] + "/observation:100",
        episode="SYNTHETIC", connection_epoch=1,
    )
    processed = producer.engine.process(raw)
    packet = producer.adapter.feed(raw, processed)
    state.accept(packet, now=producer.start + 1.01)
    native = processed["quality"]["gpu"]

    def current_gpu():
        m = next(m for m in state.snapshot()["metrics"] if m["id"] == "usage.gpu")
        return {k: m[k] for k in ("value", "status", "age_lower_bound_ms", "remaining_valid_ms")}

    first = current_gpu()
    state.refresh(producer.start + 1.6)
    later = current_gpu()
    result = {
        "nvml_base_age_ms": 2000, "outer_source_age_ms": outer_age_ms,
        "timeout_ms": 5000, "native_accepted_TJ": processed["quality"]["accepted"],
        "native_gpu": native, "web_after_10ms": first, "web_after_600ms": later,
    }
    assert processed["quality"]["accepted"] is True
    if outer_age_ms == 4000:
        assert native["reason"] == "gpu_effective_stale" and native["value"] is None
        assert first["status"] == "valid" and first["value"] == 0
    else:
        assert native["reason"] is None
        assert abs(native["valid_until"] - (producer.start + 1.5)) < 1e-6
        assert later["status"] == "valid" and later["remaining_valid_ms"] > 2000
    return result


if __name__ == "__main__":
    print(json.dumps({"python": sys.version, "cases": [case(4000), case(2500)]}, ensure_ascii=False, indent=2))
