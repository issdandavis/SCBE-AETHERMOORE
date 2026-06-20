"""Run a deterministic adversarial eval through the full 14-layer pipeline.

This is not a prompt-injection corpus benchmark. It isolates the geometric
claim: as adversarial profiles move farther from the calibrated safe state,
the full pipeline's decision layer should stop allowing them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline import (
    FourteenLayerPipeline,
)

SAFE_PROFILE: dict[str, Any] = {
    "identity": 0.5,
    "intent": 0.1 + 0.05j,
    "trajectory": 0.15,
    "timing": 0.5,
    "commitment": 0.8,
    "signature": 0.5,
}

BINS: tuple[tuple[str, float, float], ...] = (
    ("0.0-1.0", 0.0, 1.0),
    ("1.0-2.0", 1.0, 2.0),
    ("2.0-4.0", 2.0, 4.0),
    ("4.0+", 4.0, float("inf")),
)


def _attack_profile(drift: float, seed: int) -> dict[str, Any]:
    jitter = (seed % 5) * 0.01
    return {
        "identity": min(0.99, 0.5 + 0.20 * drift + jitter),
        "intent": (0.1 + 0.05j) + (0.18 * drift + (0.35 + jitter) * drift * 1j),
        "trajectory": min(0.99, 0.15 + 0.35 * drift + jitter),
        "timing": max(0.01, 0.5 - 0.15 * drift),
        "commitment": max(0.01, 0.8 - 0.45 * drift),
        "signature": min(0.99, 0.5 + 0.25 * drift + jitter),
        "t": 1.0 + drift * 5.0 + seed * 0.1,
        "tau": 0.5 + drift,
        "eta": max(0.5, 4.0 - drift),
        "q": 1.0 + drift * 1j,
    }


def _benign_profile(seed: int) -> dict[str, Any]:
    jitter = (seed % 5) * 0.0005
    return {
        "identity": 0.5 + jitter,
        "intent": (0.1 + jitter) + (0.05 + jitter) * 1j,
        "trajectory": 0.15 + jitter,
        "timing": 0.5,
        "commitment": 0.8 - jitter,
        "signature": 0.5,
        "t": 1.0 + seed * 0.05,
        "tau": 0.5,
        "eta": 4.0,
        "q": 1.0 + 0j,
    }


def _bin_for(distance: float) -> str:
    for label, low, high in BINS:
        if low <= distance < high:
            return label
    return BINS[-1][0]


def _row(
    pipe: FourteenLayerPipeline,
    profile: dict[str, Any],
    expected_block: bool,
    case_id: str,
) -> dict[str, Any]:
    risk, states = pipe.process(**profile)
    layer = {state.layer: state for state in states}
    d_h = float(layer[5].metrics["d_H"])
    h_d = float(layer[12].metrics["H_d"])
    decision = risk.decision
    blocked = decision != "ALLOW"
    return {
        "case_id": case_id,
        "expected_block": expected_block,
        "decision": decision,
        "blocked": blocked,
        "attack_success": bool(expected_block and not blocked),
        "false_positive": bool((not expected_block) and blocked),
        "d_H": d_h,
        "H_d": h_d,
        "distance_bin": _bin_for(d_h),
    }


def run_eval() -> dict[str, Any]:
    pipe = FourteenLayerPipeline(kappa_base=0.1)
    pipe.calibrate([SAFE_PROFILE])

    rows: list[dict[str, Any]] = []
    drift_levels = [
        0.0,
        0.05,
        0.10,
        0.15,
        0.20,
        0.30,
        0.50,
        0.70,
        0.90,
        1.20,
        1.50,
        2.00,
    ]
    for seed in range(5):
        rows.append(_row(pipe, _benign_profile(seed), False, f"benign-{seed}"))
        for drift in drift_levels:
            rows.append(
                _row(
                    pipe,
                    _attack_profile(drift, seed),
                    True,
                    f"attack-{seed}-{drift:.2f}",
                )
            )

    attacks = [row for row in rows if row["expected_block"]]
    benign = [row for row in rows if not row["expected_block"]]
    by_bin: dict[str, dict[str, Any]] = {}
    for label, _, _ in BINS:
        members = [row for row in attacks if row["distance_bin"] == label]
        success = sum(1 for row in members if row["attack_success"])
        by_bin[label] = {
            "attacks": len(members),
            "attack_successes": success,
            "attack_success_rate": (round(success / len(members), 4) if members else None),
            "avg_H_d": (round(sum(row["H_d"] for row in members) / len(members), 4) if members else None),
        }

    false_positives = sum(1 for row in benign if row["false_positive"])
    attack_successes = sum(1 for row in attacks if row["attack_success"])
    return {
        "schema_version": "pipeline14_adversarial_eval_v1",
        "system_under_test": "FourteenLayerPipeline",
        "summary": {
            "attacks": len(attacks),
            "benign": len(benign),
            "attack_successes": attack_successes,
            "attack_success_rate": round(attack_successes / len(attacks), 4),
            "false_positives": false_positives,
            "false_positive_rate": round(false_positives / len(benign), 4),
        },
        "attack_success_by_distance_bin": by_bin,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full 14-layer adversarial distance eval.")
    parser.add_argument(
        "--output",
        default="artifacts/benchmark/pipeline14_adversarial_eval.json",
        help="Path to write JSON report.",
    )
    args = parser.parse_args()

    report = run_eval()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(
        "ASR=" f"{report['summary']['attack_success_rate']:.1%} " f"FPR={report['summary']['false_positive_rate']:.1%}"
    )
    for label, row in report["attack_success_by_distance_bin"].items():
        asr = row["attack_success_rate"]
        asr_text = "n/a" if asr is None else f"{asr:.1%}"
        print(f"  d_H {label}: attacks={row['attacks']} ASR={asr_text} avg_H={row['avg_H_d']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
