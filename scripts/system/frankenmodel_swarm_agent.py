#!/usr/bin/env python3
"""FrankenModel Swarm Agent: capability-coupled 2-3 model synthesis.

NOTE: Requires the polly_eggs prototype at prototype/polly_eggs/.
The import below resolves to prototype.polly_eggs.src.polly_eggs.frankenmodel.
If you see ImportError, ensure the prototype subproject is present and that
the repo root is on sys.path (this script adds it automatically).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototype.polly_eggs.src.polly_eggs.frankenmodel import build_frankenmodel, candidate_from_dict


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    args = p.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    task = payload.get("task", {})
    perp = np.array(payload.get("perp_space", [0.0, 0.0, 0.0]), dtype=np.float64)
    candidates = [candidate_from_dict(x) for x in payload.get("candidates", [])]

    result = build_frankenmodel(task, candidates, perp)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
