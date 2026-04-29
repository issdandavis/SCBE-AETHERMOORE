"""
Sacred Tongue ISA dispatcher.

Bridges the existing CA (Cassisivadan) 64-opcode table to the code_prism
multi-language emitter. Takes a sequence of CA opcode bytes and produces a
PrismModule whose function body is a stack-machine program in the target
language.

Why a stack machine: it's the natural execution model for postfix/RPN, which
is exactly what "order of operations as the program" means. Token order IS
evaluation order. Each opcode pops its inputs from a stack and pushes its
result back. Bijective: every opcode maps to exactly one body line per
target, and the body line carries the opcode name as a comment so reverse
parsing is trivial.

This is the smallest first slice — CA only. KO/AV/RU/UM/DR opcode tables can
be added next without changing the dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .ca_opcode_table import OP_TABLE as CA_OP_TABLE

SUPPORTED_TARGETS = ("python", "typescript", "go")


@dataclass(frozen=True, slots=True)
class OpTemplate:
    """Per-target body line for a single opcode plus its stack effect (in, out)."""

    py: str
    ts: str
    go: str
    stack_in: int
    stack_out: int


# -- CA opcode body templates per target language --------------------------
# Stack-machine convention:
#   Python: _stack is a list[float]; pop two with `b = _stack.pop(); a = _stack.pop()`
#   TS:     _stack is number[]; pop two with `const b = _stack.pop()!; const a = _stack.pop()!;`
#   Go:     stack is []float64; helpers caPop2(stack) returns (a, b, rest)
#
# All ops use the opcode mnemonic as a trailing comment so the binary block
# can be recovered by parsing the comment back out.

_BIN = {
    "add": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a + b)",
        ts="{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a + b); }",
        go="a, b, stack := caPop2(stack); stack = append(stack, a + b)",
        stack_in=2,
        stack_out=1,
    ),
    "sub": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a - b)",
        ts="{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a - b); }",
        go="a, b, stack := caPop2(stack); stack = append(stack, a - b)",
        stack_in=2,
        stack_out=1,
    ),
    "mul": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a * b)",
        ts="{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a * b); }",
        go="a, b, stack := caPop2(stack); stack = append(stack, a * b)",
        stack_in=2,
        stack_out=1,
    ),
    "div": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a / b if b != 0 else 0)",
        ts=("{ const b = _stack.pop()!; const a = _stack.pop()!; " "_stack.push(b !== 0 ? a / b : 0); }"),
        go=(
            "a, b, stack := caPop2(stack); "
            "if b != 0 { stack = append(stack, a / b) } else { stack = append(stack, 0) }"
        ),
        stack_in=2,
        stack_out=1,
    ),
    "mod": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a % b if b != 0 else 0)",
        ts=("{ const b = _stack.pop()!; const a = _stack.pop()!; " "_stack.push(b !== 0 ? a % b : 0); }"),
        go=(
            "a, b, stack := caPop2(stack); "
            "if b != 0 { stack = append(stack, math.Mod(a, b)) } else { stack = append(stack, 0) }"
        ),
        stack_in=2,
        stack_out=1,
    ),
    "neg": OpTemplate(
        py="a = _stack.pop(); _stack.append(-a)",
        ts="_stack.push(-_stack.pop()!)",
        go="a, stack := caPop1(stack); stack = append(stack, -a)",
        stack_in=1,
        stack_out=1,
    ),
    "abs": OpTemplate(
        py="a = _stack.pop(); _stack.append(abs(a))",
        ts="_stack.push(Math.abs(_stack.pop()!))",
        go="a, stack := caPop1(stack); stack = append(stack, math.Abs(a))",
        stack_in=1,
        stack_out=1,
    ),
    "inc": OpTemplate(
        py="a = _stack.pop(); _stack.append(a + 1)",
        ts="_stack.push(_stack.pop()! + 1)",
        go="a, stack := caPop1(stack); stack = append(stack, a + 1)",
        stack_in=1,
        stack_out=1,
    ),
    "dec": OpTemplate(
        py="a = _stack.pop(); _stack.append(a - 1)",
        ts="_stack.push(_stack.pop()! - 1)",
        go="a, stack := caPop1(stack); stack = append(stack, a - 1)",
        stack_in=1,
        stack_out=1,
    ),
    "eq": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a == b else 0)",
        ts=("{ const b = _stack.pop()!; const a = _stack.pop()!; " "_stack.push(a === b ? 1 : 0); }"),
        go=(
            "a, b, stack := caPop2(stack); " "if a == b { stack = append(stack, 1) } else { stack = append(stack, 0) }"
        ),
        stack_in=2,
        stack_out=1,
    ),
    "lt": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a < b else 0)",
        ts=("{ const b = _stack.pop()!; const a = _stack.pop()!; " "_stack.push(a < b ? 1 : 0); }"),
        go=("a, b, stack := caPop2(stack); " "if a < b { stack = append(stack, 1) } else { stack = append(stack, 0) }"),
        stack_in=2,
        stack_out=1,
    ),
    "gt": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a > b else 0)",
        ts=("{ const b = _stack.pop()!; const a = _stack.pop()!; " "_stack.push(a > b ? 1 : 0); }"),
        go=("a, b, stack := caPop2(stack); " "if a > b { stack = append(stack, 1) } else { stack = append(stack, 0) }"),
        stack_in=2,
        stack_out=1,
    ),
}


def _template(op_name: str) -> Optional[OpTemplate]:
    return _BIN.get(op_name)


def supported_ca_ops() -> List[str]:
    """Subset of CA opcodes that have body templates today."""
    return sorted(_BIN.keys())


def lookup_ca(op_byte: int) -> Tuple[int, str]:
    """Return (op_id, name) for a CA opcode byte. Raises KeyError on unknown."""
    entry = CA_OP_TABLE[int(op_byte)]
    return (entry.op_id, entry.name)


@dataclass
class CompiledProgram:
    """Result of dispatching a token sequence."""

    fn_name: str
    arg_names: List[str]
    body_lines: List[str]
    op_trace: List[Tuple[int, str]]  # [(op_id, name), ...] for round-trip
    target: str

    def to_prism_module(self, module_name: str = "tongue_program"):
        """Wrap into a code_prism PrismModule for emission."""
        from src.code_prism.models import PrismFunction, PrismModule

        fn = PrismFunction(
            name=self.fn_name,
            args=self.arg_names,
            body=self.body_lines,
            returns=None,
            docstring=f"compiled from CA tongue: [{', '.join(name for _, name in self.op_trace)}]",
            metadata={"op_trace": self.op_trace, "target": self.target},
        )
        return PrismModule(
            module_name=module_name,
            source_language="ca_tongue",
            imports=[],
            functions=[fn],
            metadata={"target": self.target},
        )


def compile_ca_tokens(
    tokens: Sequence[int],
    *,
    target: str = "python",
    fn_name: str = "tongue_fn",
    arg_names: Optional[Sequence[str]] = None,
) -> CompiledProgram:
    """Compile a CA opcode sequence to target-language stack-machine source.

    Args:
        tokens: bytes (0x00–0x3F) referencing CA opcodes
        target: "python", "typescript", or "go"
        fn_name: emitted function name
        arg_names: input argument names; each becomes an initial stack value

    Returns:
        CompiledProgram ready to .to_prism_module() and run through emitter.

    Raises:
        ValueError on unknown target, unsupported opcode, or stack underflow.
    """
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target {target!r}; pick one of {SUPPORTED_TARGETS}")

    args = list(arg_names or [])
    body: List[str] = []
    trace: List[Tuple[int, str]] = []

    body.append(_stack_init(target, args))

    sim_depth = len(args)
    for byte in tokens:
        op_id, name = lookup_ca(byte)
        tpl = _template(name)
        if tpl is None:
            raise ValueError(f"opcode 0x{op_id:02X} ({name}) has no body template yet")
        if sim_depth < tpl.stack_in:
            raise ValueError(f"stack underflow at op {name}: need {tpl.stack_in}, have {sim_depth}")
        sim_depth = sim_depth - tpl.stack_in + tpl.stack_out
        body.append(_emit_line(target, tpl, op_id, name))
        trace.append((op_id, name))

    body.append(_stack_return(target))

    return CompiledProgram(
        fn_name=fn_name,
        arg_names=args,
        body_lines=body,
        op_trace=trace,
        target=target,
    )


def _stack_init(target: str, args: List[str]) -> str:
    if target == "python":
        if not args:
            return "_stack: list = []"
        return f"_stack: list = [{', '.join(args)}]"
    if target == "typescript":
        if not args:
            return "const _stack: number[] = [];"
        return f"const _stack: number[] = [{', '.join(args)}];"
    # go
    if not args:
        return "stack := []float64{}"
    return f"stack := []float64{{{', '.join(args)}}}"


def _stack_return(target: str) -> str:
    if target == "python":
        return "return _stack[-1] if _stack else None"
    if target == "typescript":
        return "return _stack.length > 0 ? _stack[_stack.length - 1] : null;"
    # go
    return "if len(stack) > 0 { return stack[len(stack)-1] }; return nil"


def _emit_line(target: str, tpl: OpTemplate, op_id: int, name: str) -> str:
    body = {"python": tpl.py, "typescript": tpl.ts, "go": tpl.go}[target]
    comment_open = "# " if target == "python" else "// "
    return f"{body}  {comment_open}{name} (0x{op_id:02X})"


# -- bijection: emitted source → token sequence ----------------------------

import re as _re  # noqa: E402

_TRACE_RE = _re.compile(r"(?:#|//)\s*([a-z]+)\s*\(0x([0-9A-Fa-f]{2})\)")


def disassemble(source: str) -> List[Tuple[int, str]]:
    """Recover (op_id, name) trace from a compiled program's emitted source.

    This is the bijection witness: compile(tokens) → source → disassemble(source)
    must equal the original token list (modulo arg-init / return lines).
    """
    out: List[Tuple[int, str]] = []
    for line in source.splitlines():
        m = _TRACE_RE.search(line)
        if m:
            out.append((int(m.group(2), 16), m.group(1)))
    return out
