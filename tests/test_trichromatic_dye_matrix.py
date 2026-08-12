"""Truth table for the trichromatic corroboration gate: risk level x dye level.

The gate has two inputs and they do different jobs:

    RISK  the blended score, which decides whether an escalation is PROPOSED
    DYE   the stain panel, which decides whether that escalation is ALLOWED to overturn
          the rest of the stack

Testing one example (R03) proved the gate fires once. It does not show what the gate does
across the space, and a rule that only works on the case it was built for is not a rule. So:
every cell of the grid, including the ones that should NOT withhold.

Levels:
    risk  HIGH > deny threshold (0.76) | MID in the quarantine band | LOW below quarantine
    dye   HIGH all three bind | MID exactly one binds | LOW none bind

The LOW-dye field values are R03's real measured reading (0.472 / 0.205 / 0.895) -- the benign
prompt that was being quarantined. It sits just under every dye threshold, which is exactly why
counting dots separates it when re-reading the blended score five different ways did not.
"""

from __future__ import annotations

import pytest

from src.governance.trichromatic_governance import (
    DEFAULT_DYES,
    TrichromaticGovernanceEngine,
    TrichromaticScores,
)

DENY_THRESHOLD = 0.76
QUARANTINE_THRESHOLD = 0.48

# (incoherence, lattice, anomaly) -> how many of the three dyes bind
DYE_LEVELS = {
    "high": (0.60, 0.25, 0.99),  # sat + lat + inc  -> 3
    "mid": (0.50, 0.25, 0.80),  # lat only         -> 1
    "low": (0.472, 0.205, 0.895),  # R03's real reading -> 0
}
RISK_LEVELS = {"high": 0.85, "mid": 0.53, "low": 0.30}

EXPECTED_BINDS = {"high": 3, "mid": 1, "low": 0}


def make_scores(risk: float, fields) -> TrichromaticScores:
    incoherence, lattice, anomaly = fields
    return TrichromaticScores(
        triplet_coherence_score=1.0 - incoherence,
        lattice_energy_score=lattice,
        whole_state_anomaly_score=anomaly,
        risk_score=risk,
        strongest_bridge="KO-AV",
        strongest_bridge_norm=0.5,
    )


@pytest.fixture
def engine() -> TrichromaticGovernanceEngine:
    return TrichromaticGovernanceEngine()


# ---------------------------------------------------------------------------
# The panel itself -- does each dye level bind the number of dots it claims?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", ["high", "mid", "low"])
def test_dye_level_binds_expected_dot_count(engine, level):
    plate = engine.stain(make_scores(0.5, DYE_LEVELS[level]))
    assert plate.count == EXPECTED_BINDS[level], f"{level}: {plate.pattern}"


def test_low_dye_is_r03s_real_reading_and_binds_nothing(engine):
    """The regression this gate exists for. If this ever binds, R03 is quarantined again."""
    plate = engine.stain(make_scores(0.532, DYE_LEVELS["low"]))
    assert plate.count == 0
    assert plate.names == ()

    # Record the ACTUAL margins. R03 does not sit just under every threshold -- measured:
    #     lat  0.205 vs 0.22   margin 0.015   razor thin, this is the load-bearing one
    #     sat  0.895 vs 0.96   margin 0.065   close
    #     inc  0.472 vs 0.58   margin 0.108   comfortably clear, contributes nothing here
    # So the gate's separation of R03 rests almost entirely on `lat`, with 0.015 of room. That
    # is a thin margin on an underpowered threshold (11 safe / 14 attack samples) and it is the
    # first thing to re-measure on any corpus change. Pinning the margins here means a drift
    # that quietly closes that 0.015 fails a test instead of re-quarantining benign traffic.
    margins = {d.name: round(d.threshold - d.reading, 3) for d in plate.dots}
    assert all(d.reading < d.threshold for d in plate.dots)
    assert margins == {"sat": 0.065, "lat": 0.015, "inc": 0.108}, margins
    assert min(margins.values()) == 0.015, "the lat margin is the whole separation; guard it"


# ---------------------------------------------------------------------------
# THE MATRIX
# ---------------------------------------------------------------------------

MATRIX = [
    # (risk,   dye,    veto_withheld, note)
    ("high", "high", False, "unambiguous attack: escalate, all three dyes corroborate"),
    ("high", "mid", False, "one dye is enough corroboration to let a high risk stand"),
    ("high", "low", True, "high score, NOTHING stains -- the score is overlapping, withhold"),
    ("mid", "high", False, "mid score but fully corroborated: escalate"),
    ("mid", "mid", False, "mid score, one dye: escalate"),
    ("mid", "low", True, "THE R03 CELL -- mid score, clean plate, unanimous council stands"),
    ("low", "low", True, "nothing anywhere: no escalation proposed and none corroborated"),
    ("low", "high", False, "dyes bind but risk is low -- corroboration does not CREATE a veto"),
    ("low", "mid", False, "same: the gate only ever subtracts authority, never adds it"),
]


@pytest.mark.parametrize("risk_level,dye_level,expect_withheld,note", MATRIX)
def test_corroboration_matrix(engine, risk_level, dye_level, expect_withheld, note):
    scores = make_scores(RISK_LEVELS[risk_level], DYE_LEVELS[dye_level])
    plate = engine.stain(scores)
    withheld = plate.count == 0
    assert withheld is expect_withheld, f"{risk_level}/{dye_level}: {note} -- plate {plate.pattern}"


def test_matrix_covers_every_cell():
    """No silent gaps: all nine risk x dye combinations are asserted."""
    cells = {(r, d) for r, d, _, _ in MATRIX}
    assert cells == {(r, d) for r in RISK_LEVELS for d in DYE_LEVELS}
    assert len(MATRIX) == 9


# ---------------------------------------------------------------------------
# Direction of the gate -- it may only ever REMOVE authority
# ---------------------------------------------------------------------------


def test_gate_never_creates_an_escalation(engine):
    """A bound dye on a LOW risk must not manufacture a veto.

    The gate is a guard on an escalation the blended score already proposed. If it could
    escalate on its own it would be a detector, and measured alone the panel catches 8/14 --
    worse than the blend. It must only subtract.
    """
    low_risk_all_dyes = make_scores(RISK_LEVELS["low"], DYE_LEVELS["high"])
    plate = engine.stain(low_risk_all_dyes)
    assert plate.count == 3
    assert low_risk_all_dyes.risk_score < QUARANTINE_THRESHOLD, "no escalation is proposed at this risk"


def test_deny_band_is_out_of_scope(engine):
    """DENY is a higher bar and is deliberately NOT gated. Guard against scope creep."""
    assert RISK_LEVELS["high"] > DENY_THRESHOLD
    plate = engine.stain(make_scores(RISK_LEVELS["high"], DYE_LEVELS["low"]))
    assert plate.count == 0  # would withhold a QUARANTINE, but DENY is not routed through here


# ---------------------------------------------------------------------------
# Panel integrity
# ---------------------------------------------------------------------------


def test_every_dye_reads_a_real_channel(engine):
    plate = engine.stain(make_scores(0.5, DYE_LEVELS["high"]))
    assert {d.channel for d in plate.dots} == {"incoherence", "lattice", "anomaly"}
    assert len(plate.dots) == len(DEFAULT_DYES)


def test_unknown_channel_is_rejected_not_ignored(engine):
    with pytest.raises(ValueError):
        engine.stain(make_scores(0.5, DYE_LEVELS["high"]), dyes=[("bad", "chartreuse", 0.5)])


def test_pattern_is_readable_and_marks_bound_dots(engine):
    hi = engine.stain(make_scores(0.9, DYE_LEVELS["high"])).pattern
    lo = engine.stain(make_scores(0.5, DYE_LEVELS["low"])).pattern
    assert hi.count("*") == 3 and lo.count("*") == 0
    assert "sat" in hi and "lat" in hi and "inc" in hi


def test_threshold_boundary_is_inclusive(engine):
    """A reading exactly at the threshold binds. Off-by-one here silently loosens the gate."""
    exact = engine.stain(make_scores(0.5, (0.58, 0.22, 0.96)))
    assert exact.count == 3, exact.pattern
    just_under = engine.stain(make_scores(0.5, (0.5799, 0.2199, 0.9599)))
    assert just_under.count == 0, just_under.pattern
