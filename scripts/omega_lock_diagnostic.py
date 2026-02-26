#!/usr/bin/env python3
"""Five-lock Omega diagnostic tool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.spiralverse.temporal_intent import TemporalSecurityGate


def recommendation(weakest_lock: str) -> str:
    recs = {
        "pqc_factor": "Validate or rotate PQC key material before routing.",
        "harm_score": "Reduce distance or intent pressure: move toward center, lower risk actions.",
        "drift_factor": "Run stabilization cycle to burn down accumulated intent.",
        "triadic_stable": "Increase triadic consistency (fast/memory/governance alignment).",
        "spectral_score": "Switch tongue/pad profile or apply spectral filter.",
        "trust_exile": "Run exile recovery ritual: reset trust path before any further routing.",
    }
    return recs.get(weakest_lock, "Inspect lock vector and reduce lowest factor first.")


def main() -> int:
    parser = argparse.ArgumentParser(description="SCBE Omega five-lock diagnostic")
    parser.add_argument("--agent-id", default="diagnostic-agent")
    parser.add_argument("--distance", type=float, default=0.20)
    parser.add_argument("--velocity", type=float, default=0.00)
    parser.add_argument("--harmony", type=float, default=0.50)
    parser.add_argument("--samples", type=int, default=1, help="repeat observation count")
    parser.add_argument("--pqc-valid", action="store_true", default=False)
    parser.add_argument("--triadic-stable", type=float, default=1.0)
    parser.add_argument("--spectral-score", type=float, default=1.0)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    gate = TemporalSecurityGate()
    for _ in range(max(1, args.samples)):
        gate.record_observation(
            args.agent_id,
            distance=max(0.0, min(0.999, args.distance)),
            velocity=args.velocity,
            harmony=max(-1.0, min(1.0, args.harmony)),
        )

    vector = gate.compute_lock_vector(
        args.agent_id,
        pqc_valid=args.pqc_valid,
        triadic_stable=args.triadic_stable,
        spectral_score=args.spectral_score,
    )
    payload = {
        "agent_id": args.agent_id,
        "locks": vector.to_dict(),
        "recommendation": recommendation(vector.weakest_lock),
    }
    if args.pretty:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
