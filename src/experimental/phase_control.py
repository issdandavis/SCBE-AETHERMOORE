"""Experimental periodic and aperiodic phase-control modulation matrices.

This module stays outside the production governance path. It provides a small,
inspectable playground for six-tongue phase modulation that can later be
attached to n8n/AetherBrowse workflow routing if the behavior is useful.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

PHI = (1.0 + math.sqrt(5.0)) / 2.0
TONGUES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")
BASE_PHASES: Tuple[float, ...] = tuple(
    (2.0 * math.pi * idx) / len(TONGUES) for idx in range(len(TONGUES))
)


def _wrap(angle: float) -> float:
    return angle % (2.0 * math.pi)


def _frac(value: float) -> float:
    return value - math.floor(value)


def _rounded_matrix(
    matrix: Sequence[Sequence[float]], digits: int = 6
) -> List[List[float]]:
    return [[round(float(value), digits) for value in row] for row in matrix]


def _phase_delta(a: float, b: float) -> float:
    raw = abs(_wrap(a) - _wrap(b))
    return min(raw, (2.0 * math.pi) - raw)


def canonical_tongue_phases() -> Dict[str, float]:
    return {tongue: BASE_PHASES[idx] for idx, tongue in enumerate(TONGUES)}


def base_coupling_matrix(phases: Sequence[float] = BASE_PHASES) -> List[List[float]]:
    matrix: List[List[float]] = []
    for phase_i in phases:
        row: List[float] = []
        for phase_j in phases:
            row.append(math.cos(_phase_delta(phase_i, phase_j)))
        matrix.append(row)
    return matrix


def periodic_modulation_vector(
    step: int, period: int, phases: Sequence[float] = BASE_PHASES
) -> List[float]:
    omega = (2.0 * math.pi) / max(1, period)
    values = []
    for phase in phases:
        values.append(0.5 * (1.0 + math.cos(phase + (omega * step))))
    return values


def aperiodic_modulation_vector(
    step: int, phases: Sequence[float] = BASE_PHASES
) -> List[float]:
    values = []
    for idx, phase in enumerate(phases):
        local_offset = 2.0 * math.pi * _frac(((idx + 1) * (step + 1)) / PHI)
        quasi_phase = phase + ((2.0 * math.pi / PHI) * step) + local_offset
        values.append(0.5 * (1.0 + math.cos(quasi_phase)))
    return values


def apply_modulation(
    coupling: Sequence[Sequence[float]], modulation: Sequence[float]
) -> List[List[float]]:
    matrix: List[List[float]] = []
    for i, row in enumerate(coupling):
        out_row: List[float] = []
        for j, base in enumerate(row):
            out_row.append(modulation[i] * modulation[j] * base)
        matrix.append(out_row)
    return matrix


def coherence_score(matrix: Sequence[Sequence[float]]) -> float:
    if not matrix:
        return 0.0
    n = len(matrix)
    off_diag = [matrix[i][j] for i in range(n) for j in range(n) if i != j]
    if not off_diag:
        return 1.0
    return sum(off_diag) / len(off_diag)


def energy_score(matrix: Sequence[Sequence[float]]) -> float:
    return sum(abs(value) for row in matrix for value in row) / max(
        1, len(matrix) * len(matrix)
    )


@dataclass(frozen=True)
class MatrixSnapshot:
    mode: str
    step: int
    modulation: List[float]
    coherence: float
    energy: float
    matrix: List[List[float]]


def periodic_snapshot(
    step: int, period: int, phases: Sequence[float] = BASE_PHASES
) -> MatrixSnapshot:
    base = base_coupling_matrix(phases)
    modulation = periodic_modulation_vector(step, period, phases)
    matrix = apply_modulation(base, modulation)
    return MatrixSnapshot(
        mode="periodic",
        step=step,
        modulation=[round(v, 6) for v in modulation],
        coherence=round(coherence_score(matrix), 6),
        energy=round(energy_score(matrix), 6),
        matrix=_rounded_matrix(matrix),
    )


def aperiodic_snapshot(
    step: int, phases: Sequence[float] = BASE_PHASES
) -> MatrixSnapshot:
    base = base_coupling_matrix(phases)
    modulation = aperiodic_modulation_vector(step, phases)
    matrix = apply_modulation(base, modulation)
    return MatrixSnapshot(
        mode="aperiodic",
        step=step,
        modulation=[round(v, 6) for v in modulation],
        coherence=round(coherence_score(matrix), 6),
        energy=round(energy_score(matrix), 6),
        matrix=_rounded_matrix(matrix),
    )


def build_report(steps: int, period: int) -> Dict[str, Any]:
    periodic = [asdict(periodic_snapshot(step, period)) for step in range(steps)]
    aperiodic = [asdict(aperiodic_snapshot(step)) for step in range(steps)]

    periodic_repeat = (
        periodic[0]["matrix"] == periodic[min(period, steps - 1)]["matrix"]
        if steps > period
        else None
    )
    aperiodic_repeat = (
        aperiodic[0]["matrix"] == aperiodic[min(period, steps - 1)]["matrix"]
        if steps > period
        else None
    )

    return {
        "run_id": datetime.now(timezone.utc).strftime("phase_control_%Y%m%dT%H%M%SZ"),
        "tongues": list(TONGUES),
        "canonical_phase_degrees": {
            tongue: round(math.degrees(angle), 3)
            for tongue, angle in canonical_tongue_phases().items()
        },
        "experiment": {
            "steps": steps,
            "period": period,
            "notes": [
                "periodic mode uses a shared rational phase frequency and repeats on the declared period",
                "aperiodic mode uses phi-based irrational phase progression with per-node quasi offsets",
                "output is safe for workflow experiments; it does not alter production governance",
            ],
        },
        "periodic": periodic,
        "aperiodic": aperiodic,
        "comparisons": {
            "periodic_repeats_at_period": periodic_repeat,
            "aperiodic_repeats_at_period": aperiodic_repeat,
            "periodic_coherence_mean": round(
                sum(item["coherence"] for item in periodic) / max(1, len(periodic)), 6
            ),
            "aperiodic_coherence_mean": round(
                sum(item["coherence"] for item in aperiodic) / max(1, len(aperiodic)), 6
            ),
        },
        "n8n_payload_hint": {
            "workflow_kind": "phase-control-modulation",
            "modes": ["periodic", "aperiodic"],
            "fields": ["mode", "step", "modulation", "matrix", "coherence", "energy"],
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate periodic and aperiodic six-tongue phase-control matrices."
    )
    parser.add_argument(
        "--steps", type=int, default=12, help="How many temporal steps to emit."
    )
    parser.add_argument("--period", type=int, default=6, help="Periodic repeat window.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/experiments/phase_control_modulation_report.json"),
        help="Where to write the experiment report JSON.",
    )
    args = parser.parse_args(argv)

    report = build_report(max(2, args.steps), max(2, args.period))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[phase-control] wrote {args.output}")
    print(
        f"[phase-control] periodic_mean={report['comparisons']['periodic_coherence_mean']} "
        f"aperiodic_mean={report['comparisons']['aperiodic_coherence_mean']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
