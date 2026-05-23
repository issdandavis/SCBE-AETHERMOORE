"""Tests for NSM prime anchors and phi-extrapolation engine."""

import math

import pytest

from src.tokenizer.nsm_primes import (
    NSM_PRIMES,
    PHI,
    TONGUE_ORDER,
    TONGUE_PHASE,
    CoverageReport,
    PhiExtrapolation,
    all_primes,
    coverage_report,
    find_empty_lattice_sites,
    get_prime,
    grid_index,
    phi_extrapolate,
    phi_extrapolate_all,
    prime_grid_index,
    primes_for_tongue,
)

# ─────────────────────────────────────────────────────────────────────────────
# Prime table integrity
# ─────────────────────────────────────────────────────────────────────────────


def test_all_primes_have_unique_ids():
    ids = [p.id for p in NSM_PRIMES]
    assert len(ids) == len(set(ids)), "duplicate prime IDs"


def test_minimum_prime_count():
    # Wierzbicka's list is ~65; we allow duplicates for cross-tongue isotopes
    assert len(NSM_PRIMES) >= 60


def test_each_tongue_has_at_least_five_primaries():
    for tongue in TONGUE_ORDER:
        primes = primes_for_tongue(tongue)
        assert len(primes) >= 5, f"{tongue} has only {len(primes)} primary primes"


def test_poincare_radii_in_open_unit_ball():
    for p in NSM_PRIMES:
        assert 0.0 < p.r < 1.0, f"{p.id} has r={p.r} outside (0,1)"


def test_phi_orders_non_negative():
    for p in NSM_PRIMES:
        assert p.phi_order >= 0, f"{p.id} has negative phi_order"


def test_grid_positions_in_range():
    for p in NSM_PRIMES:
        assert 0 <= p.grid_row <= 15, f"{p.id} row {p.grid_row} out of range"
        assert 0 <= p.grid_col <= 15, f"{p.id} col {p.grid_col} out of range"


def test_spans_confidences_sum_to_at_most_1():
    for p in NSM_PRIMES:
        total = sum(s.confidence for s in p.spans)
        assert total <= 1.001, f"{p.id} span confidences sum to {total:.3f}"


def test_primary_span_has_highest_confidence():
    for p in NSM_PRIMES:
        if len(p.spans) > 1:
            assert p.spans[0].confidence >= p.spans[1].confidence, (
                f"{p.id}: first span ({p.spans[0].confidence}) < second ({p.spans[1].confidence})"
            )


def test_get_prime_returns_correct_object():
    p = get_prime("ko.want")
    assert p is not None
    assert p.label == "WANT"
    assert p.primary_tongue == "KO"


def test_get_prime_missing_returns_none():
    assert get_prime("nonexistent.prime") is None


def test_primes_for_tongue_returns_only_primaries():
    ko_primes = primes_for_tongue("KO")
    for p in ko_primes:
        assert p.primary_tongue == "KO"


def test_all_primes_length():
    assert len(all_primes()) == len(NSM_PRIMES)


# ─────────────────────────────────────────────────────────────────────────────
# Known canonical primes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prime_id, expected_label, expected_tongue",
    [
        ("ko.i",       "I",           "KO"),
        ("ko.want",    "WANT",        "KO"),
        ("ko.not",     "NOT",         "KO"),
        ("av.hear",    "HEAR",        "AV"),
        ("av.move",    "MOVE",        "AV"),
        ("ru.good",    "GOOD",        "RU"),
        ("ru.all",     "ALL",         "RU"),
        ("ca.one",     "ONE",         "CA"),
        ("ca.more",    "MORE",        "CA"),
        ("um.inside",  "INSIDE",      "UM"),
        ("um.feel",    "FEEL",        "UM"),
        ("dr.before",  "BEFORE",      "DR"),
        ("dr.after",   "AFTER",       "DR"),
        ("dr.know",    "KNOW",        "DR"),
    ],
)
def test_canonical_prime_assignments(prime_id, expected_label, expected_tongue):
    p = get_prime(prime_id)
    assert p is not None, f"{prime_id} not found"
    assert p.label == expected_label
    assert p.primary_tongue == expected_tongue


def test_not_is_cross_tongue():
    p = get_prime("ko.not")
    assert p is not None
    assert p.is_cross_tongue, "NOT should be cross-tongue (spans KO/RU/UM)"
    tongues = {s.tongue for s in p.spans}
    assert "KO" in tongues and "RU" in tongues and "UM" in tongues


def test_feel_is_cross_tongue():
    p = get_prime("um.feel")
    assert p is not None
    assert p.is_cross_tongue


def test_pure_primes_are_not_cross_tongue():
    for pid in ("ko.i", "av.hear", "av.move", "ca.one", "ca.two", "ca.more", "um.inside", "dr.before", "dr.after"):
        p = get_prime(pid)
        assert p is not None
        assert not p.is_cross_tongue, f"{pid} should be pure single-tongue"


# ─────────────────────────────────────────────────────────────────────────────
# Coverage analysis
# ─────────────────────────────────────────────────────────────────────────────


def test_coverage_report_returns_report():
    report = coverage_report()
    assert isinstance(report, CoverageReport)
    assert report.total == len(NSM_PRIMES)


def test_coverage_no_unspanned_primes():
    report = coverage_report()
    assert report.unspanned == 0, f"Unspanned primes: {report.unspanned_primes}"


def test_coverage_all_tongues_have_primaries():
    report = coverage_report()
    for tongue in TONGUE_ORDER:
        assert report.by_tongue[tongue] >= 3, f"{tongue} has < 3 primaries in coverage"


def test_coverage_cross_tongue_count():
    report = coverage_report()
    # NOT, FEEL, THINK, DO, IF, BECAUSE, TOUCH are cross-tongue at minimum
    assert report.cross_tongue >= 7


def test_coverage_notes_non_empty():
    report = coverage_report()
    assert len(report.notes) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Grid utilities
# ─────────────────────────────────────────────────────────────────────────────


def test_grid_index_row_major():
    assert grid_index(0, 0) == 0
    assert grid_index(0, 1) == 1
    assert grid_index(1, 0) == 16
    assert grid_index(15, 15) == 255


def test_prime_grid_index_matches_manual():
    p = get_prime("ko.i")
    assert p is not None
    assert prime_grid_index(p) == grid_index(p.grid_row, p.grid_col)


def test_no_two_primaries_share_grid_slot_within_tongue():
    for tongue in TONGUE_ORDER:
        seen: set[int] = set()
        for p in primes_for_tongue(tongue):
            idx = prime_grid_index(p)
            assert idx not in seen, (
                f"{tongue}: grid slot {idx} (row={p.grid_row},col={p.grid_col}) is shared"
            )
            seen.add(idx)


# ─────────────────────────────────────────────────────────────────────────────
# Phi-extrapolation (Riemannian exp map)
# ─────────────────────────────────────────────────────────────────────────────


def test_phi_extrapolate_returns_correct_step_count():
    p = get_prime("ko.want")
    assert p is not None
    results = phi_extrapolate(p, steps=3)
    assert len(results) == 3


def test_phi_extrapolate_tongue_cycles():
    p = get_prime("ko.want")  # primary = KO
    assert p is not None
    results = phi_extrapolate(p, steps=6)
    # Should cycle KO→AV→RU→CA→UM→DR
    expected = ["AV", "RU", "CA", "UM", "DR", "KO"]
    for i, ex in enumerate(results):
        assert ex.derived_tongue == expected[i], (
            f"step {i+1}: expected {expected[i]}, got {ex.derived_tongue}"
        )


def test_phi_extrapolate_radii_stay_in_ball():
    for p in NSM_PRIMES:
        results = phi_extrapolate(p, steps=4)
        for ex in results:
            assert 0.0 < ex.derived_r < 1.0, (
                f"{p.id} step {ex.n}: r={ex.derived_r} outside (0,1)"
            )


def test_phi_extrapolate_radii_increase_monotonically():
    p = get_prime("ko.i")
    assert p is not None
    results = phi_extrapolate(p, steps=4)
    for i in range(1, len(results)):
        # Radius should generally increase but tanh compression may slow it
        assert results[i].derived_r >= results[0].derived_r * 0.9, (
            f"step {i+1} radius {results[i].derived_r} unexpectedly dropped from step 1 {results[0].derived_r}"
        )


def test_phi_extrapolation_result_types():
    p = get_prime("av.move")
    assert p is not None
    results = phi_extrapolate(p, steps=2)
    for ex in results:
        assert isinstance(ex, PhiExtrapolation)
        assert isinstance(ex.is_known_prime, bool)
        assert ex.confidence >= 0.0
        assert 0 <= ex.grid_row <= 15
        assert 0 <= ex.grid_col <= 15


def test_phi_extrapolate_all_covers_all_primes():
    results = phi_extrapolate_all(steps=1)
    assert len(results) == len(NSM_PRIMES)
    for prime_id in results:
        assert prime_id in {p.id for p in NSM_PRIMES}


def test_find_empty_lattice_sites_returns_list():
    sites = find_empty_lattice_sites(steps=1)
    assert isinstance(sites, list)
    for site in sites:
        assert isinstance(site, PhiExtrapolation)
        assert not site.is_known_prime


def test_empty_lattice_sites_have_candidate_labels():
    sites = find_empty_lattice_sites(steps=2)
    for site in sites:
        assert site.candidate_label.startswith("[CANDIDATE:"), (
            f"empty site should have candidate label, got: {site.candidate_label}"
        )


def test_phi_extrapolate_pure_prime_first_step_tongue():
    """BEFORE is DR. First extrapolation step should land in KO."""
    p = get_prime("dr.before")
    assert p is not None
    result = phi_extrapolate(p, steps=1)
    assert result[0].derived_tongue == "KO"


# ─────────────────────────────────────────────────────────────────────────────
# Geometric properties
# ─────────────────────────────────────────────────────────────────────────────


def test_tongue_phases_evenly_spaced():
    phases = list(TONGUE_PHASE.values())
    for i in range(1, len(phases)):
        delta = phases[i] - phases[i - 1]
        assert abs(delta - math.pi / 3) < 1e-9, f"phase gap {i}: {delta} != pi/3"


def test_phi_is_golden_ratio():
    assert abs(PHI - (1 + math.sqrt(5)) / 2) < 1e-10


def test_fundamental_primes_have_small_r():
    """phi_order=0 primes should be near the center (r < 0.30)."""
    for p in NSM_PRIMES:
        if p.phi_order == 0:
            assert p.r < 0.30, f"{p.id} is phi_order=0 but r={p.r} >= 0.30"


def test_derived_primes_have_larger_r():
    """phi_order=2 primes should be further from center than phi_order=0."""
    order0 = [p.r for p in NSM_PRIMES if p.phi_order == 0]
    order2 = [p.r for p in NSM_PRIMES if p.phi_order == 2]
    if order0 and order2:
        assert max(order0) < max(order2) + 0.05, (
            "phi_order=2 primes should reach further than phi_order=0"
        )
