#!/usr/bin/env python3
"""Deterministic simulator for reversible route buffers and information leakage.

This is not a lab-physics simulator. It is a small test harness for the core
question: when does an internal route leave distinguishable metadata outside
the box, and when can a reversible buffer preserve interference-like behavior?
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LeakageScenario:
    name: str
    path_balance: float = 0.5
    phase_radians: float = 0.0
    buffer_coupling: float = 0.0
    erase_strength: float = 0.0
    environment_leak: float = 0.0
    symmetric_noise: float = 0.0


@dataclass(frozen=True)
class LeakageResult:
    name: str
    distinguishability: float
    coherence: float
    constructive_probability: float
    destructive_probability: float
    interference_visibility: float
    route_metadata_leak: float
    decision: str


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def simulate(scenario: LeakageScenario) -> LeakageResult:
    """Compute leakage and interference metrics for a two-route buffer.

    `buffer_coupling` is temporary which-route marking. `erase_strength` removes
    reversible markings. `environment_leak` is irreversible route metadata.
    `symmetric_noise` hurts signal quality without identifying a route.
    """

    balance = _clamp01(scenario.path_balance)
    phase = float(scenario.phase_radians)
    reversible_mark = _clamp01(scenario.buffer_coupling) * (
        1.0 - _clamp01(scenario.erase_strength)
    )
    irreversible_mark = _clamp01(scenario.environment_leak)
    distinguishability = _clamp01(
        1.0 - (1.0 - reversible_mark) * (1.0 - irreversible_mark)
    )
    symmetric_noise = _clamp01(scenario.symmetric_noise)

    # Coherence is reduced by route-distinguishable information. Symmetric noise
    # lowers measurement quality but does not itself reveal the route.
    coherence = _clamp01((1.0 - distinguishability) * (1.0 - 0.5 * symmetric_noise))
    amplitude = 2.0 * math.sqrt(balance * (1.0 - balance))
    constructive = 0.5 * (1.0 + amplitude * coherence * math.cos(phase))
    destructive = 0.5 * (1.0 - amplitude * coherence * math.cos(phase))
    visibility = abs(constructive - destructive)
    route_metadata_leak = distinguishability

    if route_metadata_leak <= 0.05 and visibility >= 0.75:
        decision = "PRESERVE_BUFFER"
    elif route_metadata_leak <= 0.25 and visibility >= 0.45:
        decision = "WEAK_BUFFER_TEST"
    else:
        decision = "MEASURED_OR_LEAKY"

    return LeakageResult(
        name=scenario.name,
        distinguishability=round(distinguishability, 6),
        coherence=round(coherence, 6),
        constructive_probability=round(_clamp01(constructive), 6),
        destructive_probability=round(_clamp01(destructive), 6),
        interference_visibility=round(_clamp01(visibility), 6),
        route_metadata_leak=round(route_metadata_leak, 6),
        decision=decision,
    )


def default_scenarios() -> list[LeakageScenario]:
    return [
        LeakageScenario(name="sealed_symmetric_box", symmetric_noise=0.02),
        LeakageScenario(
            name="reversible_buffer_erased",
            buffer_coupling=0.8,
            erase_strength=0.95,
            symmetric_noise=0.04,
        ),
        LeakageScenario(
            name="weak_path_probe",
            buffer_coupling=0.18,
            erase_strength=0.2,
            environment_leak=0.03,
        ),
        LeakageScenario(
            name="glass_common_mode_heat", environment_leak=0.0, symmetric_noise=0.25
        ),
        LeakageScenario(
            name="left_path_heat_mark", environment_leak=0.62, symmetric_noise=0.1
        ),
        LeakageScenario(
            name="mechanical_recoil_record",
            buffer_coupling=0.5,
            erase_strength=0.0,
            environment_leak=0.45,
        ),
        LeakageScenario(
            name="imbalanced_paths", path_balance=0.8, symmetric_noise=0.02
        ),
        LeakageScenario(
            name="phase_shifted_recombined",
            phase_radians=math.pi / 2,
            symmetric_noise=0.02,
        ),
    ]


def run_suite(scenarios: list[LeakageScenario] | None = None) -> dict[str, Any]:
    scenarios = scenarios or default_scenarios()
    results = [simulate(s) for s in scenarios]
    counts: dict[str, int] = {}
    for result in results:
        counts[result.decision] = counts.get(result.decision, 0) + 1
    return {
        "schema_version": "scbe_information_leakage_buffer_v1",
        "hypothesis": "internal routing can remain coherent only when no irreversible distinguishable route metadata leaves the box",
        "metrics": {
            "route_metadata_leak": "0 means no recoverable route record; 1 means route is fully distinguishable",
            "interference_visibility": "higher values mean the two-route alternatives still recombine coherently",
        },
        "decision_counts": counts,
        "scenarios": [asdict(s) for s in scenarios],
        "results": [asdict(r) for r in results],
        "promotion_rule": "only PRESERVE_BUFFER and WEAK_BUFFER_TEST scenarios can become training examples for reversible routing",
    }


def write_suite(path: Path) -> dict[str, Any]:
    payload = run_suite()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SCBE information leakage buffer scenarios"
    )
    parser.add_argument(
        "--output",
        default="artifacts/experiments/information_leakage_buffer/latest.json",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = write_suite(Path(args.output))
    print(
        json.dumps(
            (
                payload
                if args.json
                else {
                    "output": args.output,
                    "decision_counts": payload["decision_counts"],
                }
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
