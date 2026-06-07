"""Rosetta control node for bounded Tier-2 programs.

The v1 Rosetta node compiles a linear CA opcode stack tape. This module handles
the next layer: variable binding, branch, and bounded loop programs parsed by
``src.cli.tier2_parser``.

The canonical identity is a 256-byte control ISA tape:

* ``0x00``-``0x3f``: existing CA opcode rows
* ``0x40``-``0x4f``: control rows (LET, IF, WHILE, END, ...)
* ``0x50``-``0x5f`` and ``0x80``-``0xbf``: deterministic variable slots
* ``0x60``-``0x7f`` and ``0xc0``-``0xff``: small literals
* ``0x4c`` + int64: large literal payload

Every byte maps to the corresponding prime by byte index. For the first 64
bytes this preserves the existing CA prime table exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

from python.scbe.ca_opcode_table import OP_TABLE
from python.scbe.prime_ir import first_primes
from src.cli.tier2_composer import (
    IfNode,
    LetNode,
    LitNode,
    NodeType,
    OpNode,
    SeqNode,
    VarEnv,
    VarNode,
    WhileNode,
    eval_node,
)
from src.cli.tier2_parser import parse

CONTROL_TARGETS = ("python", "typescript", "go", "c")
RUNTIME_SKIPPED = "SKIPPED_NO_RUNTIME"
RUNTIME_NOT_REQUESTED = "NOT_REQUESTED"
RUNTIME_PASS = "PASS"
RUNTIME_FAIL = "FAIL"
SOURCE_IDENTITY_SCHEMA = "scbe_rosetta_control_source_v1"
SOURCE_IDENTITY_TAG = "SCBE_ROSETTA_CONTROL_V1"


class Ctrl:
    LET = 0x40
    IF = 0x41
    ELSE = 0x42
    END = 0x43
    WHILE = 0x44
    DEF = 0x45
    CALL = 0x46
    RET = 0x47
    SEQ = 0x48
    PUSH = 0x49
    POP = 0x4A
    NOP = 0x4B
    CONST = 0x4C
    VAR = 0x4D
    ARG = 0x4E
    HALT = 0x4F


CTRL_NAMES = {
    Ctrl.LET: "LET",
    Ctrl.IF: "IF",
    Ctrl.ELSE: "ELSE",
    Ctrl.END: "END",
    Ctrl.WHILE: "WHILE",
    Ctrl.DEF: "DEF",
    Ctrl.CALL: "CALL",
    Ctrl.RET: "RET",
    Ctrl.SEQ: "SEQ",
    Ctrl.PUSH: "PUSH",
    Ctrl.POP: "POP",
    Ctrl.NOP: "NOP",
    Ctrl.CONST: "CONST",
    Ctrl.VAR: "VAR",
    Ctrl.ARG: "ARG",
    Ctrl.HALT: "HALT",
}

_BYTE_PRIMES = tuple(first_primes(256))


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    value: float | None = None
    error: str = ""
    command: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "value": self.value,
            "error": self.error,
            "command": list(self.command),
        }


@dataclass(frozen=True)
class ControlArtifact:
    target: str
    source: str
    source_chars: int
    runtime: RuntimeResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "source_chars": self.source_chars,
            "runtime": self.runtime.to_dict(),
            "source": self.source,
        }


@dataclass(frozen=True)
class ControlTape:
    bytes_: tuple[int, ...]
    primes: tuple[int, ...]
    roles: tuple[str, ...]
    var_slots: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "bytes_hex": [f"0x{byte:02X}" for byte in self.bytes_],
            "prime_sequence": list(self.primes),
            "prime_tape": " ".join(str(prime) for prime in self.primes),
            "roles": list(self.roles),
            "var_slots": [
                {"name": name, "slot": slot, "byte": f"0x{_slot_byte(slot):02X}"}
                for name, slot in self.var_slots
            ],
        }


@dataclass(frozen=True)
class RosettaControlNode:
    schema: str
    expression: str
    fn_name: str
    value: float
    control_tape: ControlTape
    artifacts: tuple[ControlArtifact, ...]
    runtime_consensus_ok: bool | None
    problems: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "expression": self.expression,
            "fn_name": self.fn_name,
            "value": self.value,
            "control_tape": self.control_tape.to_dict(),
            "runtime_consensus_ok": self.runtime_consensus_ok,
            "problems": list(self.problems),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


class _TapeBuilder:
    def __init__(self) -> None:
        self.var_to_slot: dict[str, int] = {}

    def build(self, node: NodeType) -> ControlTape:
        byte_values = self._serialize(node) + [Ctrl.HALT]
        return ControlTape(
            bytes_=tuple(byte_values),
            primes=tuple(_BYTE_PRIMES[byte] for byte in byte_values),
            roles=tuple(_roles_for_bytes(byte_values)),
            var_slots=tuple(sorted(self.var_to_slot.items(), key=lambda item: item[1])),
        )

    def _serialize(self, node: NodeType) -> list[int]:
        if isinstance(node, LitNode):
            return _literal_bytes(node.value)
        if isinstance(node, VarNode):
            return [_slot_byte(self._slot_for(node.name))]
        if isinstance(node, OpNode):
            op_id = _op_id(node.op_name)
            out = [op_id]
            for key in sorted(node.arg_nodes):
                out.extend(self._serialize(node.arg_nodes[key]))
            return out
        if isinstance(node, LetNode):
            return [Ctrl.LET, _slot_byte(self._slot_for(node.name))] + self._serialize(
                node.expr
            )
        if isinstance(node, IfNode):
            out = [Ctrl.IF]
            out.extend(self._serialize(node.cond))
            out.extend(self._serialize(node.then_body))
            if node.else_body is not None:
                out.append(Ctrl.ELSE)
                out.extend(self._serialize(node.else_body))
            out.append(Ctrl.END)
            return out
        if isinstance(node, WhileNode):
            out = [Ctrl.WHILE]
            out.extend(_literal_bytes(node.max_iterations))
            out.extend(self._serialize(node.cond))
            out.extend(self._serialize(node.body))
            out.append(Ctrl.END)
            return out
        if isinstance(node, SeqNode):
            out: list[int] = []
            for child in node.nodes:
                out.extend(self._serialize(child))
                out.append(Ctrl.SEQ)
            return out
        raise ValueError(f"unsupported control node: {type(node).__name__}")

    def _slot_for(self, name: str) -> int:
        if name not in self.var_to_slot:
            slot = len(self.var_to_slot)
            if slot >= 80:
                raise ValueError("control tape supports at most 80 variables")
            self.var_to_slot[name] = slot
        return self.var_to_slot[name]


class _Emitter:
    def __init__(
        self,
        target: str,
        fn_name: str,
        *,
        expression: str,
        prime_sequence: Sequence[int],
    ) -> None:
        self.target = target
        self.fn_name = fn_name
        self.expression = expression
        self.prime_sequence = tuple(prime_sequence)
        self.lines: list[str] = []
        self.declared: set[str] = {"__result"}
        self.loop_id = 0

    def emit(self, node: NodeType) -> str:
        if self.target == "python":
            self.lines = [
                control_source_header(
                    self.target, self.expression, self.fn_name, self.prime_sequence
                ),
                f"def {self.fn_name}():",
                "    __result = 0.0",
            ]
            self._stmt(node, indent=1, assign_result=True)
            self.lines.append("    return float(__result)")
        elif self.target == "typescript":
            self.lines = [
                control_source_header(
                    self.target, self.expression, self.fn_name, self.prime_sequence
                ),
                f"export function {self.fn_name}(): number {{",
                "  let __result = 0;",
            ]
            self._stmt(node, indent=1, assign_result=True)
            self.lines.append("  return Number(__result);")
            self.lines.append("}")
        elif self.target == "c":
            self.lines = [
                control_source_header(
                    self.target, self.expression, self.fn_name, self.prime_sequence
                ),
                f"double {self.fn_name}(void) {{",
                "    double __result = 0;",
            ]
            self._stmt(node, indent=1, assign_result=True)
            self.lines.append("    return __result;")
            self.lines.append("}")
        elif self.target == "go":
            self.lines = [
                control_source_header(
                    self.target, self.expression, self.fn_name, self.prime_sequence
                ),
                f"func {self.fn_name}() float64 {{",
                "\tvar __result float64 = 0",
            ]
            self._stmt(node, indent=1, assign_result=True)
            self.lines.append("\treturn __result")
            self.lines.append("}")
        else:
            raise ValueError(f"unsupported control target {self.target!r}")
        return "\n".join(self.lines) + "\n"

    def _stmt(
        self, node: NodeType, *, indent: int, assign_result: bool = False
    ) -> None:
        if isinstance(node, SeqNode):
            for index, child in enumerate(node.nodes):
                self._stmt(
                    child,
                    indent=indent,
                    assign_result=assign_result and index == len(node.nodes) - 1,
                )
            return
        if isinstance(node, LetNode):
            self._assign(node.name, self._expr(node.expr), indent)
            if assign_result:
                self._assign("__result", self._var(node.name), indent)
            return
        if isinstance(node, IfNode):
            self._if(node, indent, assign_result=assign_result)
            return
        if isinstance(node, WhileNode):
            self._while(node, indent)
            if assign_result:
                self._assign("__result", "0", indent)
            return

        expr = self._expr(node)
        if assign_result:
            self._assign("__result", expr, indent)
        else:
            self._line(expr + self._statement_suffix(), indent)

    def _if(self, node: IfNode, indent: int, *, assign_result: bool) -> None:
        cond = self._truth(self._expr(node.cond))
        if self.target == "python":
            self._line(f"if {cond}:", indent)
            self._stmt(node.then_body, indent=indent + 1, assign_result=assign_result)
            if node.else_body is not None:
                self._line("else:", indent)
                self._stmt(
                    node.else_body, indent=indent + 1, assign_result=assign_result
                )
            return
        if self.target == "go":
            self._line(f"if {cond} {{", indent)
            self._stmt(node.then_body, indent=indent + 1, assign_result=assign_result)
            if node.else_body is not None:
                self._line("} else {", indent)
                self._stmt(
                    node.else_body, indent=indent + 1, assign_result=assign_result
                )
            self._line("}", indent)
            return

        self._line(f"if ({cond}) {{", indent)
        self._stmt(node.then_body, indent=indent + 1, assign_result=assign_result)
        if node.else_body is not None:
            self._line("} else {", indent)
            self._stmt(node.else_body, indent=indent + 1, assign_result=assign_result)
        self._line("}", indent)

    def _while(self, node: WhileNode, indent: int) -> None:
        loop_name = f"__loop_{self.loop_id}"
        self.loop_id += 1
        self._assign(loop_name, "0", indent)
        cond = self._truth(self._expr(node.cond))
        if self.target == "python":
            self._line(f"while {cond}:", indent)
            self._line(f"if {loop_name} >= {node.max_iterations}:", indent + 1)
            self._line(
                f"raise RuntimeError('bounded loop exceeded: {loop_name}')", indent + 2
            )
            self._line(f"{loop_name} += 1", indent + 1)
            self._stmt(node.body, indent=indent + 1)
            return
        if self.target == "go":
            self._line(f"for {cond} {{", indent)
            self._line(
                f'if {loop_name} >= {node.max_iterations} {{ panic("bounded loop exceeded") }}',
                indent + 1,
            )
            self._line(f"{loop_name} = {loop_name} + 1", indent + 1)
            self._stmt(node.body, indent=indent + 1)
            self._line("}", indent)
            return

        self._line(f"while ({cond}) {{", indent)
        if self.target == "typescript":
            self._line(
                f"if ({loop_name} >= {node.max_iterations}) throw new Error('bounded loop exceeded');",
                indent + 1,
            )
        else:
            self._line(
                f"if ({loop_name} >= {node.max_iterations}) {{ return NAN; }}",
                indent + 1,
            )
        self._line(
            f"{loop_name} = {loop_name} + 1{self._statement_suffix()}", indent + 1
        )
        self._stmt(node.body, indent=indent + 1)
        self._line("}", indent)

    def _assign(self, name: str, expr: str, indent: int) -> None:
        var = self._var(name)
        if self.target == "python":
            self._line(f"{var} = {expr}", indent)
            self.declared.add(name)
            return
        if self.target == "typescript":
            prefix = "let " if name not in self.declared else ""
            self._line(f"{prefix}{var} = {expr};", indent)
            self.declared.add(name)
            return
        if self.target == "c":
            prefix = "double " if name not in self.declared else ""
            self._line(f"{prefix}{var} = {expr};", indent)
            self.declared.add(name)
            return
        if self.target == "go":
            if name not in self.declared:
                self._line(f"var {var} float64 = {expr}", indent)
            else:
                self._line(f"{var} = {expr}", indent)
            self.declared.add(name)

    def _expr(self, node: NodeType) -> str:
        if isinstance(node, LitNode):
            return _number_literal(node.value)
        if isinstance(node, VarNode):
            return self._var(node.name)
        if isinstance(node, OpNode):
            return self._op_expr(node)
        if isinstance(node, SeqNode):
            raise ValueError("nested SeqNode cannot be emitted inline")
        if isinstance(node, LetNode):
            raise ValueError("LetNode cannot be emitted inline")
        if isinstance(node, IfNode):
            raise ValueError("IfNode cannot be emitted inline")
        if isinstance(node, WhileNode):
            raise ValueError("WhileNode cannot be emitted inline")
        raise ValueError(f"unsupported expression node: {type(node).__name__}")

    def _op_expr(self, node: OpNode) -> str:
        args = {key: self._expr(value) for key, value in node.arg_nodes.items()}
        name = node.op_name
        if name in {"add", "sub", "mul", "div", "mod", "pow", "shl", "shr"}:
            return self._binary_expr(name, args["a"], args["b"])
        if name in {"eq", "neq", "lt", "lte", "gt", "gte"}:
            return self._bool_number(self._comparison_expr(name, args["a"], args["b"]))
        if name == "or":
            return self._bool_number(
                self._logical_expr("or", self._truth(args["a"]), self._truth(args["b"]))
            )
        if name == "and":
            return self._bool_number(
                self._logical_expr(
                    "and", self._truth(args["a"]), self._truth(args["b"])
                )
            )
        if name == "abs":
            return self._call_abs(args["a"])
        if name == "neg":
            return f"(-{args['a']})"
        if name == "inc":
            return f"({args['a']} + 1)"
        if name == "dec":
            return f"({args['a']} - 1)"
        if name == "min":
            return self._call_min(args["a"], args["b"])
        if name == "max":
            return self._call_max(args["a"], args["b"])
        raise ValueError(f"control emitter does not support op {name!r} yet")

    def _binary_expr(self, name: str, a: str, b: str) -> str:
        if name == "add":
            return f"({a} + {b})"
        if name == "sub":
            return f"({a} - {b})"
        if name == "mul":
            return f"({a} * {b})"
        if name == "div":
            return (
                f"(({b}) != 0 ? ({a}) / ({b}) : 0)"
                if self.target != "python"
                else f"(({a}) / ({b}) if ({b}) != 0 else 0)"
            )
        if name == "mod":
            if self.target == "python":
                return f"(({a}) % ({b}) if ({b}) != 0 else 0)"
            if self.target == "go":
                return f"caMod({a}, {b})"
            if self.target == "c":
                return f"(({b}) != 0 ? fmod(({a}), ({b})) : 0)"
            return f"(({b}) !== 0 ? ({a}) % ({b}) : 0)"
        if name == "pow":
            if self.target == "python":
                return f"(({a}) ** ({b}))"
            if self.target == "go":
                return f"math.Pow({a}, {b})"
            if self.target == "c":
                return f"pow(({a}), ({b}))"
            return f"Math.pow({a}, {b})"
        if name == "shl":
            if self.target in {"python", "typescript", "go"}:
                return (
                    f"float64(int64({a}) << int64({b}))"
                    if self.target == "go"
                    else (
                        f"(int({a}) << int({b}))"
                        if self.target == "python"
                        else f"(({a}) << ({b}))"
                    )
                )
            return f"((double)((long long)({a}) << (long long)({b})))"
        if name == "shr":
            if self.target in {"python", "typescript", "go"}:
                return (
                    f"float64(int64({a}) >> int64({b}))"
                    if self.target == "go"
                    else (
                        f"(int({a}) >> int({b}))"
                        if self.target == "python"
                        else f"(({a}) >> ({b}))"
                    )
                )
            return f"((double)((long long)({a}) >> (long long)({b})))"
        raise ValueError(name)

    def _comparison_expr(self, name: str, a: str, b: str) -> str:
        op = {"eq": "==", "neq": "!=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}[
            name
        ]
        return f"(({a}) {op} ({b}))"

    def _logical_expr(self, name: str, a: str, b: str) -> str:
        if self.target == "python":
            op = "or" if name == "or" else "and"
        else:
            op = "||" if name == "or" else "&&"
        return f"({a} {op} {b})"

    def _bool_number(self, expr: str) -> str:
        if self.target == "python":
            return f"(1 if {expr} else 0)"
        if self.target == "go":
            return f"caBool({expr})"
        return f"({expr} ? 1 : 0)"

    def _truth(self, expr: str) -> str:
        return f"(({expr}) != 0)"

    def _call_abs(self, expr: str) -> str:
        if self.target == "python":
            return f"abs({expr})"
        if self.target == "go":
            return f"math.Abs({expr})"
        if self.target == "c":
            return f"fabs({expr})"
        return f"Math.abs({expr})"

    def _call_min(self, a: str, b: str) -> str:
        if self.target == "python":
            return f"min({a}, {b})"
        if self.target == "go":
            return f"math.Min({a}, {b})"
        if self.target == "c":
            return f"fmin({a}, {b})"
        return f"Math.min({a}, {b})"

    def _call_max(self, a: str, b: str) -> str:
        if self.target == "python":
            return f"max({a}, {b})"
        if self.target == "go":
            return f"math.Max({a}, {b})"
        if self.target == "c":
            return f"fmax({a}, {b})"
        return f"Math.max({a}, {b})"

    def _var(self, name: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_]", "_", name)
        if not re.match(r"^[A-Za-z_]", safe):
            safe = "_" + safe
        return safe

    def _line(self, text: str, indent: int) -> None:
        pad = {"python": "    ", "typescript": "  ", "c": "    ", "go": "\t"}[
            self.target
        ]
        self.lines.append((pad * indent) + text)

    def _statement_suffix(self) -> str:
        return ";" if self.target in {"typescript", "c"} else ""


def build_rosetta_control_node(
    expression: str,
    *,
    targets: Sequence[str] = CONTROL_TARGETS,
    fn_name: str = "control_fn",
    run: bool = False,
) -> RosettaControlNode:
    ast = parse(expression)
    value = eval_node(ast, VarEnv())
    if not isinstance(value, (int, float, bool)):
        raise ValueError(f"control node result is not numeric: {value!r}")
    tape = _TapeBuilder().build(ast)
    normalized_targets = _normalize_targets(targets)

    artifacts: list[ControlArtifact] = []
    problems: list[str] = []
    for target in normalized_targets:
        try:
            source = _Emitter(
                target,
                fn_name,
                expression=expression,
                prime_sequence=tape.primes,
            ).emit(ast)
            runtime = (
                _run_target(target, source, fn_name)
                if run
                else RuntimeResult(status=RUNTIME_NOT_REQUESTED)
            )
            artifacts.append(
                ControlArtifact(
                    target=target,
                    source=source,
                    source_chars=len(source),
                    runtime=runtime,
                )
            )
        except (ValueError, TypeError) as exc:
            problems.append(f"{target}: {exc}")

    return RosettaControlNode(
        schema="scbe_rosetta_control_node_v1",
        expression=expression,
        fn_name=fn_name,
        value=float(value),
        control_tape=tape,
        artifacts=tuple(artifacts),
        runtime_consensus_ok=_runtime_consensus(artifacts, float(value), run),
        problems=tuple(problems),
    )


def _normalize_targets(targets: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(target.strip().lower() for target in targets if target.strip())
    if not normalized:
        raise ValueError("at least one target is required")
    unknown = [target for target in normalized if target not in CONTROL_TARGETS]
    if unknown:
        raise ValueError(f"unsupported control target(s): {', '.join(unknown)}")
    return normalized


def control_source_header(
    target: str, expression: str, fn_name: str, prime_sequence: Sequence[int]
) -> str:
    """Return the one-line Rosetta delivery label for generated control source."""
    prefix = "#" if target == "python" else "//"
    payload = {
        "schema": SOURCE_IDENTITY_SCHEMA,
        "expression": expression,
        "target": target,
        "fn_name": fn_name,
        "prime_tape": " ".join(str(int(prime)) for prime in prime_sequence),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{prefix} {SOURCE_IDENTITY_TAG} {encoded}"


def parse_control_source_header(source: str) -> dict[str, Any] | None:
    """Parse the Rosetta control source label from generated source text."""
    for raw in source.lstrip().splitlines():
        line = raw.strip()
        if not line:
            continue
        if SOURCE_IDENTITY_TAG not in line:
            if not line.startswith(("#", "//")):
                return None
            continue
        _, payload = line.split(SOURCE_IDENTITY_TAG, 1)
        try:
            parsed = json.loads(payload.strip())
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _op_id(name: str) -> int:
    for op_id, entry in OP_TABLE.items():
        if entry.name == name:
            return op_id
    raise ValueError(f"unknown CA op {name!r}")


def _literal_bytes(value: Any) -> list[int]:
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if not isinstance(value, int):
        raise ValueError(
            f"control tape only supports integer literals today: {value!r}"
        )
    if 0 <= value <= 31:
        return [0x60 + value]
    if 32 <= value <= 95:
        return [0xC0 + (value - 32)]
    return [Ctrl.CONST] + list(int(value).to_bytes(8, "little", signed=True))


def _slot_byte(slot: int) -> int:
    if 0 <= slot <= 15:
        return 0x50 + slot
    if 16 <= slot <= 79:
        return 0x80 + (slot - 16)
    raise ValueError(f"variable slot out of range: {slot}")


def _role_for_byte(byte: int) -> str:
    if 0 <= byte <= 0x3F:
        return f"OP:{OP_TABLE[byte].name}"
    if byte in CTRL_NAMES:
        return f"CTRL:{CTRL_NAMES[byte]}"
    if 0x50 <= byte <= 0x5F:
        return f"VAR_SLOT:{byte - 0x50}"
    if 0x60 <= byte <= 0x7F:
        return f"LIT:{byte - 0x60}"
    if 0x80 <= byte <= 0xBF:
        return f"EXT_VAR_SLOT:{16 + byte - 0x80}"
    return f"EXT_LIT:{32 + byte - 0xC0}"


def _roles_for_bytes(byte_values: Sequence[int]) -> list[str]:
    roles: list[str] = []
    index = 0
    while index < len(byte_values):
        byte = byte_values[index]
        roles.append(_role_for_byte(byte))
        if byte == Ctrl.CONST:
            payload = byte_values[index + 1 : index + 9]
            for offset, payload_byte in enumerate(payload):
                roles.append(f"CONST_PAYLOAD:{offset}:0x{payload_byte:02X}")
            index += 1 + len(payload)
        else:
            index += 1
    return roles


def _number_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return repr(float(value))


def _run_target(target: str, source: str, fn_name: str) -> RuntimeResult:
    if target == "python":
        return _run_python(source, fn_name)
    if target == "typescript":
        return _run_typescript(source, fn_name)
    if target == "c":
        return _run_c(source, fn_name)
    if target == "go":
        return _run_go(source, fn_name)
    return RuntimeResult(
        status=RUNTIME_SKIPPED, error=f"no runtime adapter for {target}"
    )


def _run_python(source: str, fn_name: str) -> RuntimeResult:
    namespace: dict[str, Any] = {
        "__builtins__": {
            "abs": abs,
            "float": float,
            "int": int,
            "max": max,
            "min": min,
            "RuntimeError": RuntimeError,
        }
    }
    try:
        exec(source, namespace)  # noqa: S102 -- generated scaffold only
        return RuntimeResult(status=RUNTIME_PASS, value=float(namespace[fn_name]()))
    except Exception as exc:
        return RuntimeResult(status=RUNTIME_FAIL, error=str(exc))


def _run_typescript(source: str, fn_name: str) -> RuntimeResult:
    node = shutil.which("node")
    if not node:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="node not found")
    js = source.replace(f"export function {fn_name}(): number", f"function {fn_name}()")
    js += f"\nconsole.log(JSON.stringify({fn_name}()));\n"
    return _run_temp_file((node,), ".js", js)


def _run_c(source: str, fn_name: str) -> RuntimeResult:
    gcc = shutil.which("gcc")
    if not gcc:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="gcc not found")
    code = (
        "#include <math.h>\n#include <stdio.h>\n"
        f"{source}\n"
        f'int main(void) {{ printf("%.17g\\n", {fn_name}()); return 0; }}\n'
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe.c"
        exe = Path(tmp) / "probe.exe"
        src.write_text(code, encoding="utf-8")
        command = (gcc, str(src), "-lm", "-o", str(exe))
        compiled = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if compiled.returncode != 0:
            return RuntimeResult(
                status=RUNTIME_FAIL,
                error=(compiled.stderr or compiled.stdout).strip(),
                command=command,
            )
        return _run_command((str(exe),))


def _run_go(source: str, fn_name: str) -> RuntimeResult:
    go = shutil.which("go")
    if not go:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="go not found")
    imports = ['"fmt"']
    if any(token in source for token in ("math.", "caBool", "caMod")):
        imports.append('"math"')
    import_block = (
        "import " + imports[0]
        if len(imports) == 1
        else "import (\n\t" + "\n\t".join(imports) + "\n)"
    )
    helpers = (
        "func caBool(v bool) float64 { if v { return 1 }; return 0 }\n"
        "func caMod(a float64, b float64) float64 { if b == 0 { return 0 }; return math.Mod(a, b) }\n"
    )
    code = (
        "package main\n\n"
        + import_block
        + "\n\n"
        + helpers
        + "\n"
        + source
        + f'\nfunc main() {{ fmt.Printf("%.17g\\n", {fn_name}()) }}\n'
    )
    return _run_temp_file((go, "run"), ".go", code)


def _run_temp_file(
    command_prefix: Sequence[str], suffix: str, content: str
) -> RuntimeResult:
    with tempfile.NamedTemporaryFile(
        "w", suffix=suffix, delete=False, encoding="utf-8"
    ) as handle:
        handle.write(content)
        path = handle.name
    try:
        return _run_command(tuple(command_prefix) + (path,))
    finally:
        Path(path).unlink(missing_ok=True)


def _run_command(command: Sequence[str]) -> RuntimeResult:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return RuntimeResult(
            status=RUNTIME_FAIL, error=str(exc), command=tuple(command)
        )
    if result.returncode != 0:
        return RuntimeResult(
            status=RUNTIME_FAIL,
            error=(result.stderr or result.stdout).strip(),
            command=tuple(command),
        )
    try:
        return RuntimeResult(
            status=RUNTIME_PASS,
            value=float(json.loads(result.stdout.strip())),
            command=tuple(command),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return RuntimeResult(
            status=RUNTIME_FAIL,
            error=f"could not parse runtime output {result.stdout!r}: {exc}",
            command=tuple(command),
        )


def _runtime_consensus(
    artifacts: Sequence[ControlArtifact], expected: float, run_requested: bool
) -> bool | None:
    if not run_requested:
        return None
    values = [
        artifact.runtime.value
        for artifact in artifacts
        if artifact.runtime.status == RUNTIME_PASS
    ]
    if not values:
        return None
    return all(
        math.isclose(expected, value, rel_tol=1e-9, abs_tol=1e-9)
        for value in values
        if value is not None
    )
