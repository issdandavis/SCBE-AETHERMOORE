"""analog_solve: inference with NO neural forward pass -- navigating a geometry maze of verified cases.

These prove the two honest outcomes that make analog inference safe to route to: it SOLVES by
interpolation when the new problem is near a verified case (graft + adapt + verify, zero model calls),
and it returns solved=False -- never unverified code -- when no aligned crack exists (the caller falls
back to a model). Plus the spin math (alignment/disorder) and the entry-point adaptation.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.analog_solve import (  # noqa: E402
    Maze,
    adapt,
    adapt_basis,
    alignment,
    analog_solve,
    analog_solver,
    disorder,
    featurize,
    target_name,
)


def test_spin_alignment_and_disorder_are_complementary():
    a = featurize("add two numbers")
    assert abs(alignment(a, a) - 1.0) < 1e-9  # a spin is fully aligned with itself
    assert disorder(a, a) < 1e-9
    b = featurize("reverse a string")
    assert alignment(a, b) < alignment(a, a)  # unrelated text is less aligned (more disorder = a wall)
    assert abs((alignment(a, b) + disorder(a, b)) - 1.0) < 1e-9


def test_target_name_reads_the_function_the_tests_call():
    assert target_name(["assert total(2, 3) == 5"]) == "total"
    assert target_name(["assert rev('ab') == 'ba'"]) == "rev"


def test_adapt_renames_a_single_def_to_the_target_entry_point():
    grafted = adapt("def add(a, b):\n    return a + b", ["assert total(2, 3) == 5"])
    assert "def total(a, b):" in grafted and "def add" not in grafted


def test_adapt_leaves_code_alone_when_target_already_defined():
    code = "def total(a, b):\n    return a + b"
    assert adapt(code, ["assert total(2, 3) == 5"]) == code


def test_interpolation_solves_a_renamed_variant_with_zero_model_calls():
    maze = Maze.from_solved(
        [("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"])]
    )
    out = analog_solve("sum / total of two numbers a and b", ["assert total(2, 3) == 5"], maze)
    assert out["solved"] is True and out["solver"] == "analog"
    assert "def total(a, b):" in out["code"]  # the grafted, entry-point-adapted neighbor
    assert out["path"] and out["path"][-1]["passed"] is True  # it exited through a crack, not a wall


def test_novel_problem_falls_back_instead_of_emitting_unverified_code():
    maze = Maze.from_solved(
        [("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"])]
    )
    out = analog_solve("compute the nth Fibonacci number recursively", ["assert fib(10) == 55"], maze)
    assert out["solved"] is False and out["code"] is None  # honest: no aligned crack -> no guess


def test_from_solved_drops_a_case_whose_code_does_not_actually_pass():
    # the walls vouch for every node: a (problem, WRONG code) pair never enters the maze
    maze = Maze.from_solved(
        [
            ("add", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"]),  # real -> kept
            ("bad", "def add(a, b):\n    return a - b", ["assert add(2, 3) == 5"]),  # wrong -> dropped
        ]
    )
    assert len(maze.cases) == 1


def test_from_corpus_reads_problem_and_solution_from_messages():
    rec = {
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "add a and b"},
            {"role": "assistant", "content": "def add(a, b):\n    return a + b"},
        ],
        "meta": {"task_id": "t1"},
    }
    maze = Maze.from_corpus([rec])
    assert len(maze.cases) == 1 and maze.cases[0].cid == "t1"


def test_adapt_basis_tries_rename_first_then_widens():
    # cheapest graft (rename entry) is candidate 0 so old behavior is preserved; the basis only widens after
    code = "def half(n):\n    return n // 2"
    basis = adapt_basis(code, ["assert dbl(3) == 6"])
    assert basis[0] == adapt(code, ["assert dbl(3) == 6"])
    assert any("n * 2" in c for c in basis)  # an operator-swap variant is reachable


def test_op_swap_basis_solves_a_genuine_near_duplicate():
    # half -> double: n // 2 becomes n * 2 (renamed dbl). single-rename could NEVER do this; the graft is
    # genuinely CORRECT (it really doubles), not a weak-oracle coincidence.
    maze = Maze.from_solved([("halve the number n", "def half(n):\n    return n // 2", ["assert half(4) == 2"])])
    out = analog_solve("double the number n", ["assert dbl(3) == 6"], maze)
    assert out["solved"] is True and "n * 2" in out["code"]


def test_basis_still_falls_back_on_genuine_novelty():
    # the wider basis must NOT manufacture a pass on a problem nothing in the maze can reach
    maze = Maze.from_solved(
        [("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"])]
    )
    out = analog_solve("compute the nth Fibonacci number recursively", ["assert fib(10) == 55"], maze)
    assert out["solved"] is False and out["code"] is None


def test_learn_admits_only_verified_and_enables_free_recurrence():
    maze = Maze()
    assert maze.learn("add a and b", "def add(a, b):\n    return a + b", checks=["assert add(2, 3) == 5"]) is True
    assert maze.learn("bad", "def sub(a, b):\n    return a - b", checks=["assert sub(2, 3) == 5"]) is False  # rejected
    assert len(maze.cases) == 1  # only the verified solve grew the library
    # a paraphrase of the learned problem is now sunk for free (recurrence the growing library bought)
    out = analog_solve("sum / total of a and b", ["assert total(2, 3) == 5"], maze)
    assert out["solved"] is True


def test_analog_solver_is_run_step_compatible():
    maze = Maze.from_solved(
        [("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"])]
    )
    solve = analog_solver(maze)
    candidate = solve({"spec": "total two numbers", "check": ["assert total(2, 3) == 5"]})
    assert "def total(a, b):" in candidate  # returns the top-aligned graft for run_step to verify
