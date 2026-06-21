"""reversible_circuit: the reversible STRUCTURE of a quantum circuit (unitary = bijective), honest scope.

These pin: a reversible circuit run forward then backward is the IDENTITY (no information lost -- the
unitary property), the reversible gates are their own inverses, and Bennett UNCOMPUTATION computes a result
while erasing nothing (scratch returns to clean 0, the answer is kept). Plus the honest arrow: without
uncomputing, the scratch is left dirty -- the information you'd have to erase (Landauer), which is the
irreversible step.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.elastic_bijective_hash import splitmix64  # noqa: E402
from python.scbe.reversible_circuit import (  # noqa: E402
    MASK,
    REG_BITS,
    EnergyLedger,
    bennett_uncompute,
    demo,
    energy_compare,
    hash_into,
    landauer_joules,
    run,
    unrun,
    xor_into,
)


def test_reversible_circuit_run_then_unrun_is_identity():
    gates = [hash_into("scratch", "x"), xor_into("out", "scratch"), hash_into("scratch", "x")]
    for x in (0, 1, 42, 2**50 + 9):
        start = {"x": x, "scratch": 0, "out": 0}
        end = run(dict(start), gates)
        assert unrun(dict(end), gates) == start  # forward then backward == identity (unitary)


def test_reversible_gates_are_their_own_inverse():
    g = xor_into("a", "b")
    s = {"a": 5, "b": 3}
    assert g.fwd(g.fwd(dict(s))) == s  # apply twice -> identity
    h = hash_into("scratch", "x")
    s2 = {"scratch": 0, "x": 99}
    assert h.fwd(h.fwd(dict(s2))) == s2


def test_bennett_uncompute_cleans_scratch_and_keeps_the_answer():
    x = 1234567
    end = bennett_uncompute(x)
    assert end["scratch"] == 0  # scratch uncomputed back to clean -- nothing left to erase
    assert end["out"] == (splitmix64(x) & MASK)  # the answer was copied out before uncomputing
    assert end["x"] == x  # input preserved -- the whole thing is reversible


def test_without_uncompute_the_scratch_is_dirty_the_arrow():
    # the honest contrast: compute + copy but DON'T uncompute -> scratch still holds h(x). That residual is
    # the information you'd have to ERASE to reset, and erasing it is the only irreversible (arrow) step.
    x = 42
    compute = [hash_into("scratch", "x")]
    s = run({"x": x, "scratch": 0, "out": 0}, compute)
    s = xor_into("out", "scratch").fwd(s)
    assert s["scratch"] != 0  # left dirty -- no free lunch unless you uncompute


def test_landauer_floor_is_the_known_constant():
    # one bit erased at 300K costs k*T*ln2 ~= 2.87e-21 J -- the textbook Landauer floor
    j = landauer_joules(1, 300.0)
    assert abs(j - 2.8e-21) < 0.2e-21  # ~2.87e-21 J
    assert landauer_joules(0) == 0.0  # erasing nothing costs nothing
    assert landauer_joules(64) == 64 * landauer_joules(1)  # linear in bits erased


def test_energy_ledger_reversible_is_free_erase_pays():
    led = EnergyLedger()
    led.reversible("gate a").reversible("gate b")
    assert led.bits_erased == 0 and led.joules() == 0.0  # bijective gates: free
    led.erase("reset reg", REG_BITS)
    assert led.bits_erased == REG_BITS and led.joules() > 0.0  # the irreversible step pays


def test_energy_compare_forward_pays_reversible_recovers():
    # the load-bearing result: same end state both ways, but force-erase pays the Landauer floor for the
    # whole 64-bit scratch while uncomputing pays exactly zero -- the energy difference is the recovery
    for x in (0, 1, 42, 1234567, 2**50 + 9):
        e = energy_compare(x)
        assert e["same_result"] is True  # scratch=0, out=h(x) reached identically both ways
        assert e["forward_only_bits_erased"] == REG_BITS  # force-clear erases the full register
        assert e["reversible_bits_erased"] == 0  # uncomputation erases nothing
        assert e["reversible_joules"] == 0.0  # ...so it is thermodynamically free
        assert e["forward_only_joules"] > 0.0  # ...while the dissipating path pays heat
        assert e["energy_recovered_joules"] == e["forward_only_joules"]  # all of it recovered


def test_demo_all_true():
    d = demo()
    assert all(v for k, v in d.items() if not k.startswith("_"))  # skip the _energy detail dict
