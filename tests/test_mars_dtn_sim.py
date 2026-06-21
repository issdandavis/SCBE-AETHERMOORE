"""mars_dtn_sim: time_machine deterministic replay under simulated NASA-DTN comms conditions.

These prove the load-bearing claim for the "Mars relay" use of the time machine: deterministic
event-sourced replay converges to IDENTICAL state across a delay/disruption-tolerant relay -- through
delay, out-of-order delivery, and duplicate bundles -- as long as every turn eventually arrives. The honest
counter-case is pinned too: with no custody/retransmit, a permanently-lost bundle makes the ends DIVERGE.
(Simulated conditions with NASA-realistic params; not the literal ION-DTN suite.)
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "comms_sim" / "mars_dtn_sim.py"


def _mod():
    spec = importlib.util.spec_from_file_location("_mars_dtn_test", MODULE_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_all_recoverable_conditions_converge_and_permanent_loss_diverges():
    m = _mod()
    for s in m.run_suite():
        if s["scenario"] == "permanent_loss_no_custody":
            assert s["converged"] is False, "permanent loss without custody must diverge"
        else:
            assert s["converged"] is True, s["scenario"]


def test_out_of_order_and_duplicates_still_converge():
    # the core DTN property: arrival order != send order, and duplicate copies arrive, yet the far end
    # rebuilds identical state because it replays in LOGICAL (seq) order and dedups
    m = _mod()
    s = m.run_scenario("dup_reorder", {"dup_prob": 0.5, "reorder": True}, n_turns=30, seed=3)
    assert s["converged"] is True
    assert s["bundles_delivered"] >= s["unique_turns_received"]  # duplicates inflated the delivered count


def test_loss_with_custody_retransmit_converges():
    m = _mod()
    s = m.run_scenario("loss_custody", {"drop_prob": 0.4, "reorder": True, "retransmit": True}, n_turns=30, seed=5)
    assert s["converged"] is True  # dropped bundles retransmit (custody) -> all turns eventually arrive


def test_permanent_loss_without_custody_loses_a_turn():
    m = _mod()
    s = m.run_scenario("perm_loss", {"drop_prob": 0.4, "retransmit": False}, n_turns=30, seed=5)
    assert s["converged"] is False and s["unique_turns_received"] < s["turns"]


def test_simulation_is_reproducible():
    m = _mod()
    assert m.run_suite(seed=11) == m.run_suite(seed=11)  # seeded chaos -> identical runs (the whole point)


def test_mars_delay_is_in_the_realistic_range():
    m = _mod()
    for s in m.run_suite():
        assert m.MARS_MIN_DELAY_S <= s["one_way_delay_s"] <= m.MARS_MAX_DELAY_S
