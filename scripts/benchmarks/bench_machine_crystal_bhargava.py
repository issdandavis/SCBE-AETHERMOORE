"""Validate the Bhargava-cube overlay for Machine Crystal."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.machine_crystal_bhargava import bhargava_crystal_receipt


def main() -> int:
    started = time.perf_counter()
    receipt = bhargava_crystal_receipt()
    receipt["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
    out_dir = Path("artifacts/machine_crystal")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bhargava_cube_overlay.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
