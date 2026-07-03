"""Tests for squad_autonomy_sim -- the role squad as a long-range-autonomous multi-agent mechanism.

Proves: the squad's solved board CONVERGES at the far end under Mars-DTN chaos (delay/reorder/duplicate,
loss-with-custody) because the solve is deterministic + event-sourced; it DIVERGES only under permanent
loss with no custody (the honest counter-case); a delayed CBJ corrective bundle lands on the repaired
state; and the whole sim is seeded/reproducible.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "comms_sim"))

import squad_autonomy_sim as sa  # noqa: E402


def test_squad_converges_under_dtn_chaos_but_not_permanent_loss():
    results = {s["scenario"]: s for s in sa.run_suite()}
    for name in (
        "instant_link",
        "mars_far_delay+reorder",
        "duplicate_bundles",
        "loss_WITH_custody",
        "solar_conjunction_blackout(custody)",  # NASA-grounded severe outage; custody carries it through
    ):
        assert results[name]["converged"] is True, name  # delay/reorder/dup/custody/conjunction all converge
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
    # the honest gap is recorded, not hidden: loss-rate has no published figure -> custody, not a rate
    assert "NO clean published figure" in sa.DOC_SOURCES["loss-rate %"]


def test_documented_autonomy_payoff_zero_vs_42_min():
    # the demo's documented handshake: pre-synchronized squad starts at 0; a round-trip protocol at 3x14=42
    assert sa.time_to_first_decision_min(pre_synchronized=True) == 0.0
    assert sa.time_to_first_decision_min(pre_synchronized=False) == 42.0


# ---- grounded in NASA-published Mars-relay figures (each carries a source URL in NASA_SOURCES) ------------
def test_nasa_relay_figures_match_published_values():
    # NASA/JPL Electra spec: 2.048 Mbps max, typical coded 8-256 kbps
    assert sa.MARS.uhf_relay_max_kbps == 2048
    assert sa.MARS.uhf_relay_typical_kbps_min == 8 and sa.MARS.uhf_relay_typical_kbps_max == 256
    # NASA Mars 2020: ~8 min/pass, 100-250 Mbit/pass, ~2 passes/sol
    assert sa.MARS.relay_pass_minutes == 8.0 and sa.MARS.relay_passes_per_sol == 2
    assert (sa.MARS.relay_data_per_pass_mbit_min, sa.MARS.relay_data_per_pass_mbit_max) == (100, 250)
    # NASA solar conjunction: ~2 weeks every ~2 years
    assert sa.MARS.conjunction_blackout_days == 14.0 and sa.MARS.conjunction_period_years == 2.0
    # NASA Goddard canonical OWLT: ~4-24 min one-way
    assert sa.MARS.owlt_min_minutes_nasa == 4.0 and sa.MARS.owlt_max_minutes_nasa == 24.0
    # NASA PACE 2024 DTN custody demonstration
    assert sa.MARS.dtn_demonstrated_bundles == 34_000_000


def test_every_nasa_figure_carries_a_nasa_source_url():
    # no fabricated figure: every NASA_SOURCES entry cites a nasa.gov URL so it can be audited back to NASA
    assert sa.NASA_SOURCES, "NASA_SOURCES must be populated"
    for key, src in sa.NASA_SOURCES.items():
        host = urlparse(src).netloc.split("@")[-1].split(":")[0].lower()
        assert host == "nasa.gov" or host.endswith(".nasa.gov"), key
        assert src.startswith(("http://", "https://")), key
