#!/usr/bin/env python3
"""Small EML tree probe for source-faithful experiments.

This is intentionally not wired into the production tokenizer. It validates a
few paper-stated identities before any SCBE training or tokenizer integration
uses EML-shaped features.
"""

from __future__ import annotations

import argparse
import cmath
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


TreeKind = Literal["one", "var", "eml"]


@dataclass(frozen=True)
class EMLTree:
    kind: TreeKind
    left: "EMLTree | None" = None
    right: "EMLTree | None" = None

    def to_json(self) -> dict[str, Any]:
        if self.kind in {"one", "var"}:
            return {"kind": self.kind}
        return {
            "kind": self.kind,
            "left": self.left.to_json() if self.left else None,
            "right": self.right.to_json() if self.right else None,
        }


ONE = EMLTree("one")
VAR = EMLTree("var")


def eml(x: complex, y: complex) -> complex:
    """Exp-Minus-Log operator: exp(x) - log(y)."""

    return cmath.exp(x) - cmath.log(y)


def ternary_candidate(x: complex, y: complex, z: complex) -> complex:
    """Constant-free ternary self-seeding candidate from the current notes.

    T(x,y,z) = (exp(x) / log(x)) * (log(z) / exp(y)).
    This probe only verifies T(x,x,x)=1 on valid inputs. It does not assert
    universality.
    """

    return (cmath.exp(x) / cmath.log(x)) * (cmath.log(z) / cmath.exp(y))


def node(left: EMLTree, right: EMLTree) -> EMLTree:
    return EMLTree("eml", left=left, right=right)


EXP_TREE = node(VAR, ONE)
LN_TREE = node(ONE, node(node(ONE, VAR), ONE))

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Treat EML/T operator records as experimental, "
    "source-bounded symbolic computation traces. Preserve the formula, domain boundary, and verification result."
)


def evaluate(tree: EMLTree, x: complex) -> complex:
    if tree.kind == "one":
        return 1 + 0j
    if tree.kind == "var":
        return x
    if tree.kind == "eml" and tree.left and tree.right:
        return eml(evaluate(tree.left, x), evaluate(tree.right, x))
    raise ValueError(f"invalid EML tree: {tree!r}")


def _error(actual: complex, expected: complex) -> float:
    return abs(actual - expected)


def _complex_json(value: complex) -> list[float]:
    return [value.real, value.imag]


def run_probe(samples: list[complex] | None = None, tolerance: float = 1e-10) -> dict[str, Any]:
    real_samples = samples or [0.25 + 0j, 0.5 + 0j, 2 + 0j, 3.5 + 0j]
    complex_samples = real_samples + [0.5 + 0.25j, 1.5 - 0.75j]

    exp_rows = []
    for sample in complex_samples:
        actual = evaluate(EXP_TREE, sample)
        expected = cmath.exp(sample)
        exp_rows.append(
            {
                "x": _complex_json(sample),
                "actual": _complex_json(actual),
                "expected": _complex_json(expected),
                "abs_error": _error(actual, expected),
            }
        )

    ln_rows = []
    for sample in real_samples:
        actual = evaluate(LN_TREE, sample)
        expected = cmath.log(sample)
        ln_rows.append(
            {
                "x": _complex_json(sample),
                "actual": _complex_json(actual),
                "expected": _complex_json(expected),
                "abs_error": _error(actual, expected),
            }
        )

    ternary_rows = []
    for sample in [0.25 + 0j, 0.5 + 0j, 2 + 0j, 3.5 + 0j, 0.5 + 0.25j]:
        actual = ternary_candidate(sample, sample, sample)
        ternary_rows.append(
            {
                "x": _complex_json(sample),
                "actual": _complex_json(actual),
                "expected": [1.0, 0.0],
                "abs_error": _error(actual, 1 + 0j),
            }
        )

    all_errors = [row["abs_error"] for row in exp_rows + ln_rows + ternary_rows]
    return {
        "version": "scbe-eml-tree-probe-v1",
        "source": {
            "paper": "https://arxiv.org/abs/2603.21852",
            "boundary_note": "This probe verifies paper-stated identities and a ternary self-seed check only.",
        },
        "tolerance": tolerance,
        "passed": all(error <= tolerance for error in all_errors),
        "max_abs_error": max(all_errors) if all_errors else 0.0,
        "trees": {
            "exp_x": EXP_TREE.to_json(),
            "ln_x": LN_TREE.to_json(),
        },
        "checks": {
            "exp_x": exp_rows,
            "ln_x": ln_rows,
            "ternary_self_seed": ternary_rows,
        },
    }


def _sft_record(record_id: str, instruction: str, response: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record_id,
        "source": "eml_tree_probe.py",
        "track": "geoseal_coding_eml_operator_substrate",
        "source_type": "verified_experiment",
        "quality": "experimental_reference",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ],
        "metadata": metadata,
    }


def build_sft_records(tolerance: float = 1e-10) -> list[dict[str, Any]]:
    probe = run_probe(tolerance=tolerance)
    records: list[dict[str, Any]] = []

    for idx, row in enumerate(probe["checks"]["exp_x"], start=1):
        records.append(
            _sft_record(
                f"eml_operator_v1_exp_{idx:02d}",
                "Construct exp(x) using only the EML operator and the constant 1. Include the verified numeric trace.",
                (
                    "Identity: exp(x) = eml(x, 1).\n"
                    f"Input x={row['x']}.\n"
                    f"Expected exp(x)={row['expected']}.\n"
                    f"EML output={row['actual']}.\n"
                    f"Absolute error={row['abs_error']}."
                ),
                {"function": "exp", "tree": probe["trees"]["exp_x"], "check": row},
            )
        )

    for idx, row in enumerate(probe["checks"]["ln_x"], start=1):
        records.append(
            _sft_record(
                f"eml_operator_v1_ln_{idx:02d}",
                "Construct ln(x) using only the EML operator and the constant 1. Include the positive-real domain boundary.",
                (
                    "Identity: ln(x) = eml(1, eml(eml(1, x), 1)) for this tested positive-real lane.\n"
                    f"Input x={row['x']}.\n"
                    f"Expected ln(x)={row['expected']}.\n"
                    f"EML output={row['actual']}.\n"
                    f"Absolute error={row['abs_error']}."
                ),
                {"function": "ln", "tree": probe["trees"]["ln_x"], "check": row, "domain": "positive real samples"},
            )
        )

    for idx, row in enumerate(probe["checks"]["ternary_self_seed"], start=1):
        records.append(
            _sft_record(
                f"eml_operator_v1_ternary_seed_{idx:02d}",
                "Verify the ternary candidate self-seeding identity T(x,x,x)=1 without claiming universality.",
                (
                    "Candidate: T(x,y,z) = (exp(x) / ln(x)) * (ln(z) / exp(y)).\n"
                    "Verified boundary: T(x,x,x)=1 wherever the expression is defined.\n"
                    f"Input x={row['x']}.\n"
                    f"T output={row['actual']}.\n"
                    f"Absolute error={row['abs_error']}.\n"
                    "This record does not prove T is universal."
                ),
                {"function": "ternary_self_seed", "check": row, "claim_boundary": "self-seed only"},
            )
        )

    records.append(
        _sft_record(
            "eml_operator_v1_boundary",
            "State the safe claim boundary for SCBE EML/T operator training records.",
            (
                "Safe claim: EML plus the constant 1 constructively generates the scientific-calculator "
                "elementary-function basis studied in Odrzywolek 2026. The ternary T candidate is only verified "
                "here for T(x,x,x)=1 on valid inputs. Do not claim unrestricted elementary-function universality "
                "or production tokenizer behavior from this experimental probe."
            ),
            {
                "paper": "https://arxiv.org/abs/2603.21852",
                "critique_boundary": "https://www.stylewarning.com/posts/not-all-elementary/",
            },
        )
    )
    return records


def write_sft_dataset(output_path: Path, manifest_path: Path, tolerance: float = 1e-10) -> dict[str, Any]:
    records = build_sft_records(tolerance=tolerance)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "eml_operator_sft_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "output_path": str(output_path),
        "record_count": len(records),
        "tolerance": tolerance,
        "source": {
            "paper": "https://arxiv.org/abs/2603.21852",
            "integration_note": "docs/specs/EML_OPERATOR_SCBE_INTEGRATION_NOTE_2026-04-25.md",
        },
        "claim_boundary": "experimental verified identities only; no production tokenizer integration",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated EML tree probe.")
    parser.add_argument("--out", default="", help="Optional JSON output path.")
    parser.add_argument("--sft-output", default="", help="Optional JSONL SFT output path.")
    parser.add_argument("--sft-manifest", default="", help="Optional SFT manifest path.")
    parser.add_argument("--tolerance", type=float, default=1e-10)
    args = parser.parse_args()

    if args.sft_output:
        manifest_path = Path(args.sft_manifest) if args.sft_manifest else Path(args.sft_output).with_suffix(".manifest.json")
        manifest = write_sft_dataset(Path(args.sft_output), manifest_path, tolerance=args.tolerance)
        print(json.dumps(manifest, indent=2))
        return 0

    result = run_probe(tolerance=args.tolerance)
    payload = json.dumps(result, indent=2)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
