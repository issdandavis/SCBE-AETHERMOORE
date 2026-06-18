"""Public benchmark runner: pull MBPP and run the forge loop with public/hidden checks.

Hermetic -- uses the bundled 3-problem MBPP sample, no network. Proves: the reference solver
passes real problems (harness works on real data), the naive stub is the failing floor, and --
the point of the public/hidden split -- a tool that overfits the public check is CAUGHT by the
hidden check.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.public_bench import (  # noqa: E402
    func_name,
    load_fixture,
    naive_generator,
    reference_generator,
    run_public_bench,
)

FIXTURE = load_fixture()


def test_fixture_is_real_mbpp():
    assert len(FIXTURE) == 3
    assert func_name(FIXTURE[0]) == "similar_elements"  # task 2
    assert all(p.get("test_list") for p in FIXTURE)


def test_reference_solver_passes_real_problems():
    s = run_public_bench(FIXTURE, generator=reference_generator, public_k=1)
    assert s["attempted"] == 3
    assert s["verified"] == 3  # reference solutions pass public + hidden
    assert s["pass_rate"] == 1.0
    assert s["public_pass"] == 3 and s["hidden_pass"] == 3


def test_naive_stub_is_the_failing_floor():
    s = run_public_bench(FIXTURE, generator=naive_generator, public_k=1)
    assert s["verified"] == 0
    assert s["public_pass"] == 0


# a tool that returns a constant: passes the first (public) assert, fails the held-out ones.
_OVERFIT_PROBLEM = {
    "task_id": 9001,
    "code": "def echo(x):\n    return x\n",
    "test_list": ["assert echo(1) == 1", "assert echo(2) == 2", "assert echo(5) == 5"],
    "test_imports": [],
}


def _overfit_generator(problem):
    return "def echo(x):\n    return 1\n"  # only correct for the public example echo(1)


def test_hidden_check_catches_public_overfit():
    s = run_public_bench([_OVERFIT_PROBLEM], generator=_overfit_generator, public_k=1)
    row = s["results"][0]
    assert row["public_passed"] is True  # passes the public assert echo(1) == 1
    assert row["hidden_passed"] is False  # fails hidden echo(2), echo(5)
    assert row["verified"] is False
    assert s["overfit_caught"] == 1  # the hidden check did its job
