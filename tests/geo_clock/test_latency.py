"""RTT-floor invariants: vacuum < fiber, LEO crossover, monotonicity."""

from __future__ import annotations

import pytest

from src.geo_clock import latency


def test_vacuum_is_lower_bound_of_fiber():
    for d in (10.0, 100.0, 1000.0, 10000.0):
        assert latency.vacuum_rtt_ms(d) <= latency.fiber_rtt_ms(d) + 1e-9


def test_fiber_floor_about_one_hundredth_ms_per_km():
    # 0.01 ms/km approx (VoP=0.67 -> 0.00997)
    assert latency.fiber_rtt_ms(1000.0) == pytest.approx(9.97, abs=0.05)


def test_leo_starts_above_fiber_at_short_range():
    # Short hops are dominated by the 4-leg vertical, so fiber wins.
    assert latency.leo_starlink_rtt_ms(100.0) > latency.fiber_rtt_ms(100.0)


def test_crossover_around_2235_km():
    cx = latency.crossover_km()
    assert 2100.0 < cx < 2400.0


def test_leo_beats_fiber_above_crossover():
    cx = latency.crossover_km()
    # Sample 10% above the crossover: LEO should now be the winner.
    d = cx * 1.1
    assert latency.leo_starlink_rtt_ms(d) < latency.fiber_rtt_ms(d)


def test_quote_picks_correct_path_short():
    q = latency.quote(100.0)
    assert q.best_path == "fiber"


def test_quote_picks_correct_path_long():
    q = latency.quote(5000.0)
    assert q.best_path == "leo"


def test_quote_vacuum_only_when_allowed():
    q_terrestrial = latency.quote(5000.0)
    q_deep = latency.quote(5000.0, vacuum_ok=True)
    assert q_terrestrial.best_path != "vacuum"
    # vacuum_ok=True doesn't force vacuum; for terrestrial distances LEO
    # still beats fiber, but vacuum beats both. So vacuum should win.
    assert q_deep.best_path == "vacuum"


def test_measured_rtt_falls_back_to_fiber_floor():
    # The probe hook is a placeholder; without a probe it returns fiber.
    assert latency.measured_rtt_ms(1000.0) == pytest.approx(latency.fiber_rtt_ms(1000.0))


def test_rtt_is_monotone_in_distance():
    a = latency.fiber_rtt_ms(100.0)
    b = latency.fiber_rtt_ms(500.0)
    c = latency.fiber_rtt_ms(2000.0)
    assert a < b < c
