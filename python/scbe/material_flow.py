"""Deterministic voltage-pulse propagation over categorical material grids.

One pulse is a discrete graph tick, not one second of wall-clock time. Binary
voltage carries reachability; categorical material IDs remain an independent
channel that controls which transitions conduct. Every pulse is receipted and
the total filled area is reduced only after the flow halts or exhausts budget.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

from python.scbe.loomflow import parse as parse_loomflow
from python.scbe.loomflow import trace_execution

MaterialEdge = Tuple[int, int]


@dataclass(frozen=True)
class MaterialPolicy:
    """Categorical conductivity without assigning an order to material IDs."""

    conductive_materials: frozenset[int]
    allowed_transitions: Optional[frozenset[MaterialEdge]] = None

    @classmethod
    def from_materials(
        cls,
        conductive_materials: Iterable[int],
        allowed_transitions: Optional[Iterable[MaterialEdge]] = None,
    ) -> "MaterialPolicy":
        transitions = (
            frozenset((int(left), int(right)) for left, right in allowed_transitions)
            if allowed_transitions is not None
            else None
        )
        return cls(frozenset(int(value) for value in conductive_materials), transitions)

    def allows(self, source: int, target: int) -> bool:
        if source not in self.conductive_materials or target not in self.conductive_materials:
            return False
        return self.allowed_transitions is None or (source, target) in self.allowed_transitions


@dataclass(frozen=True)
class PulseResult:
    filled: np.ndarray
    voltage: np.ndarray
    total_area: int
    area_by_material: dict[int, int]
    pulses: int
    fixed_point: bool
    receipt: dict


def _mask_sha256(mask: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(mask, dtype=np.uint8).tobytes()).hexdigest()


def _directions(connectivity: int) -> Sequence[Tuple[int, int]]:
    if connectivity == 4:
        return ((-1, 0), (0, 1), (1, 0), (0, -1))
    if connectivity == 8:
        return (
            (-1, 0),
            (0, 1),
            (1, 0),
            (0, -1),
            (-1, -1),
            (-1, 1),
            (1, 1),
            (1, -1),
        )
    raise ValueError("connectivity must be 4 or 8")


def _propagate(
    materials: np.ndarray,
    frontier: np.ndarray,
    filled: np.ndarray,
    policy: MaterialPolicy,
    connectivity: int,
) -> np.ndarray:
    height, width = materials.shape
    next_frontier = np.zeros_like(frontier, dtype=bool)
    for y, x in np.argwhere(frontier):
        source_material = int(materials[y, x])
        for dy, dx in _directions(connectivity):
            ny, nx = int(y + dy), int(x + dx)
            if not (0 <= ny < height and 0 <= nx < width) or filled[ny, nx]:
                continue
            if policy.allows(source_material, int(materials[ny, nx])):
                next_frontier[ny, nx] = True
    return next_frontier


def _controller_receipt(pulses: int) -> dict:
    source = f"""const phase 0
const limit {pulses}
label pulse
lt active phase limit
brz active done
inc phase
jmp pulse
label done
print phase
halt"""
    return trace_execution(parse_loomflow(source))


def pulse_fill(
    materials: np.ndarray,
    seeds: np.ndarray,
    policy: MaterialPolicy,
    *,
    connectivity: int = 4,
    max_pulses: Optional[int] = None,
    voltage_level: float = 1.0,
) -> PulseResult:
    """Pulse seed voltage through allowed material edges and reduce filled area."""
    material_grid = np.asarray(materials, dtype=np.int64)
    seed_mask = np.asarray(seeds, dtype=bool)
    if material_grid.ndim != 2 or seed_mask.shape != material_grid.shape:
        raise ValueError("materials and seeds must be equally shaped 2D arrays")
    if not np.isfinite(voltage_level) or voltage_level <= 0:
        raise ValueError("voltage_level must be finite and positive")
    if max_pulses is not None and max_pulses < 0:
        raise ValueError("max_pulses must be non-negative or None")

    conductive = np.isin(material_grid, list(policy.conductive_materials))
    if np.any(seed_mask & ~conductive):
        raise ValueError("every voltage seed must lie on a conductive material")
    filled = seed_mask.copy()
    frontier = seed_mask.copy()
    rows = [
        {
            "phase": 0,
            "frontier_area": int(np.count_nonzero(frontier)),
            "added_area": int(np.count_nonzero(frontier)),
            "total_area": int(np.count_nonzero(filled)),
            "mask_sha256": _mask_sha256(filled),
        }
    ]
    pulses = 0
    fixed_point = False
    while max_pulses is None or pulses < max_pulses:
        next_frontier = _propagate(material_grid, frontier, filled, policy, connectivity)
        pulses += 1
        added = int(np.count_nonzero(next_frontier))
        filled |= next_frontier
        rows.append(
            {
                "phase": pulses,
                "frontier_area": added,
                "added_area": added,
                "total_area": int(np.count_nonzero(filled)),
                "mask_sha256": _mask_sha256(filled),
            }
        )
        frontier = next_frontier
        if added == 0:
            fixed_point = True
            break

    area_by_material = {
        int(material): int(np.count_nonzero(filled & (material_grid == material)))
        for material in np.unique(material_grid[filled])
    }
    receipt = {
        "schema": "scbe.material-flow-pulse.v1",
        "shape": list(material_grid.shape),
        "connectivity": connectivity,
        "voltage_level": float(voltage_level),
        "policy": {
            "conductive_materials": sorted(policy.conductive_materials),
            "allowed_transitions": (
                sorted([list(edge) for edge in policy.allowed_transitions])
                if policy.allowed_transitions is not None
                else "all conductive pairs"
            ),
        },
        "pulses": rows,
        "fixed_point": fixed_point,
        "total_area": int(np.count_nonzero(filled)),
        "area_by_material": area_by_material,
        "controller": _controller_receipt(pulses),
    }
    if not verify_pulse_receipt(receipt):
        raise RuntimeError("material-flow receipt failed its own integrity gate")
    return PulseResult(
        filled=filled,
        voltage=filled.astype(np.float64) * voltage_level,
        total_area=receipt["total_area"],
        area_by_material=area_by_material,
        pulses=pulses,
        fixed_point=fixed_point,
        receipt=receipt,
    )


def verify_pulse_receipt(receipt: dict) -> bool:
    """Verify phase order, monotone area, count deltas, and control trace."""
    if receipt.get("schema") != "scbe.material-flow-pulse.v1":
        return False
    rows = receipt.get("pulses")
    if not isinstance(rows, list) or not rows:
        return False
    for phase, row in enumerate(rows):
        if row.get("phase") != phase or row.get("frontier_area") != row.get("added_area"):
            return False
        if phase == 0:
            if row.get("total_area") != row.get("added_area"):
                return False
            continue
        previous = rows[phase - 1]
        if row.get("total_area") != previous.get("total_area") + row.get("added_area"):
            return False
    if rows[-1].get("total_area") != receipt.get("total_area"):
        return False
    controller = receipt.get("controller", {})
    outputs = controller.get("outputs", []) if isinstance(controller, dict) else []
    return bool(outputs) and outputs[-1] == float(len(rows) - 1)


def receipt_sha256(receipt: dict) -> str:
    """Stable identifier for a completed material-flow run."""
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()
