#!/usr/bin/env python3
"""Build SFT records for the Binary Lambda Calculus time-placement lane."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto.binary_lambda import BLCTerm, blc_to_surfaces


SYSTEM = (
    "You are an SCBE coding instructor. Explain the same computation across "
    "binary, hex, and Binary Lambda Calculus time-placement surfaces. Keep "
    "binary/hex as byte views and BLC as computation grammar over time."
)


EXAMPLES = [
    {
        "id": "identity",
        "name": "identity function",
        "term": BLCTerm.lam(BLCTerm.var(1)),
        "meaning": "A lambda binder is opened, then the body references the nearest binder.",
    },
    {
        "id": "apply_identity_to_identity",
        "name": "identity applied to identity",
        "term": BLCTerm.app(BLCTerm.lam(BLCTerm.var(1)), BLCTerm.lam(BLCTerm.var(1))),
        "meaning": "Application places the function in time before the argument; both subterms are identity functions.",
    },
    {
        "id": "constant_function",
        "name": "constant function",
        "term": BLCTerm.lam(BLCTerm.lam(BLCTerm.var(2))),
        "meaning": "Two binders are opened; the body references the outer binder.",
    },
]


def build_records() -> list[dict]:
    records = []
    for item in EXAMPLES:
        surfaces = blc_to_surfaces(item["term"])
        response = {
            "id": item["id"],
            "name": item["name"],
            "meaning": item["meaning"],
            **surfaces,
            "integration_rule": (
                "binary and hex preserve the padded byte view; blc_bits preserve "
                "the computation grammar; placements explain when each bit span "
                "acts as binder, branch, or reference."
            ),
        }
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {
                        "role": "user",
                        "content": f"Map the lambda term '{item['name']}' into binary, hex, and BLC time placement.",
                    },
                    {"role": "assistant", "content": json.dumps(response, indent=2, ensure_ascii=True)},
                ],
                "meta": {
                    "source": "blc_time_placement_v1",
                    "example_id": item["id"],
                    "surfaces": ["de_bruijn", "blc_bits", "binary", "hex", "placements"],
                },
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="training-data/sft/blc_time_placement_v1.sft.jsonl")
    parser.add_argument("--manifest", default="training-data/sft/blc_time_placement_v1_manifest.json")
    args = parser.parse_args()

    output = Path(args.output)
    manifest = Path(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = build_records()
    output.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in records) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "blc_time_placement_v1",
                "record_count": len(records),
                "output": str(output),
                "surfaces": ["de_bruijn", "blc_bits", "binary", "hex", "placements"],
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "manifest": str(manifest), "records": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
