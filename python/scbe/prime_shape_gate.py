"""Security gate for prime-shaped opcode traces.

Generated code can be treated as valid only when it carries a reversible opcode
shape witness:

    source trace comments -> CA opcodes -> ordered prime tape -> optional expected tape

This gate is intentionally about code composition, not primality discovery. The
prime tape is a deterministic security shape that proves the source still
matches the command substrate it claims to implement.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from src.governance.bijection_gate import audit_bijection

from .ca_opcode_table import OP_TABLE
from .prime_ir import encode_opcodes_to_primes, parse_prime_sequence
from .tongue_isa import disassemble

PRIME_OPCODE_SHAPE_PASS = "PRIME_OPCODE_SHAPE_PASS"
MISSING_OPCODE_TRACE = "MISSING_OPCODE_TRACE"
INVALID_OPCODE_TRACE = "INVALID_OPCODE_TRACE"
PRIME_SHAPE_MISMATCH = "PRIME_SHAPE_MISMATCH"
UNTRACED_SOURCE_BODY = "UNTRACED_SOURCE_BODY"


@dataclass(frozen=True)
class PrimeShapeAudit:
    """Result of auditing a source file's prime-opcode shape."""

    schema: str
    verdict: str
    ok: bool
    trace_count: int
    opcodes: tuple[int, ...]
    op_names: tuple[str, ...]
    prime_sequence: tuple[int, ...]
    prime_derivative: tuple[int, ...]
    prime_shape_hash: str
    expected_prime_sequence: tuple[int, ...] | None = None
    bijection_verdict: str | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "verdict": self.verdict,
            "ok": self.ok,
            "trace_count": self.trace_count,
            "opcodes": list(self.opcodes),
            "op_names": list(self.op_names),
            "prime_sequence": list(self.prime_sequence),
            "prime_derivative": list(self.prime_derivative),
            "prime_shape_hash": self.prime_shape_hash,
            "expected_prime_sequence": (
                None
                if self.expected_prime_sequence is None
                else list(self.expected_prime_sequence)
            ),
            "bijection_verdict": self.bijection_verdict,
            "problems": list(self.problems),
        }


def audit_prime_opcode_shape(
    source: str,
    *,
    expected_primes: Sequence[int] | str | None = None,
    strict_generated: bool = True,
) -> PrimeShapeAudit:
    """Audit source code for a valid prime-coded opcode shape.

    Args:
        source: Source text containing opcode trace comments such as
            `# abs (0x09)` or `// add (0x00)`.
        expected_primes: Optional ordered prime tape. If provided, the source's
            recovered prime tape must match slot-by-slot.
        strict_generated: When true, generated CA output must exactly match the
            compiler scaffold regenerated from the recovered opcode trace. This
            prevents extra executable lines from hiding behind a valid trace.
    """
    problems: list[str] = []
    trace = disassemble(source)
    if not trace:
        return _audit_result(
            verdict=MISSING_OPCODE_TRACE,
            problems=["source has no CA opcode trace comments"],
        )

    opcodes: list[int] = []
    op_names: list[str] = []
    for op_id, op_name in trace:
        entry = OP_TABLE.get(op_id)
        if entry is None:
            problems.append(f"unknown opcode 0x{op_id:02X}")
            continue
        if entry.name != op_name:
            problems.append(
                f"opcode/name mismatch: 0x{op_id:02X} is {entry.name!r}, got {op_name!r}"
            )
        opcodes.append(op_id)
        op_names.append(op_name)

    prime_sequence = encode_opcodes_to_primes(opcodes) if opcodes else []
    if strict_generated and opcodes and not problems:
        scaffold_problem = _python_generated_scaffold_problem(source, opcodes)
        if scaffold_problem:
            problems.append(scaffold_problem)

    expected_sequence = _normalize_expected_primes(expected_primes)
    bijection_verdict = None
    if expected_sequence is not None:
        truth = _slot_map(expected_sequence)
        candidate = _slot_map(prime_sequence)
        bijection = audit_bijection(truth, candidate)
        bijection_verdict = bijection.verdict
        if not bijection.usable_as_router:
            problems.append(f"prime tape mismatch: {bijection.verdict}")

    if any(
        problem.startswith("source body is not the generated CA scaffold")
        for problem in problems
    ):
        verdict = UNTRACED_SOURCE_BODY
    elif problems:
        verdict = (
            PRIME_SHAPE_MISMATCH
            if expected_sequence is not None
            else INVALID_OPCODE_TRACE
        )
    else:
        verdict = PRIME_OPCODE_SHAPE_PASS

    return _audit_result(
        verdict=verdict,
        problems=problems,
        opcodes=opcodes,
        op_names=op_names,
        prime_sequence=prime_sequence,
        expected_prime_sequence=expected_sequence,
        bijection_verdict=bijection_verdict,
    )


def _normalize_expected_primes(
    values: Sequence[int] | str | None,
) -> tuple[int, ...] | None:
    if values is None:
        return None
    if isinstance(values, str):
        return tuple(parse_prime_sequence(values))
    return tuple(int(value) for value in values)


def _slot_map(primes: Sequence[int]) -> dict[str, str]:
    return {f"slot:{i}": f"slot:{i}:prime:{prime}" for i, prime in enumerate(primes)}


def _python_generated_scaffold_problem(
    source: str, opcodes: Sequence[int]
) -> str | None:
    """Return a problem string when source is not compiler-owned.

    The trace proves only the marked opcode rows. The stronger generated
    scaffold check proves that there are no untraced executable rows, imports,
    calls, or tampered stack mutations wrapped around those opcode rows.
    """
    identity = _detect_generated_identity(source)
    if identity is None:
        return "source body is not the generated CA scaffold: unsupported or ambiguous target"
    target, fn_name, arg_names = identity

    try:
        expected = _render_compiled_source(
            opcodes, target=target, fn_name=fn_name, arg_names=arg_names
        )
    except ValueError as exc:
        return f"source body is not the generated CA scaffold: {exc}"

    if _normalize_source(source) != _normalize_source(expected):
        return "source body is not the generated CA scaffold: untraced or tampered executable source"
    return None


def _detect_generated_identity(source: str) -> tuple[str, str, list[str]] | None:
    stripped = source.lstrip()
    lines = stripped.splitlines()
    first_line = lines[0].strip() if lines else ""
    if first_line.startswith("def "):
        return _detect_python_identity(source)
    if first_line.startswith("export function "):
        return _detect_typescript_identity(first_line)
    if first_line.startswith("func "):
        return _detect_go_identity(first_line)
    if first_line.startswith("double "):
        return _detect_c_identity(first_line)
    return _detect_haskell_identity(first_line)


def _detect_python_identity(source: str) -> tuple[str, str, list[str]] | None:
    try:
        module = ast.parse(source)
    except SyntaxError:
        return None

    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        return None

    function = module.body[0]
    if (
        function.args.posonlyargs
        or function.args.vararg
        or function.args.kwonlyargs
        or function.args.kw_defaults
        or function.args.kwarg
        or function.args.defaults
    ):
        return None

    return ("python", function.name, [arg.arg for arg in function.args.args])


_TS_SIGNATURE_RE = re.compile(
    r"^export\s+function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\((?P<args>[^)]*)\):\s*number\s*\|\s*null\s*\{$"
)
_GO_SIGNATURE_RE = re.compile(
    r"^func\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\((?P<args>[^)]*)\)\s+interface\{\}\s*\{$"
)
_C_SIGNATURE_RE = re.compile(
    r"^double\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)" r"\((?P<args>[^)]*)\)\s*\{$"
)
_HS_SIGNATURE_RE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_']*)"
    r"(?P<args>(?:\s+[A-Za-z_][A-Za-z0-9_']*)*)\s*=$"
)


def _detect_typescript_identity(first_line: str) -> tuple[str, str, list[str]] | None:
    match = _TS_SIGNATURE_RE.match(first_line)
    if not match:
        return None
    args = []
    for raw in _split_signature_args(match.group("args")):
        arg_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*number$", raw)
        if not arg_match:
            return None
        args.append(arg_match.group(1))
    return ("typescript", match.group("name"), args)


def _detect_go_identity(first_line: str) -> tuple[str, str, list[str]] | None:
    match = _GO_SIGNATURE_RE.match(first_line)
    if not match:
        return None
    args = []
    for raw in _split_signature_args(match.group("args")):
        arg_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+float64$", raw)
        if not arg_match:
            return None
        args.append(arg_match.group(1))
    return ("go", match.group("name"), args)


def _detect_c_identity(first_line: str) -> tuple[str, str, list[str]] | None:
    match = _C_SIGNATURE_RE.match(first_line)
    if not match:
        return None
    args = []
    for raw in _split_signature_args(match.group("args")):
        arg_match = re.match(r"^double\s+([A-Za-z_][A-Za-z0-9_]*)$", raw)
        if not arg_match:
            return None
        args.append(arg_match.group(1))
    return ("c", match.group("name"), args)


def _detect_haskell_identity(first_line: str) -> tuple[str, str, list[str]] | None:
    match = _HS_SIGNATURE_RE.match(first_line)
    if not match:
        return None
    return (
        "haskell",
        match.group("name"),
        [arg for arg in match.group("args").split() if arg],
    )


def _split_signature_args(args: str) -> list[str]:
    return [arg.strip() for arg in args.split(",") if arg.strip()]


def _render_compiled_source(
    opcodes: Sequence[int], *, target: str, fn_name: str, arg_names: Sequence[str]
) -> str:
    from .tongue_isa import compile_ca_tokens, wrap_program_source

    program = compile_ca_tokens(
        opcodes,
        target=target,
        fn_name=fn_name,
        arg_names=arg_names,
    )
    return wrap_program_source(program)


def _normalize_source(source: str) -> str:
    return "\n".join(line.rstrip() for line in source.strip().splitlines())


def _prime_derivative(primes: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(primes[i + 1]) - int(primes[i]) for i in range(len(primes) - 1))


def _shape_hash(opcodes: Sequence[int], primes: Sequence[int]) -> str:
    payload = {
        "opcodes": list(opcodes),
        "prime_sequence": list(primes),
        "prime_derivative": list(_prime_derivative(primes)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _audit_result(
    *,
    verdict: str,
    problems: Sequence[str],
    opcodes: Sequence[int] = (),
    op_names: Sequence[str] = (),
    prime_sequence: Sequence[int] = (),
    expected_prime_sequence: Sequence[int] | None = None,
    bijection_verdict: str | None = None,
) -> PrimeShapeAudit:
    primes = tuple(int(prime) for prime in prime_sequence)
    return PrimeShapeAudit(
        schema="scbe_prime_opcode_shape_gate_v1",
        verdict=verdict,
        ok=verdict == PRIME_OPCODE_SHAPE_PASS,
        trace_count=len(opcodes),
        opcodes=tuple(int(opcode) for opcode in opcodes),
        op_names=tuple(str(name) for name in op_names),
        prime_sequence=primes,
        prime_derivative=_prime_derivative(primes),
        prime_shape_hash=_shape_hash(opcodes, primes),
        expected_prime_sequence=(
            None
            if expected_prime_sequence is None
            else tuple(int(prime) for prime in expected_prime_sequence)
        ),
        bijection_verdict=bijection_verdict,
        problems=tuple(str(problem) for problem in problems),
    )
