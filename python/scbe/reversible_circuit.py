"""reversible_circuit: reversible computing = the structural model of a QUANTUM circuit (Issac's point).

Quantum gates are UNITARY = invertible = bijective, so a quantum circuit (everything except measurement) is
REVERSIBLE -- the bijective clock of time_machine, generalized to a SEQUENCE of gates. Superposition is the
"all at once"; MEASUREMENT is the only irreversible, information-erasing step (the arrow). This models the
REVERSIBLE STRUCTURE: gates you can run forward and back, and Bennett UNCOMPUTATION -- compute a result,
copy it out, then UNCOMPUTE the scratch back to clean, erasing NOTHING. Uncomputation is the core technique
that lets quantum / low-energy reversible computers avoid the heat (Landauer) and decoherence of erasing
information; here it is just forward-then-rewind on bijective gates.

HONEST BOUNDARY: this is reversible CLASSICAL computing. It captures quantum's REVERSIBILITY and
UNCOMPUTATION faithfully, but NOT superposition amplitudes, interference, or entanglement (those need a
complex state vector). It is the substrate quantum needs, not the quantum magic -- do not call it a quantum
computer. The bijective gate here is the same splitmix64 used as the time-step in time_machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from .elastic_bijective_hash import splitmix64

MASK = (1 << 64) - 1
Reg = Dict[str, int]


@dataclass
class Gate:
    """A reversible gate: a bijection on the register file, with its inverse. (forward, inverse) are the
    two directions of the same unitary -- run either way, no information lost."""

    name: str
    fwd: Callable[[Reg], Reg]
    inv: Callable[[Reg], Reg]


def xor_into(dst: str, src: str) -> Gate:
    """CNOT-like: dst ^= src. Self-inverse (applying it twice restores dst) -- the reversible 'copy'."""

    def op(s: Reg) -> Reg:
        r = dict(s)
        r[dst] = r[dst] ^ r[src]
        return r

    return Gate("xor %s<-%s" % (dst, src), op, op)


def hash_into(dst: str, src: str) -> Gate:
    """dst ^= splitmix64(src), with src PRESERVED. Self-inverse (XOR), so it uncomputes by re-application --
    the reversible 'compute a function into a scratch register'. The bijective hash is the gate's logic."""

    def op(s: Reg) -> Reg:
        r = dict(s)
        r[dst] = r[dst] ^ (splitmix64(r[src]) & MASK)
        return r

    return Gate("hash %s<-h(%s)" % (dst, src), op, op)


def run(state: Reg, gates: List[Gate]) -> Reg:
    for g in gates:
        state = g.fwd(state)
    return state


def unrun(state: Reg, gates: List[Gate]) -> Reg:
    """Run the circuit BACKWARD: inverses, in reverse order. run then unrun is the identity (reversible)."""
    for g in reversed(gates):
        state = g.inv(state)
    return state


def bennett_uncompute(x: int) -> Reg:
    """The core quantum/reversible move: compute h(x) into a scratch register, COPY it to an output, then
    UNCOMPUTE the scratch back to 0 -- nothing erased. End state: x preserved, scratch CLEAN (0), out = h(x).
    This is why quantum avoids garbage qubits and why reversible computing avoids Landauer heat."""
    compute = [hash_into("scratch", "x")]
    s: Reg = {"x": x, "scratch": 0, "out": 0}
    s = run(s, compute)  # scratch = h(x)
    s = xor_into("out", "scratch").fwd(s)  # copy the answer out (reversibly)
    s = unrun(s, compute)  # UNCOMPUTE the scratch -> 0, leaving out = h(x)
    return s


def demo() -> Dict[str, object]:
    x = 1234567
    expected = splitmix64(x) & MASK

    # 1. a circuit run forward then backward is the identity (a reversible / unitary process)
    gates = [hash_into("scratch", "x"), xor_into("out", "scratch"), hash_into("scratch", "x")]
    start = {"x": x, "scratch": 0, "out": 0}
    there = run(dict(start), gates)
    roundtrip_identity = unrun(dict(there), gates) == start

    # 2. Bennett uncomputation: scratch cleaned, output kept, nothing erased
    end = bennett_uncompute(x)
    clean_scratch = end["scratch"] == 0
    answer_kept = end["out"] == expected
    input_preserved = end["x"] == x

    return {
        "circuit_run_then_unrun_is_identity": roundtrip_identity,
        "uncompute_cleans_scratch": clean_scratch,
        "uncompute_keeps_answer": answer_kept,
        "input_preserved": input_preserved,
    }


def main() -> int:
    d = demo()
    print("REVERSIBLE CIRCUIT -- the reversible STRUCTURE of a quantum circuit (no superposition; honest)")
    print("  run forward then backward == identity (unitary/reversible): %s" % d["circuit_run_then_unrun_is_identity"])
    print("  Bennett uncompute -> scratch back to CLEAN 0            : %s" % d["uncompute_cleans_scratch"])
    print(
        "  ...output keeps the answer h(x), input preserved        : %s, %s"
        % (d["uncompute_keeps_answer"], d["input_preserved"])
    )
    print("  => computed a result and erased NOTHING (no Landauer cost, no garbage qubit).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
