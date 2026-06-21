"""coding_squad: a role squad that solves the coding board, grounded in Issac's clone-trooper / Polly Pad
doctrine (POLLY_PADS_ARCHITECTURE.md "Clone Trooper Field Upgrade Stations"; HYDRA_COORDINATION.md "Clone
Trooper armor any AI can wear", PHDM = "the Geometric Skull").

Differentiated ROLES (drone classes -> coding roles) each carry a GOAL + a role-scoped gate sub-alphabet,
and are ENCODED AS A POINT in the geometric shape structure (the Poincare ball -- the "Geometric Skull"
that the instructions live in). Roles are paired into GEOMETRIC BUDDY TEAMS by hyperbolic proximity
(the doc's "hyperbolic-distance proximity") for overlapping board coverage. The squad then solves the
coding_board (the CSP); CHECK runs the energy + CBJ jump-back (= Bennett uncompute) repair.

    ARCHITECT  (Mother Ship)  -> frame the board: operators, regions, rules
    RECON                     -> scout targets: the unknowns + known-unknowns (empty constrained cells)
    CODER      (filler)       -> assign operations to operators            [gate sub-alphabet: TRANSFORM]
    CHECK      (constraint)   -> verify global energy; jump-back/uncompute on conflict   [CHECK gates]
    OPTIMIZER                 -> tighten the solved board (micro + macro)   [TRANSFORM]

HONEST: this is a COORDINATION layer over the existing CSP solve -- coding_board.solve does the actual
work; the roles/pairs/shape decide WHO covers WHAT and WHICH gate sub-alphabet each may use. That is what
squad doctrine IS (a coordination + coverage structure), not new solving power. The clone-trooper/Polly
Pad docs are DESIGN-phase vision; this is a small executable slice grounded in them, reusing the shipped
coding_board (#2568), coding_board_gates (#2570) and geometric_router shape primitives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .coding_board import Board, SolveResult, solve
from .coding_board_gates import CHECK, TRANSFORM, gate_names
from .geometric_router import poincare_distance, to_ball


@dataclass(frozen=True)
class Role:
    """A drone class -> coding role. `profile` is the role's point in the shape structure (the 'armor'
    encodes role+goal as geometry); `gate_role` is the sub-alphabet it may use (None = non-coding role)."""

    name: str
    goal: str
    gate_role: Optional[str]
    profile: Tuple[float, ...]

    def legal_operations(self) -> Tuple[str, ...]:
        return gate_names(self.gate_role) if self.gate_role else ()


# the squad doctrine made concrete: drone classes -> coding roles, each a point in the shape structure
SQUAD: List[Role] = [
    Role("ARCHITECT", "frame the board: operators, regions, rules", None, (1.0, 0.2, 0.2, 0.1, 0.1, 0.1)),
    Role(
        "RECON",
        "scout targets: unknowns + known-unknowns (empty constrained cells)",
        None,
        (0.2, 1.0, 0.3, 0.1, 0.1, 0.1),
    ),
    Role("CODER", "assign operations to operators (do the work)", TRANSFORM, (0.1, 0.3, 1.0, 0.4, 0.1, 0.1)),
    Role("CHECK", "verify global energy; jump-back/uncompute on conflict", CHECK, (0.1, 0.1, 0.4, 1.0, 0.3, 0.1)),
    Role("OPTIMIZER", "tighten the solved board (micro + macro)", TRANSFORM, (0.1, 0.1, 0.3, 0.3, 1.0, 0.2)),
]


def geometric_pairs(roles: List[Role]) -> List[Tuple[str, Optional[str], float]]:
    """Pair roles into BUDDY TEAMS by hyperbolic proximity in the shape structure (the doc's geometric
    pairs for situation coverage). Greedy nearest-neighbour; an odd role solos (e.g. the Mother Ship /
    ARCHITECT). Returns (role, buddy_or_None, hyperbolic_distance)."""
    balls = [(r, to_ball(np.array(r.profile, dtype=float))) for r in roles]
    used: set = set()
    pairs: List[Tuple[str, Optional[str], float]] = []
    for i, (r, b) in enumerate(balls):
        if r.name in used:
            continue
        best: Optional[Tuple[str, float]] = None
        for j, (r2, b2) in enumerate(balls):
            if j == i or r2.name in used:
                continue
            d = poincare_distance(b, b2)
            if best is None or d < best[1]:
                best = (r2.name, d)
        used.add(r.name)
        if best is not None:
            used.add(best[0])
            pairs.append((r.name, best[0], round(best[1], 4)))
        else:
            pairs.append((r.name, None, 0.0))
    return pairs


def cover_regions(board: Board, pairs: List[Tuple[str, Optional[str], float]]) -> Dict[str, str]:
    """Assign board regions to buddy teams for overlapping coverage (each region gets a team). With no
    regions, the whole board is one coverage zone."""
    regions = sorted({op.region for op in board.operators if op.region})
    teams = ["%s+%s" % (a, b) if b else a for a, b, _d in pairs]
    if not regions:
        return {"<whole-board>": teams[0] if teams else "<none>"}
    return {region: teams[k % len(teams)] for k, region in enumerate(regions)}


@dataclass
class SquadResult:
    solved: bool
    assignment: Dict[str, str]
    energy: int
    jumps: List[int]  # the CHECK role's CBJ jump-backs (= uncompute targets)
    targets: List[str]  # RECON's unknowns (operators to solve)
    pairs: List[Tuple[str, Optional[str], float]]  # the geometric buddy teams
    coverage: Dict[str, str]  # region -> team
    roster: Dict[str, str] = field(default_factory=dict)  # role -> its legal-operation sub-alphabet size


def solve_with_squad(board: Board, roles: Optional[List[Role]] = None) -> SquadResult:
    """Run the squad over the board: pair roles geometrically, assign region coverage, RECON the targets,
    then solve the CSP (CODER fills, CHECK runs the energy/CBJ jump-back). The solve is coding_board.solve;
    the squad layer is the coordination + coverage around it."""
    roles = roles or SQUAD
    pairs = geometric_pairs(roles)
    coverage = cover_regions(board, pairs)
    targets = [op.id for op in board.operators if op.fixed is None]  # RECON: the unknowns
    res: SolveResult = solve(board)  # CODER fills; CHECK's repair = the CBJ jumps inside the solve
    roster = {r.name: ("%d ops" % len(r.legal_operations())) for r in roles}
    return SquadResult(
        solved=res.solved,
        assignment=res.assignment,
        energy=res.energy,
        jumps=res.jumps,
        targets=targets,
        pairs=pairs,
        coverage=coverage,
        roster=roster,
    )
