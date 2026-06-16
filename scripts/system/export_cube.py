"""Build-time export of the REAL cube faces for the web product.

The web (Vercel) is Node-only, but the rich cube faces — chemistry, the six
tongue/code faces, Wolfram-CA — live in the Python engines. Rather than fake them
(the old atomic-lab regex toy) or duplicate the engines in JS, this runs the real
`python/scbe/cube_faces` over a curated token set and writes `docs/cube-faces.json`.

The live site then serves GENUINE cube data with no Python runtime in production.
Re-run on each build (or extend TOKENS) to refresh. For arbitrary free-text input,
the proper upgrade is a Python serverless function (`@vercel/python`) calling
`cube_faces.all_faces` directly — that needs a deploy that serves Python.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.cube_faces import all_faces  # noqa: E402  (after sys.path setup)

# Curated showcase: control/flow keywords, real chemistry, and plain words.
TOKENS = [
    "loop", "gate", "calc", "ward", "move", "sense", "morph", "area",
    "H", "O", "C", "N", "Na", "Cl", "Fe", "H2O", "CO2", "NaCl", "C3H8",
    "fox", "build", "verify", "secret",
]


def main() -> int:
    payload = {
        "schema_version": "scbe-cube-faces-v1",
        "generated_by": "scripts/system/export_cube.py",
        "note": "Real cube faces from python/scbe/cube_faces.all_faces — not a mock.",
        "tokens": {t: all_faces(t) for t in TOKENS},
    }
    dest = Path(__file__).resolve().parents[2] / "docs" / "cube-faces.json"
    dest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"wrote {dest} ({len(TOKENS)} tokens, {dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
