from __future__ import annotations

import json

from python.scbe.prime_shape_gate import (
    INVALID_OPCODE_TRACE,
    MISSING_OPCODE_TRACE,
    PRIME_OPCODE_SHAPE_PASS,
    PRIME_SHAPE_MISMATCH,
    UNTRACED_SOURCE_BODY,
    audit_prime_opcode_shape,
)

VALID_SOURCE = (
    "def abs_add(a, b):\n"
    "    _stack: list = [a, b]\n"
    "    a = _stack.pop(); _stack.append(abs(a))  # abs (0x09)\n"
    "    a = _stack.pop(); _stack.append(abs(a))  # abs (0x09)\n"
    "    b = _stack.pop(); a = _stack.pop(); _stack.append(a + b)  # add (0x00)\n"
    "    return _stack[-1] if _stack else None\n"
)

BAD_EXTRA_EXECUTABLE_SOURCE = (
    "def abs_add(a, b):\n"
    "    import os\n"
    '    os.system("echo pwned")\n'
    "    _stack: list = [a, b]\n"
    "    a = _stack.pop(); _stack.append(abs(a))  # abs (0x09)\n"
    "    a = _stack.pop(); _stack.append(abs(a))  # abs (0x09)\n"
    "    b = _stack.pop(); a = _stack.pop(); _stack.append(a + b)  # add (0x00)\n"
    "    return _stack[-1] if _stack else None\n"
)


def _generated_source(target: str) -> str:
    from python.scbe.tongue_isa import compile_ca_tokens, wrap_program_source

    program = compile_ca_tokens(
        [0x09, 0x09, 0x00],
        target=target,
        fn_name="abs_add",
        arg_names=["a", "b"],
    )
    return wrap_program_source(program)


def _inject_target_payload(source: str, target: str) -> str:
    if target == "python":
        return BAD_EXTRA_EXECUTABLE_SOURCE
    if target == "typescript":
        return source.replace(
            "{\n", '{\n  require("child_process").execSync("echo pwned");\n', 1
        )
    if target == "go":
        return source.replace("{\n", '{\n\texec.Command("echo", "pwned").Run()\n', 1)
    if target == "c":
        return source.replace("{\n", '{\n    system("echo pwned");\n', 1)
    if target == "haskell":
        return source.replace("  let\n", "  let\n    pwn = 1\n", 1)
    raise AssertionError(target)


def test_prime_shape_gate_passes_valid_trace_and_expected_tape() -> None:
    audit = audit_prime_opcode_shape(VALID_SOURCE, expected_primes=[29, 29, 2])

    assert audit.ok is True
    assert audit.verdict == PRIME_OPCODE_SHAPE_PASS
    assert audit.opcodes == (9, 9, 0)
    assert audit.prime_sequence == (29, 29, 2)
    assert audit.prime_derivative == (0, -27)
    assert audit.bijection_verdict == "BIJECTIVE_SOLVER"


def test_prime_shape_gate_rejects_missing_trace() -> None:
    audit = audit_prime_opcode_shape("def f(a, b):\n    return abs(a) + abs(b)\n")

    assert audit.ok is False
    assert audit.verdict == MISSING_OPCODE_TRACE
    assert audit.problems == ("source has no CA opcode trace comments",)


def test_prime_shape_gate_rejects_opcode_name_mismatch() -> None:
    tampered = VALID_SOURCE.replace("# abs (0x09)", "# add (0x09)", 1)

    audit = audit_prime_opcode_shape(tampered)

    assert audit.ok is False
    assert audit.verdict == INVALID_OPCODE_TRACE
    assert "opcode/name mismatch" in audit.problems[0]


def test_prime_shape_gate_rejects_wrong_expected_tape() -> None:
    audit = audit_prime_opcode_shape(VALID_SOURCE, expected_primes=[2, 29, 29])

    assert audit.ok is False
    assert audit.verdict == PRIME_SHAPE_MISMATCH
    assert audit.bijection_verdict == "INCOMPLETE_OR_HALLUCINATING"
    assert "prime tape mismatch" in audit.problems[0]


def test_prime_shape_gate_rejects_untraced_executable_source() -> None:
    audit = audit_prime_opcode_shape(
        BAD_EXTRA_EXECUTABLE_SOURCE, expected_primes=[29, 29, 2]
    )

    assert audit.ok is False
    assert audit.verdict == UNTRACED_SOURCE_BODY
    assert audit.prime_sequence == (29, 29, 2)
    assert audit.bijection_verdict == "BIJECTIVE_SOLVER"
    assert "untraced or tampered executable source" in audit.problems[0]


def test_prime_shape_gate_passes_all_generated_target_scaffolds() -> None:
    for target in ("python", "typescript", "go", "c", "haskell"):
        audit = audit_prime_opcode_shape(
            _generated_source(target), expected_primes=[29, 29, 2]
        )

        assert audit.ok is True, target
        assert audit.verdict == PRIME_OPCODE_SHAPE_PASS, target


def test_prime_shape_gate_rejects_untraced_executable_source_in_all_targets() -> None:
    for target in ("python", "typescript", "go", "c", "haskell"):
        source = _inject_target_payload(_generated_source(target), target)
        audit = audit_prime_opcode_shape(source, expected_primes=[29, 29, 2])

        assert audit.ok is False, target
        assert audit.verdict == UNTRACED_SOURCE_BODY, target
        assert audit.prime_sequence == (29, 29, 2), target
        assert audit.bijection_verdict == "BIJECTIVE_SOLVER", target


def test_scbe_code_lint_prime_shape_cli() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "lint-prime-shape",
            "--content",
            VALID_SOURCE,
            "--expected-primes",
            "29 29 2",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["verdict"] == PRIME_OPCODE_SHAPE_PASS
    assert payload["prime_sequence"] == [29, 29, 2]


def test_scbe_code_lint_prime_shape_cli_rejects_untraced_executable_source() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "lint-prime-shape",
            "--content",
            BAD_EXTRA_EXECUTABLE_SOURCE,
            "--expected-primes",
            "29 29 2",
            "--json",
        ]
    )

    assert rc == 1
    payload = json.loads(stdout)
    assert payload["verdict"] == UNTRACED_SOURCE_BODY
    assert payload["ok"] is False
