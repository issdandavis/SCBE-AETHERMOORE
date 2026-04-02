#!/usr/bin/env python3
"""
Replay temporal/Omega telemetry against alternate alpha policies.

This script is the offline fitting lane for the live temporal gate. It keeps the
runtime doctrine unchanged:

    - production alpha stays fixed at 2.0
    - H_eff is still a shaping term
    - final decisions still come from the coupled Omega lock

Given exported telemetry packets with schema_version
`temporal_omega_telemetry_v1`, the harness recomputes the harmonic sublock under
counterfactual alpha policies and reports:

    - decision flips relative to the live gate
    - mean omega deltas (stricter vs looser than live)
    - class-preserving margin changes
    - regime summaries across early / mid / late x buckets

If no input files are provided, the script falls back to deterministic demo
events from the Aethermoor spiral engine so the replay lane is usable
immediately.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.spiralverse.aethermoor_spiral_engine import run_demo
from src.spiralverse.temporal_intent import (
    R_HARMONIC,
    TEMPORAL_OMEGA_TELEMETRY_SCHEMA_VERSION,
    TEMPORAL_CURVATURE_ALPHA,
    TemporalSecurityGate,
    validate_telemetry_event,
)


PHI = (1.0 + math.sqrt(5.0)) / 2.0
EXPONENTS: Dict[str, float] = {
    "1.5": 1.5,
    "phi": PHI,
    "sqrt2": math.sqrt(2.0),
    "2": 2.0,
    "e": math.e,
}


@dataclass(frozen=True)
class ReplayPoint:
    event_index: int
    event_id: str
    layer: str
    x_factor: float
    distance: float
    actual_decision: str
    actual_omega: float
    actual_harm_score: float
    policy_name: str
    alpha_value: float
    counterfactual_decision: str
    counterfactual_omega: float
    counterfactual_harm_score: float
    omega_delta: float
    margin_delta: float
    decision_flipped: bool
    x_regime: str


@dataclass(frozen=True)
class PolicySummary:
    policy_name: str
    event_count: int
    mean_alpha: float
    decision_match_rate: float
    decision_flip_rate: float
    mean_omega_delta: float
    mean_margin_delta: float
    class_preserving_mean_margin_delta: float
    class_preserving_margin_gain_rate: float
    decision_counts: Dict[str, int]
    flip_breakdown: Dict[str, int]
    x_regimes: Dict[str, Dict[str, float]]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def temporal_harmonic_wall(d: float, x_factor: float, alpha: float, r_base: float = R_HARMONIC) -> float:
    return r_base ** (d**alpha * x_factor)


def temporal_harm_score(d: float, x_factor: float, alpha: float, r_base: float = R_HARMONIC) -> float:
    h_temporal = temporal_harmonic_wall(d=d, x_factor=x_factor, alpha=alpha, r_base=r_base)
    return _clamp01(1.0 / (1.0 + math.log(max(1.0, h_temporal))))


def temporal_decision(
    omega: float,
    allow_threshold: float = TemporalSecurityGate.ALLOW_THRESHOLD,
    quarantine_threshold: float = TemporalSecurityGate.QUARANTINE_THRESHOLD,
) -> str:
    if omega > allow_threshold:
        return "ALLOW"
    if omega > quarantine_threshold:
        return "QUARANTINE"
    return "DENY"


def class_margin(
    omega: float,
    decision: str,
    allow_threshold: float = TemporalSecurityGate.ALLOW_THRESHOLD,
    quarantine_threshold: float = TemporalSecurityGate.QUARANTINE_THRESHOLD,
) -> float:
    if decision == "ALLOW":
        return omega - allow_threshold
    if decision == "QUARANTINE":
        return min(omega - quarantine_threshold, allow_threshold - omega)
    if decision == "DENY":
        return quarantine_threshold - omega
    return 0.0


def x_regime(x_factor: float) -> str:
    if x_factor < 1.0:
        return "early"
    if x_factor < 2.0:
        return "mid"
    return "late"


def select_policy_alpha(policy_name: str, *, x_factor: float, layer: str) -> float:
    if policy_name.startswith("fixed_"):
        key = policy_name.split("_", 1)[1]
        if key not in EXPONENTS:
            raise KeyError(f"Unknown fixed alpha policy: {policy_name}")
        return EXPONENTS[key]

    if policy_name == "schedule_guardrail":
        if x_factor < 1.0:
            return EXPONENTS["sqrt2"]
        if x_factor < 2.0:
            return EXPONENTS["2"]
        return EXPONENTS["e"]

    if policy_name == "schedule_phi_bridge":
        if x_factor < 1.0:
            return EXPONENTS["sqrt2"]
        if x_factor < 2.0:
            return EXPONENTS["phi"]
        return EXPONENTS["e"]

    if policy_name == "schedule_layer_guard":
        if layer in {"L0", "L1"}:
            return EXPONENTS["sqrt2"]
        if layer == "L3" and x_factor >= 2.0:
            return EXPONENTS["e"]
        return EXPONENTS["2"]

    raise KeyError(f"Unknown policy: {policy_name}")


def policy_catalog() -> Dict[str, Callable[[float, str], float]]:
    policies: Dict[str, Callable[[float, str], float]] = {}
    for exponent_name in EXPONENTS:
        policies[f"fixed_{exponent_name}"] = (
            lambda x_factor, layer, name=f"fixed_{exponent_name}": select_policy_alpha(
                name,
                x_factor=x_factor,
                layer=layer,
            )
        )
    policies["schedule_guardrail"] = (
        lambda x_factor, layer: select_policy_alpha("schedule_guardrail", x_factor=x_factor, layer=layer)
    )
    policies["schedule_phi_bridge"] = (
        lambda x_factor, layer: select_policy_alpha("schedule_phi_bridge", x_factor=x_factor, layer=layer)
    )
    policies["schedule_layer_guard"] = (
        lambda x_factor, layer: select_policy_alpha("schedule_layer_guard", x_factor=x_factor, layer=layer)
    )
    return policies


def extract_telemetry_events(payload: object) -> List[Dict[str, object]]:
    if isinstance(payload, dict):
        if payload.get("schema_version") == TEMPORAL_OMEGA_TELEMETRY_SCHEMA_VERSION:
            return [validate_telemetry_event(payload)]
        if "events" in payload:
            return extract_telemetry_events(payload["events"])
        if "history" in payload and isinstance(payload["history"], list):
            collected: List[Dict[str, object]] = []
            for entry in payload["history"]:
                if isinstance(entry, dict) and "telemetry" in entry:
                    collected.extend(extract_telemetry_events(entry["telemetry"]))
            return collected
        return []

    if isinstance(payload, list):
        collected: List[Dict[str, object]] = []
        for item in payload:
            collected.extend(extract_telemetry_events(item))
        return collected

    return []


def read_telemetry_file(path: Path) -> List[Dict[str, object]]:
    if path.suffix.lower() == ".jsonl":
        events: List[Dict[str, object]] = []
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                events.extend(extract_telemetry_events(json.loads(line)))
        return events
    return extract_telemetry_events(json.loads(path.read_text(encoding="utf-8")))


def generate_demo_events(seed: int = 7, turns: int = 12) -> List[Dict[str, object]]:
    payload = run_demo(seed=seed, turns=turns)
    return extract_telemetry_events(payload)


def load_telemetry_events(paths: Sequence[Path], *, demo_seed: int, demo_turns: int) -> List[Dict[str, object]]:
    if not paths:
        return generate_demo_events(seed=demo_seed, turns=demo_turns)

    events: List[Dict[str, object]] = []
    for path in paths:
        events.extend(read_telemetry_file(path))
    return events


def replay_event_against_policy(event: Dict[str, object], policy_name: str, event_index: int) -> ReplayPoint:
    state = event["state"]
    temporal = event["temporal"]
    omega = event["omega"]
    sublocks = omega["sublocks"]
    outcome = event["outcome"]

    actual_decision = str(outcome["decision"])
    if actual_decision == "EXILE":
        alpha_value = TEMPORAL_CURVATURE_ALPHA
        counterfactual_harm = 0.0
        counterfactual_omega = 0.0
        counterfactual_decision = "EXILE"
    else:
        alpha_value = float(select_policy_alpha(policy_name, x_factor=float(state["x"]), layer=str(event["layer"])))
        counterfactual_harm = temporal_harm_score(
            d=float(state["d"]),
            x_factor=float(state["x"]),
            alpha=alpha_value,
        )
        counterfactual_omega = (
            float(sublocks["pqc"])
            * counterfactual_harm
            * float(sublocks["drift"])
            * float(sublocks["triadic"])
            * float(sublocks["spectral"])
        )
        counterfactual_decision = temporal_decision(counterfactual_omega)

    actual_omega = float(omega["omega_score"])
    actual_margin = class_margin(actual_omega, actual_decision)
    counterfactual_margin = class_margin(counterfactual_omega, actual_decision)
    event_id = event.get("event_id") or f"telemetry-{event_index:04d}"

    return ReplayPoint(
        event_index=event_index,
        event_id=str(event_id),
        layer=str(event["layer"]),
        x_factor=float(state["x"]),
        distance=float(state["d"]),
        actual_decision=actual_decision,
        actual_omega=actual_omega,
        actual_harm_score=float(temporal["harm_score"]),
        policy_name=policy_name,
        alpha_value=float(alpha_value),
        counterfactual_decision=counterfactual_decision,
        counterfactual_omega=float(counterfactual_omega),
        counterfactual_harm_score=float(counterfactual_harm),
        omega_delta=float(counterfactual_omega - actual_omega),
        margin_delta=float(counterfactual_margin - actual_margin),
        decision_flipped=counterfactual_decision != actual_decision,
        x_regime=x_regime(float(state["x"])),
    )


def summarize_policy(points: Sequence[ReplayPoint]) -> PolicySummary:
    if not points:
        raise ValueError("Cannot summarize an empty policy replay")

    decision_counts = Counter(point.counterfactual_decision for point in points)
    flip_breakdown = Counter(
        f"{point.actual_decision}->{point.counterfactual_decision}" for point in points if point.decision_flipped
    )
    class_preserving = [point for point in points if not point.decision_flipped]

    regime_stats: Dict[str, Dict[str, float]] = {}
    buckets: Dict[str, List[ReplayPoint]] = defaultdict(list)
    for point in points:
        buckets[point.x_regime].append(point)
    for regime_name, regime_points in sorted(buckets.items()):
        flips = sum(1 for point in regime_points if point.decision_flipped)
        regime_stats[regime_name] = {
            "count": float(len(regime_points)),
            "flip_rate": flips / len(regime_points),
            "mean_omega_delta": sum(point.omega_delta for point in regime_points) / len(regime_points),
            "mean_margin_delta": sum(point.margin_delta for point in regime_points) / len(regime_points),
        }

    return PolicySummary(
        policy_name=points[0].policy_name,
        event_count=len(points),
        mean_alpha=sum(point.alpha_value for point in points) / len(points),
        decision_match_rate=1.0 - (sum(1 for point in points if point.decision_flipped) / len(points)),
        decision_flip_rate=sum(1 for point in points if point.decision_flipped) / len(points),
        mean_omega_delta=sum(point.omega_delta for point in points) / len(points),
        mean_margin_delta=sum(point.margin_delta for point in points) / len(points),
        class_preserving_mean_margin_delta=(
            sum(point.margin_delta for point in class_preserving) / len(class_preserving) if class_preserving else 0.0
        ),
        class_preserving_margin_gain_rate=(
            sum(1 for point in class_preserving if point.margin_delta > 0.0) / len(class_preserving)
            if class_preserving
            else 0.0
        ),
        decision_counts=dict(decision_counts),
        flip_breakdown=dict(flip_breakdown),
        x_regimes=regime_stats,
    )


def collect_policy_summaries(
    events: Sequence[Dict[str, object]],
    policies: Sequence[str] | None = None,
) -> tuple[List[ReplayPoint], List[PolicySummary]]:
    selected = list(policies or policy_catalog().keys())
    all_points: List[ReplayPoint] = []
    summaries: List[PolicySummary] = []
    for policy_name in selected:
        points = [replay_event_against_policy(event, policy_name, idx) for idx, event in enumerate(events, start=1)]
        all_points.extend(points)
        summaries.append(summarize_policy(points))
    summaries.sort(key=lambda item: (item.decision_flip_rate, -item.class_preserving_mean_margin_delta, abs(item.mean_omega_delta)))
    return all_points, summaries


def top_flip_examples(points: Sequence[ReplayPoint], limit: int = 5) -> List[Dict[str, object]]:
    flipped = [point for point in points if point.decision_flipped]
    flipped.sort(key=lambda point: (abs(point.margin_delta), abs(point.omega_delta)), reverse=True)
    return [
        {
            "event_id": point.event_id,
            "policy_name": point.policy_name,
            "layer": point.layer,
            "x_factor": point.x_factor,
            "distance": point.distance,
            "actual_decision": point.actual_decision,
            "counterfactual_decision": point.counterfactual_decision,
            "actual_omega": point.actual_omega,
            "counterfactual_omega": point.counterfactual_omega,
            "omega_delta": point.omega_delta,
            "margin_delta": point.margin_delta,
        }
        for point in flipped[:limit]
    ]


def write_points_jsonl(path: Path, points: Iterable[ReplayPoint]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for point in points:
            handle.write(json.dumps(asdict(point)) + "\n")


def plot_policy_summary(output_path: Path, summaries: Sequence[PolicySummary]) -> None:
    names = [summary.policy_name for summary in summaries]
    flip_rates = [summary.decision_flip_rate for summary in summaries]
    margin_deltas = [summary.class_preserving_mean_margin_delta for summary in summaries]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    axes[0].bar(names, flip_rates, color="#8fb3ff")
    axes[0].set_title("Decision flip rate vs live alpha=2")
    axes[0].set_ylabel("flip rate")
    axes[0].tick_params(axis="x", rotation=35)
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(names, margin_deltas, color="#7fd18b")
    axes[1].set_title("Class-preserving margin delta")
    axes[1].set_ylabel("mean margin delta")
    axes[1].tick_params(axis="x", rotation=35)
    axes[1].axhline(0.0, color="black", linewidth=1.0)
    axes[1].grid(axis="y", alpha=0.25)

    fig.suptitle("Temporal Omega replay policy comparison")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def format_report(
    source_count: int,
    summaries: Sequence[PolicySummary],
    examples: Sequence[Dict[str, object]],
) -> str:
    lines = [
        "Temporal Omega Replay",
        "=====================",
        f"events replayed: {source_count}",
        f"production alpha baseline: {TEMPORAL_CURVATURE_ALPHA:.1f}",
        "",
        (
            f"{'policy':<24} {'flip_rate':>10} {'match_rate':>11} "
            f"{'mean_domega':>12} {'mean_margin':>12} {'preserve_gain':>14}"
        ),
    ]
    for summary in summaries:
        lines.append(
            f"{summary.policy_name:<24} "
            f"{summary.decision_flip_rate:>10.4f} "
            f"{summary.decision_match_rate:>11.4f} "
            f"{summary.mean_omega_delta:>12.4f} "
            f"{summary.class_preserving_mean_margin_delta:>12.4f} "
            f"{summary.class_preserving_margin_gain_rate:>14.4f}"
        )

    best_preserving = max(summaries, key=lambda item: item.class_preserving_mean_margin_delta)
    lowest_flip = min(summaries, key=lambda item: item.decision_flip_rate)
    lines.extend(
        [
            "",
            f"lowest flip rate: {lowest_flip.policy_name}",
            f"best class-preserving margin gain: {best_preserving.policy_name}",
        ]
    )
    if examples:
        lines.append("")
        lines.append("largest flip examples:")
        for example in examples:
            lines.append(
                "  - "
                f"{example['policy_name']} flipped {example['event_id']} "
                f"{example['actual_decision']} -> {example['counterfactual_decision']} "
                f"(x={example['x_factor']:.3f}, d={example['distance']:.3f}, domega={example['omega_delta']:.4f})"
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="*", type=Path, help="Telemetry JSON or JSONL files to replay")
    parser.add_argument("--demo-seed", type=int, default=7, help="Seed used when no input files are provided")
    parser.add_argument("--demo-turns", type=int, default=12, help="Turn count used when no input files are provided")
    parser.add_argument(
        "--policy",
        action="append",
        dest="policies",
        help="Policy name to evaluate (repeatable). Defaults to all fixed and schedule policies.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "artifacts" / "research" / "temporal_omega_replay",
        help="Directory for JSON, JSONL, and plot outputs.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary instead of human report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    events = load_telemetry_events(args.input, demo_seed=args.demo_seed, demo_turns=args.demo_turns)
    if not events:
        raise SystemExit("No temporal telemetry events found in the supplied inputs")

    available = policy_catalog()
    selected_policies = args.policies or list(available.keys())
    for policy_name in selected_policies:
        if policy_name not in available:
            raise SystemExit(f"Unknown policy: {policy_name}")

    points, summaries = collect_policy_summaries(events, selected_policies)
    examples = top_flip_examples(points)

    payload = {
        "schema_version": "temporal_omega_replay_v1",
        "source_event_count": len(events),
        "production_alpha": TEMPORAL_CURVATURE_ALPHA,
        "policies": [asdict(summary) for summary in summaries],
        "top_flip_examples": examples,
        "output_dir": str(args.output_dir),
    }

    (args.output_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_points_jsonl(args.output_dir / "counterfactual_points.jsonl", points)
    plot_policy_summary(args.output_dir / "policy_replay_summary.png", summaries)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(len(events), summaries, examples))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
