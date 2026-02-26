#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototype.polly_eggs.src.polly_eggs.semantic_mesh import encode_tokens, governance_signal, hamming_distance


def main() -> int:
    a = encode_tokens(["navigation-basics", "aethermore-v1", "egg-0001"])
    b = encode_tokens(["resource-discipline", "aethermore-v1", "egg-0001"])
    out = {
        "mesh_a_hex": a.to_hex(),
        "mesh_b_hex": b.to_hex(),
        "signal_a": governance_signal(a),
        "signal_b": governance_signal(b),
        "hamming": hamming_distance(a, b),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
