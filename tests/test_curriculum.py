"""curriculum: a graded coding ladder (elementary -> PhD+) where any `generator(problem)->code`
is a climber, scored through the same sandboxed hidden-test verification as the forge loop.

The reference answer-key must clear every tier (proves the ladder is solvable and the hidden tests
are correct); the naive stub must clear nothing (the floor proves the ladder discriminates); and a
climber that fails a single mid-ladder problem must stop there (the climb is contiguous from the
bottom -- no skipping grades).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.curriculum import CURRICULUM, run_curriculum  # noqa: E402
from python.helm.public_bench import naive_generator, reference_generator  # noqa: E402


def test_ladder_shape_is_graded_and_real():
    grades = [t["grade"] for t in CURRICULUM]
    assert grades == ["elementary", "middle-school", "high-school", "undergrad", "grad/phd+"]
    for t in CURRICULUM:
        assert len(t["problems"]) == 3
        for p in t["problems"]:
            assert "def " in p["code"]  # a real reference solution
            assert len(p["test_list"]) >= 3  # >=1 public example + >=2 hidden checks


def test_reference_climber_clears_the_whole_ladder():
    # the answer key proves every tier is solvable and every hidden test is correct
    s = run_curriculum(reference_generator)
    assert s["highest_tier_cleared"] == 5
    assert s["highest_grade_cleared"] == "grad/phd+"
    assert s["total_verified"] == s["total_problems"] == 15


def test_naive_floor_clears_nothing():
    # the floor proves the ladder is not flattering anyone
    s = run_curriculum(naive_generator)
    assert s["highest_tier_cleared"] == 0
    assert s["total_verified"] == 0


def test_climb_is_contiguous_from_the_bottom():
    # a climber that aces everything EXCEPT one tier-3 problem must stop at tier 2,
    # even though it would solve tiers 4 and 5 -- no skipping grades.
    def all_but_one_t3(problem):
        if problem["task_id"] == "t3_is_prime":
            return naive_generator(problem)
        return reference_generator(problem)

    all_but_one_t3.__name__ = "all_but_one_t3"
    s = run_curriculum(all_but_one_t3)
    assert s["highest_tier_cleared"] == 2  # blocked at high-school
    assert s["total_verified"] == 14  # solved everything except the one held-back problem
    t3 = next(r for r in s["tiers"] if r["tier"] == 3)
    assert t3["verified"] == 2 and t3["cleared"] is False


def test_overfit_is_caught_not_counted_as_cleared():
    # a climber that hardcodes only the PUBLIC example (first assert) must fail the hidden checks
    def overfit_t1_add(problem):
        if problem["task_id"] == "t1_add":
            return "def add(a, b):\n    return 5\n"  # only satisfies add(2,3)==5 (the public example)
        return naive_generator(problem)

    overfit_t1_add.__name__ = "overfit_t1_add"
    s = run_curriculum(overfit_t1_add, public_k=1)
    t1 = next(r for r in s["tiers"] if r["tier"] == 1)
    assert t1["verified"] == 0  # hidden checks (add(-1,1), add(0,0)) catch the overfit
    assert t1["overfit_caught"] >= 1
