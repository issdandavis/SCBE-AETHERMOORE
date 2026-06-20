"""leveling: the curriculum as a "slope to skill" track (Line Rider), not an all-or-nothing tier cliff.

Same problems, same hidden-test verification (run_public_bench) -- but laid out as a smooth difficulty
track a rider climbs with momentum + crash detection, so partial progress is a graded number instead
of a zero. These tests prove the track shape, the ceiling-stop, the forgiveness knob, and -- the
point -- that the slope recovers signal the tier cliff throws away.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.leveling import (  # noqa: E402
    CURVES,
    cliff_vs_slope,
    difficulty,
    ride,
    skill_capped_generator,
    track,
)
from python.helm.public_bench import naive_generator, reference_generator  # noqa: E402

# --- the track (level layout) --------------------------------------------------


def test_track_orders_problems_easiest_first():
    levels = track()
    assert len(levels) == 15  # 5 tiers x 3 problems
    assert [lv["rank"] for lv in levels] == list(range(15))  # contiguous ranks from the bottom
    assert levels[0]["id"] == "t1_add" and levels[0]["tier"] == 1
    assert levels[-1]["tier"] == 5


def test_every_curve_is_monotonic_0_to_100():
    n = 15
    for curve in CURVES:
        vals = [difficulty(r, n, curve) for r in range(n)]
        assert vals[0] == 0.0 and vals[-1] == 100.0  # same endpoints, different shape between
        assert all(b >= a for a, b in zip(vals, vals[1:]))  # never goes downhill


def test_unknown_curve_raises():
    with pytest.raises(ValueError, match="unknown curve"):
        difficulty(1, 15, "spiral")


# --- the ride (momentum + crash + ceiling) -------------------------------------


def test_reference_rides_clean_to_the_top():
    r = ride(reference_generator)
    assert r["cleared"] == 15 and r["crashes"] == 0
    assert r["peak_difficulty"] == 100.0 and r["smoothness"] == 1.0


def test_naive_crashes_at_the_first_rung():
    r = ride(naive_generator)
    assert r["cleared"] == 0 and r["crashes"] == 1
    assert r["attempted"] == 1  # patience 1 -> the run ends at the first crash


def test_capped_rider_stops_at_its_ceiling():
    # solves levels with difficulty <= 25 (ranks 0..3 on the linear track), then crashes
    r = ride(skill_capped_generator(25))
    assert r["cleared"] == 4
    assert r["crashes"] == 1 and r["attempted"] == 5  # one crash ends it (patience 1)
    assert r["peak_difficulty"] == difficulty(3, 15, "linear")


def test_patience_lets_a_rider_survive_one_crash():
    # a rider that misses exactly t1_maximum but could clear everything after it
    def skips_maximum(problem):
        return naive_generator(problem) if problem["task_id"] == "t1_maximum" else reference_generator(problem)

    strict = ride(skips_maximum, patience=1)
    forgiving = ride(skips_maximum, patience=2)
    assert strict["cleared"] == 1  # add, then crash on maximum, stop
    assert forgiving["cleared"] > strict["cleared"]  # skips the bump, keeps riding
    assert forgiving["crashes"] >= 1


# --- the point: a slope recovers what a cliff discards --------------------------


def test_slope_recovers_signal_the_tier_cliff_drops():
    gen = skill_capped_generator(25)  # clears all of tier 1 + reverse_string in tier 2
    c = cliff_vs_slope(gen)
    assert c["cliff_tier"] == 1  # the cliff: only 1/3 of tier 2 -> credited tier 1, partial work lost
    assert "t2_reverse" in c["recovered"]  # the slope credits the tier-2 problem it actually solved
    assert c["slope_cleared"] == 4 and c["slope_of"] == 15


def test_curve_rescales_height_for_the_same_cleared_levels():
    gen = skill_capped_generator(25)
    steep = ride(gen, curve="steep")
    gentle = ride(gen, curve="gentle")
    assert steep["cleared"] == gentle["cleared"]  # same problems pass/fail -- the curve is a lens
    assert steep["peak_difficulty"] > gentle["peak_difficulty"]  # steep front-loads difficulty


# --- the small-model climb wires up (no network needed to construct it) ---------


def test_llm_generator_composes_offline():
    # the small-model climb is `ride(make_generator())`; building the generator must not hit the
    # network -- it only calls the endpoint when actually invoked on a problem.
    from python.helm.free_generator import make_generator

    gen = make_generator(model="dummy-model")
    assert callable(gen)  # ready to drop into ride() / cliff_vs_slope() once a model is serving
