"""perturbed: the curriculum twisted so a climber can't win by RECALL (measures reasoning, not memory).

Each problem is a renamed, spec-changed variant of a canonical one, with a correct reference + hidden
tests for the NEW spec. These tests prove the twisted ladder is a valid instrument: the answer key
clears every problem (the twists are solvable), the naive floor clears none, and the problems are
genuinely distinct from the canonical curriculum.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.curriculum import CURRICULUM  # noqa: E402
from python.helm.perturbed import PERTURBED_CURRICULUM, verify_buildable  # noqa: E402


def test_perturbed_ladder_is_solvable_and_floored():
    r = verify_buildable()
    assert r["problems"] == 15
    assert r["reference_verified"] == 15  # the answer key clears all -> the twists are solvable
    assert r["naive_verified"] == 0  # the failing stub clears none -> a real floor


def test_perturbed_problems_are_disjoint_from_the_canonical_ones():
    canon = {p["task_id"] for t in CURRICULUM for p in t["problems"]}
    pert = {p["task_id"] for t in PERTURBED_CURRICULUM for p in t["problems"]}
    assert not (canon & pert)  # no shared task ids -- these are new problems
    assert len(pert) == 15


def test_perturbed_mirrors_the_tier_structure():
    assert [t["tier"] for t in PERTURBED_CURRICULUM] == [1, 2, 3, 4, 5]
    assert all(len(t["problems"]) == 3 for t in PERTURBED_CURRICULUM)


def test_a_twisted_reference_encodes_the_new_spec_not_the_canonical_one():
    # buzzfizz SWAPS fizz/buzz -- the reference must produce 'Buzz' for multiples of 3, not 'Fizz'
    probs = {p["task_id"]: p for t in PERTURBED_CURRICULUM for p in t["problems"]}
    ns: dict = {}
    exec(probs["p2_buzzfizz"]["code"], ns)
    assert ns["buzzfizz"](3) == ["1", "2", "Buzz"]  # swapped vs canonical fizzbuzz
    assert ns["buzzfizz"](15)[-1] == "BuzzFizz"
