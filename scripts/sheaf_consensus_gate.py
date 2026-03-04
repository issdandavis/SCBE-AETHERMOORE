#!/usr/bin/env python3
"""CLI for lattice sheaf consensus gating."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.harmonic.sheaf_consensus_gate import run_jsonl, sheaf_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="SCBE Sheaf Consensus Gate")
    parser.add_argument("--input-jsonl", default="", help="Input JSONL with signals")
    parser.add_argument("--output-jsonl", default="", help="Output JSONL path")
    parser.add_argument("--fast", type=float, default=None, help="Single-shot fast signal [0,1]")
    parser.add_argument("--memory", type=float, default=None, help="Single-shot memory signal [0,1]")
    parser.add_argument("--governance", type=float, default=None, help="Single-shot governance signal [0,1]")
    parser.add_argument("--pqc-valid", type=float, default=1.0)
    parser.add_argument("--harm-score", type=float, default=1.0)
    parser.add_argument("--drift-factor", type=float, default=1.0)
    parser.add_argument("--spectral-score", type=float, default=1.0)
    args = parser.parse_args()

    if args.input_jsonl:
        if not args.output_jsonl:
            raise SystemExit("--output-jsonl is required with --input-jsonl")
        counts = run_jsonl(Path(args.input_jsonl), Path(args.output_jsonl))
        print(json.dumps({"status": "ok", "counts": counts, "output": args.output_jsonl}, indent=2))
        return 0

    if args.fast is None or args.memory is None or args.governance is None:
        raise SystemExit("Provide either --input-jsonl or single-shot --fast --memory --governance")

    result = sheaf_gate(
        fast_signal=args.fast,
        memory_signal=args.memory,
        governance_signal=args.governance,
        pqc_valid=args.pqc_valid,
        harm_score=args.harm_score,
        drift_factor=args.drift_factor,
        spectral_score=args.spectral_score,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

