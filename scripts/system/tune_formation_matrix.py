#!/usr/bin/env python3
"""Sweep SCBE formation-matrix ratios for agent-team parallelism.

This is a deterministic design tuner, not a training run. It scores candidate
formations by balancing variable coverage, coherence, validation pressure,
communication chatter, cost, and external-variable handling.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "agent_context_vault" / "formation_matrix_tuning.json"
PHI = (1 + 5**0.5) / 2
TARGET_BASE_RATIO = 1.5 * PHI
SCHEMA_VERSION = "scbe_formation_matrix_tuning_v1"


@dataclass(frozen=True)
class Candidate:
    formation: str
    agents: int
    base_scale: float
    expansion: float
    interaction: float
    gate_pressure: float
    externality: float

    @property
    def base_ratio(self) -> float:
        return self.base_scale * PHI


FORMATION_SIZES = {
    "pair": 2,
    "triad": 3,
    "quad": 4,
    "hex": 6,
    "oct": 8,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _round(value: float) -> float:
    return round(value, 6)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step = (stop - start) / (count - 1)
    return [start + idx * step for idx in range(count)]


def _topology_bonus(candidate: Candidate) -> float:
    if candidate.agents == 3:
        return 1.0
    if candidate.agents == 4:
        return 0.88
    if candidate.agents == 2:
        return 0.74
    if candidate.agents == 6:
        return 0.72
    return 0.58


def _score_candidate(candidate: Candidate) -> dict[str, Any]:
    agents = candidate.agents
    base = candidate.base_ratio
    edges = agents * (agents - 1) / 2
    density = edges / max(1.0, 15.0)
    base_alignment = math.exp(-((base - TARGET_BASE_RATIO) ** 2) / (PHI**2))
    topology = _topology_bonus(candidate)

    exploration_mass = agents * candidate.expansion * (0.72 + candidate.externality)
    interaction_mass = candidate.interaction * (1.0 + candidate.externality * 0.35)
    coverage = _clamp01(1.0 - math.exp(-(exploration_mass * interaction_mass) / (base * 1.85)))
    coverage = _clamp01(coverage + 0.10 * candidate.externality)

    ideal_interaction = 1.0 / math.sqrt(max(1.0, agents - 1))
    interaction_alignment = math.exp(-((candidate.interaction - ideal_interaction) ** 2) / 0.18)
    coherence = _clamp01(0.45 * base_alignment + 0.35 * interaction_alignment + 0.20 * topology)

    validation = _clamp01(1.0 - math.exp(-(candidate.gate_pressure * math.log1p(agents)) / 2.8))
    chatter = _clamp01((density * candidate.interaction**2 * candidate.expansion) / (base / TARGET_BASE_RATIO))
    cost = _clamp01((agents * (0.11 + 0.18 * candidate.expansion + 0.06 * candidate.gate_pressure)) / 8.0)
    risk = _clamp01(max(0.0, chatter - validation * 0.72) + max(0.0, candidate.externality - 0.26) * 0.35)
    ext_mapping = _clamp01(candidate.externality * (0.55 + coverage) * validation)

    score = (
        0.34 * coverage
        + 0.24 * coherence
        + 0.18 * validation
        + 0.14 * ext_mapping
        - 0.16 * chatter
        - 0.08 * cost
        - 0.18 * risk
    )
    return {
        "formation": candidate.formation,
        "agents": agents,
        "base_scale": _round(candidate.base_scale),
        "base_ratio": _round(base),
        "target_base_ratio": _round(TARGET_BASE_RATIO),
        "expansion": _round(candidate.expansion),
        "interaction": _round(candidate.interaction),
        "gate_pressure": _round(candidate.gate_pressure),
        "externality": _round(candidate.externality),
        "score": _round(score),
        "metrics": {
            "coverage": _round(coverage),
            "coherence": _round(coherence),
            "validation": _round(validation),
            "chatter": _round(chatter),
            "cost": _round(cost),
            "risk": _round(risk),
            "external_variable_mapping": _round(ext_mapping),
            "topology_bonus": _round(topology),
        },
    }


def _agent_roles(agents: int) -> list[str]:
    base = ["scout", "coder", "verifier", "firefighter", "context_roller", "release_gate", "researcher", "packager"]
    return base[:agents]


def build_graph_matrix(agents: int, interaction: float, gate_pressure: float) -> list[list[float]]:
    roles = _agent_roles(agents)
    matrix: list[list[float]] = []
    for row_idx, row_role in enumerate(roles):
        row: list[float] = []
        for col_idx, col_role in enumerate(roles):
            if row_idx == col_idx:
                row.append(0.0)
                continue
            distance = abs(row_idx - col_idx)
            local_weight = interaction / (1.0 + distance / PHI)
            if {row_role, col_role} & {"verifier", "release_gate"}:
                local_weight *= 1.0 + gate_pressure * 0.18
            if {row_role, col_role} == {"firefighter", "context_roller"}:
                local_weight *= 0.85
            row.append(_round(min(1.0, local_weight)))
        matrix.append(row)
    return matrix


def run_sweep(
    *,
    grid: int = 5,
    top_n: int = 10,
    output_path: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    base_scales = _linspace(1.18, 1.82, grid)
    expansions = _linspace(0.72, 1.44, grid)
    interactions = _linspace(0.34, 1.02, grid)
    gates = _linspace(0.58, 1.34, grid)
    externalities = _linspace(0.0, 0.36, grid)
    scored: list[dict[str, Any]] = []
    for formation, agents in FORMATION_SIZES.items():
        for base_scale in base_scales:
            for expansion in expansions:
                for interaction in interactions:
                    for gate_pressure in gates:
                        for externality in externalities:
                            scored.append(
                                _score_candidate(
                                    Candidate(
                                        formation=formation,
                                        agents=agents,
                                        base_scale=base_scale,
                                        expansion=expansion,
                                        interaction=interaction,
                                        gate_pressure=gate_pressure,
                                        externality=externality,
                                    )
                                )
                            )
    scored.sort(key=lambda row: (-float(row["score"]), float(row["metrics"]["chatter"]), int(row["agents"])))
    best = scored[0]
    best["roles"] = _agent_roles(int(best["agents"]))
    best["graph_matrix"] = build_graph_matrix(
        int(best["agents"]),
        float(best["interaction"]),
        float(best["gate_pressure"]),
    )
    by_formation: dict[str, Any] = {}
    for formation in FORMATION_SIZES:
        winner = next(row for row in scored if row["formation"] == formation)
        by_formation[formation] = {
            "score": winner["score"],
            "agents": winner["agents"],
            "base_ratio": winner["base_ratio"],
            "expansion": winner["expansion"],
            "interaction": winner["interaction"],
            "gate_pressure": winner["gate_pressure"],
            "externality": winner["externality"],
            "metrics": winner["metrics"],
        }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "phi": _round(PHI),
        "target_base_ratio": _round(TARGET_BASE_RATIO),
        "grid_points_per_dimension": grid,
        "candidate_count": len(scored),
        "objective": "maximize variable coverage and external mapping while penalizing chatter, cost, and risk",
        "best": best,
        "best_by_formation": by_formation,
        "top": scored[:top_n],
        "interpretation": {
            "sweet_spot": "triads or quads usually win because they add enough interaction surface without full mesh chatter",
            "use_pair_when": "the task is narrow, private, or one model is only verifying another",
            "use_triad_when": "the task needs builder, verifier, and context roller lanes",
            "use_hex_when": "the task needs broad research/release coverage and can tolerate higher coordination cost",
        },
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=int, default=5, help="points per swept dimension")
    parser.add_argument("--top", type=int, default=10, help="number of top candidates to include")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_sweep(
        grid=max(2, args.grid),
        top_n=max(1, args.top),
        output_path=None if args.no_write else args.output,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
