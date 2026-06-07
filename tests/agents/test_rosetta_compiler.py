from __future__ import annotations

import json

import pytest

from python.scbe.rosetta_compiler import (
    RUNTIME_PASS,
    RUNTIME_SKIPPED,
    build_rosetta_node_from_primes,
)


def test_rosetta_node_compiles_many_lenses_and_runs_available_runtimes() -> None:
    node = build_rosetta_node_from_primes(
        [29, 29, 2],
        targets=["python", "typescript", "go", "c", "haskell"],
        fn_name="abs_add",
        arg_names=["a", "b"],
        run_values=[3, -4],
    )

    assert node.schema == "scbe_rosetta_compiler_node_v1"
    assert node.prime_sequence == (29, 29, 2)
    assert node.opcodes == (9, 9, 0)
    assert node.op_names == ("abs", "abs", "add")
    assert node.shortest_target == "haskell"
    assert {artifact.target for artifact in node.artifacts} == {
        "python",
        "typescript",
        "go",
        "c",
        "haskell",
    }
    assert all(artifact.round_trip_ok for artifact in node.artifacts)

    by_target = {artifact.target: artifact for artifact in node.artifacts}
    assert by_target["python"].runtime.status == RUNTIME_PASS
    assert by_target["python"].runtime.value == pytest.approx(7)

    # Node is available on this workstation, but this assertion stays portable.
    assert by_target["typescript"].runtime.status in {RUNTIME_PASS, RUNTIME_SKIPPED}
    if by_target["typescript"].runtime.status == RUNTIME_PASS:
        assert by_target["typescript"].runtime.value == pytest.approx(7)
        assert node.shortest_runnable_target == "python"


def test_scbe_code_rosetta_node_cli_json() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "rosetta-node",
            "--primes",
            "29 29 2",
            "--targets",
            "python,typescript",
            "--fn",
            "abs_add",
            "--args",
            "a,b",
            "--values",
            "3,-4",
            "--run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["schema"] == "scbe_rosetta_compiler_node_v1"
    assert payload["prime_sequence"] == [29, 29, 2]
    assert payload["opcodes"] == [9, 9, 0]
    assert payload["shortest_runnable_target"] == "python"
    by_target = {artifact["target"]: artifact for artifact in payload["artifacts"]}
    assert by_target["python"]["runtime"]["status"] == RUNTIME_PASS
    assert by_target["python"]["runtime"]["value"] == pytest.approx(7)
    assert by_target["typescript"]["runtime"]["status"] in {
        RUNTIME_PASS,
        RUNTIME_SKIPPED,
    }
