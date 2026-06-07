"""ChemCode: a bounded chemistry-primer language for agentic research tasks.

ChemCode gives the atomic/chemistry primer an executable surface:

    chemistry task source -> safe research events -> atomic/fusion receipts
                         -> numeric control projection -> prime/control tape

The language semantics are Turing-complete because they include mutable
integer variables plus ``while`` loops. The runtime is deliberately fuel-limited
so an agent can use it as a governed research tool without unbounded execution.

This is a computational/symbolic research lane. It does not generate wet-lab
synthesis procedures, dosing guidance, or hazardous material recipes.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from src.cli.tier2_composer import VarEnv, eval_node
from src.cli.tier2_parser import ParseError, parse_expr
from src.tokenizer.atomic_workflow_units import build_atomic_workflow_unit

from .atomic_tokenization import AtomicTokenState, map_token_to_atomic_state
from .chemical_fusion import FusionResult, fuse_atomic_states
from .reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    ReactionStatePacket,
    build_reaction_state_packet,
    sha256_value,
)

SAFE_CHEM_OPS = {
    "observe",
    "measure",
    "lookup",
    "screen",
    "descriptor",
    "compare",
    "report",
}

FORBIDDEN_PATTERNS = (
    r"\bsynth(?:esize|esis|etic)\b",
    r"\broute\s+(?:optimization|planning|synthesis)\b",
    r"\b(?:dose|dosage|administer|clinical\s+advice)\b",
    r"\b(?:weaponize|explosive|detonat(?:e|ion)|toxic\s+gas)\b",
    r"\b(?:fentanyl|methamphetamine|ricin|sarin)\b",
)

CLAIM_BOUNDARY = (
    "ChemCode is a governed computational chemistry research language.",
    "It supports symbolic, descriptor, graph-intent, and literature-evidence tasks.",
    "It does not provide wet-lab synthesis recipes, dosing, or hazardous enablement.",
)


class ChemCodeError(ValueError):
    """Raised for syntax or runtime failures inside ChemCode."""


@dataclass(frozen=True)
class AssignStmt:
    name: str
    expr: str


@dataclass(frozen=True)
class ChemOpStmt:
    op: str
    target: str
    other: str | None = None


@dataclass(frozen=True)
class WhileStmt:
    cond: str
    body: tuple["ChemStatement", ...]


@dataclass(frozen=True)
class IfStmt:
    cond: str
    then_body: tuple["ChemStatement", ...]
    else_body: tuple["ChemStatement", ...] = ()


ChemStatement = AssignStmt | ChemOpStmt | WhileStmt | IfStmt


@dataclass(frozen=True)
class ChemEvent:
    index: int
    op: str
    target: str
    other: str | None
    target_tokens: tuple[str, ...]
    semantic_unit: dict[str, Any]
    chemistry_unit: dict[str, Any]
    fusion_tau_hat: dict[str, int]
    fusion_votes: dict[str, float]
    signed_edge_tension: float
    coherence_penalty: float
    valence_pressure: float
    safety_class: str = "allow_computational_research"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChemCodeResult:
    schema: str
    source_sha256: str
    canonical_source: str
    ok: bool
    safety_verdict: str
    problems: tuple[str, ...]
    turing_complete_claim: str
    fuel_limit: int
    fuel_used: int
    fuel_remaining: int
    final_env: dict[str, Any]
    events: tuple[ChemEvent, ...]
    control_program: str
    control_prime_sequence: tuple[int, ...] = ()
    control_prime_tape: str = ""
    reaction_packet: ReactionStatePacket | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_sha256": self.source_sha256,
            "canonical_source": self.canonical_source,
            "ok": self.ok,
            "safety_verdict": self.safety_verdict,
            "problems": list(self.problems),
            "turing_complete_claim": self.turing_complete_claim,
            "fuel_limit": self.fuel_limit,
            "fuel_used": self.fuel_used,
            "fuel_remaining": self.fuel_remaining,
            "final_env": dict(self.final_env),
            "event_count": len(self.events),
            "events": [event.to_dict() for event in self.events],
            "control_program": self.control_program,
            "control_prime_sequence": list(self.control_prime_sequence),
            "control_prime_tape": self.control_prime_tape,
            "reaction_packet": (
                None if self.reaction_packet is None else self.reaction_packet.to_dict()
            ),
        }


@dataclass
class _Runtime:
    fuel_limit: int
    fuel_used: int = 0
    events: list[ChemEvent] = field(default_factory=list)

    @property
    def fuel_remaining(self) -> int:
        return max(0, self.fuel_limit - self.fuel_used)

    def consume(self, reason: str) -> None:
        if self.fuel_remaining <= 0:
            raise ChemCodeError(f"fuel exhausted before {reason}")
        self.fuel_used += 1


def run_chem_code(
    source: str,
    *,
    fuel: int = 200,
    compile_control: bool = True,
) -> ChemCodeResult:
    """Parse and execute ChemCode source under a bounded fuel budget."""

    source_hash = _source_hash(source)
    canonical = canonicalize_chem_source(source)
    safety_problems = _safety_problems(source)
    if fuel <= 0:
        safety_problems.append("fuel must be positive")
    if safety_problems:
        return _result(
            source_hash=source_hash,
            canonical_source=canonical,
            ok=False,
            safety_verdict="DENY",
            problems=safety_problems,
            fuel_limit=max(0, fuel),
            fuel_used=0,
            final_env={},
            events=[],
            control_program="",
        )

    try:
        statements = parse_chem_code(source)
    except ChemCodeError as exc:
        return _result(
            source_hash=source_hash,
            canonical_source=canonical,
            ok=False,
            safety_verdict="INVALID",
            problems=[str(exc)],
            fuel_limit=fuel,
            fuel_used=0,
            final_env={},
            events=[],
            control_program="",
        )

    env = VarEnv()
    runtime = _Runtime(fuel_limit=fuel)
    problems: list[str] = []
    try:
        _execute_block(statements, env, runtime)
    except (
        ChemCodeError,
        ParseError,
        RecursionError,
        NameError,
        TypeError,
        ValueError,
    ) as exc:
        problems.append(str(exc))

    control_program = _control_program(statements)
    control_primes: tuple[int, ...] = ()
    control_tape = ""
    if compile_control and not problems:
        try:
            from .rosetta_control import build_rosetta_control_node

            node = build_rosetta_control_node(
                control_program,
                targets=("python",),
                fn_name="chem_control",
                run=False,
            )
            control_primes = node.control_tape.primes
            control_tape = node.control_tape.to_dict()["prime_tape"]
            problems.extend(node.problems)
        except (ValueError, RecursionError, TypeError) as exc:
            problems.append(f"control projection failed: {exc}")

    ok = not problems
    packet = _reaction_packet(
        source=source,
        source_hash=source_hash,
        canonical_source=canonical,
        events=runtime.events,
        control_program=control_program,
        ok=ok,
        problems=problems,
    )
    return _result(
        source_hash=source_hash,
        canonical_source=canonical,
        ok=ok,
        safety_verdict="ALLOW" if ok else "QUARANTINE",
        problems=problems,
        fuel_limit=fuel,
        fuel_used=runtime.fuel_used,
        final_env=env.snapshot(),
        events=runtime.events,
        control_program=control_program,
        control_primes=control_primes,
        control_tape=control_tape,
        reaction_packet=packet,
    )


def parse_chem_code(source: str) -> tuple[ChemStatement, ...]:
    """Parse ChemCode source into statements."""
    lines = _logical_lines(source)
    statements, index = _parse_block(lines, 0, stop_on_else=False)
    if index != len(lines):
        raise ChemCodeError(f"unexpected trailing token: {lines[index]!r}")
    return statements


def canonicalize_chem_source(source: str) -> str:
    """Return a normalized source form for hashing, docs, and receipts."""
    return "\n".join(_logical_lines(source))


def _result(
    *,
    source_hash: str,
    canonical_source: str,
    ok: bool,
    safety_verdict: str,
    problems: Sequence[str],
    fuel_limit: int,
    fuel_used: int,
    final_env: dict[str, Any],
    events: Sequence[ChemEvent],
    control_program: str,
    control_primes: Sequence[int] = (),
    control_tape: str = "",
    reaction_packet: ReactionStatePacket | None = None,
) -> ChemCodeResult:
    return ChemCodeResult(
        schema="scbe_chem_code_v1",
        source_sha256=source_hash,
        canonical_source=canonical_source,
        ok=ok,
        safety_verdict=safety_verdict,
        problems=tuple(problems),
        turing_complete_claim=(
            "while loops plus mutable integer variables are sufficient for "
            "Turing-complete semantics; this runtime remains fuel-bounded"
        ),
        fuel_limit=int(fuel_limit),
        fuel_used=int(fuel_used),
        fuel_remaining=max(0, int(fuel_limit) - int(fuel_used)),
        final_env=dict(final_env),
        events=tuple(events),
        control_program=control_program,
        control_prime_sequence=tuple(int(prime) for prime in control_primes),
        control_prime_tape=control_tape,
        reaction_packet=reaction_packet,
    )


def _logical_lines(source: str) -> list[str]:
    expanded = source.replace("{", "\n{\n").replace("}", "\n}\n")
    lines: list[str] = []
    for raw in expanded.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("} else"):
            lines.append("}")
            lines.append("else")
            continue
        lines.append(stripped)
    return lines


def _parse_block(
    lines: Sequence[str], index: int, *, stop_on_else: bool
) -> tuple[tuple[ChemStatement, ...], int]:
    statements: list[ChemStatement] = []
    while index < len(lines):
        line = lines[index]
        if line == "}":
            return tuple(statements), index + 1
        if stop_on_else and line == "else":
            return tuple(statements), index
        if line == "{":
            raise ChemCodeError("unexpected block opener")
        statement, index = _parse_statement(lines, index)
        statements.append(statement)
    return tuple(statements), index


def _parse_statement(lines: Sequence[str], index: int) -> tuple[ChemStatement, int]:
    line = lines[index]
    if line.startswith("while "):
        cond = line[len("while ") :].strip()
        body, next_index = _parse_required_braced_block(lines, index + 1)
        return WhileStmt(cond=cond, body=body), next_index
    if line.startswith("if "):
        cond = line[len("if ") :].strip()
        then_body, next_index = _parse_required_braced_block(lines, index + 1)
        else_body: tuple[ChemStatement, ...] = ()
        if next_index < len(lines) and lines[next_index] == "else":
            else_body, next_index = _parse_required_braced_block(lines, next_index + 1)
        return IfStmt(cond=cond, then_body=then_body, else_body=else_body), next_index

    assignment = re.match(r"^(?:let\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", line)
    if assignment:
        name, expr = assignment.group(1), assignment.group(2).strip()
        return AssignStmt(name=name, expr=expr), index + 1

    return _parse_chem_op(line), index + 1


def _parse_required_braced_block(
    lines: Sequence[str], index: int
) -> tuple[tuple[ChemStatement, ...], int]:
    if index >= len(lines) or lines[index] != "{":
        raise ChemCodeError("expected '{' after control statement")
    return _parse_block(lines, index + 1, stop_on_else=True)


def _parse_chem_op(line: str) -> ChemOpStmt:
    try:
        parts = shlex.split(line, posix=True)
    except ValueError as exc:
        raise ChemCodeError(f"invalid chemistry statement {line!r}: {exc}") from exc
    if not parts:
        raise ChemCodeError("empty chemistry statement")
    op = parts[0].lower()
    if op not in SAFE_CHEM_OPS:
        raise ChemCodeError(f"unsupported or unsafe chemistry op: {op!r}")
    if op == "compare":
        if len(parts) != 3:
            raise ChemCodeError("compare requires exactly two targets")
        return ChemOpStmt(op=op, target=parts[1], other=parts[2])
    if len(parts) < 2:
        raise ChemCodeError(f"{op} requires a target")
    return ChemOpStmt(op=op, target=" ".join(parts[1:]))


def _execute_block(
    statements: Sequence[ChemStatement], env: VarEnv, runtime: _Runtime
) -> Any:
    result: Any = None
    for statement in statements:
        runtime.consume(type(statement).__name__)
        if isinstance(statement, AssignStmt):
            result = _eval_expr(statement.expr, env)
            env.bind(statement.name, result, source_op="chemcode_assign")
        elif isinstance(statement, ChemOpStmt):
            result = _execute_chem_op(statement, runtime)
        elif isinstance(statement, IfStmt):
            branch = (
                statement.then_body
                if _eval_expr(statement.cond, env)
                else statement.else_body
            )
            result = _execute_block(branch, env, runtime)
        elif isinstance(statement, WhileStmt):
            while _eval_expr(statement.cond, env):
                result = _execute_block(statement.body, env, runtime)
        else:
            raise TypeError(f"unknown statement type: {type(statement).__name__}")
    return result


def _eval_expr(expr: str, env: VarEnv) -> Any:
    try:
        return eval_node(parse_expr(expr), env)
    except Exception as exc:  # tier2 raises several small domain exceptions
        raise ChemCodeError(f"expression {expr!r} failed: {exc}") from exc


def _execute_chem_op(statement: ChemOpStmt, runtime: _Runtime) -> ChemEvent:
    index = len(runtime.events)
    target_tokens = _target_tokens(statement.target)
    if statement.other:
        target_tokens += _target_tokens(statement.other)
    states = [
        map_token_to_atomic_state(
            token,
            language="chemcode",
            context_class="chem_research",
        )
        for token in target_tokens
    ]
    fusion = fuse_atomic_states(states)
    event = _event_from_fusion(index, statement, target_tokens, states, fusion)
    runtime.events.append(event)
    return event


def _event_from_fusion(
    index: int,
    statement: ChemOpStmt,
    target_tokens: Sequence[str],
    states: Sequence[AtomicTokenState],
    fusion: FusionResult,
) -> ChemEvent:
    _ = states  # states remain represented through fusion and target tokens.
    return ChemEvent(
        index=index,
        op=statement.op,
        target=statement.target,
        other=statement.other,
        target_tokens=tuple(target_tokens),
        semantic_unit=build_atomic_workflow_unit(statement.op),
        chemistry_unit=build_atomic_workflow_unit(
            statement.target
            if statement.other is None
            else f"{statement.target} {statement.other}"
        ),
        fusion_tau_hat=dict(fusion.tau_hat),
        fusion_votes={
            key: float(value) for key, value in fusion.reconstruction_votes.items()
        },
        signed_edge_tension=float(fusion.signed_edge_tension),
        coherence_penalty=float(fusion.coherence_penalty),
        valence_pressure=float(fusion.valence_pressure),
    )


def _target_tokens(target: str) -> tuple[str, ...]:
    tokens = [
        token
        for token in re.findall(r"[A-Z][a-z]?|[A-Za-z_][A-Za-z0-9_]*|\d+", target)
        if not token.isdigit()
    ]
    return tuple(tokens or [target.strip()])


def _control_program(statements: Sequence[ChemStatement]) -> str:
    lines = ["__chem_events = 0"]
    lines.extend(_control_lines(statements, indent=0))
    lines.append("__chem_events")
    return "\n".join(lines)


def _control_lines(statements: Sequence[ChemStatement], *, indent: int) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    for statement in statements:
        if isinstance(statement, AssignStmt):
            lines.append(f"{pad}{statement.name} = {statement.expr}")
        elif isinstance(statement, ChemOpStmt):
            lines.append(f"{pad}__chem_events = add(__chem_events, 1)")
        elif isinstance(statement, WhileStmt):
            lines.append(f"{pad}while {statement.cond} {{")
            lines.extend(_control_lines(statement.body, indent=indent + 1))
            lines.append(f"{pad}}}")
        elif isinstance(statement, IfStmt):
            lines.append(f"{pad}if {statement.cond} {{")
            lines.extend(_control_lines(statement.then_body, indent=indent + 1))
            if statement.else_body:
                lines.append(f"{pad}}} else {{")
                lines.extend(_control_lines(statement.else_body, indent=indent + 1))
            lines.append(f"{pad}}}")
    return lines


def _reaction_packet(
    *,
    source: str,
    source_hash: str,
    canonical_source: str,
    events: Sequence[ChemEvent],
    control_program: str,
    ok: bool,
    problems: Sequence[str],
) -> ReactionStatePacket:
    target_payload = {
        "canonical_source": canonical_source,
        "events": [event.to_dict() for event in events],
        "control_program": control_program,
    }
    loss_notes = list(problems)
    recovery_evidence: list[str] = []
    if ok:
        loss_notes.append(
            "source formatting/comments normalized; canonical source retained"
        )
        recovery_evidence.extend(
            [
                "canonical ChemCode source retained",
                "source hash retained for exact external comparison",
            ]
        )
    return build_reaction_state_packet(
        domain="chem",
        step=1,
        bounded_operation="chemcode_execute",
        source=ReactionEndpoint(
            identity="chemcode:source",
            representation="chemcode_source",
            language="chemcode",
            payload_sha256=source_hash,
        ),
        target=ReactionEndpoint(
            identity="chemcode:research_event_ledger",
            representation="safe_research_events_plus_control_projection",
            language="json",
            payload_sha256=sha256_value(target_payload),
            metadata={"event_count": len(events)},
        ),
        semantic_engravings=[
            "chemistry primer statements lowered to bounded research events",
            "numeric branch and loop structure projected into Rosetta control tape",
        ],
        loss_notes=loss_notes,
        recalculation=ReactionRecalculation(
            syntax_ok=ok,
            scientific_checks_ok=ok,
            unit_checks_ok=ok,
            identity_ok=ok,
            extra={"source_sha256": source_hash, "event_count": len(events)},
        ),
        identity_preserved=ok,
        recovery_evidence=recovery_evidence,
        claim_boundary=list(CLAIM_BOUNDARY),
    )


def _safety_problems(source: str) -> list[str]:
    lowered = source.lower()
    problems: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            problems.append(f"denied unsafe chemistry request pattern: {pattern}")
    return problems


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def result_to_json(result: ChemCodeResult) -> str:
    """Serialize a result with stable key ordering."""
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)
