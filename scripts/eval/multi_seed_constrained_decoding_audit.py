"""Audit the constrained-decoding shim's 92% claim with the multi-seed harness.

The bijective-coder constrained-decoding shim lives at
``src/governance/coding_eval_constrained_decoding.py``. Its claim is
that ``build_prefix_from_required`` renders a forced prefix that
satisfies the contract's required-substring matching by construction,
and the model continuation only needs to avoid forbidden tokens.

This script audits two flavors:

1. **Prefix-only** (no model, deterministic). Returns the rendered
   forced prefix as the model output. Verifies the structural claim:
   does the prefix alone clear the gate? If recall < 100%, the shim
   has a forbidden-collision bug. Fully deterministic, so all seeds and
   temperatures should report the same pass rate.

2. **Prefix + uniform-noise continuation** (no model, parameterized
   noise). Appends a deterministic-by-(seed, temperature) suffix that
   may or may not include forbidden tokens, simulating model
   continuation drift. Tests how robust the gate is to continuation
   noise.

A real-model run (HF Inference Endpoint, vLLM, local transformers) is
left as a future dispatch. This script gives us an immediate
seed-distribution audit on the structural mechanism without GPU cost.

Output: artifacts/eval/constrained_decoding_audit.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval.multi_seed_gate_eval import (  # noqa: E402
    run_sweep,
    required_forbidden_checker,
)
from src.governance.coding_eval_constrained_decoding import (  # noqa: E402
    build_prefix_from_required,
)


def prefix_only_model(prompt: dict, seed: int, temperature: float) -> str:
    """Return only the forced prefix the shim would inject.

    Tests the structural claim: does the prefix alone satisfy the
    contract? Recall under this model is the shim's worst-case
    structural bound -- a real-model continuation can only add more
    text, which can only trigger forbidden substrings. Required-substring
    coverage is fully achieved by the prefix when present.
    """

    required = list(prompt.get("required", []) or [])
    forbidden = list(prompt.get("forbidden", []) or [])
    return build_prefix_from_required(required, forbidden)


def prefix_plus_noisy_continuation_model(
    *, forbidden_collision_rate: float = 0.0
) -> "callable":
    """Return a model that appends deterministic-by-(seed, temp) noise.

    At ``forbidden_collision_rate=0.0`` the continuation is harmless
    filler. At higher rates, a deterministic fraction of (prompt, seed,
    temp) triples emits one of the prompt's own forbidden tokens after
    the prefix. Useful for sanity-checking what happens when a real
    model occasionally drifts into forbidden territory.
    """

    def model(prompt: dict, seed: int, temperature: float) -> str:
        required = list(prompt.get("required", []) or [])
        forbidden = list(prompt.get("forbidden", []) or [])
        prefix = build_prefix_from_required(required, forbidden)
        if forbidden_collision_rate <= 0.0 or not forbidden:
            return prefix + "\n# bare code follows here\n"
        # Deterministic per-(prompt, seed, temp) collision draw
        material = json.dumps(
            {
                "prompt_id": str(prompt.get("id", "")),
                "seed": int(seed),
                "temperature": round(float(temperature), 4),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        h = int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:16], 16)
        rng = h / float(0xFFFF_FFFF_FFFF_FFFF)
        if rng < forbidden_collision_rate:
            tok = forbidden[h % len(forbidden)]
            return prefix + f"\n# noise: {tok}\n"
        return prefix + "\n# bare code follows here\n"

    return model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/model_training/coding_verification_eval_contract.json"),
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="0,1,2,3,4",
    )
    parser.add_argument(
        "--temperatures",
        type=str,
        default="0.0,0.3,0.7",
    )
    parser.add_argument(
        "--forbidden-collision-rate",
        type=float,
        default=0.0,
        help="Fraction of (prompt, seed, temp) triples where the noisy "
        "continuation emits a forbidden token (simulates real-model drift).",
    )
    parser.add_argument(
        "--mode",
        choices=("prefix_only", "prefix_plus_noise"),
        default="prefix_only",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/eval/constrained_decoding_audit.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    temperatures = [float(t) for t in args.temperatures.split(",") if t.strip()]

    if args.mode == "prefix_only":
        model = prefix_only_model
        mode_label = "prefix_only (deterministic)"
    else:
        model = prefix_plus_noisy_continuation_model(
            forbidden_collision_rate=args.forbidden_collision_rate
        )
        mode_label = (
            f"prefix_plus_noise (forbidden_collision_rate={args.forbidden_collision_rate})"
        )

    report = run_sweep(
        contract,
        model,
        seeds=seeds,
        temperatures=temperatures,
        checker=required_forbidden_checker,
    )
    report["audit_mode"] = mode_label
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    overall = report["aggregate"]["overall"]
    risk = report["aggregate"]["seed_lucky_risk"]
    print(f"\nconstrained-decoding audit: {mode_label}")
    print(f"contract: {report['contract_id']}")
    print(f"seeds: {seeds}  temperatures: {temperatures}")
    print(
        f"overall pass_rate={overall['pass_rate']:.3f}  "
        f"95% CI [{overall['wilson_95ci_low']:.3f}, {overall['wilson_95ci_high']:.3f}]  "
        f"({overall['passed_count']}/{overall['n_trials']})"
    )
    print(
        f"seed-lucky risk: spread={risk['spread']:.3f}  "
        f"distribution={risk['single_seed_distribution']}"
    )
    print("\nper-prompt pass rates:")
    for pid, row in report["aggregate"]["per_prompt"].items():
        marker = "*" if row["must_pass"] else " "
        print(f"  {marker} {pid:<48} {row['pass_rate']:.2f}  ({row['passed']}/{row['n']})")
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
