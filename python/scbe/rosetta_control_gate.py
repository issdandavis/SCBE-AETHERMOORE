"""Strict source-shape gate for Rosetta bounded-control output.

The control tape proves the semantic program shape. This gate proves the
language body is exactly the compiler-owned scaffold for that semantic program,
so extra executable source cannot ride behind a valid control tape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Sequence

from src.governance.bijection_gate import audit_bijection

from .prime_ir import parse_prime_sequence
from .rosetta_control import CONTROL_TARGETS, build_rosetta_control_node

CONTROL_SHAPE_PASS = "CONTROL_SHAPE_PASS"
CONTROL_SHAPE_MISMATCH = "CONTROL_SHAPE_MISMATCH"
MISSING_CONTROL_IDENTITY = "MISSING_CONTROL_IDENTITY"
UNTRACED_CONTROL_SOURCE = "UNTRACED_CONTROL_SOURCE"


@dataclass(frozen=True)
class ControlShapeAudit:
    """Result of auditing a bounded-control source scaffold."""

    schema: str
    verdict: str
    ok: bool
    expression: str
    target: str | None
    fn_name: str | None
    control_prime_sequence: tuple[int, ...]
    control_prime_derivative: tuple[int, ...]
    control_shape_hash: str
    expected_prime_sequence: tuple[int, ...] | None = None
    bijection_verdict: str | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "verdict": self.verdict,
            "ok": self.ok,
            "expression": self.expression,
            "target": self.target,
            "fn_name": self.fn_name,
            "control_prime_sequence": list(self.control_prime_sequence),
            "control_prime_derivative": list(self.control_prime_derivative),
            "control_shape_hash": self.control_shape_hash,
            "expected_prime_sequence": (
                None
                if self.expected_prime_sequence is None
                else list(self.expected_prime_sequence)
            ),
            "bijection_verdict": self.bijection_verdict,
            "problems": list(self.problems),
        }


def audit_rosetta_control_shape(
    source: str,
    *,
    expression: str,
    target: str | None = None,
    fn_name: str | None = None,
    expected_primes: Sequence[int] | str | None = None,
) -> ControlShapeAudit:
    """Audit that source is the exact Rosetta control scaffold for expression.

    Args:
        source: Generated source body for one control target.
        expression: Canonical Tier-2 expression/program that owns the source.
        target: Optional target language. Inferred from the source when omitted.
        fn_name: Optional function name. Inferred from the source when omitted.
        expected_primes: Optional expected control-tape prime sequence.

    This does not attempt to prove arbitrary human code is equivalent. It proves
    a generated body is exactly the compiler-owned body for a known expression.
    """
    problems: list[str] = []
    identity = _detect_identity(source)
    resolved_target = _normalize_target(target, problems)
    resolved_fn = fn_name

    if identity is not None:
        detected_target, detected_fn = identity
        if resolved_target is None:
            resolved_target = detected_target
        elif resolved_target != detected_target:
            problems.append(
                f"target mismatch: expected {resolved_target!r}, source looks like {detected_target!r}"
            )
        if resolved_fn is None:
            resolved_fn = detected_fn
        elif resolved_fn != detected_fn:
            problems.append(
                f"function mismatch: expected {resolved_fn!r}, source declares {detected_fn!r}"
            )

    if resolved_target is None or resolved_fn is None:
        problems.append(
            "source has no unambiguous Rosetta control target/function identity"
        )
        return _audit_result(
            verdict=MISSING_CONTROL_IDENTITY,
            expression=expression,
            target=resolved_target,
            fn_name=resolved_fn,
            problems=problems,
        )

    generated_primes: tuple[int, ...] = ()
    try:
        node = build_rosetta_control_node(
            expression,
            targets=[resolved_target],
            fn_name=resolved_fn,
            run=False,
        )
        generated_primes = node.control_tape.primes
        expected_artifact = node.artifacts[0]
    except (ValueError, TypeError, IndexError) as exc:
        problems.append(f"could not regenerate Rosetta control source: {exc}")
        return _audit_result(
            verdict=CONTROL_SHAPE_MISMATCH,
            expression=expression,
            target=resolved_target,
            fn_name=resolved_fn,
            prime_sequence=generated_primes,
            problems=problems,
        )

    if _normalize_source(source) != _normalize_source(expected_artifact.source):
        problems.append(
            "source body is not the generated Rosetta control scaffold: "
            "untraced or tampered executable source"
        )

    expected_sequence = _normalize_expected_primes(expected_primes)
    bijection_verdict = None
    if expected_sequence is not None:
        bijection = audit_bijection(
            _slot_map(expected_sequence), _slot_map(generated_primes)
        )
        bijection_verdict = bijection.verdict
        if not bijection.usable_as_router:
            problems.append(f"control prime tape mismatch: {bijection.verdict}")

    if any(problem.startswith("source body is not") for problem in problems):
        verdict = UNTRACED_CONTROL_SOURCE
    elif problems:
        verdict = CONTROL_SHAPE_MISMATCH
    else:
        verdict = CONTROL_SHAPE_PASS

    return _audit_result(
        verdict=verdict,
        expression=expression,
        target=resolved_target,
        fn_name=resolved_fn,
        prime_sequence=generated_primes,
        expected_prime_sequence=expected_sequence,
        bijection_verdict=bijection_verdict,
        problems=problems,
    )


_PY_RE = re.compile(r"^def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\(\):$")
_TS_RE = re.compile(
    r"^export\s+function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\(\):\s*number\s*\{$"
)
_GO_RE = re.compile(r"^func\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\(\)\s+float64\s*\{$")
_C_RE = re.compile(r"^double\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\(void\)\s*\{$")


def _detect_identity(source: str) -> tuple[str, str] | None:
    first_line = _first_code_line(source)
    for target, regex in (
        ("python", _PY_RE),
        ("typescript", _TS_RE),
        ("go", _GO_RE),
        ("c", _C_RE),
    ):
        match = regex.match(first_line)
        if match:
            return target, match.group("name")
    return None


def _first_code_line(source: str) -> str:
    for raw in source.lstrip().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("#", "//")):
            continue
        return line
    return ""


def _normalize_target(target: str | None, problems: list[str]) -> str | None:
    if target is None:
        return None
    normalized = target.strip().lower()
    if normalized not in CONTROL_TARGETS:
        problems.append(f"unsupported Rosetta control target: {target!r}")
        return None
    return normalized


def _normalize_expected_primes(
    values: Sequence[int] | str | None,
) -> tuple[int, ...] | None:
    if values is None:
        return None
    if isinstance(values, str):
        if not values.strip():
            return None
        return tuple(parse_prime_sequence(values))
    return tuple(int(value) for value in values)


def _slot_map(primes: Sequence[int]) -> dict[str, str]:
    return {f"slot:{i}": f"slot:{i}:prime:{prime}" for i, prime in enumerate(primes)}


def _normalize_source(source: str) -> str:
    return "\n".join(line.rstrip() for line in source.strip().splitlines())


def _prime_derivative(primes: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(primes[i + 1]) - int(primes[i]) for i in range(len(primes) - 1))


def _shape_hash(
    expression: str, target: str | None, fn_name: str | None, primes: Sequence[int]
) -> str:
    payload = {
        "expression": expression,
        "target": target,
        "fn_name": fn_name,
        "prime_sequence": list(primes),
        "prime_derivative": list(_prime_derivative(primes)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _audit_result(
    *,
    verdict: str,
    expression: str,
    target: str | None,
    fn_name: str | None,
    problems: Sequence[str],
    prime_sequence: Sequence[int] = (),
    expected_prime_sequence: Sequence[int] | None = None,
    bijection_verdict: str | None = None,
) -> ControlShapeAudit:
    primes = tuple(int(prime) for prime in prime_sequence)
    return ControlShapeAudit(
        schema="scbe_rosetta_control_shape_gate_v1",
        verdict=verdict,
        ok=verdict == CONTROL_SHAPE_PASS,
        expression=expression,
        target=target,
        fn_name=fn_name,
        control_prime_sequence=primes,
        control_prime_derivative=_prime_derivative(primes),
        control_shape_hash=_shape_hash(expression, target, fn_name, primes),
        expected_prime_sequence=(
            None
            if expected_prime_sequence is None
            else tuple(int(prime) for prime in expected_prime_sequence)
        ),
        bijection_verdict=bijection_verdict,
        problems=tuple(str(problem) for problem in problems),
    )
