from __future__ import annotations

import json

import pytest

from python.scbe.prime_ir import first_primes
from python.scbe.rosetta_control import (
    RUNTIME_PASS,
    RUNTIME_SKIPPED,
    build_rosetta_control_node,
)


def test_rosetta_control_factorial_builds_bounded_loop_prime_tape() -> None:
    node = build_rosetta_control_node(
        "factorial(5)",
        targets=["python", "typescript"],
        fn_name="factorial_5",
        run=True,
    )
    tape = node.control_tape.to_dict()
    by_target = {artifact.target: artifact for artifact in node.artifacts}

    assert node.schema == "scbe_rosetta_control_node_v1"
    assert node.value == pytest.approx(120)
    assert "CTRL:WHILE" in tape["roles"]
    assert "CTRL:CONST" in tape["roles"]  # loop bound is part of the key
    assert first_primes(256)[0x44] in node.control_tape.primes
    assert by_target["python"].runtime.status == RUNTIME_PASS
    assert by_target["python"].runtime.value == pytest.approx(120)
    assert "__loop_0" in by_target["python"].source
    assert "bounded loop exceeded" in by_target["python"].source

    assert by_target["typescript"].runtime.status in {RUNTIME_PASS, RUNTIME_SKIPPED}
    if by_target["typescript"].runtime.status == RUNTIME_PASS:
        assert by_target["typescript"].runtime.value == pytest.approx(120)
        assert node.runtime_consensus_ok is True


def test_rosetta_control_gcd_tracks_variable_slots_and_runtime_value() -> None:
    node = build_rosetta_control_node(
        "gcd(48,18)",
        targets=["python"],
        fn_name="gcd_48_18",
        run=True,
    )
    tape = node.control_tape.to_dict()

    assert node.value == pytest.approx(6)
    assert node.artifacts[0].runtime.status == RUNTIME_PASS
    assert node.artifacts[0].runtime.value == pytest.approx(6)
    assert {slot["name"] for slot in tape["var_slots"]} >= {"__a", "__b", "__t"}
    assert tape["roles"].count("CTRL:WHILE") == 1


def test_rosetta_control_lucas_lehmer_uses_logical_or_without_python_drift() -> None:
    node = build_rosetta_control_node(
        "lucas_lehmer(7)",
        targets=["python", "typescript"],
        fn_name="ll7",
        run=True,
    )
    by_target = {artifact.target: artifact for artifact in node.artifacts}

    assert node.value == pytest.approx(1)
    assert "OP:or" in node.control_tape.roles
    assert by_target["python"].runtime.status == RUNTIME_PASS
    assert by_target["python"].runtime.value == pytest.approx(1)
    assert " or " in by_target["python"].source
    assert "||" in by_target["typescript"].source


def test_scbe_code_rosetta_control_node_cli_json() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "rosetta-control-node",
            "--expr",
            "factorial(5)",
            "--targets",
            "python,typescript",
            "--fn",
            "factorial_5",
            "--run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["schema"] == "scbe_rosetta_control_node_v1"
    assert payload["value"] == pytest.approx(120)
    assert "CTRL:WHILE" in payload["control_tape"]["roles"]
    by_target = {artifact["target"]: artifact for artifact in payload["artifacts"]}
    assert by_target["python"]["runtime"]["status"] == RUNTIME_PASS
