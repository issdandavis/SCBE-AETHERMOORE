"""coding_board: code-as-a-board CSP -- the substrate for Issac's all-at-once coding vision.

A task is a BOARD of OPERATORS (cells / places). Each operator is assigned an OPERATION (a value / command
/ token / reversible gate) drawn from its OWN narrowed legal-operation vector (the operator's DOMAIN = the
alphabet of legal+verified moves = governance by construction). Operator and operation are DECOUPLED: the
cell is a variable, the operation is its value. The whole board is solved ALL AT ONCE as a Constraint
Satisfaction Problem -- the admissible assignment is the global ENERGY MINIMUM (energy = number of
constraint violations; the ground state has energy 0), not a left-to-right time-evolution (Adlam's
Sudoku move). Constraints are:

  * SPATIAL (relations among operators / cells -- spatial non-locality): e.g. cells in a region must be
    DISTINCT (sudoku row) or must AGREE (an interface contract);
  * TEMPORAL (a later operation in the solve/program order conflicts with an earlier one -- temporal
    non-locality, the same idea as observer_dynamics): e.g. an operation must not appear after a forbidden
    predecessor.

Repair uses CONFLICT-DIRECTED BACKJUMPING: on a dead end, jump back to the EARLIEST operator implicated in
the conflict (the root cause), not one step back. Reuses observer_dynamics.Violation so the conflict set +
its earliest_index ARE the jump-back target.

HONEST: the solver is textbook CSP (backtracking + forward-checking domain narrowing + conflict-directed
backjumping). The algorithm is not new. The contribution is the FRAMING made executable -- operator !=
operation, a governed legal vector per operator, spatial + temporal constraints unified as one energy
landscape, CBJ root-cause repair -- the substrate for "every token a governed operation on a board".
Consistency != correctness: a solved board is internally consistent, not a guaranteed-correct program.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .observer_dynamics import Violation  # reuse the conflict-set type (rule, message, involved indices)

Assignment = Dict[str, str]  # operator id -> operation


@dataclass
class Operator:
    """A cell / place on the board. `domain` is the narrowed legal-operation vector (the moves allowed
    here); `region` groups operators for spatial constraints; `fixed` locks a KNOWN operation."""

    id: str
    domain: Tuple[str, ...]
    region: Optional[str] = None
    fixed: Optional[str] = None


# a constraint maps (board, assignment-so-far) -> violations; `involved` lists operator INDICES
Constraint = Callable[["Board", Assignment], List[Violation]]


@dataclass
class Board:
    operators: List[Operator]
    constraints: List[Constraint] = field(default_factory=list)

    def index_of(self, oid: str) -> int:
        for i, op in enumerate(self.operators):
            if op.id == oid:
                return i
        raise KeyError(oid)


# ---------------------------------------------------------------------------
# Example constraints (the board's rules)
# ---------------------------------------------------------------------------
def all_distinct_in_region(board: Board, assign: Assignment) -> List[Violation]:
    """SPATIAL: operators sharing a region must hold DISTINCT operations (the sudoku 'no repeat' rule)."""
    out: List[Violation] = []
    by_region: Dict[str, List[int]] = {}
    for i, op in enumerate(board.operators):
        if op.region and op.id in assign:
            by_region.setdefault(op.region, []).append(i)
    for region, idxs in by_region.items():
        seen: Dict[str, int] = {}
        for i in idxs:
            val = assign[board.operators[i].id]
            if val in seen:
                out.append(Violation("all_distinct_in_region", "region %r repeats %r" % (region, val), [seen[val], i]))
            else:
                seen[val] = i
    return out


def region_must_agree(board: Board, assign: Assignment) -> List[Violation]:
    """SPATIAL: operators sharing a region must hold the SAME operation (an interface/contract must match)."""
    out: List[Violation] = []
    by_region: Dict[str, List[int]] = {}
    for i, op in enumerate(board.operators):
        if op.region and op.id in assign:
            by_region.setdefault(op.region, []).append(i)
    for region, idxs in by_region.items():
        vals = {assign[board.operators[i].id] for i in idxs}
        if len(vals) > 1:
            out.append(Violation("region_must_agree", "region %r disagrees: %s" % (region, sorted(vals)), idxs))
    return out


def forbidden_after(predecessor: str, operation: str) -> Constraint:
    """TEMPORAL: `operation` must not appear at a later operator than `predecessor` (a sequence rule over
    the board/program order). Mirrors observer_dynamics' across-time non-locality."""

    def constraint(board: Board, assign: Assignment) -> List[Violation]:
        pred_idx = [i for i, op in enumerate(board.operators) if assign.get(op.id) == predecessor]
        if not pred_idx:
            return []
        first_pred = min(pred_idx)
        return [
            Violation("forbidden_after", "%r appears after %r" % (operation, predecessor), [first_pred, i])
            for i, op in enumerate(board.operators)
            if i > first_pred and assign.get(op.id) == operation
        ]

    return constraint


# ---------------------------------------------------------------------------
# Energy + domain narrowing (the non-linear, all-at-once view)
# ---------------------------------------------------------------------------
def violations(board: Board, assign: Assignment) -> List[Violation]:
    out: List[Violation] = []
    for c in board.constraints:
        out.extend(c(board, assign))
    return out


def energy(board: Board, assign: Assignment) -> int:
    """The board's energy = number of constraint violations. Ground state (energy 0) == admissible solve.
    This is the all-at-once objective: minimize global violations, not evolve forward in time."""
    return len(violations(board, assign))


def narrowed_domains(board: Board, assign: Assignment) -> Dict[str, Tuple[str, ...]]:
    """Forward-checking: prune each UNassigned operator's legal vector to operations that do not, on their
    own, violate a constraint against the current partial assignment (using the knowns to narrow the
    unknowns -- Issac's 'narrowed vector per operator using the knowns')."""
    out: Dict[str, Tuple[str, ...]] = {}
    for op in board.operators:
        if op.id in assign:
            out[op.id] = (assign[op.id],)
            continue
        legal = []
        for val in (op.fixed,) if op.fixed is not None else op.domain:
            trial = dict(assign)
            trial[op.id] = val
            if not any(board.index_of(op.id) in v.involved for v in violations(board, trial)):
                legal.append(val)
        out[op.id] = tuple(legal)
    return out


# ---------------------------------------------------------------------------
# Solve: backtracking + forward-checking + Conflict-Directed Backjumping
# ---------------------------------------------------------------------------
@dataclass
class SolveResult:
    solved: bool
    assignment: Assignment
    energy: int
    backtracks: int
    jumps: List[int]  # CBJ jump-back targets taken (operator indices) -- root causes, not one-step


def jumpback_target(board: Board, assign: Assignment) -> Optional[int]:
    """The CBJ target: the earliest operator index across all current conflict sets (root cause)."""
    vs = violations(board, assign)
    return min((v.earliest_index for v in vs), default=None)


def solve(board: Board, max_backtracks: int = 100000) -> SolveResult:
    """Solve the board by backtracking with forward-checking + conflict-directed backjumping. Assigns
    operators in order; on a dead end (an operator whose narrowed domain is empty) jumps back to the
    EARLIEST operator implicated in the conflict, not one step. Returns the ground-state assignment
    (energy 0) or the best partial with its residual energy."""
    ops = board.operators
    n = len(ops)
    assign: Assignment = {op.id: op.fixed for op in ops if op.fixed is not None}
    cursor = {op.id: 0 for op in ops}  # next domain index to try, per operator
    jumps: List[int] = []
    backtracks = 0
    pos = 0
    # skip fixed operators at the front of the order is unnecessary; we just try their single value
    while 0 <= pos < n:
        op = ops[pos]
        if op.fixed is not None:
            assign[op.id] = op.fixed
            pos += 1
            continue
        dom = narrowed_domains(board, {k: v for k, v in assign.items() if board.index_of(k) < pos})[op.id]
        placed = False
        while cursor[op.id] < len(dom):
            val = dom[cursor[op.id]]
            cursor[op.id] += 1
            assign[op.id] = val
            if not any(pos in v.involved for v in violations(board, assign)):
                placed = True
                break
            assign.pop(op.id, None)
        if placed:
            pos += 1
        else:
            backtracks += 1
            if backtracks > max_backtracks:
                break
            assign.pop(op.id, None)
            cursor[op.id] = 0  # reset this operator's choices for the next visit
            # CBJ: jump to the earliest operator implicated in a conflict at this dead end, else step back
            target = jumpback_target(board, {**assign, op.id: (dom[0] if dom else "")})
            jump_to = target if (target is not None and target < pos) else pos - 1
            jumps.append(jump_to)
            # undo everything after the jump target
            for k in range(jump_to + 1, pos + 1):
                assign.pop(ops[k].id, None)
                cursor[ops[k].id] = 0
            pos = jump_to
    e = energy(board, assign)
    return SolveResult(
        solved=(pos == n and e == 0), assignment=dict(assign), energy=e, backtracks=backtracks, jumps=jumps
    )
