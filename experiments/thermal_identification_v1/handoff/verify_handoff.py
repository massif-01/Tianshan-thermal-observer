"""Verify this handoff's bytes only. No extraction, network, or experiment execution."""
from pathlib import Path
import hashlib, json, sys
root = Path(__file__).resolve().parent
items = json.loads((root / "SHA256.json").read_text(encoding="utf-8"))
failures = []
for item in items:
    p = (root / item["path"]).resolve()
    if root not in p.parents or not p.is_file():
        failures.append(item["path"] + ": missing or unsafe path")
        continue
    if p.stat().st_size != item["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest() != item["sha256"]:
        failures.append(item["path"] + ": bytes mismatch")
if failures:
    print("\n".join(failures)); sys.exit(1)
print(f"Handoff integrity OK: {len(items)} files. No model experiment has been run.")
