"""Emit a deterministic mechanics receipt for the atomic stitch overlay."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.atomic_context_bundle import (  # noqa: E402
    build_atomic_context_bundle,
    compute_drift_clock,
    equilibrate_semantic_charge,
    fuse_atomic_context,
)
from python.scbe.frozen_stitch_protocol import DEFAULT_STITCH_REGISTRY  # noqa: E402
from python.scbe.reaction_state import canonical_json, sha256_value  # noqa: E402

PINNED_B256_TABLE_SHA256 = "fc85ad01480c1d0b72de32645b77538dfc0110cc58461eb9e8f9a50bc2d51009"
PINNED_TOKENIZER_SHA256 = "6c14a5cd26188678f920273cff49483f535e340caa98e3a7eb4d3285286c37c6"


def build_demo_receipt(tokens: list[str], *, charge_gain: float) -> dict[str, object]:
    bundle = build_atomic_context_bundle(
        tokens,
        tokenizer_id=f"clay-frozen-bpe4096:{PINNED_TOKENIZER_SHA256}",
        token_table_sha256=PINNED_B256_TABLE_SHA256,
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        context_class="operator",
        step_clock=1,
        neighbor_count=min(2, max(0, len(tokens) - 1)),
    )
    equilibrium = equilibrate_semantic_charge(bundle)
    frozen_baseline = fuse_atomic_context(bundle, equilibrium, charge_gain=0.0)
    stitched = fuse_atomic_context(bundle, equilibrium, charge_gain=charge_gain)
    clock = compute_drift_clock(bundle, equilibrium)
    vote_delta = {
        tongue: stitched.reconstruction_votes[tongue] - frozen_baseline.reconstruction_votes[tongue]
        for tongue in stitched.reconstruction_votes
    }
    receipt = {
        "schema_version": "scbe_atomic_stitch_demo_receipt_v1",
        "claim_status": "PASS_MECHANICS_ONLY",
        "training_authorized": False,
        "runtime_profile": bundle.runtime_profile,
        "tokenizer_id": bundle.tokenizer_id,
        "token_table_sha256": bundle.token_table_sha256,
        "bundle_hash": bundle.bundle_hash,
        "equilibrium_hash": equilibrium.result_hash,
        "stitch_registry_hash": DEFAULT_STITCH_REGISTRY.manifest_hash,
        "tokens": tokens,
        "node_count": len(bundle.nodes),
        "edge_count": len(bundle.edges),
        "semantic_charge": equilibrium.to_dict(),
        "frozen_baseline": {
            "tau_hat": frozen_baseline.tau_hat,
            "votes": frozen_baseline.reconstruction_votes,
        },
        "bounded_intervention": {
            "charge_gain": charge_gain,
            "tau_hat": stitched.tau_hat,
            "votes": stitched.reconstruction_votes,
            "vote_delta": vote_delta,
        },
        "drift_clock": asdict(clock),
        "claim_boundary": [
            "mechanics and replay only; no neural gain measured",
            "semantic charge is not physical electrostatic charge",
            "drift clock is not photon propagation or relativistic time dilation",
            "deterministic compiler authority is unchanged",
        ],
    }
    receipt["receipt_sha256"] = sha256_value(receipt)
    # Return the same JSON-native value that is written to durable storage.
    # This avoids tuple/list drift between an in-memory receipt and its replay.
    return json.loads(canonical_json(receipt))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tokens", nargs="*", default=["not", "build", "the", "compiler"])
    parser.add_argument("--charge-gain", type=float, default=0.25)
    args = parser.parse_args()
    print(
        json.dumps(
            build_demo_receipt(args.tokens, charge_gain=args.charge_gain),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
