"""coding_board_gates: bind the REVERSIBLE gate alphabet to the coding board (option A).

coding_board treats operations as opaque strings. This makes the operation SET the bijective gates from
reversible_circuit (the #2566 thread: gates you run forward AND uncompute), so an ASSIGNED board IS a
reversible circuit:

    * assigning operations to operators builds a gate sequence (operator order = circuit order);
    * running it forward is the computation;
    * the CBJ jump-back is Bennett UNCOMPUTE -- rewind the gates AFTER the conflict back to a clean
      checkpoint, erasing nothing (run then unrun is the identity).

This realises "every token a reversible gate": the cube_token.CubeToken is the bijective object the vision
is built on (rotate to any face, rotate back -- no information lost); here the board's alphabet is the
register-level bijections that have a concrete forward/inverse, so jump-back == uncompute is executable.

DESIGNED FOR THE ROLE SQUAD (C): every gate carries a ROLE tag -- TRANSFORM gates are the fillers' moves
(they do work on the registers); CHECK gates are the constraint-model's moves (identity-like / verify).
A later differentiated team can be handed role-scoped sub-alphabets (gate_names(role=...)) without
touching this layer.

HONEST: reversible CLASSICAL computing (see reversible_circuit) -- reversibility + uncompute, NOT quantum
superposition/interference/entanglement. The board solve is still textbook CSP; this only makes its
operations invertible, so the jump-back is a true uncompute rather than a discard.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .coding_board import Assignment, Board
from .reversible_circuit import MASK, Gate, Reg, run, unrun, xor_into

# roles, designed so the future squad can take role-scoped sub-alphabets
TRANSFORM = "transform"  # fillers' moves: they change the register state
CHECK = "check"  # constraint-model's moves: identity-like / verification


def _identity() -> Gate:
    return Gate("id", lambda s: dict(s), lambda s: dict(s))


def _add_k(reg: str, k: int) -> Gate:
    """reg += k (mod 2^64) forward; reg -= k inverse -- a reversible affine step."""

    def fwd(s: Reg) -> Reg:
        r = dict(s)
        r[reg] = (r.get(reg, 0) + k) & MASK
        return r

    def inv(s: Reg) -> Reg:
        r = dict(s)
        r[reg] = (r.get(reg, 0) - k) & MASK
        return r

    return Gate("add_%s_%d" % (reg, k), fwd, inv)


# the reversible operation alphabet (the cube-token gate set), each tagged with the role it serves
GATE_ALPHABET: Dict[str, Tuple[Gate, str]] = {
    "xor_a_b": (xor_into("a", "b"), TRANSFORM),
    "xor_b_a": (xor_into("b", "a"), TRANSFORM),
    "add_a_1": (_add_k("a", 1), TRANSFORM),
    "add_b_1": (_add_k("b", 1), TRANSFORM),
    "id": (_identity(), CHECK),
}


def gate_names(role: Optional[str] = None) -> Tuple[str, ...]:
    """The legal-operation vector for a board operator -- optionally scoped to a role (for the squad)."""
    return tuple(n for n, (_g, r) in GATE_ALPHABET.items() if role is None or r == role)


def gate_role(name: str) -> str:
    return GATE_ALPHABET[name][1]


def circuit_from_board(board: Board, assign: Assignment) -> List[Gate]:
    """Turn an assigned board into a reversible circuit: the gate at each operator, in operator order."""
    return [GATE_ALPHABET[assign[op.id]][0] for op in board.operators if assign.get(op.id) in GATE_ALPHABET]


def run_board(reg: Reg, board: Board, assign: Assignment) -> Reg:
    """Run the board's circuit FORWARD over the register state."""
    return run(reg, circuit_from_board(board, assign))


def uncompute_after(reg: Reg, board: Board, assign: Assignment, checkpoint: int) -> Reg:
    """Bennett uncompute == the CBJ jump-back at the primitive level: rewind the gates AFTER `checkpoint`
    (an operator index), restoring the register to its state at the checkpoint -- erasing nothing. This is
    `unrun` applied to the tail of the circuit, so it is exactly the inverse of having run those gates."""
    gates = circuit_from_board(board, assign)
    return unrun(reg, gates[checkpoint + 1 :])


def jumpback_is_uncompute(reg: Reg, board: Board, assign: Assignment, checkpoint: int) -> bool:
    """Proof, for a given board/assignment, that jumping back to `checkpoint` is a true uncompute: running
    the whole circuit forward then uncomputing the tail equals running only up to the checkpoint."""
    gates = circuit_from_board(board, assign)
    full_then_back = uncompute_after(run_board(dict(reg), board, assign), board, assign, checkpoint)
    only_to_checkpoint = run(dict(reg), gates[: checkpoint + 1])
    return full_then_back == only_to_checkpoint
