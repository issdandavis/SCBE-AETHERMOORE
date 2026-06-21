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

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .coding_board import Board, Operator, SolveResult, region_must_agree, solve
from .coding_board_gates import CHECK, TRANSFORM, gate_names
from .geometric_router import poincare_distance, to_ball
from .observer_dynamics import decision_bits
from .reversible_circuit import ROOM_T_K, EnergyLedger
from .squad_puzzle import (
    DOMINO,
    I_TROMINO,
    L_TROMINO,
    SQUARE,
    T_TETRO,
    Cell,
    Piece,
    Region,
    coverable_cells,
    holes,
)


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
    gate: Optional["CoverageGate"] = None  # the geometric coverage pre-check (None when not computed)
    rejected: bool = False  # True when require_coverage refused the board for a coverage gap (no solve run)
    squad_energy: Optional["SquadEnergy"] = None  # Landauer cost of the solve's CBJ re-decisions (None if none)


@dataclass
class SquadEnergy:
    """The thermodynamic cost of a squad solve, by Landauer's principle (the bijective-time/reversible arc
    meeting the squad). Each CBJ jump-back is an irreversible RE-DECISION that overwrites an operator's
    assignment, erasing decision_bits(domain) bits; a conflict-free (forward-only) solve pays 0. Metered the
    same way as observer_dynamics.resolve_by_jumpback_metered -- the two CBJ solvers share one ledger."""

    overwrites: int  # CBJ jump-backs the solve committed (irreversible re-decisions; -1 dead-ends excluded)
    bits_erased: int  # sum of decision_bits(operator domain) over those re-decisions
    irreversible_joules: float  # the Landauer FLOOR the dissipating (overwrite) solve pays (a lower bound)
    reversible_joules: float  # 0.0 -- logging the jumps (an undo-tape) erases nothing during the solve (Bennett)


def solve_energy(board: Board, jumps: List[int], temperature_k: float = ROOM_T_K) -> SquadEnergy:
    """Meter a solve's CBJ jump-backs with the Landauer ledger. Each valid jump overwrites that operator's
    decision (erasing log2(domain) bits); -1 dead-end sentinels are not real re-decisions and are skipped.
    The reversible alternative (log the jumps as an undo-tape) erases nothing -- it defers the cost to space."""
    valid = [j for j in jumps if 0 <= j < len(board.operators)]
    ledger = EnergyLedger(temperature_k=temperature_k)
    for j in valid:
        ledger.erase("re-decide op[%d]" % j, decision_bits(len(board.operators[j].domain)))
    return SquadEnergy(
        overwrites=len(valid),
        bits_erased=ledger.bits_erased,
        irreversible_joules=ledger.joules(),
        reversible_joules=0.0,
    )


def board_region(board: Board) -> "Region":
    """A deterministic geometric layout for a board: pack its operators row-major into a near-square grid,
    one cell per operator. Gives the coverage gate a SHAPE to reach over when the board has no spatial info."""
    n = len(board.operators)
    if n == 0:
        return frozenset()
    w = math.ceil(math.sqrt(n))
    return frozenset(((i // w), (i % w)) for i in range(n))


def solve_with_squad(
    board: Board,
    roles: Optional[List[Role]] = None,
    region: "Optional[Region]" = None,
    require_coverage: bool = False,
) -> SquadResult:
    """Run the squad over the board: pair roles geometrically, assign region coverage, RECON the targets,
    then solve the CSP (CODER fills, CHECK runs the energy/CBJ jump-back). The solve is coding_board.solve;
    the squad layer is the coordination + coverage around it.

    The geometric coverage GATE runs first: it checks the squad's role-pieces can reach every cell of the
    board's layout (`region`, or a packed default). The gate is always ATTACHED to the result; when
    `require_coverage` is set, a board with a coverage gap is REJECTED before any solve (governance: don't
    attempt work the squad-as-composed cannot cover). HONEST: coverage is necessary, not sufficient -- it
    does not promise the CSP is solvable, only that no board cell is unreachable by the roster's shapes."""
    roles = roles or SQUAD
    pairs = geometric_pairs(roles)
    coverage = cover_regions(board, pairs)
    targets = [op.id for op in board.operators if op.fixed is None]  # RECON: the unknowns
    roster = {r.name: ("%d ops" % len(r.legal_operations())) for r in roles}
    reg = region if region is not None else board_region(board)
    gate = coverage_gate(roles, reg)
    if require_coverage and not gate.covered:
        # the squad's pieces leave a hole on this board's layout -> reject up front, do not solve
        return SquadResult(False, {}, 0, [], targets, pairs, coverage, roster, gate, rejected=True)
    res: SolveResult = solve(board)  # CODER fills; CHECK's repair = the CBJ jumps inside the solve
    return SquadResult(
        solved=res.solved,
        assignment=res.assignment,
        energy=res.energy,
        jumps=res.jumps,
        targets=targets,
        pairs=pairs,
        coverage=coverage,
        roster=roster,
        gate=gate,
        squad_energy=solve_energy(board, res.jumps),  # the Landauer cost of this solve's CBJ re-decisions
    )


# ---------------------------------------------------------------------------
# MULTIDIMENSIONAL TRIANGULATION: make "coverage" rigorous. The differentiated roles' profiles are a BASIS;
# the squad can LOCALIZE a target in concept space only inside the subspace its profiles SPAN. The null
# space names the BLIND directions (the doc's "absence is information" -- the tongues no member senses); the
# condition number is the geometric dilution of precision (GDOP) -- low = a crisp fix, infinite = a
# degenerate "all-clones" squad that cannot triangulate. This is the Bad-Batch claim made measurable:
# DIFFERENTIATION is what makes the fix possible -- a squad of identical clones is rank-deficient and blind.
#
# HONEST: this is linear least-squares localization (the backbone under multilateration / GPS). It
# QUANTIFIES the squad's coverage; it does NOT add solving power to the CSP (coding_board.solve still does
# the work). "Reading" is an abstract projection r_i = <profile_i, target>, not a physical range.
# ---------------------------------------------------------------------------
_RANK_TOL = 1e-9


@dataclass
class Coverage:
    """How much of concept space a differentiated roster can resolve. `rank` dims are seeable;
    `blind_directions` (the null-space basis) are not; `dilution` is the geometric dilution of precision
    (condition number over the nonzero singular values, inf when rank < dim)."""

    dim: int
    rank: int
    blind_directions: Tuple[Tuple[float, ...], ...]
    dilution: float
    full_rank: bool


@dataclass
class Triangulation:
    target_estimate: Tuple[float, ...]  # the min-norm point in the squad's span consistent with the readings
    reading_residual: float  # ||B x_hat - r||: ~0 == the readings agree on a single point
    coverage: Coverage  # the roster's resolving power (whatever lay in blind_directions is unrecoverable)


def squad_basis(roles: List[Role]) -> np.ndarray:
    """The squad's basis matrix B: row i is role i's profile (its specialty direction in concept space)."""
    return np.array([r.profile for r in roles], dtype=float)


def _coverage(B: np.ndarray) -> Coverage:
    dim = B.shape[1]
    _u, s, vt = np.linalg.svd(B)  # right-singular vectors past the rank span the null (blind) space
    rank = int((s > _RANK_TOL).sum())
    blind = tuple(tuple(round(float(x), 12) for x in vt[i]) for i in range(rank, dim))
    nonzero = s[s > _RANK_TOL]
    # dilution is the IN-SPAN geometric dilution of precision: the condition number over the resolvable
    # directions. It catches weak differentiation even at full rank (nearly-collinear members -> large
    # dilution -> a sloppy fix). Coverage GAPS (blind directions) are reported separately via rank/blind.
    if nonzero.size == 0:
        dilution = float("inf")
    elif nonzero.size == 1:
        dilution = 1.0  # a single resolvable axis is trivially well-conditioned within its 1-D span
    else:
        dilution = float(nonzero[0] / nonzero[-1])
    return Coverage(dim=dim, rank=rank, blind_directions=blind, dilution=dilution, full_rank=(rank == dim))


def squad_coverage(roles: List[Role]) -> Coverage:
    """The rigorous form of cover_regions: how many concept dimensions this differentiated roster can
    resolve (rank), which directions are BLIND (null space), and the dilution of precision. A roster of
    clones is rank-1 and blind everywhere else; a diverse roster spans more of the space."""
    return _coverage(squad_basis(roles))


def triangulate(roles: List[Role], readings: Sequence[float]) -> Triangulation:
    """Localize a target in concept space from each role's READING -- the target's coordinate along that
    role's specialty axis, r_i = <profile_i, target>. Least-squares fuse: x_hat = lstsq(B, r) (the min-norm
    point in the squad's span). A DIFFERENTIATED roster pins the target inside its span; whatever component
    of the true target lies in the squad's blind directions is unrecoverable (that is the coverage gap)."""
    B = squad_basis(roles)
    r = np.asarray(list(readings), dtype=float)
    x_hat, *_ = np.linalg.lstsq(B, r, rcond=None)
    residual = float(np.linalg.norm(B @ x_hat - r))
    return Triangulation(
        target_estimate=tuple(round(float(v), 12) for v in x_hat),
        reading_residual=residual,
        coverage=_coverage(B),
    )


def robust_triangulate(roles: List[Role], readings: Sequence[float]) -> Tuple[Triangulation, Optional[str]]:
    """One member may report a corrupted reading (a traitor). Least-trimmed fuse: drop the single member
    whose removal most reduces the residual, then triangulate with the rest. A differentiated squad still
    localizes with one bad bearing (BFT-flavoured). Returns (triangulation, dropped_role_name); dropped is
    None when no single drop materially helps (no traitor).

    Identifiability needs a TWO-member margin (n >= rank + 2): after dropping the traitor the rest must stay
    OVERDETERMINED, else every leave-one-out fit is exact (residual 0) and the outlier cannot be told apart."""
    readings = list(readings)
    base = triangulate(roles, readings)
    if len(roles) <= base.coverage.rank + 1:
        return base, None  # < rank+2 members -> dropping one leaves an exact fit; a traitor is unidentifiable
    best: Optional[Tuple[Triangulation, str]] = None
    for k in range(len(roles)):
        kept_roles = roles[:k] + roles[k + 1 :]
        if squad_coverage(kept_roles).rank < base.coverage.rank:
            continue  # dropping this one shrinks the span -> the fit underdetermines and residual lies
        kept_readings = readings[:k] + readings[k + 1 :]
        t = triangulate(kept_roles, kept_readings)
        if best is None or t.reading_residual < best[0].reading_residual:
            best = (t, roles[k].name)
    if best is not None and best[0].reading_residual < base.reading_residual - 1e-6:
        return best  # dropping that member materially cleaned the fit -> it was the traitor
    return base, None


# ---------------------------------------------------------------------------
# ROLE -> PIECE binding + the COVERAGE GATE. Each differentiated role carries a distinct geometric PIECE
# (squad_puzzle), so the squad literally COVERS a board with its shapes. This makes cover_regions rigorous:
# the gate reports the cells NO role-piece can reach (the coverage gap / blind spots) BEFORE a solve is
# attempted -- the governance form of "absence is information". A clone roster (one shape) leaves gaps a
# differentiated roster covers. HONEST: reachability is NECESSARY, not sufficient -- a gap-free board can
# still be untileable (parity); the gate flags structural gaps, it does not promise a solve.
# ---------------------------------------------------------------------------
ROLE_PIECES: Dict[str, Piece] = {
    "ARCHITECT": SQUARE,  # the 2x2 frame -- big footprint, no thin reach
    "RECON": I_TROMINO,  # the long scout
    "CODER": T_TETRO,  # the worker
    "CHECK": L_TROMINO,  # the bent checker
    "OPTIMIZER": DOMINO,  # the tightener -- reaches 1-wide seams the frame cannot
}


def squad_pieces(roles: List[Role]) -> List[Piece]:
    """The geometric piece each role carries (its non-standard value). Unknown roles fall back to a domino."""
    return [ROLE_PIECES.get(r.name, DOMINO) for r in roles]


@dataclass
class CoverageGate:
    covered: bool  # every board cell is reachable by SOME role-piece (no holes)
    holes: Tuple[Cell, ...]  # cells no role-piece can reach -- the coverage gap (the blind spots)
    reachable: int  # how many board cells the role-squad's shapes can reach
    total: int  # board cell count


def coverage_gate(roles: List[Role], region) -> CoverageGate:
    """Can the differentiated role-squad COVER this board with its shapes? Reports the holes (cells no role-
    piece can reach) -- the rigorous form of cover_regions and a governance pre-check: a board with holes for
    the current roster has a structural blind spot (recompose the squad, or reject the board). Necessary, not
    sufficient: no holes does not guarantee an exact tiling (parity can still block it)."""
    pieces = squad_pieces(roles)
    h = holes(region, pieces)
    return CoverageGate(
        covered=(len(h) == 0), holes=h, reachable=len(coverable_cells(region, pieces)), total=len(region)
    )


def demo() -> Dict[str, object]:
    cov = squad_coverage(SQUAD)  # 5 differentiated roles in 6-D tongue space

    # add a 6th differentiated role to close the structural blind spot (full rank)
    sixth = Role("SCOUT2", "cover the remaining tongue", None, (0.1, 0.1, 0.1, 0.1, 0.2, 1.0))
    cov6 = squad_coverage(SQUAD + [sixth])

    # a degenerate "all clones" squad: five copies of one role -> rank 1, blind in the other 5 dims
    clones = [SQUAD[0]] * 5
    cov_clone = squad_coverage(clones)

    # localize a target that lies in the squad's span: readings are exact, residual ~0
    B = squad_basis(SQUAD)
    true_in_span = (B[0] + 0.5 * B[2] - 0.3 * B[4]).tolist()  # a combination of role directions -> in span
    readings = (B @ np.array(true_in_span)).tolist()
    tri = triangulate(SQUAD, readings)
    recovered = np.allclose(B @ np.array(tri.target_estimate), readings, atol=1e-9)

    # the role-squad COVERS a board with its differentiated pieces; a clone roster leaves a coverage gap
    from .squad_puzzle import rect

    board = frozenset(rect(2, 2)) | {(0, 2), (0, 3)}  # a 2x2 block + a 1-wide arm of 2 cells
    diff_gate = coverage_gate(SQUAD, board)
    clone_gate = coverage_gate([SQUAD[0]] * 5, board)  # all ARCHITECT (the 2x2 frame) -> cannot reach the arm

    # the bijective-time Landauer ledger meets the squad solve: a clean (forward-only) solve pays 0 J; a solve
    # that CBJ-jumps-back pays the Landauer floor for each irreversible re-decision (the arrow's heat)
    clean_e = solve_with_squad(
        Board([Operator("a", gate_names(TRANSFORM)), Operator("b", gate_names(TRANSFORM))], [])
    ).squad_energy
    conflict_e = solve_with_squad(
        Board(
            [
                Operator("a", ("A", "B"), region="r"),
                Operator("b", ("B",), region="r", fixed="B"),
                Operator("c", ("A",), region="r"),
            ],
            [region_must_agree],
        )
    ).squad_energy

    return {
        "squad_resolves_5_of_6_one_blind_tongue": (
            cov.rank == 5 and not cov.full_rank and len(cov.blind_directions) == 1
        ),
        "sixth_role_closes_the_blind_spot": cov6.full_rank,
        "clone_squad_collapses_to_rank_1_blind_in_5": (cov_clone.rank == 1 and len(cov_clone.blind_directions) == 5),
        "differentiated_squad_localizes_in_span": recovered and tri.reading_residual < 1e-9,
        "role_squad_covers_the_board_no_holes": diff_gate.covered,
        "clone_roster_leaves_a_coverage_gap": (not clone_gate.covered) and len(clone_gate.holes) == 2,
        "clean_solve_is_energy_free": clean_e.overwrites == 0 and clean_e.irreversible_joules == 0.0,
        "backtracking_solve_pays_landauer": conflict_e.overwrites >= 1 and conflict_e.irreversible_joules > 0.0,
        "_cov": cov,
        "_cov_clone": cov_clone,
        "_clone_gate": clone_gate,
        "_clean_e": clean_e,
        "_conflict_e": conflict_e,
    }


def main() -> int:
    d = demo()
    cov, covc = d["_cov"], d["_cov_clone"]
    print("CODING SQUAD -- multidimensional triangulation (differentiation is load-bearing, measured)")
    print(
        "  5 differentiated roles in %d-D tongue space: rank %d -> %d blind tongue(s), in-span dilution %.2f"
        % (cov.dim, cov.rank, cov.dim - cov.rank, cov.dilution)
    )
    print(
        "  add a 6th differentiated role -> full rank (no blind spot)      : %s" % d["sixth_role_closes_the_blind_spot"]
    )
    print(
        "  clone squad (5x the SAME role): rank %d, blind in %d dims         : %s"
        % (covc.rank, len(covc.blind_directions), d["clone_squad_collapses_to_rank_1_blind_in_5"])
    )
    print(
        "  differentiated squad localizes a target in its span (residual~0): %s"
        % d["differentiated_squad_localizes_in_span"]
    )
    print("  => a diverse squad triangulates what a squad of clones cannot. Coverage = rank; blind = null space.")
    cg = d["_clone_gate"]
    print("  --- role -> piece coverage gate (the squad tiles a board with its shapes) ---")
    print(
        "  role-squad's differentiated pieces cover the board (no holes)   : %s"
        % d["role_squad_covers_the_board_no_holes"]
    )
    print(
        "  clone roster (all ARCHITECT/2x2) leaves a coverage gap at %s : %s"
        % (cg.holes, d["clone_roster_leaves_a_coverage_gap"])
    )
    print("  => holes = the cells no role-piece can reach (governance pre-check; necessary, not sufficient).")
    ce, qe = d["_clean_e"], d["_conflict_e"]
    print("  --- the Landauer ledger meets the squad solve (energy = the CBJ re-decisions) ---")
    print(
        "  clean forward-only solve: %d re-decision(s) -> %.3e J (erases nothing, free)"
        % (ce.overwrites, ce.irreversible_joules)
    )
    print(
        "  backtracking solve: %d CBJ re-decision(s) -> %.3e J (the arrow's heat; reversible undo-tape = 0 J)"
        % (qe.overwrites, qe.irreversible_joules)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
