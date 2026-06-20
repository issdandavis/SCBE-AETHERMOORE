#!/usr/bin/env python3
"""Build the canonical methalox signed-chain demo artifact.

Produces ``artifacts/demo/methalox/signed_chain.json`` -- a small, real
ReactionLedger chain that `scbe react checkpoint` (and the docs) point at as a
ready-to-run example. The artifacts/ tree is git-ignored, so run this once on a
fresh clone to create the example:

    python scripts/demo/build_methalox_demo.py
    scbe react checkpoint --packets artifacts/demo/methalox/signed_chain.json --rekor-dry-run

The chain tells a methalox-propellant story end to end:
  1. balance  CH4 + 2 O2 -> CO2 + 2 H2O   (methane/oxygen combustion)
  2. geometry CO2 conformer                (a product's 3D shape, if RDKit present)
  3. balance  C3H8 + 5 O2 -> 3 CO2 + 4 H2O (a second, larger combustion step)

Each packet is chained (previous_packet_hash) and signed under one identity, so
`verify()` re-checks every hash, link, and signature. Re-running regenerates a
fresh-but-equivalent chain (timestamps and ML-DSA-65 signature bytes differ each
run) -- which is exactly why the output is git-ignored rather than committed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.reaction_balance import balance_reaction_packet  # noqa: E402
from python.scbe.reaction_state import ReactionLedger  # noqa: E402

OUT_PATH = REPO_ROOT / "artifacts" / "demo" / "methalox" / "signed_chain.json"
AGENT_ID = "scbe-methalox-demo"


def build() -> ReactionLedger:
    ledger = ReactionLedger(agent_id=AGENT_ID)
    ledger.append_packet(balance_reaction_packet(["CH4", "O2"], ["CO2", "H2O"]))
    # Geometry is best-effort: skip cleanly if RDKit is not installed so the
    # demo still builds a valid (shorter) chain anywhere the repo runs.
    try:
        from python.scbe.geometry_view import geometry_view_packet

        ledger.append_packet(geometry_view_packet("O=C=O"))
    except Exception as exc:  # pragma: no cover - environment specific
        print(f"note: geometry step skipped ({exc.__class__.__name__})", file=sys.stderr)
    ledger.append_packet(balance_reaction_packet(["C3H8", "O2"], ["CO2", "H2O"]))
    return ledger


def main() -> int:
    ledger = build()
    if not ledger.verify():
        print("ERROR: freshly built chain failed verify()", file=sys.stderr)
        return 1
    checkpoint = ledger.checkpoint()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"packets": [p.to_dict() for p in ledger.packets]}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(ledger.packets)} packets -> {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"merkle root:    {checkpoint['merkle_root']}")
    print(f"chain verified: {checkpoint['chain_verified']}")
    print(f"signed:         {checkpoint['signature_alg'] or 'no signer backend'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
