"""Tests for squad_autonomy_sim -- the role squad as a long-range-autonomous multi-agent mechanism.

Proves: the squad's solved board CONVERGES at the far end under Mars-DTN chaos (delay/reorder/duplicate,
loss-with-custody) because the solve is deterministic + event-sourced; it DIVERGES only under permanent
loss with no custody (the honest counter-case); a delayed CBJ corrective bundle lands on the repaired
state; and the whole sim is seeded/reproducible.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "comms_sim"))

import squad_autonomy_sim as sa  # noqa: E402


def test_squad_converges_under_dtn_chaos_but_not_permanent_loss():
    results = {s["scenario"]: s for s in sa.run_suite()}
    for name in ("instant_link", "mars_far_delay+reorder", "duplicate_bundles", "loss_WITH_custody"):
        assert results[name]["converged"] is True, name  # delay/reorder/dup/custody-loss all converge
    assert results["permanent_loss_NO_custody"]["converged"] is False  # honest counter-case


def test_all_scenarios_match_expected():
    for s in sa.run_suite():
        assert s["converged"] == s["expected"], s["scenario"]


def test_reorder_and_duplicates_reconstruct_identical_to_local():
    board = sa._pipeline_board()
    r = sa.run_link(board, {"reorder": True, "dup_prob": 0.5}, seed=7)
    assert r["recon"] == r["local"]  # the far end rebuilt the exact locally-solved board


def test_delayed_cbj_repair_lands_on_repaired_state():
    board = sa._pipeline_board()
    r = sa.run_link(board, {"reorder": True}, extra=[(999, ("slot0", "id"))])
    assert r["converged"] and r["recon"]["slot0"] == "id"  # late corrective bundle wins by higher seq


def test_seeded_run_is_reproducible():
    a = [x["converged"] for x in sa.run_suite(seed=7)]
    b = [x["converged"] for x in sa.run_suite(seed=7)]
    assert a == b


# ---- grounded in Issac's Mars docs ------------------------------------------------------------
def test_mars_profile_matches_the_documented_numbers():
    # demo/mars-communication.html: 14 min OWLT, 3-round-trip handshake, 0 pre-synced; mars_dtn_sim: 182/1342 s
    assert sa.MARS.owlt_typical_s == 14 * 60
    assert sa.MARS.owlt_min_s == 182 and sa.MARS.owlt_max_s == 1342
    assert sa.MARS.handshake_round_trips == 3 and sa.MARS.squad_handshake_minutes == 0.0
    # the honest gap is recorded, not hidden
    assert "NOT IN ANY DOC" in sa.DOC_SOURCES["loss / dup / reorder / contact_gap rates"]


def test_documented_autonomy_payoff_zero_vs_42_min():
    # the demo's documented handshake: pre-synchronized squad starts at 0; a round-trip protocol at 3x14=42
    assert sa.time_to_first_decision_min(pre_synchronized=True) == 0.0
    assert sa.time_to_first_decision_min(pre_synchronized=False) == 42.0
