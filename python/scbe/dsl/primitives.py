"""DSL primitives over the 6-tongue / 14-layer SCBE substrate.

A naming contract on top of existing implementations. Per the lane spec
(artifacts/blind_spot_ledger/lanes/L_dsl_synthesis.md), these 8 primitives
wrap the canonical TONGUES registry, phi-scaling, Poincare projection, and
MSR-style state transformations already present in the package.

Programs are line-separated `name(args)` strings; sequence == composition.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Sequence, Tuple, Union

import numpy as np

from ..brain import GOLDEN_RATIO, TONGUES, _project_to_poincare_ball

GRID_SIZE = 16  # 16x16 = 256 tokens per tongue (CLAUDE.md Sacred Tongues)


@dataclass(frozen=True)
class GridState:
    """Working state for the DSL.

    Fields:
        grid          16x16 token / value grid for the active tongue
        tongue        current tongue code (KO/AV/RU/CA/UM/DR)
        phi_power     accumulated phi^k weighting exponent
        phase         Mobius phase angle in radians
        breath_phase  breathing-transform phase
        well          selected Hamiltonian realm tag (None = unselected)
    """

    grid: np.ndarray
    tongue: str = "KO"
    phi_power: int = 0
    phase: float = 0.0
    breath_phase: float = 0.0
    well: Union[str, None] = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GridState):
            return False
        return (
            np.array_equal(self.grid, other.grid)
            and self.tongue == other.tongue
            and self.phi_power == other.phi_power
            and abs(self.phase - other.phase) < 1e-9
            and abs(self.breath_phase - other.breath_phase) < 1e-9
            and self.well == other.well
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.tongue,
                self.phi_power,
                self.well,
                round(self.phase, 6),
                round(self.breath_phase, 6),
            )
        )


def _validate_tongue(t: str) -> None:
    if t not in TONGUES:
        raise ValueError(f"unknown tongue {t!r}; expected one of {sorted(TONGUES)}")


def tongue_shift(state: GridState, src: str, dst: str) -> GridState:
    """Shift the working state from one tongue to another."""
    _validate_tongue(src)
    _validate_tongue(dst)
    if state.tongue != src:
        raise ValueError(f"tongue mismatch: state={state.tongue} src={src}")
    src_phase = float(TONGUES[src]["phase"])
    dst_phase = float(TONGUES[dst]["phase"])
    return replace(state, tongue=dst, phase=state.phase + (dst_phase - src_phase))


def phi_weight(state: GridState, t: str, k: int) -> GridState:
    """Apply phi^k weighting in tongue t to the grid."""
    _validate_tongue(t)
    if state.tongue != t:
        raise ValueError(f"tongue mismatch: state={state.tongue} t={t}")
    factor = float(GOLDEN_RATIO) ** int(k)
    return replace(
        state,
        grid=state.grid * factor,
        phi_power=state.phi_power + int(k),
    )


def mobius_phase(state: GridState, theta: float) -> GridState:
    """Rotate the Mobius phase by theta radians (additive in this contract)."""
    return replace(state, phase=state.phase + float(theta))


def breath(state: GridState, omega: float) -> GridState:
    """Advance the breathing-transform phase by omega."""
    return replace(state, breath_phase=state.breath_phase + float(omega))


def compose(
    f: Callable[..., GridState], g: Callable[..., GridState]
) -> Callable[..., GridState]:
    """Function composition (axiom A5): compose(f, g)(x) == f(g(x))."""

    def composed(state: GridState, *args: Any, **kwargs: Any) -> GridState:
        return f(g(state, *args, **kwargs))

    return composed


def vote(*states: GridState) -> GridState:
    """Swarm consensus over candidate states (L13).

    Picks the consensus tongue (mode), then the candidate whose grid is
    closest to the mean of that group, with shorter explanations (lower
    phi_power) winning ties. Idempotent for a single argument.
    """
    if not states:
        raise ValueError("vote requires at least one state")
    if len(states) == 1:
        return states[0]
    tongue_counts = Counter(s.tongue for s in states)
    consensus_tongue = tongue_counts.most_common(1)[0][0]
    candidates = [s for s in states if s.tongue == consensus_tongue]
    mean_grid = np.mean(np.stack([c.grid for c in candidates]), axis=0)

    def score(s: GridState) -> Tuple[int, float]:
        return (s.phi_power, float(np.linalg.norm(s.grid - mean_grid)))

    return min(candidates, key=score)


def well_select(state: GridState, realm: str) -> GridState:
    """Pick a Hamiltonian CFI realm (L8). The choice persists until overwritten."""
    if not isinstance(realm, str) or not realm:
        raise ValueError("realm must be a non-empty string")
    return replace(state, well=realm)


def seal(state: GridState) -> GridState:
    """Sacred-Egg / GeoSeal output stage (L14 boundary).

    Projects the flattened grid into the Poincare ball. Idempotent: a state
    already marked SEALED is returned unchanged.
    """
    if state.well == "SEALED":
        return state
    flat = state.grid.reshape(-1).astype(float)
    projected = _project_to_poincare_ball(flat)
    return replace(state, grid=projected.reshape(state.grid.shape), well="SEALED")


PRIMITIVE_TABLE: Dict[str, Callable[..., GridState]] = {
    "tongue_shift": tongue_shift,
    "phi_weight": phi_weight,
    "mobius_phase": mobius_phase,
    "breath": breath,
    "compose": compose,
    "vote": vote,
    "well_select": well_select,
    "seal": seal,
}


@dataclass(frozen=True)
class Op:
    name: str
    args: Tuple[Any, ...] = field(default_factory=tuple)


_LINE_RE = re.compile(r"^\s*([a-z_]+)\s*\((.*)\)\s*$")


def _parse_arg(name: str, raw: str) -> Tuple[Any, ...]:
    raw = raw.strip()
    if name == "tongue_shift":
        parts = re.split(r"\s*(?:->|→)\s*", raw)
        if len(parts) != 2:
            raise ValueError(f"tongue_shift expects 'A -> B', got {raw!r}")
        return (parts[0].strip(), parts[1].strip())
    if name == "phi_weight":
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2:
            raise ValueError(f"phi_weight expects 'TONGUE, k', got {raw!r}")
        return (parts[0], int(parts[1]))
    if name in ("mobius_phase", "breath"):
        if not raw:
            raise ValueError(f"{name} expects a single float, got empty")
        return (float(raw),)
    if name == "well_select":
        if not raw:
            raise ValueError("well_select expects a realm name")
        return (raw,)
    if name == "seal":
        if raw:
            raise ValueError(f"seal takes no args, got {raw!r}")
        return ()
    if name in ("compose", "vote"):
        # Higher-order / n-ary primitives are not expressed as line ops; the
        # parser accepts them for catalog completeness but run_program treats
        # them as no-ops. They are unit-tested at the function level.
        return tuple(p.strip() for p in raw.split(",") if p.strip())
    raise ValueError(f"unknown primitive {name!r}")


def parse_program(text: str) -> List[Op]:
    """Parse a multiline program of `name(args)` lines into Op objects."""
    ops: List[Op] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        m = _LINE_RE.match(line)
        if not m:
            raise ValueError(f"could not parse program line: {raw_line!r}")
        name, raw_args = m.group(1), m.group(2)
        if name not in PRIMITIVE_TABLE:
            raise ValueError(f"unknown primitive {name!r} in program")
        args = _parse_arg(name, raw_args)
        ops.append(Op(name=name, args=args))
    return ops


# Primitives that are line-emittable and apply to a single state in run_program.
_LINE_APPLICABLE = {
    "tongue_shift",
    "phi_weight",
    "mobius_phase",
    "breath",
    "well_select",
    "seal",
}


def run_program(ops: Sequence[Op], state: GridState) -> GridState:
    """Apply each op sequentially. Sequence is implicit composition."""
    for op in ops:
        if op.name not in _LINE_APPLICABLE:
            continue
        fn = PRIMITIVE_TABLE[op.name]
        state = fn(state, *op.args)
    return state


def initial_state(tongue: str = "KO") -> GridState:
    """Return a zero grid in the named tongue."""
    _validate_tongue(tongue)
    return GridState(grid=np.zeros((GRID_SIZE, GRID_SIZE), dtype=float), tongue=tongue)


def name_of(fn: Callable[..., GridState]) -> str:
    """Reverse lookup: function -> primitive name."""
    for n, f in PRIMITIVE_TABLE.items():
        if f is fn:
            return n
    raise KeyError(f"function {fn} not in PRIMITIVE_TABLE")
