#!/usr/bin/env python3
"""CLI agent for coupling 2 or 3 models with M4-style governance.

NOTE: Requires the polly_eggs prototype at prototype/polly_eggs/.
The import below resolves to prototype.polly_eggs.src.polly_eggs.model_synthesis.
If you see ImportError, ensure the prototype subproject is present and that
the repo root is on sys.path (this script adds it automatically).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototype.polly_eggs.src.polly_eggs.model_synthesis import from_payload, synthesize


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="path to synthesis JSON payload")
    args = p.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    nodes, perp, threshold = from_payload(payload)
    result = synthesize(nodes, perp, threshold)

    out = {
        "decision": result.decision,
        "composite_pos": [float(x) for x in result.composite_pos],
        "inherited_trust": result.inherited_trust,
        "harmonic_energy": result.harmonic_energy,
        "reason": result.reason,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
