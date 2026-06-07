"""Ingress gate for compiler-owned Rosetta control source.

This is the narrow v1 inverse lane:

    generated source -> Rosetta source label -> exact scaffold proof -> control tape

It intentionally does not claim arbitrary human-written source can be parsed into
the control ISA. It accepts only source that carries the generated Rosetta label
and still matches the compiler-owned scaffold for that label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from .prime_ir import parse_prime_sequence
from .rosetta_control import (
    CONTROL_TARGETS,
    SOURCE_IDENTITY_SCHEMA,
    build_rosetta_control_node,
    parse_control_source_header,
)
from .rosetta_control_gate import (
    CONTROL_SHAPE_PASS,
    audit_rosetta_control_shape,
)

CONTROL_SOURCE_INGRESS_PASS = "CONTROL_SOURCE_INGRESS_PASS"
MISSING_CONTROL_SOURCE_HEADER = "MISSING_CONTROL_SOURCE_HEADER"
INVALID_CONTROL_SOURCE_HEADER = "INVALID_CONTROL_SOURCE_HEADER"
CONTROL_SOURCE_SHAPE_FAILED = "CONTROL_SOURCE_SHAPE_FAILED"


@dataclass(frozen=True)
class ControlSourceIngress:
    """Source-to-tape ingress record for generated Rosetta control code."""

    schema: str
    verdict: str
    ok: bool
    expression: str | None
    target: str | None
    fn_name: str | None
    value: float | None
    control_bytes_hex: tuple[str, ...]
    control_prime_sequence: tuple[int, ...]
    roles: tuple[str, ...]
    shape_verdict: str | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "verdict": self.verdict,
            "ok": self.ok,
            "expression": self.expression,
            "target": self.target,
            "fn_name": self.fn_name,
            "value": self.value,
            "control_bytes_hex": list(self.control_bytes_hex),
            "control_prime_sequence": list(self.control_prime_sequence),
            "prime_tape": " ".join(str(prime) for prime in self.control_prime_sequence),
            "roles": list(self.roles),
            "shape_verdict": self.shape_verdict,
            "problems": list(self.problems),
        }


def ingest_rosetta_control_source(
    source: str,
    *,
    expected_primes: Sequence[int] | str | None = None,
) -> ControlSourceIngress:
    """Accept generated Rosetta control source and return its canonical tape."""
    header = parse_control_source_header(source)
    if header is None:
        return _ingress_result(
            verdict=MISSING_CONTROL_SOURCE_HEADER,
            problems=["source has no Rosetta control identity header"],
        )

    problems = _header_problems(header)
    expression = _string_field(header, "expression")
    target = _string_field(header, "target")
    fn_name = _string_field(header, "fn_name")
    header_primes = _string_field(header, "prime_tape")

    if problems or expression is None or target is None or fn_name is None:
        return _ingress_result(
            verdict=INVALID_CONTROL_SOURCE_HEADER,
            expression=expression,
            target=target,
            fn_name=fn_name,
            problems=problems,
        )

    expected_sequence = _normalize_expected_primes(expected_primes)
    shape_expected = (
        expected_sequence if expected_sequence is not None else header_primes
    )
    shape = audit_rosetta_control_shape(
        source,
        expression=expression,
        target=target,
        fn_name=fn_name,
        expected_primes=shape_expected,
    )
    if shape.verdict != CONTROL_SHAPE_PASS:
        return _ingress_result(
            verdict=CONTROL_SOURCE_SHAPE_FAILED,
            expression=expression,
            target=target,
            fn_name=fn_name,
            shape_verdict=shape.verdict,
            problems=shape.problems,
        )

    node = build_rosetta_control_node(
        expression,
        targets=[target],
        fn_name=fn_name,
        run=False,
    )
    tape = node.control_tape.to_dict()
    return _ingress_result(
        verdict=CONTROL_SOURCE_INGRESS_PASS,
        problems=(),
        expression=expression,
        target=target,
        fn_name=fn_name,
        value=node.value,
        control_bytes_hex=tuple(tape["bytes_hex"]),
        control_prime_sequence=node.control_tape.primes,
        roles=node.control_tape.roles,
        shape_verdict=shape.verdict,
    )


def _header_problems(header: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if header.get("schema") != SOURCE_IDENTITY_SCHEMA:
        problems.append("header schema is not scbe_rosetta_control_source_v1")
    for field_name in ("expression", "target", "fn_name", "prime_tape"):
        if (
            not isinstance(header.get(field_name), str)
            or not header[field_name].strip()
        ):
            problems.append(f"header missing string field {field_name!r}")
    target = header.get("target")
    if isinstance(target, str) and target.strip().lower() not in CONTROL_TARGETS:
        problems.append(f"unsupported Rosetta control target in header: {target!r}")
    prime_tape = header.get("prime_tape")
    if isinstance(prime_tape, str) and prime_tape.strip():
        try:
            parse_prime_sequence(prime_tape)
        except ValueError as exc:
            problems.append(f"header prime_tape is invalid: {exc}")
    return problems


def _string_field(header: dict[str, Any], field_name: str) -> str | None:
    value = header.get(field_name)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


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


def _ingress_result(
    *,
    verdict: str,
    problems: Sequence[str],
    expression: str | None = None,
    target: str | None = None,
    fn_name: str | None = None,
    value: float | None = None,
    control_bytes_hex: Sequence[str] = (),
    control_prime_sequence: Sequence[int] = (),
    roles: Sequence[str] = (),
    shape_verdict: str | None = None,
) -> ControlSourceIngress:
    return ControlSourceIngress(
        schema="scbe_rosetta_control_source_ingress_v1",
        verdict=verdict,
        ok=verdict == CONTROL_SOURCE_INGRESS_PASS,
        expression=expression,
        target=target,
        fn_name=fn_name,
        value=value,
        control_bytes_hex=tuple(str(value) for value in control_bytes_hex),
        control_prime_sequence=tuple(int(prime) for prime in control_prime_sequence),
        roles=tuple(str(role) for role in roles),
        shape_verdict=shape_verdict,
        problems=tuple(str(problem) for problem in problems),
    )
