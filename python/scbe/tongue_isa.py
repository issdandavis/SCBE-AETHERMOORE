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

SUPPORTED_TARGETS = ("python", "typescript", "go", "c", "haskell")


@dataclass(frozen=True, slots=True)
class OpTemplate:
    """Per-target body line for a single opcode plus its stack effect (in, out).

    py/ts/go/c are imperative stack mutations on a shared stack. hs is the PURE
    transform lambda applied to the immutable stack list (head = top); the
    dispatcher threads it as ``s{i+1} = (hs) s{i}`` so Haskell round-trips too.
    """

    py: str
    ts: str
    go: str
    c: str
    hs: str
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
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = _st[_sp-1] + b; }",
        hs=r"\(b:a:r) -> (a + b) : r",
        stack_in=2,
        stack_out=1,
    ),
    "sub": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a - b)",
        ts="{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a - b); }",
        go="a, b, stack := caPop2(stack); stack = append(stack, a - b)",
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = _st[_sp-1] - b; }",
        hs=r"\(b:a:r) -> (a - b) : r",
        stack_in=2,
        stack_out=1,
    ),
    "mul": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a * b)",
        ts="{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a * b); }",
        go="a, b, stack := caPop2(stack); stack = append(stack, a * b)",
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = _st[_sp-1] * b; }",
        hs=r"\(b:a:r) -> (a * b) : r",
        stack_in=2,
        stack_out=1,
    ),
    "div": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a / b if b != 0 else 0)",
        ts=(
            "{ const b = _stack.pop()!; const a = _stack.pop()!; "
            "_stack.push(b !== 0 ? a / b : 0); }"
        ),
        go=(
            "a, b, stack := caPop2(stack); "
            "if b != 0 { stack = append(stack, a / b) } else { stack = append(stack, 0) }"
        ),
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = b != 0 ? _st[_sp-1] / b : 0; }",
        hs=r"\(b:a:r) -> (if b /= 0 then a / b else 0) : r",
        stack_in=2,
        stack_out=1,
    ),
    "mod": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(a % b if b != 0 else 0)",
        ts=(
            "{ const b = _stack.pop()!; const a = _stack.pop()!; "
            "_stack.push(b !== 0 ? a % b : 0); }"
        ),
        go=(
            "a, b, stack := caPop2(stack); "
            "if b != 0 { stack = append(stack, math.Mod(a, b)) } else { stack = append(stack, 0) }"
        ),
        # floor-mod (sign follows divisor) to match Python `%` and the Haskell template;
        # NOT C's native fmod, which truncates toward zero and diverges on negative operands.
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = b != 0 ? _st[_sp-1] - b * floor(_st[_sp-1] / b) : 0; }",
        hs=r"\(b:a:r) -> (if b /= 0 then a - b * fromIntegral (floor (a / b) :: Integer) else 0) : r",
        stack_in=2,
        stack_out=1,
    ),
    "neg": OpTemplate(
        py="a = _stack.pop(); _stack.append(-a)",
        ts="_stack.push(-_stack.pop()!)",
        go="a, stack := caPop1(stack); stack = append(stack, -a)",
        c="_st[_sp-1] = -_st[_sp-1];",
        hs=r"\(a:r) -> negate a : r",
        stack_in=1,
        stack_out=1,
    ),
    "abs": OpTemplate(
        py="a = _stack.pop(); _stack.append(abs(a))",
        ts="_stack.push(Math.abs(_stack.pop()!))",
        go="a, stack := caPop1(stack); stack = append(stack, math.Abs(a))",
        c="_st[_sp-1] = fabs(_st[_sp-1]);",
        hs=r"\(a:r) -> Prelude.abs a : r",
        stack_in=1,
        stack_out=1,
    ),
    "inc": OpTemplate(
        py="a = _stack.pop(); _stack.append(a + 1)",
        ts="_stack.push(_stack.pop()! + 1)",
        go="a, stack := caPop1(stack); stack = append(stack, a + 1)",
        c="_st[_sp-1] = _st[_sp-1] + 1;",
        hs=r"\(a:r) -> (a + 1) : r",
        stack_in=1,
        stack_out=1,
    ),
    "dec": OpTemplate(
        py="a = _stack.pop(); _stack.append(a - 1)",
        ts="_stack.push(_stack.pop()! - 1)",
        go="a, stack := caPop1(stack); stack = append(stack, a - 1)",
        c="_st[_sp-1] = _st[_sp-1] - 1;",
        hs=r"\(a:r) -> (a - 1) : r",
        stack_in=1,
        stack_out=1,
    ),
    "eq": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a == b else 0)",
        ts=(
            "{ const b = _stack.pop()!; const a = _stack.pop()!; "
            "_stack.push(a === b ? 1 : 0); }"
        ),
        go=(
            "a, b, stack := caPop2(stack); "
            "if a == b { stack = append(stack, 1) } else { stack = append(stack, 0) }"
        ),
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = _st[_sp-1] == b ? 1 : 0; }",
        hs=r"\(b:a:r) -> (if a == b then 1 else 0) : r",
        stack_in=2,
        stack_out=1,
    ),
    "lt": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a < b else 0)",
        ts=(
            "{ const b = _stack.pop()!; const a = _stack.pop()!; "
            "_stack.push(a < b ? 1 : 0); }"
        ),
        go=(
            "a, b, stack := caPop2(stack); "
            "if a < b { stack = append(stack, 1) } else { stack = append(stack, 0) }"
        ),
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = _st[_sp-1] < b ? 1 : 0; }",
        hs=r"\(b:a:r) -> (if a < b then 1 else 0) : r",
        stack_in=2,
        stack_out=1,
    ),
    "gt": OpTemplate(
        py="b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a > b else 0)",
        ts=(
            "{ const b = _stack.pop()!; const a = _stack.pop()!; "
            "_stack.push(a > b ? 1 : 0); }"
        ),
        go=(
            "a, b, stack := caPop2(stack); "
            "if a > b { stack = append(stack, 1) } else { stack = append(stack, 0) }"
        ),
        c="{ double b = _st[_sp-1]; _sp -= 1; _st[_sp-1] = _st[_sp-1] > b ? 1 : 0; }",
        hs=r"\(b:a:r) -> (if a > b then 1 else 0) : r",
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


def wrap_program_source(program: CompiledProgram) -> str:
    """Wrap a compiled program's body lines in target-language function syntax.

    This is the shared source renderer for cross-language lenses. Keep every
    CLI or runner path routed through this function so compile-ca, compile-prime,
    and Rosetta nodes cannot drift apart.
    """
    target = program.target
    source_lines: List[str] = []
    if target == "python":
        source_lines.append(f"def {program.fn_name}({', '.join(program.arg_names)}):")
        for line in program.body_lines:
            source_lines.append("    " + line)
    elif target == "typescript":
        source_lines.append(
            f"export function {program.fn_name}"
            f"({', '.join(a + ': number' for a in program.arg_names)}): number | null {{"
        )
        for line in program.body_lines:
            source_lines.append("  " + line)
        source_lines.append("}")
    elif target == "go":
        source_lines.append(
            f"func {program.fn_name}"
            f"({', '.join(a + ' float64' for a in program.arg_names)}) interface{{}} {{"
        )
        for line in program.body_lines:
            source_lines.append("\t" + line)
        source_lines.append("}")
    elif target == "c":
        source_lines.append(
            f"double {program.fn_name}({', '.join('double ' + a for a in program.arg_names)}) {{"
        )
        for line in program.body_lines:
            source_lines.append("    " + line)
        source_lines.append("}")
    elif target == "haskell":  # let/in over the threaded pure-transform lines
        source_lines.append(f"{program.fn_name} {' '.join(program.arg_names)} =")
        body = program.body_lines
        source_lines.append("  let")
        for line in body[:-1]:
            source_lines.append("    " + line)
        source_lines.append("  in " + body[-1])
    else:
        raise ValueError(f"no source wrapper for target {target!r}")
    return "\n".join(source_lines) + "\n"


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
        target: one of SUPPORTED_TARGETS (python, typescript, go, c, haskell)
        fn_name: emitted function name
        arg_names: input argument names; each becomes an initial stack value

    Returns:
        CompiledProgram ready to .to_prism_module() and run through emitter.

    Raises:
        ValueError on unknown target, unsupported opcode, or stack underflow.
    """
    if target not in SUPPORTED_TARGETS:
        raise ValueError(
            f"unsupported target {target!r}; pick one of {SUPPORTED_TARGETS}"
        )

    args = list(arg_names or [])
    body: List[str] = []
    trace: List[Tuple[int, str]] = []

    body.append(_stack_init(target, args))

    sim_depth = len(args)
    for step, byte in enumerate(tokens):
        op_id, name = lookup_ca(byte)
        tpl = _template(name)
        if tpl is None:
            raise ValueError(f"opcode 0x{op_id:02X} ({name}) has no body template yet")
        if sim_depth < tpl.stack_in:
            raise ValueError(
                f"stack underflow at op {name}: need {tpl.stack_in}, have {sim_depth}"
            )
        sim_depth = sim_depth - tpl.stack_in + tpl.stack_out
        body.append(_emit_line(target, tpl, op_id, name, step))
        trace.append((op_id, name))

    body.append(_stack_return(target, len(trace)))

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
    if target == "c":
        if not args:
            return "double _st[256]; int _sp = 0;"
        return f"double _st[256] = {{{', '.join(args)}}}; int _sp = {len(args)};"
    if target == "haskell":
        # head = top of stack, so reverse the arg order (Python pushes left->right,
        # making the last arg the top).
        reversed_args = ", ".join(reversed(args))
        return f"s0 = [{reversed_args}] :: [Double]"
    # go
    if not args:
        return "stack := []float64{}"
    return f"stack := []float64{{{', '.join(args)}}}"


def _stack_return(target: str, n_ops: int) -> str:
    if target == "python":
        return "return _stack[-1] if _stack else None"
    if target == "typescript":
        return "return _stack.length > 0 ? _stack[_stack.length - 1] : null;"
    if target == "c":
        return "return _sp > 0 ? _st[_sp-1] : 0;"
    if target == "haskell":
        return f"if null s{n_ops} then 0 else head s{n_ops}"
    # go
    return "if len(stack) > 0 { return stack[len(stack)-1] }; return nil"


def _emit_line(target: str, tpl: OpTemplate, op_id: int, name: str, step: int) -> str:
    if target == "haskell":
        # thread the pure transform: s{step+1} = (lambda) s{step}
        return f"s{step + 1} = ({tpl.hs}) s{step}  -- {name} (0x{op_id:02X})"
    body = {"python": tpl.py, "typescript": tpl.ts, "go": tpl.go, "c": tpl.c}[target]
    comment_open = "# " if target == "python" else "// "
    return f"{body}  {comment_open}{name} (0x{op_id:02X})"


# -- bijection: emitted source → token sequence ----------------------------

import re as _re  # noqa: E402

# `#` (python), `//` (ts/go/c), `--` (haskell). C uses `_sp -= 1` / `_sp - 1`
# (single dash, never `--`), so the `--` branch only matches Haskell comments.
_TRACE_RE = _re.compile(r"(?:#|//|--)\s*([a-z]+)\s*\(0x([0-9A-Fa-f]{2})\)")


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
