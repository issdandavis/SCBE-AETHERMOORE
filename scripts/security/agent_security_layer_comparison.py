#!/usr/bin/env python3
"""Compare lexical and SCBE prompt signals on a frozen agent holdout.

This is an ablation harness, not a certification. The lexical-only and
SCBE-only decisions are extracted from one SCBEDetectionGate pass so every arm
sees identical input and session order. Standard cryptographic and capability
controls live at the tool boundary and are outside this prompt-detector test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.adversarial.attack_corpus import BASELINE_CLEAN  # noqa: E402
from tests.adversarial.scbe_harness import (  # noqa: E402
    AttackResult,
    SCBEDetectionGate,
)

DEFAULT_FIXTURE = (
    ROOT / "tests" / "security" / "fixtures" / "agent_security_holdout_v1.json"
)
DEFAULT_JSON_REPORT = (
    ROOT / "reports" / "security" / "agent_security_layer_comparison_20260919.json"
)
DEFAULT_MD_REPORT = (
    ROOT / "reports" / "security" / "agent_security_layer_comparison_20260919.md"
)
DEFAULT_SEEDS = (11, 29, 47)
ARM_NAMES = ("no_guard", "lexical_baseline", "scbe_custom", "combined")

_LEXICAL_MATCHES = re.compile(r"^adversarial_lexical\(matches=(\d+)\)$")
_STANDARD_STRONG_SIGNALS = {
    "strong_obfuscation_marker",
    "strong_public_benchmark_marker",
}
_GEOMETRIC_PREFIXES = (
    "spin_drift(",
    "tongue_imbalance(",
    "cost_exceeded(",
    "boundary_violation(",
    "dispersal_shift(",
)


@dataclass(frozen=True)
class HoldoutCase:
    case_id: str
    source: str
    policy_target: str
    category: str
    text: str

    @property
    def should_block(self) -> bool:
        return self.policy_target == "deny"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_holdout(
    path: Path = DEFAULT_FIXTURE,
) -> tuple[dict[str, Any], list[HoldoutCase]]:
    raw = path.read_bytes()
    document = json.loads(raw)
    if document.get("schema") != "scbe.agent-security-holdout.v1":
        raise ValueError("unsupported holdout schema")

    cases: list[HoldoutCase] = []
    seen: set[str] = set()
    for record in document.get("cases", []):
        case = HoldoutCase(
            case_id=str(record["id"]),
            source=str(record["source"]),
            policy_target=str(record["policy_target"]),
            category=str(record["category"]),
            text=str(record["text"]),
        )
        if case.case_id in seen:
            raise ValueError(f"duplicate case id: {case.case_id}")
        if case.policy_target not in {"allow", "deny"}:
            raise ValueError(f"invalid policy target for {case.case_id}")
        if not case.text.strip():
            raise ValueError(f"empty text for {case.case_id}")
        seen.add(case.case_id)
        cases.append(case)

    if not cases:
        raise ValueError("holdout contains no cases")
    provenance = dict(document.get("provenance", {}))
    provenance["fixture_sha256"] = _sha256_bytes(raw)
    return provenance, cases


def arm_decisions(result: AttackResult) -> dict[str, bool]:
    """Return block decisions for each ablation arm.

    The lexical baseline follows the gate's explicit lexical policy: two ordinary lexical
    matches, one multilingual override, or one strong marker.  SCBE custom uses
    a phase-lattice hit or two independent geometric signal families.  Session
    suspicion is excluded from the standalone arms because it mixes both signal
    families; the combined arm uses the shipped gate verdict, including state.
    """

    lexical_matches = 0
    strong_lexical = False
    geometric_families: set[str] = set()
    phase_lattice = False

    for signal in result.detection_signals:
        lexical = _LEXICAL_MATCHES.match(signal)
        if lexical:
            lexical_matches = max(lexical_matches, int(lexical.group(1)))
        if signal in _STANDARD_STRONG_SIGNALS:
            strong_lexical = True
        if signal.startswith("cross_lingual_override("):
            strong_lexical = True
        if signal.startswith("phase_lattice_hit("):
            phase_lattice = True
        for prefix in _GEOMETRIC_PREFIXES:
            if signal.startswith(prefix):
                geometric_families.add(prefix.removesuffix("("))

    return {
        "no_guard": False,
        "lexical_baseline": lexical_matches >= 2 or strong_lexical,
        "scbe_custom": phase_lattice or len(geometric_families) >= 2,
        "combined": bool(result.detected),
    }


def _metrics(labels: Sequence[bool], predictions: Sequence[bool]) -> dict[str, Any]:
    tp = sum(label and prediction for label, prediction in zip(labels, predictions))
    fn = sum(label and not prediction for label, prediction in zip(labels, predictions))
    fp = sum(not label and prediction for label, prediction in zip(labels, predictions))
    tn = sum(
        not label and not prediction for label, prediction in zip(labels, predictions)
    )
    attack_count = tp + fn
    benign_count = fp + tn
    tpr = tp / attack_count if attack_count else 0.0
    fpr = fp / benign_count if benign_count else 0.0
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "attack_detection_rate": tpr,
        "attack_success_rate": 1.0 - tpr,
        "false_positive_rate": fpr,
        "benign_allow_rate": 1.0 - fpr,
        "balanced_accuracy": (tpr + (1.0 - fpr)) / 2.0,
    }


def _sample_summary(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def _summarize_arms(per_seed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in ARM_NAMES:
        arm_runs = [run["arms"][arm] for run in per_seed]
        summary[arm] = {
            metric: _sample_summary([float(run[metric]) for run in arm_runs])
            for metric in (
                "attack_detection_rate",
                "attack_success_rate",
                "false_positive_rate",
                "benign_allow_rate",
                "balanced_accuracy",
            )
        }
    return summary


def run_comparison(
    cases: Sequence[HoldoutCase],
    *,
    seeds: Iterable[int] = DEFAULT_SEEDS,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seed_values = tuple(int(seed) for seed in seeds)
    if not seed_values:
        raise ValueError("at least one order seed is required")

    baseline_texts = [entry["prompt"] for entry in BASELINE_CLEAN]
    baseline_hashes = {_sha256_bytes(text.encode("utf-8")) for text in baseline_texts}
    holdout_hashes = {_sha256_bytes(case.text.encode("utf-8")) for case in cases}
    exact_overlap = sorted(baseline_hashes & holdout_hashes)

    per_seed: list[dict[str, Any]] = []
    all_latencies_us: list[float] = []
    evaluations: list[dict[str, Any]] = []

    for seed in seed_values:
        ordered = list(cases)
        # Deterministic ordering is required for repeatable measurement, not security.
        random.Random(seed).shuffle(ordered)  # nosec B311
        gate = SCBEDetectionGate()
        gate.calibrate(baseline_texts)
        labels: list[bool] = []
        predictions = {arm: [] for arm in ARM_NAMES}

        for case in ordered:
            started = time.perf_counter_ns()
            result = gate.process(
                case.text,
                attack_id=case.case_id,
                attack_class=case.category,
            )
            latency_us = (time.perf_counter_ns() - started) / 1_000.0
            all_latencies_us.append(latency_us)
            decisions = arm_decisions(result)
            labels.append(case.should_block)
            for arm in ARM_NAMES:
                predictions[arm].append(decisions[arm])
            evaluations.append(
                {
                    "seed": seed,
                    "case_id": case.case_id,
                    "policy_target": case.policy_target,
                    "decisions": decisions,
                    "signal_families": [
                        signal.split("(", 1)[0] for signal in result.detection_signals
                    ],
                }
            )

        per_seed.append(
            {
                "seed": seed,
                "arms": {arm: _metrics(labels, predictions[arm]) for arm in ARM_NAMES},
            }
        )

    arm_summary = _summarize_arms(per_seed)
    lexical_tpr = arm_summary["lexical_baseline"]["attack_detection_rate"]
    combined_tpr = arm_summary["combined"]["attack_detection_rate"]
    pooled_sd = math.sqrt(
        (lexical_tpr["sample_sd"] ** 2 + combined_tpr["sample_sd"] ** 2) / 2.0
    )
    tpr_delta = combined_tpr["mean"] - lexical_tpr["mean"]

    incremental_attack_ids = sorted(
        {
            row["case_id"]
            for row in evaluations
            if row["policy_target"] == "deny"
            and row["decisions"]["combined"]
            and not row["decisions"]["lexical_baseline"]
        }
    )
    added_false_positive_ids = sorted(
        {
            row["case_id"]
            for row in evaluations
            if row["policy_target"] == "allow"
            and row["decisions"]["combined"]
            and not row["decisions"]["lexical_baseline"]
        }
    )
    false_positive_ids = {
        arm: sorted(
            {
                row["case_id"]
                for row in evaluations
                if row["policy_target"] == "allow" and row["decisions"][arm]
            }
        )
        for arm in ARM_NAMES
    }

    return {
        "schema": "scbe.agent-security-layer-comparison.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "fixed local holdout; no external systems contacted",
        "fixture": provenance or {},
        "case_counts": {
            "total": len(cases),
            "deny": sum(case.should_block for case in cases),
            "allow": sum(not case.should_block for case in cases),
            "exact_calibration_overlap": len(exact_overlap),
        },
        "method": {
            "order_seeds": list(seed_values),
            "lexical_baseline_rule": (
                "lexical_matches>=2 OR cross-lingual override OR strong marker"
            ),
            "standard_control_scope": (
                "Cryptographic identity, capabilities, replay protection, and sandboxing "
                "are tested separately at the tool boundary."
            ),
            "scbe_custom_rule": "phase-lattice hit OR at least two geometric signal families",
            "combined_rule": "shipped SCBEDetectionGate verdict, including bounded session state",
            "latency_note": (
                "Latency measures the full combined detector pass. Standalone arms are diagnostic "
                "ablations extracted from that pass, not separate runtime implementations."
            ),
        },
        "per_seed": per_seed,
        "arm_summary": arm_summary,
        "full_gate_latency_us": {
            "median": statistics.median(all_latencies_us),
            "p95": _percentile(all_latencies_us, 0.95),
            "max": max(all_latencies_us),
            "samples": len(all_latencies_us),
        },
        "incremental": {
            "combined_over_lexical_attack_case_ids": incremental_attack_ids,
            "combined_over_lexical_added_false_positive_case_ids": added_false_positive_ids,
            "false_positive_case_ids_by_arm": false_positive_ids,
        },
        "measurement_claim": {
            "combined_minus_lexical_tpr_mean": tpr_delta,
            "pooled_order_sd": pooled_sd,
            "two_pooled_sd": 2.0 * pooled_sd,
            "clears_two_pooled_sd": tpr_delta > 2.0 * pooled_sd,
            "research_status": "UNDERPOWERED",
            "reason": (
                "The three runs permute one fixed holdout and are not independent samples; there "
                "is no size-matched implementation control. Treat this as engineering evidence."
            ),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Security Layer Comparison",
        "",
        f"Cases: {report['case_counts']['total']} "
        f"({report['case_counts']['deny']} deny / {report['case_counts']['allow']} allow).",
        "",
        "| Arm | Attack detection | False positives | Benign allowed | Balanced accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm in ARM_NAMES:
        metrics = report["arm_summary"][arm]
        lines.append(
            f"| {arm} | {metrics['attack_detection_rate']['mean']:.1%} | "
            f"{metrics['false_positive_rate']['mean']:.1%} | "
            f"{metrics['benign_allow_rate']['mean']:.1%} | "
            f"{metrics['balanced_accuracy']['mean']:.1%} |"
        )
    latency = report["full_gate_latency_us"]
    claim = report["measurement_claim"]
    lines.extend(
        [
            "",
            "## Runtime",
            "",
            f"Full detector median: {latency['median']:.1f} µs; p95: {latency['p95']:.1f} µs "
            f"across {latency['samples']} evaluations.",
            "",
            "## Interpretation",
            "",
            f"Research claim status: **{claim['research_status']}**. {claim['reason']}",
            "",
            "The JSON report contains per-seed confusion matrices and case IDs for incremental "
            "catches and false positives. It intentionally excludes prompt text.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_REPORT)
    parser.add_argument(
        "--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS)
    )
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    seeds = tuple(
        int(value.strip()) for value in args.seeds.split(",") if value.strip()
    )
    provenance, cases = load_holdout(args.fixture)
    report = run_comparison(cases, seeds=seeds, provenance=provenance)
    markdown = render_markdown(report)

    if not args.no_write:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        args.markdown_out.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
