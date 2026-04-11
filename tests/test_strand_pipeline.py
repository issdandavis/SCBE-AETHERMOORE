"""Integration: strand -> op_binary -> rhombic, one pass."""

from __future__ import annotations

import numpy as np
import pytest

from src.symphonic.multipath.strand_pipeline import (
    PipelineResult,
    StringLedger,
    decide,
    run_pipeline,
)


DEMO_OPS = ["add", "if_", "own", "promise", "matrix", "bind_d"]
EXPECTED_DOMINANTS = ["CA", "KO", "RU", "AV", "UM", "DR"]


def test_pipeline_produces_all_outputs():
    ledger = StringLedger()
    r = run_pipeline(DEMO_OPS, ledger)
    assert isinstance(r, PipelineResult)
    assert r.dominants() == EXPECTED_DOMINANTS
    assert len(r.per_bead_bits) == len(DEMO_OPS)
    assert r.bitstream == "".join(r.per_bead_bits)
    assert r.symbolic_x.shape == (6,)
    # No sensors -> rhombic fields stay None
    assert r.rhombic_R is None
    assert r.rhombic_score is None


def test_bitstream_widths_match_dominant_tongue():
    """Each bead's bit length equals its dominant tongue's width."""
    from src.symphonic.multipath.op_binary import TONGUE_WIDTH
    ledger = StringLedger()
    r = run_pipeline(DEMO_OPS, ledger)
    for bead, bits in zip(r.strand.beads, r.per_bead_bits):
        assert len(bits) == TONGUE_WIDTH[bead.dominant]


def test_ledger_cost_drops_with_repetition():
    """Grooves wear in: repeated runs over the same ops shrink the cost."""
    ledger = StringLedger(growth=1.5)
    cold = run_pipeline(DEMO_OPS, ledger)
    for _ in range(10):
        warm = run_pipeline(DEMO_OPS, ledger)
    assert warm.ledger_cost < cold.ledger_cost


def test_ledger_touches_dominant_not_all_tongues():
    """Only the winning tongue per op gets widened, not all 6."""
    ledger = StringLedger()
    run_pipeline(DEMO_OPS, ledger)
    # Exactly len(DEMO_OPS) keys, one per (op, dominant) pair
    assert len(ledger.width) == len(DEMO_OPS)
    for op, dom in zip(DEMO_OPS, EXPECTED_DOMINANTS):
        assert (op, dom) in ledger.width


def test_symbolic_x_is_phi_scaled_strand_energy():
    """x should reflect phi-weighted coactivation across all beads."""
    ledger = StringLedger()
    r = run_pipeline(DEMO_OPS, ledger)
    # Every tongue fired on at least one bead -> no zero channels
    assert (r.symbolic_x > 0).all()
    # phi scaling makes DR (channel 5) the loudest possible contribution
    # (bind_d lands on DR at phi_weight 11.09)
    assert r.symbolic_x[5] > r.symbolic_x[0]


def test_rhombic_fires_when_sensors_provided():
    rng = np.random.default_rng(42)
    ledger = StringLedger()
    r = run_pipeline(
        DEMO_OPS, ledger,
        audio=rng.normal(size=6),
        vision=rng.normal(size=6),
        governance=rng.normal(size=6),
    )
    assert r.rhombic_R is not None
    assert r.rhombic_score is not None
    assert 0.0 <= r.rhombic_score <= 1.0


def test_rhombic_phase_cycles_mod_3():
    """phase_k changes R via (-1/phi)^(k mod 3), so k=0 vs k=1 should differ."""
    rng = np.random.default_rng(7)
    a = rng.normal(size=6)
    v = rng.normal(size=6)
    g = rng.normal(size=6)
    ledger = StringLedger()
    r0 = run_pipeline(DEMO_OPS, ledger, audio=a, vision=v, governance=g, phase_k=0)
    ledger = StringLedger()
    r1 = run_pipeline(DEMO_OPS, ledger, audio=a, vision=v, governance=g, phase_k=1)
    assert r0.rhombic_R != pytest.approx(r1.rhombic_R)


def test_decide_maps_score_to_tier():
    assert decide(None) == "ALLOW"
    assert decide(0.9) == "ALLOW"
    assert decide(0.5) == "ALLOW"
    assert decide(0.3) == "QUARANTINE"
    assert decide(0.1) == "ESCALATE"
    assert decide(0.01) == "DENY"


def test_pipeline_populates_decision_without_sensors():
    r = run_pipeline(DEMO_OPS, StringLedger())
    assert r.decision == "ALLOW"


def test_pipeline_populates_decision_with_sensors():
    rng = np.random.default_rng(0)
    r = run_pipeline(
        DEMO_OPS, StringLedger(),
        audio=rng.normal(size=6),
        vision=rng.normal(size=6),
        governance=rng.normal(size=6),
    )
    assert r.decision in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert r.rhombic_score is not None


def test_unknown_op_still_encodes():
    """Silent bead falls back to CA; bitstream still emits CA-width bits."""
    from src.symphonic.multipath.op_binary import TONGUE_WIDTH
    ledger = StringLedger()
    r = run_pipeline(["totally_unknown_op"], ledger)
    assert r.strand.beads[0].dominant == "CA"
    assert len(r.per_bead_bits[0]) == TONGUE_WIDTH["CA"]
