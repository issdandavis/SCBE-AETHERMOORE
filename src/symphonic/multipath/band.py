"""Stage 4 lattice arbitration for Prism->Rainbow->Beam.

This module resolves cross-tongue cell conflicts using ownership evidence,
not language popularity. Promotion order follows the grounded policy:

    DR -> RU -> AV -> UM -> KO -> CA

Write/write collisions on RU and CA are safety-relevant. All other
write/write collisions are correctness-relevant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping


TONGUE_PRIORITY: tuple[str, ...] = ("DR", "RU", "AV", "UM", "KO", "CA")
TONGUES: tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")
SAFETY_CRITICAL_WRITERS = frozenset({"RU", "CA"})


@dataclass(frozen=True)
class CellArbitration:
    cell_id: int
    writers: tuple[str, ...]
    readers: tuple[str, ...]
    blockers: tuple[str, ...]
    winner: str | None
    promotion_order: tuple[str, ...]
    desync_required: bool
    safety_risk: str
    correctness_risk: str
    failure_mode: str

    @property
    def resolved(self) -> bool:
        return self.failure_mode == "none"


def _ordered_active(tongues: Iterable[str]) -> tuple[str, ...]:
    active = set(tongues)
    return tuple(t for t in TONGUE_PRIORITY if t in active)


def arbitrate_cell(cell_id: int, tongue_votes: Mapping[str, int]) -> CellArbitration:
    """Resolve one lattice cell from per-tongue trit votes."""

    unknown = sorted(set(tongue_votes) - set(TONGUES))
    if unknown:
        raise ValueError(f"unknown tongues in cell {cell_id}: {unknown}")

    invalid = {tongue: vote for tongue, vote in tongue_votes.items() if vote not in (-1, 0, 1)}
    if invalid:
        raise ValueError(f"invalid trit votes in cell {cell_id}: {invalid}")

    writers = _ordered_active(t for t, vote in tongue_votes.items() if vote == 1)
    readers = _ordered_active(t for t, vote in tongue_votes.items() if vote == 0)
    blockers = _ordered_active(t for t, vote in tongue_votes.items() if vote == -1)

    if len(writers) <= 1:
        return CellArbitration(
            cell_id=cell_id,
            writers=writers,
            readers=readers,
            blockers=blockers,
            winner=writers[0] if writers else None,
            promotion_order=writers,
            desync_required=False,
            safety_risk="LOW",
            correctness_risk="LOW",
            failure_mode="none",
        )

    winner = writers[0]
    safety_critical = any(t in SAFETY_CRITICAL_WRITERS for t in writers)
    return CellArbitration(
        cell_id=cell_id,
        writers=writers,
        readers=readers,
        blockers=blockers,
        winner=winner,
        promotion_order=writers,
        desync_required=safety_critical,
        safety_risk="HIGH" if safety_critical else "LOW",
        correctness_risk="HIGH",
        failure_mode="write_write_collision",
    )


def closure_check(cells: Mapping[int, Mapping[str, int]]) -> List[CellArbitration]:
    """Run arbitration over a band/lattice slice keyed by cell id."""

    return [arbitrate_cell(cell_id, votes) for cell_id, votes in sorted(cells.items())]


def summarize_closure(results: Iterable[CellArbitration]) -> dict:
    resolved = 0
    desync_required = 0
    failures = 0
    safety_high = 0
    correctness_high = 0
    for result in results:
        resolved += int(result.resolved)
        desync_required += int(result.desync_required)
        failures += int(not result.resolved)
        safety_high += int(result.safety_risk == "HIGH")
        correctness_high += int(result.correctness_risk == "HIGH")
    return {
        "resolved": resolved,
        "desync_required": desync_required,
        "failures": failures,
        "safety_high": safety_high,
        "correctness_high": correctness_high,
    }
