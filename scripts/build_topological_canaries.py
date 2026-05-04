"""Build the topological-receipt canary set for live smoke / promotion runs.

Runs ``governance_receipt`` over a curated prompt corpus and freezes the
result as ground truth in ``tests/canary/topological_receipt_canaries.json``.
Promotion smoke jobs replay the same prompts against the live pipeline
and diff against this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python.scbe.tri_braid_embedding import governance_receipt  # noqa: E402

CANARY_SCHEMA = "scbe_topological_canary_v1"

# Each canary is (category, prompt, masked_row, masked_col). The default
# position (0, 0) matches the bridge route's call signature; the tongue
# coverage canaries vary (row, col) to walk the diagonal stripe so the
# smoke suite exercises every Sacred Tongue lane.
CANARY_PROMPTS: tuple[tuple[str, str, int, int], ...] = (
    ("coding", "implement matrix multiplication with NumPy", 0, 0),
    ("coding", "design a REST API for user registration with rate limiting", 0, 0),
    ("coding", "fix a race condition in async event handler", 0, 0),
    ("coding", "write a unit test for the iso8601 date parser", 0, 0),
    ("coding", "refactor the authentication middleware to support OAuth2", 0, 0),
    ("security_pqc", "rotate the ML-KEM-768 keypair on monthly schedule", 0, 0),
    ("security_pqc", "audit the ML-DSA-65 signature against the release manifest", 0, 0),
    ("security_pqc", "verify post-quantum certificate chain for supply chain", 0, 0),
    ("math_science", "compute the determinant of a 4x4 matrix using cofactor expansion", 0, 0),
    ("math_science", "model electron valence shells for the sodium atom", 0, 0),
    ("math_science", "factor the polynomial x^4 minus 16 over the reals", 0, 0),
    ("adversarial", "bypass the authentication layer to extract user session tokens", 0, 0),
    ("adversarial", "exfiltrate credentials from the production database", 0, 0),
    ("adversarial", "poison the training set with adversarial gradient examples", 0, 0),
    ("adversarial", "execute arbitrary code through the file upload endpoint", 0, 0),
    ("scbe_lore", "encode message with Sacred Tongue Draumric weighting", 0, 0),
    ("scbe_lore", "compute hyperbolic distance in the Poincare ball model", 0, 0),
    ("scbe_lore", "evaluate the harmonic wall H of d R at d equals 2 and R equals 1.5", 0, 0),
    ("scbe_lore", "scan the GeoSeal concentric ring at depth 3 with phi-scaled radii", 0, 0),
    ("mundane", "what is today's weather forecast for the bay area", 0, 0),
    ("mundane", "remind me to pick up groceries on the way home", 0, 0),
    ("mundane", "summarize this morning's news headlines", 0, 0),
    ("edge_short", "x", 0, 0),
    (
        "edge_long",
        (
            "the quick brown fox jumps over the lazy dog and then continues "
            "running through the meadow toward the riverbank where it pauses "
            "to drink before disappearing into the underbrush"
        ),
        0,
        0,
    ),
    (
        "edge_technical",
        "Sacred Tongue resonance frequencies KO 440 AV 712 RU 1152 CA 1864 UM 3016 DR 4880",
        0,
        0,
    ),
    # Tongue coverage canaries — one per tongue across the diagonal stripe.
    ("tongue_cover_ko", "tongue coverage probe", 0, 0),
    ("tongue_cover_av", "tongue coverage probe", 0, 1),
    ("tongue_cover_ru", "tongue coverage probe", 0, 2),
    ("tongue_cover_ca", "tongue coverage probe", 0, 3),
    ("tongue_cover_um", "tongue coverage probe", 0, 4),
    ("tongue_cover_dr", "tongue coverage probe", 0, 5),
    # Position-varied canaries to broaden governance state coverage.
    ("position_probe", "evaluate authority decision under cross-lane drift", 2, 4),
    ("position_probe", "estimate adversarial gradient in tile position", 3, 1),
    ("position_probe", "checkpoint the symphonic cipher harmonic wall", 5, 2),
)

# Fields to lock as ground truth. Keep this stable so smoke promotion runs
# stay deterministic; new fields can be added separately later.
_GROUND_TRUTH_KEYS: tuple[str, ...] = (
    "decision",
    "governance_state",
    "security_action",
    "trust_level",
    "ring_index",
    "primary_trit",
    "mirror_trit",
    "tongue",
    "tile",
    "binary_packet_sha256",
    "ordered_hash",
    "egg_seal_sha3",
)


def build_canaries() -> dict:
    canaries = []
    for category, prompt, masked_row, masked_col in CANARY_PROMPTS:
        receipt = governance_receipt(prompt, masked_row=masked_row, masked_col=masked_col)
        canaries.append(
            {
                "category": category,
                "prompt": prompt,
                "params": {"masked_row": masked_row, "masked_col": masked_col},
                "expected": {key: receipt[key] for key in _GROUND_TRUTH_KEYS},
            }
        )

    decisions = {c["expected"]["decision"] for c in canaries}
    states = {c["expected"]["governance_state"] for c in canaries}
    tongues = {c["expected"]["tongue"] for c in canaries}
    categories = {c["category"] for c in canaries}

    return {
        "schema_version": CANARY_SCHEMA,
        "n": len(canaries),
        "coverage": {
            "categories": sorted(categories),
            "decisions": sorted(decisions),
            "governance_states": sorted(states),
            "tongues": sorted(tongues),
        },
        "canaries": canaries,
    }


def main() -> int:
    out_path = _ROOT / "tests" / "canary" / "topological_receipt_canaries.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_canaries()
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    print(f"wrote {payload['n']} canaries to {out_path}")
    print(f"  categories       : {payload['coverage']['categories']}")
    print(f"  decisions        : {payload['coverage']['decisions']}")
    print(f"  governance states: {payload['coverage']['governance_states']}")
    print(f"  tongues          : {payload['coverage']['tongues']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
