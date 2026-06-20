"""pair_loop: a deterministic harness that pairs small models, improvising only at the blanks.

The harness emits fixed structure for free (zero model calls), routes each blank to the model good
at its capability, and a checker accepts/rejects against the walls. Proven with deterministic stubs;
a real free model drops into a capability slot. Like juggling: blanks thrown to the right hand, the
checker is the catch.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.pair_loop import (  # noqa: E402
    BLANK,
    STUBS,
    Blank,
    accepting_checker,
    run_loop,
    template_level,
)


def test_count_strength_is_routed_into_the_command():
    lvl = template_level("[1, 2, 3] has ", BLANK, " items", blanks=[Blank("count", ["3"])], name="count_items")
    r = run_loop(lvl, STUBS, accepting_checker)
    assert r["cleared"] is True
    assert r["output"] == "[1, 2, 3] has 3 items"  # the counting model's answer routed into the slot
    assert r["model_calls"] == 1
    assert r["by_capability"] == {"count": 1}


def test_improvise_only_when_needed():
    # fixed structure costs zero model calls; the model is only called at blanks
    fixed = run_loop(template_level("x = 1", name="fully_fixed"), STUBS, accepting_checker)
    assert fixed["cleared"] is True
    assert fixed["model_calls"] == 0
    two = template_level(
        "def ",
        BLANK,
        "(): return ",
        BLANK,
        blanks=[Blank("name", ["greet"]), Blank("pick", ["42"])],
    )
    r = run_loop(two, STUBS, accepting_checker)
    assert r["output"] == "def greet(): return 42"
    assert r["counts"]["deterministic"] == 2  # the two fixed tokens
    assert r["model_calls"] == 2  # one per blank, never the structure


def test_route_by_strength_picks_the_capability_model():
    lvl = template_level("v=", BLANK, blanks=[Blank("count", ["X"])])
    used = {}

    def marker(goal, out, allowed):
        used["count"] = True
        return "X"

    r = run_loop(lvl, {"count": marker}, accepting_checker)
    assert used.get("count") is True  # the count blank went to the count router
    assert r["output"] == "v=X"


def test_checker_drops_out_of_wall_values_and_fails_honestly():
    lvl = template_level("a=", BLANK, blanks=[Blank("pick", ["1", "2"])])

    def bad(goal, out, allowed):
        return "9"  # 9 is not in the walls -> dropped every time

    r = run_loop(lvl, {"pick": bad}, accepting_checker, budget=5)
    assert r["cleared"] is False  # the harness never fakes success
    assert r["counts"]["rejected"] > 0
    assert "9" not in r["output"]  # a bad guess never corrupts the output


def test_template_blank_mismatch_raises():
    with pytest.raises(ValueError, match="blanks"):
        template_level("x ", BLANK, " y", blanks=[])  # one blank, no specs
