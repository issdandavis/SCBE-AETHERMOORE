from __future__ import annotations

import json

import pytest

from python.scbe.rosetta_frontend import LoweringError, compile_python_control_source

SUM_TO_N = """
def sum_to_n(n):
    total = 0
    i = 0
    while i < n:
        total += i
        i += 1
    return total
"""


SUM_TO_N_RENAMED = """
def renamed(limit):
    # Same computation, different surface spelling.
    acc = 0
    cursor = 0
    while cursor < limit:
        acc = acc + cursor
        cursor = cursor + 1
    return acc
"""


RANGE_SUM = """
def range_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""


BRANCH = """
def floor_plus_one(n):
    if n < 0:
        return 0
    else:
        return n + 1
"""


def _python_result(source: str, fn_name: str, **kwargs: int) -> int:
    namespace: dict[str, object] = {}
    exec(source, namespace)  # noqa: S102 -- test fixture source only
    return int(namespace[fn_name](**kwargs))  # type: ignore[index,operator]


@pytest.mark.parametrize("n", [0, 1, 2, 5, 10, 50])
def test_python_frontend_preserves_while_loop_meaning(n: int) -> None:
    frontend = compile_python_control_source(
        SUM_TO_N,
        constants={"n": n},
        targets=["python"],
        run=True,
    )

    assert frontend.control_node.value == pytest.approx(
        _python_result(SUM_TO_N, "sum_to_n", n=n)
    )
    assert frontend.control_node.artifacts[0].runtime.value == pytest.approx(
        frontend.control_node.value
    )
    assert "CTRL:WHILE" in frontend.control_node.control_tape.roles


@pytest.mark.parametrize("n", [0, 4, 9])
def test_python_frontend_range_for_lowers_to_same_control_tape_as_while(n: int) -> None:
    while_frontend = compile_python_control_source(
        SUM_TO_N,
        constants={"n": n},
        targets=["python"],
        run=True,
    )
    range_frontend = compile_python_control_source(
        RANGE_SUM,
        constants={"n": n},
        targets=["python"],
        run=True,
    )

    assert range_frontend.control_node.value == pytest.approx(
        _python_result(RANGE_SUM, "range_sum", n=n)
    )
    assert (
        range_frontend.control_node.control_tape.primes
        == while_frontend.control_node.control_tape.primes
    )
    assert range_frontend.canonical_program == while_frontend.canonical_program


def test_python_frontend_many_to_one_under_variable_rename_and_comments() -> None:
    left = compile_python_control_source(
        SUM_TO_N,
        constants={"n": 7},
        targets=["python"],
    )
    right = compile_python_control_source(
        SUM_TO_N_RENAMED,
        constants={"limit": 7},
        targets=["python"],
    )

    assert (
        left.control_node.control_tape.primes == right.control_node.control_tape.primes
    )
    assert left.canonical_program == right.canonical_program


@pytest.mark.parametrize("n,expected", [(-3, 0), (0, 1), (8, 9)])
def test_python_frontend_preserves_if_else_meaning(n: int, expected: int) -> None:
    frontend = compile_python_control_source(
        BRANCH,
        constants={"n": n},
        targets=["python"],
        run=True,
    )

    assert frontend.control_node.value == pytest.approx(expected)
    assert frontend.control_node.artifacts[0].runtime.value == pytest.approx(expected)
    assert "CTRL:IF" in frontend.control_node.control_tape.roles


def test_python_frontend_refuses_arrays_instead_of_faking_lowering() -> None:
    source = """
def first():
    xs = [1, 2, 3]
    return xs[0]
"""

    with pytest.raises(LoweringError, match="List is not supported"):
        compile_python_control_source(source)


def test_python_frontend_refuses_module_level_imports() -> None:
    source = """
import os

def f():
    return 1
"""

    with pytest.raises(LoweringError, match="module-level statements"):
        compile_python_control_source(source)


def test_scbe_code_compile_python_control_cli_json() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "compile-python-control",
            "--content",
            SUM_TO_N,
            "--const",
            "n=5",
            "--targets",
            "python",
            "--run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["schema"] == "scbe_rosetta_python_frontend_v1"
    assert payload["canonical_program"].startswith("arg0 = 5")
    assert payload["control_node"]["value"] == pytest.approx(10)
    assert payload["control_node"]["artifacts"][0]["runtime"]["status"] == "PASS"


def test_scbe_code_compile_python_control_cli_rejects_unsupported_source() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, _, stderr = _run_cli(
        [
            "compile-python-control",
            "--content",
            "def f():\n    return [1, 2][0]\n",
            "--json",
        ]
    )

    assert rc == 2
    assert "Subscript is not supported" in stderr
