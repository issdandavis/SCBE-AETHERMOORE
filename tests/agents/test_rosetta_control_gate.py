from __future__ import annotations

import json

from python.scbe.rosetta_control import build_rosetta_control_node
from python.scbe.rosetta_control_gate import (
    CONTROL_SHAPE_MISMATCH,
    CONTROL_SHAPE_PASS,
    UNTRACED_CONTROL_SOURCE,
    audit_rosetta_control_shape,
)


def _control_node():
    return build_rosetta_control_node(
        "factorial(5)",
        targets=["python", "typescript", "go", "c"],
        fn_name="factorial_5",
        run=False,
    )


def _artifact_sources() -> dict[str, str]:
    node = _control_node()
    return {artifact.target: artifact.source for artifact in node.artifacts}


def _prime_tape() -> tuple[int, ...]:
    return _control_node().control_tape.primes


def _inject_payload(source: str, target: str) -> str:
    if target == "python":
        return source.replace(
            "    __result = 0.0\n",
            "    __result = 0.0\n    __import__('os').system('echo pwned')\n",
            1,
        )
    if target == "typescript":
        return source.replace("{\n", "{\n  console.log('pwned');\n", 1)
    if target == "go":
        return source.replace("{\n", '{\n\tfmt.Println("pwned")\n', 1)
    if target == "c":
        return source.replace("{\n", '{\n    system("echo pwned");\n', 1)
    raise AssertionError(target)


def test_rosetta_control_shape_gate_passes_generated_scaffolds() -> None:
    expected = _prime_tape()

    for target, source in _artifact_sources().items():
        audit = audit_rosetta_control_shape(
            source,
            expression="factorial(5)",
            expected_primes=expected,
        )

        assert audit.ok is True, target
        assert audit.verdict == CONTROL_SHAPE_PASS, target
        assert audit.target == target
        assert audit.fn_name == "factorial_5"
        assert audit.control_prime_sequence == expected
        assert audit.bijection_verdict == "BIJECTIVE_SOLVER"


def test_rosetta_control_shape_gate_rejects_untraced_payloads_all_targets() -> None:
    expected = _prime_tape()

    for target, source in _artifact_sources().items():
        audit = audit_rosetta_control_shape(
            _inject_payload(source, target),
            expression="factorial(5)",
            target=target,
            fn_name="factorial_5",
            expected_primes=expected,
        )

        assert audit.ok is False, target
        assert audit.verdict == UNTRACED_CONTROL_SOURCE, target
        assert audit.control_prime_sequence == expected, target
        assert audit.bijection_verdict == "BIJECTIVE_SOLVER", target
        assert "untraced or tampered executable source" in audit.problems[0], target


def test_rosetta_control_shape_gate_rejects_wrong_expected_prime_tape() -> None:
    source = _artifact_sources()["python"]

    audit = audit_rosetta_control_shape(
        source,
        expression="factorial(5)",
        expected_primes=[2, 3, 5],
    )

    assert audit.ok is False
    assert audit.verdict == CONTROL_SHAPE_MISMATCH
    assert audit.bijection_verdict == "INCOMPLETE_OR_HALLUCINATING"
    assert "control prime tape mismatch" in audit.problems[0]


def test_rosetta_control_shape_gate_rejects_wrong_expression() -> None:
    source = _artifact_sources()["python"]

    audit = audit_rosetta_control_shape(
        source,
        expression="gcd(48,18)",
        expected_primes=_prime_tape(),
    )

    assert audit.ok is False
    assert audit.verdict == UNTRACED_CONTROL_SOURCE


def test_scbe_code_lint_rosetta_control_shape_cli_passes() -> None:
    from tests.agents.test_scbe_code import _run_cli

    source = _artifact_sources()["python"]
    expected = " ".join(str(prime) for prime in _prime_tape())
    rc, stdout, _ = _run_cli(
        [
            "lint-rosetta-control-shape",
            "--content",
            source,
            "--expr",
            "factorial(5)",
            "--expected-primes",
            expected,
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["verdict"] == CONTROL_SHAPE_PASS
    assert payload["target"] == "python"


def test_scbe_code_lint_rosetta_control_shape_cli_rejects_payload() -> None:
    from tests.agents.test_scbe_code import _run_cli

    source = _inject_payload(_artifact_sources()["typescript"], "typescript")
    rc, stdout, _ = _run_cli(
        [
            "lint-rosetta-control-shape",
            "--content",
            source,
            "--expr",
            "factorial(5)",
            "--target",
            "typescript",
            "--fn",
            "factorial_5",
            "--json",
        ]
    )

    assert rc == 1
    payload = json.loads(stdout)
    assert payload["verdict"] == UNTRACED_CONTROL_SOURCE
    assert payload["ok"] is False
