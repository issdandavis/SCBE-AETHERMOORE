"""
Sheaf Consensus Gate
====================

Operational gate using lattice-valued temporal sheaf consistency.
Designed as a utility module for SCBE pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .tarski_sheaf import (
    TemporalSheaf,
    make_temporal_sheaf,
    fail_to_noise_projection,
    obstruction_count,
)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _to_lattice_level(x: float) -> int:
    y = clamp01(x)
    if y < 0.25:
        return 0
    if y < 0.50:
        return 1
    if y < 0.75:
        return 2
    return 3


@dataclass(frozen=True)
class SheafGateResult:
    decision: str
    omega: float
    triadic_stable: float
    sheaf_obstructions: int
    assignment: Dict[str, int]
    projected: Dict[str, int]
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "decision": self.decision,
            "omega": round(self.omega, 6),
            "triadic_stable": round(self.triadic_stable, 6),
            "sheaf_obstructions": self.sheaf_obstructions,
            "assignment": self.assignment,
            "projected": self.projected,
            "reason": self.reason,
        }


def build_temporal_sheaf() -> TemporalSheaf:
    # Monotone restrictions: drift can relax by at most one level on Ti->Tm and Tm->Tg.
    def relax_one(v: int) -> int:
        return max(0, int(v) - 1)

    return make_temporal_sheaf(
        nodes=("Ti", "Tm", "Tg"),
        lattice_values=(0, 1, 2, 3),
        twisted_edges={
            ("Ti", "Tm"): relax_one,
            ("Tm", "Tg"): relax_one,
        },
    )


def sheaf_stability(
    *,
    fast_signal: float,
    memory_signal: float,
    governance_signal: float,
    sheaf: TemporalSheaf | None = None,
) -> Tuple[float, int, Dict[str, int], Dict[str, int]]:
    sh = sheaf or build_temporal_sheaf()
    assignment = {
        "Ti": _to_lattice_level(fast_signal),
        "Tm": _to_lattice_level(memory_signal),
        "Tg": _to_lattice_level(governance_signal),
    }
    projected = fail_to_noise_projection(sh, assignment)
    obs = obstruction_count(sh, assignment)
    stable = max(0.0, 1.0 - obs / 3.0)
    return stable, obs, assignment, projected


def sheaf_gate(
    *,
    fast_signal: float,
    memory_signal: float,
    governance_signal: float,
    pqc_valid: float = 1.0,
    harm_score: float = 1.0,
    drift_factor: float = 1.0,
    spectral_score: float = 1.0,
) -> SheafGateResult:
    triadic_stable, obs, assignment, projected = sheaf_stability(
        fast_signal=fast_signal,
        memory_signal=memory_signal,
        governance_signal=governance_signal,
    )
    omega = (
        clamp01(pqc_valid)
        * clamp01(harm_score)
        * clamp01(drift_factor)
        * clamp01(triadic_stable)
        * clamp01(spectral_score)
    )

    if clamp01(pqc_valid) <= 0.0:
        return SheafGateResult(
            decision="DENY",
            omega=0.0,
            triadic_stable=triadic_stable,
            sheaf_obstructions=obs,
            assignment=assignment,
            projected=projected,
            reason="pqc invalid",
        )

    if omega >= 0.70:
        decision = "ALLOW"
        reason = "omega above allow threshold"
    elif omega >= 0.30:
        decision = "QUARANTINE"
        reason = "omega in quarantine band"
    else:
        decision = "DENY"
        reason = "omega below deny threshold"

    return SheafGateResult(
        decision=decision,
        omega=omega,
        triadic_stable=triadic_stable,
        sheaf_obstructions=obs,
        assignment=assignment,
        projected=projected,
        reason=reason,
    )


def run_jsonl(
    input_path: Path,
    output_path: Path,
) -> Dict[str, int]:
    rows = [x.strip() for x in input_path.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    counts = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
    with output_path.open("w", encoding="utf-8") as handle:
        for line in rows:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue

            fast = float(rec.get("fast_signal", rec.get("distance", 0.0)) or 0.0)
            memory = float(rec.get("memory_signal", rec.get("intent", 0.0)) or 0.0)
            gov = float(rec.get("governance_signal", 1.0 - float(rec.get("trust", 1.0))) or 0.0)

            result = sheaf_gate(
                fast_signal=fast,
                memory_signal=memory,
                governance_signal=gov,
                pqc_valid=float(rec.get("pqc_valid", 1.0) or 0.0),
                harm_score=float(rec.get("harm_score", 1.0) or 0.0),
                drift_factor=float(rec.get("drift_factor", 1.0) or 0.0),
                spectral_score=float(rec.get("spectral_score", 1.0) or 0.0),
            )
            out = dict(rec)
            out["sheaf_gate"] = result.to_dict()
            counts[result.decision] += 1
            handle.write(json.dumps(out, ensure_ascii=True) + "\n")

    return counts

