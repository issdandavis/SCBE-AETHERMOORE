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

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .elastic_bijective_hash import splitmix64

MASK = (1 << 64) - 1
Reg = Dict[str, int]

# Landauer's principle: erasing ONE bit of information dissipates at least k*T*ln2 of energy as heat, and
# THAT dissipation is the forward arrow. A reversible (bijective) gate erases nothing -> thermodynamically
# free. So the Landauer (ERASURE) component of the energy bill == the bits it irreversibly ERASES, and
# UNCOMPUTING instead of erasing pays that component back to ~0. These constants make it a real number of J.
#
# HONEST SCOPE of the energy claim: reversible_joules==0 is the information-ERASURE (Landauer) floor ONLY.
# It is NOT net-zero total energy: (1) Bennett -- the answer is kept in the `out` register, so clearing it for
# the next computation costs the same bill (the cost is deferred into space, not eliminated); (2) real
# gate-switching/dynamical energy (the splitmix64 mixing, the XORs) is not modeled and on any real device
# dominates k*T*ln2 by orders of magnitude. This models the erasure floor, not a chip's power.
K_BOLTZMANN = 1.380649e-23  # J/K (exact, SI)
ROOM_T_K = 300.0  # K, ~room temperature
REG_BITS = 64  # register WIDTH; a force-clear erases AT MOST this many bits (actual = bit_length of the value)


def landauer_joules(bits_erased: int, temperature_k: float = ROOM_T_K) -> float:
    """The Landauer floor for erasing `bits_erased` bits at temperature T: bits * k*T*ln2 joules."""
    return bits_erased * K_BOLTZMANN * temperature_k * math.log(2)


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


@dataclass
class EnergyLedger:
    """Accounts a computation's THERMODYNAMIC cost by Landauer's principle. Every reversible (bijective) gate
    is recorded at ZERO cost; every irreversible ERASE charges its information-bearing bits. `joules()` is the
    heat the forward arrow costs you -- and a fully reversible (uncomputed) run lands at 0. This makes the
    abstract "energy IS the arrow, reversibility recovers it" point a number you can run."""

    temperature_k: float = ROOM_T_K
    bits_erased: int = 0
    log: List[Tuple[str, int]] = field(default_factory=list)

    def reversible(self, name: str) -> "EnergyLedger":
        """Record a bijective gate: erases nothing, so it is thermodynamically free."""
        self.log.append((name, 0))
        return self

    def erase(self, name: str, bits: int) -> "EnergyLedger":
        """Record an irreversible erase of `bits` information-bearing bits: charges the Landauer floor."""
        self.bits_erased += bits
        self.log.append((name, bits))
        return self

    def joules(self) -> float:
        return landauer_joules(self.bits_erased, self.temperature_k)


def run_metered(state: Reg, gates: List[Gate], ledger: EnergyLedger) -> Reg:
    """run(), but record every gate on the ledger as reversible (free). Reversible computation, billed."""
    for g in gates:
        state = g.fwd(state)
        ledger.reversible(g.name)
    return state


def erase_register(state: Reg, reg: str, ledger: EnergyLedger, bits: Optional[int] = None) -> Reg:
    """The one IRREVERSIBLE move: force `reg` to 0, throwing away the information it held. Charges the ledger
    for the information ACTUALLY erased -- the bit_length of the prior value (0 when it was already 0, up to
    REG_BITS), or `bits` if given explicitly. This is the cost of the arrow; UNCOMPUTING restores 0 for free
    by running the bijective gates backward (run_metered over the inverses). NOTE: clearing a known-zero
    register costs 0 -- erasing information you don't have is free."""
    r = dict(state)
    erased = state[reg].bit_length() if bits is None else bits
    r[reg] = 0
    ledger.erase("erase %s" % reg, erased)
    return r


def energy_compare(x: int) -> Dict[str, object]:
    """The whole point in one number. Compute h(x), copy it out, then CLEAN the scratch two ways:
      (1) forward-only -> FORCE-ERASE the scratch (irreversible): pays bit_length(h(x))*k*T*ln2 (up to REG_BITS;
          0 in the degenerate x=0 case where h(0)=0 -- erasing a zero register erases nothing).
      (2) reversible   -> UNCOMPUTE the scratch (run the gates backward): pays ~0.
    Both end identical (scratch=0, out=h(x)); the difference is the ERASURE (Landauer) energy reversibility
    recovers -- NOT total energy (the answer stays in `out`, Bennett; gate-switching is not modeled)."""
    compute = [hash_into("scratch", "x")]
    expected = splitmix64(x) & MASK

    # (1) forward-only, then force-clear the scratch (the dissipating computer)
    led_a = EnergyLedger()
    a = run_metered({"x": x, "scratch": 0, "out": 0}, compute, led_a)  # scratch = h(x)
    a = xor_into("out", "scratch").fwd(a)
    led_a.reversible("copy out")
    a = erase_register(a, "scratch", led_a)  # IRREVERSIBLE reset -> pays Landauer

    # (2) reversible, then uncompute the scratch (the reversible computer)
    led_b = EnergyLedger()
    b = run_metered({"x": x, "scratch": 0, "out": 0}, compute, led_b)
    b = xor_into("out", "scratch").fwd(b)
    led_b.reversible("copy out")
    b = run_metered(b, list(reversed(compute)), led_b)  # UNCOMPUTE -> scratch back to 0, free

    same_result = a == b and a["scratch"] == 0 and a["out"] == expected
    return {
        "same_result": same_result,
        "forward_only_bits_erased": led_a.bits_erased,
        "forward_only_joules": led_a.joules(),
        "reversible_bits_erased": led_b.bits_erased,
        "reversible_joules": led_b.joules(),
        "energy_recovered_joules": led_a.joules() - led_b.joules(),
    }


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

    # 3. Landauer energy ledger: forward-only ERASES the scratch (pays heat); reversible UNCOMPUTES it (free)
    energy = energy_compare(x)

    return {
        "circuit_run_then_unrun_is_identity": roundtrip_identity,
        "uncompute_cleans_scratch": clean_scratch,
        "uncompute_keeps_answer": answer_kept,
        "input_preserved": input_preserved,
        "energy_same_result_both_ways": energy["same_result"],
        "energy_reversible_is_free": energy["reversible_joules"] == 0.0,
        "energy_forward_only_pays": energy["forward_only_joules"] > 0.0,
        "_energy": energy,
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
    print("  => computed a result while erasing nothing reclaimable (the Landauer ERASURE floor is 0).\n")

    e = d["_energy"]
    print("LANDAUER ENERGY LEDGER -- energy IS the arrow; reversibility recovers it")
    print("  both paths reach the SAME end state (scratch=0, out=h(x))         : %s" % e["same_result"])
    print(
        "  forward-only: ERASE %d-bit scratch -> pays %.3e J (the arrow's heat)"
        % (e["forward_only_bits_erased"], e["forward_only_joules"])
    )
    print(
        "  reversible  : UNCOMPUTE scratch     -> pays %.3e J (%d bits erased)"
        % (e["reversible_joules"], e["reversible_bits_erased"])
    )
    print(
        "  => reversibility recovered %.3e J of ERASURE energy at T=300K (over 1e9 ops, %.3e J)."
        % (e["energy_recovered_joules"], e["energy_recovered_joules"] * 1e9)
    )
    print("  honest: the Landauer FLOOR only -- the answer stays in `out` (Bennett, deferred), gate-switching")
    print("          energy is not modeled, and a real chip dissipates orders of magnitude more. Not net-zero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
