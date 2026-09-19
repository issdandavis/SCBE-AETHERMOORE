#!/usr/bin/env python3
"""Multi-seed stress benchmark for SCBE fleet composition coordination.

The benchmark compares four policies on identical tasks and network events:

* sticky: keep the current eligible roster (no-recomposition baseline)
* round_robin: rotate through governance-eligible rosters
* distance: equal-weight, zero-tuned geometric/cost control
* composition_aware: task-adaptive coverage and transition accounting
* stability_guarded: composition-aware routing with bounded dwell hysteresis

Every policy pays for the governance checks and candidate evaluations it
actually performs. Results are simulation evidence, not deployment claims.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.coding_squad import SQUAD  # noqa: E402
from src.fleet.composition_coordinator import (  # noqa: E402
    CoordinationPolicy,
    FleetComposition,
    FleetMember,
    FleetTask,
    MissionMetrics,
    NetworkCondition,
    TONGUES,
    composition_geometry,
    simulate_mission,
)

SCHEMA_VERSION = "scbe_fleet_composition_stress_v1"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "benchmarks" / "fleet_composition" / "latest_report.json"
DEFAULT_SEEDS = (7, 11, 19, 23, 31, 43, 59, 71, 83)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dominant_tongue(vector: Sequence[float]) -> str:
    index = max(range(len(vector)), key=lambda idx: (vector[idx], -idx))
    return TONGUES[index]


def build_compositions() -> list[FleetComposition]:
    """Build clone, specialist, differentiated, and full-spectrum rosters."""

    role_members: dict[str, FleetMember] = {}
    for idx, role in enumerate(SQUAD):
        role_members[role.name] = FleetMember(
            member_id=role.name.lower(),
            tongue=_dominant_tongue(role.profile),
            capability_vector=tuple(role.profile),
            base_cost=0.75 + 0.05 * idx,
            reliability=0.94 + 0.01 * (idx % 3),
            latency_ticks=1 + idx % 3,
        )

    scout = FleetMember(
        member_id="scout2",
        tongue="DR",
        capability_vector=(0.1, 0.1, 0.1, 0.1, 0.2, 1.0),
        base_cost=0.95,
        reliability=0.95,
        latency_ticks=2,
    )
    architect = role_members["ARCHITECT"]
    clone_members = tuple(
        FleetMember(
            member_id=f"clone-{idx}",
            tongue=architect.tongue,
            capability_vector=architect.capability_vector,
            base_cost=0.42,
            reliability=0.97,
            latency_ticks=1,
        )
        for idx in range(5)
    )

    differentiated = tuple(role_members[role.name] for role in SQUAD)
    return [
        FleetComposition("clone_line", clone_members, "CA", fixed_overhead=0.05),
        FleetComposition(
            "command_pair",
            (role_members["ARCHITECT"], role_members["RECON"]),
            "RU",
            fixed_overhead=0.08,
        ),
        FleetComposition(
            "build_cell",
            (role_members["CODER"], role_members["CHECK"], role_members["OPTIMIZER"]),
            "CA",
            fixed_overhead=0.12,
        ),
        FleetComposition(
            "guard_cell",
            (role_members["CHECK"], role_members["OPTIMIZER"], scout),
            "UM",
            fixed_overhead=0.16,
        ),
        FleetComposition("differentiated_5", differentiated, "UM", fixed_overhead=0.24),
        FleetComposition("full_spectrum_6", differentiated + (scout,), "DR", fixed_overhead=0.30),
    ]


TASK_TEMPLATES: tuple[tuple[tuple[float, ...], str], ...] = (
    ((1, 0, 0, 0, 0, 0), "KO"),
    ((0, 1, 0, 0, 0, 0), "AV"),
    ((0, 0, 1, 0, 0, 0), "RU"),
    ((0, 0, 0, 1, 0, 0), "CA"),
    ((0, 0, 0, 0, 1, 0), "UM"),
    ((0, 0, 0, 0, 0, 1), "DR"),
    ((1, 1, 0, 1, 0, 0), "RU"),
    ((0, 0, 1, 1, 1, 0), "CA"),
    ((1, 0, 0, 1, 1, 1), "UM"),
    ((1, 1, 1, 1, 1, 1), "RU"),
)


def build_tasks(seed: int, count: int) -> list[FleetTask]:
    rng = random.Random(seed)
    tasks: list[FleetTask] = []
    for idx in range(count):
        base_vector, tier = TASK_TEMPLATES[idx % len(TASK_TEMPLATES)]
        vector = tuple(value + (rng.uniform(0.0, 0.12) if value else 0.0) for value in base_vector)
        work_units = round(rng.uniform(1.0, 4.0), 3)
        risk = round(rng.uniform(0.05, 0.95), 3)
        inertia = round(rng.uniform(0.05, 0.95), 3)
        deadline = 12 + math.ceil(work_units * 3.0) + math.ceil((1.0 - risk) * 6.0)
        tasks.append(
            FleetTask(
                task_id=f"seed-{seed}-task-{idx:04d}",
                requirement_vector=vector,
                required_governance_tier=tier,
                work_units=work_units,
                risk=risk,
                inertia=inertia,
                deadline_ticks=deadline,
                minimum_coverage=0.82,
            )
        )
    return tasks


def network_scenarios() -> tuple[NetworkCondition, ...]:
    """Normalized analogs of the repository's existing Mars/DTN cases."""

    return (
        NetworkCondition("nominal"),
        NetworkCondition("delay_reorder", base_delay_ticks=4, reorder_probability=0.65),
        NetworkCondition("duplicate_bundles", base_delay_ticks=2, duplicate_probability=0.40),
        NetworkCondition(
            "loss_with_custody",
            base_delay_ticks=3,
            drop_probability=0.40,
            reorder_probability=0.35,
            custody_retransmit=True,
        ),
        NetworkCondition(
            "blackout_with_custody",
            base_delay_ticks=4,
            drop_probability=0.60,
            reorder_probability=0.50,
            custody_retransmit=True,
            blackout_ticks=10,
        ),
        NetworkCondition(
            "permanent_loss_no_custody",
            base_delay_ticks=3,
            drop_probability=0.40,
            reorder_probability=0.35,
            custody_retransmit=False,
        ),
    )


def _metric_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 9),
        "sd": round(statistics.stdev(values), 9) if len(values) > 1 else 0.0,
        "min": round(min(values), 9),
        "max": round(max(values), 9),
    }


def _group_summary(rows: Sequence[MissionMetrics]) -> dict[str, Any]:
    numeric = {
        "completion_rate": [row.completion_rate for row in rows],
        "cost_per_completed": [row.cost_per_completed for row in rows if row.cost_per_completed is not None],
        "total_cost": [row.total_cost for row in rows],
        "transition_instability": [row.transition_instability for row in rows],
        "mean_transition_stability": [row.mean_transition_stability for row in rows],
        "transition_churn": [row.transition_churn for row in rows],
        "candidate_evaluations": [float(row.candidate_evaluations) for row in rows],
        "deadline_misses": [float(row.deadline_misses) for row in rows],
        "capability_misses": [float(row.capability_misses) for row in rows],
        "permanent_losses": [float(row.permanent_losses) for row in rows],
        "utilization_fairness": [row.utilization_fairness for row in rows],
    }
    return {name: _metric_summary(values) for name, values in numeric.items()}


def _effect(
    custom_rows: Sequence[MissionMetrics],
    baseline_rows: Sequence[MissionMetrics],
    *,
    metric: str,
    higher_is_better: bool,
) -> dict[str, Any]:
    custom_values = [getattr(row, metric) for row in custom_rows]
    baseline_values = [getattr(row, metric) for row in baseline_rows]
    custom_values = [float(value) for value in custom_values if value is not None]
    baseline_values = [float(value) for value in baseline_values if value is not None]
    if not custom_values or not baseline_values:
        return {
            "metric": metric,
            "higher_is_better": higher_is_better,
            "custom_mean": round(statistics.fmean(custom_values), 9) if custom_values else None,
            "baseline_mean": round(statistics.fmean(baseline_values), 9) if baseline_values else None,
            "raw_delta": None,
            "directed_delta": None,
            "pooled_sd": None,
            "two_pooled_sd_threshold": None,
            "status": "INSUFFICIENT_DATA",
        }
    custom_mean = statistics.fmean(custom_values)
    baseline_mean = statistics.fmean(baseline_values)
    custom_sd = statistics.stdev(custom_values) if len(custom_values) > 1 else 0.0
    baseline_sd = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0.0
    pooled_sd = math.sqrt((custom_sd**2 + baseline_sd**2) / 2.0)
    raw_delta = custom_mean - baseline_mean
    directed_delta = raw_delta if higher_is_better else -raw_delta
    threshold = 2.0 * pooled_sd
    if directed_delta <= 0.0:
        status = "NO_LIFT"
    elif directed_delta > threshold:
        status = "SUPPORTED"
    else:
        status = "UNDERPOWERED"
    return {
        "metric": metric,
        "higher_is_better": higher_is_better,
        "custom_mean": round(custom_mean, 9),
        "baseline_mean": round(baseline_mean, 9),
        "raw_delta": round(raw_delta, 9),
        "directed_delta": round(directed_delta, 9),
        "pooled_sd": round(pooled_sd, 9),
        "two_pooled_sd_threshold": round(threshold, 9),
        "status": status,
    }


def _comparison_bundle(
    custom_rows: Sequence[MissionMetrics],
    baseline_rows: Sequence[MissionMetrics],
) -> dict[str, Any]:
    return {
        "completion_rate": _effect(
            custom_rows,
            baseline_rows,
            metric="completion_rate",
            higher_is_better=True,
        ),
        "cost_per_completed": _effect(
            custom_rows,
            baseline_rows,
            metric="cost_per_completed",
            higher_is_better=False,
        ),
        "mean_transition_stability": _effect(
            custom_rows,
            baseline_rows,
            metric="mean_transition_stability",
            higher_is_better=True,
        ),
        "transition_churn": _effect(
            custom_rows,
            baseline_rows,
            metric="transition_churn",
            higher_is_better=False,
        ),
    }


def run_benchmark(seeds: Sequence[int], tasks_per_seed: int) -> dict[str, Any]:
    compositions = build_compositions()
    networks = network_scenarios()
    policies = tuple(CoordinationPolicy)
    rows: list[MissionMetrics] = []

    for seed in seeds:
        tasks = build_tasks(seed, tasks_per_seed)
        for network in networks:
            for policy in policies:
                rows.append(
                    simulate_mission(
                        compositions,
                        tasks,
                        policy=policy,
                        network=network,
                        seed=seed,
                    )
                )

    by_policy = {
        policy.value: _group_summary([row for row in rows if row.policy == policy.value]) for policy in policies
    }
    by_scenario = {
        network.name: {
            policy.value: _group_summary(
                [row for row in rows if row.network == network.name and row.policy == policy.value]
            )
            for policy in policies
        }
        for network in networks
    }

    custom_policy = CoordinationPolicy.STABILITY_GUARDED
    custom = [row for row in rows if row.policy == custom_policy.value]
    baseline_policies = (
        CoordinationPolicy.STICKY,
        CoordinationPolicy.DISTANCE,
    )
    comparisons: dict[str, dict[str, Any]] = {}
    for baseline_policy in baseline_policies:
        baseline = [row for row in rows if row.policy == baseline_policy.value]
        comparisons[baseline_policy.value] = _comparison_bundle(custom, baseline)

    comparisons_by_scenario = {
        network.name: {
            baseline_policy.value: _comparison_bundle(
                [row for row in rows if row.network == network.name and row.policy == custom_policy.value],
                [row for row in rows if row.network == network.name and row.policy == baseline_policy.value],
            )
            for baseline_policy in baseline_policies
        }
        for network in networks
    }

    completion_statuses = [
        comparisons[baseline]["completion_rate"]["status"]
        for baseline in (CoordinationPolicy.STICKY.value, CoordinationPolicy.DISTANCE.value)
    ]
    if all(status == "SUPPORTED" for status in completion_statuses):
        claim_status = "SUPPORTED"
    elif any(status == "NO_LIFT" for status in completion_statuses):
        claim_status = "NO_LIFT"
    else:
        claim_status = "UNDERPOWERED"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "scope": (
            "Deterministic simulated fleet coordination. This measures routing, cost accounting, "
            "coverage, transitions, and DTN-like disruption; it is not a production certification."
        ),
        "method": {
            "seeds": list(seeds),
            "tasks_per_seed": tasks_per_seed,
            "policies": [policy.value for policy in policies],
            "network_scenarios": [asdict(network) for network in networks],
            "controls": {
                "no_intervention": CoordinationPolicy.STICKY.value,
                "size_matched_zero_tuned": CoordinationPolicy.DISTANCE.value,
                "adaptive_ablation": CoordinationPolicy.COMPOSITION_AWARE.value,
            },
            "custom_policy": custom_policy.value,
            "claim_rule": (
                "A lift is SUPPORTED only when its directed mean delta exceeds 2x pooled sample SD. "
                "The custom completion-rate arm must beat both controls."
            ),
            "candidate_accounting": (
                "All governance checks and every candidate assessment are charged; no multi-candidate "
                "search is billed as one operation."
            ),
        },
        "composition_geometry": {
            composition.composition_id: {
                "members": [member.member_id for member in composition.members],
                "max_governance_tier": composition.max_governance_tier,
                "base_cost": round(composition.base_cost, 9),
                **{
                    key: value for key, value in asdict(composition_geometry(composition)).items() if key != "projector"
                },
            }
            for composition in compositions
        },
        "summary_by_policy": by_policy,
        "summary_by_scenario": by_scenario,
        "comparisons": comparisons,
        "comparisons_by_scenario": comparisons_by_scenario,
        "claim_status": claim_status,
        "runs": [asdict(row) for row in rows],
    }
    return payload


def write_report(payload: dict[str, Any], output: Path) -> tuple[Path, Path]:
    def render(value: float | int | None, *, signed: bool = False) -> str:
        if value is None:
            return "n/a"
        return f"{value:+.4f}" if signed else f"{value:.4f}"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    markdown = output.with_suffix(".md")
    lines = [
        "# Fleet Composition Stress Benchmark",
        "",
        f"- Claim status: **{payload['claim_status']}**",
        f"- Seeds: {len(payload['method']['seeds'])}",
        f"- Tasks per seed: {payload['method']['tasks_per_seed']}",
        f"- Simulated runs: {len(payload['runs'])}",
        "",
        "## Policy means",
        "",
        "| Policy | Completion | Cost/completed | Mean transition stability | Churn | Candidate evaluations |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for policy, summary in payload["summary_by_policy"].items():
        lines.append(
            f"| {policy} | {render(summary['completion_rate']['mean'])} | "
            f"{render(summary['cost_per_completed']['mean'])} | "
            f"{render(summary['mean_transition_stability']['mean'])} | "
            f"{render(summary['transition_churn']['mean'])} | "
            f"{render(summary['candidate_evaluations']['mean'])} |"
        )
    lines.extend(["", "## Claim gate", ""])
    for baseline, metrics in payload["comparisons"].items():
        completion = metrics["completion_rate"]
        lines.append(
            f"- vs {baseline} completion: **{completion['status']}** "
            f"(delta {render(completion['raw_delta'], signed=True)}, "
            f"2x pooled SD {render(completion['two_pooled_sd_threshold'])})"
        )
        cost = metrics["cost_per_completed"]
        stability = metrics["mean_transition_stability"]
        churn = metrics["transition_churn"]
        lines.append(
            f"  Cost/completed: **{cost['status']}** "
            f"(delta {render(cost['raw_delta'], signed=True)}); transition stability: **{stability['status']}** "
            f"(delta {render(stability['raw_delta'], signed=True)}); churn: **{churn['status']}** "
            f"(delta {render(churn['raw_delta'], signed=True)})."
        )
    lines.extend(
        [
            "",
            "## Scenario deltas for stability-guarded policy",
            "",
            "| Scenario | vs sticky completion | vs sticky cost | vs distance completion | vs distance cost |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for scenario, baselines in payload["comparisons_by_scenario"].items():
        sticky = baselines[CoordinationPolicy.STICKY.value]
        distance = baselines[CoordinationPolicy.DISTANCE.value]
        lines.append(
            "| {scenario} | {sticky_completion} | {sticky_cost} | "
            "{distance_completion} | {distance_cost} |".format(
                scenario=scenario,
                sticky_completion=render(sticky["completion_rate"]["raw_delta"], signed=True),
                sticky_cost=render(sticky["cost_per_completed"]["raw_delta"], signed=True),
                distance_completion=render(distance["completion_rate"]["raw_delta"], signed=True),
                distance_cost=render(distance["cost_per_completed"]["raw_delta"], signed=True),
            )
        )
    lines.extend(
        [
            "",
            "The JSON receipt contains every run, component metric, composition rank, and control comparison.",
            "These are normalized simulations; production performance still needs live-model and real-link validation.",
            "",
        ]
    )
    markdown.write_text("\n".join(lines), encoding="utf-8")
    return output, markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=int, default=180, help="Tasks per seed")
    parser.add_argument(
        "--seeds",
        default=",".join(str(seed) for seed in DEFAULT_SEEDS),
        help="Comma-separated integer seeds",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seeds = tuple(int(part.strip()) for part in args.seeds.split(",") if part.strip())
    if len(seeds) < 3:
        raise SystemExit("at least three seeds are required")
    if args.tasks <= 0:
        raise SystemExit("--tasks must be positive")
    payload = run_benchmark(seeds, args.tasks)
    json_path, md_path = write_report(payload, args.output)
    print(
        json.dumps(
            {
                "claim_status": payload["claim_status"],
                "json": str(json_path),
                "markdown": str(md_path),
                "runs": len(payload["runs"]),
                "summary_by_policy": payload["summary_by_policy"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
