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


def run_probe(samples: list[complex] | None = None, tolerance: float = 1e-10) -> dict[str, Any]:
    real_samples = samples or [0.25 + 0j, 0.5 + 0j, 2 + 0j, 3.5 + 0j]
    complex_samples = real_samples + [0.5 + 0.25j, 1.5 - 0.75j]

    exp_rows = []
    for sample in complex_samples:
        actual = evaluate(EXP_TREE, sample)
        expected = cmath.exp(sample)
        exp_rows.append(
            {
                "x": [sample.real, sample.imag],
                "actual": [actual.real, actual.imag],
                "expected": [expected.real, expected.imag],
                "abs_error": _error(actual, expected),
            }
        )

    ln_rows = []
    for sample in real_samples:
        actual = evaluate(LN_TREE, sample)
        expected = cmath.log(sample)
        ln_rows.append(
            {
                "x": [sample.real, sample.imag],
                "actual": [actual.real, actual.imag],
                "expected": [expected.real, expected.imag],
                "abs_error": _error(actual, expected),
            }
        )

    ternary_rows = []
    for sample in [0.25 + 0j, 0.5 + 0j, 2 + 0j, 3.5 + 0j, 0.5 + 0.25j]:
        actual = ternary_candidate(sample, sample, sample)
        ternary_rows.append(
            {
                "x": [sample.real, sample.imag],
                "actual": [actual.real, actual.imag],
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated EML tree probe.")
    parser.add_argument("--out", default="", help="Optional JSON output path.")
    parser.add_argument("--tolerance", type=float, default=1e-10)
    args = parser.parse_args()

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

