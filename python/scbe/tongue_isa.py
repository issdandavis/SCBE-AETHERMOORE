"""
Sacred Tongue ISA dispatcher.

Bridges the CA (Cassisivadan) 64-opcode table to target-language stack-machine
source. Token order is evaluation order: each opcode consumes values from a
stack and pushes one result. The emitted lines carry ``opname (0xHH)`` trace
comments so source can be disassembled back into the original opcode sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
import re as _re
from typing import List, Optional, Sequence, Tuple

from .ca_opcode_table import OP_TABLE as CA_OP_TABLE

SUPPORTED_TARGETS = ("python", "typescript", "go", "rust", "c", "julia", "haskell", "zig")


@dataclass(frozen=True, slots=True)
class OpTemplate:
    """Stack effect plus per-target stack-machine body snippets."""

    stack_in: int
    stack_out: int
    py: str
    ts: str
    go: str
    rust: str
    c: str
    julia: str
    zig: str
    haskell: str


def _bin(py: str, ts: str, go: str, rust: str, c: str, julia: str, zig: str, haskell: str) -> OpTemplate:
    return OpTemplate(2, 1, py, ts, go, rust, c, julia, zig, haskell)


def _unary(py: str, ts: str, go: str, rust: str, c: str, julia: str, zig: str, haskell: str) -> OpTemplate:
    return OpTemplate(1, 1, py, ts, go, rust, c, julia, zig, haskell)


# Haskell emits pure helper calls because immutable stack threading is clearer
# than mutating a shared stack name.
_BIN = {
    "add": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(a + b)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a + b); }",
        "a, b, stack := caPop2(stack); stack = append(stack, a + b)",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(a + b);",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = a + b;",
        "b = pop!(stack); a = pop!(stack); push!(stack, a + b)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(a + b);",
        "caAdd",
    ),
    "sub": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(a - b)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a - b); }",
        "a, b, stack := caPop2(stack); stack = append(stack, a - b)",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(a - b);",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = a - b;",
        "b = pop!(stack); a = pop!(stack); push!(stack, a - b)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(a - b);",
        "caSub",
    ),
    "mul": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(a * b)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a * b); }",
        "a, b, stack := caPop2(stack); stack = append(stack, a * b)",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(a * b);",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = a * b;",
        "b = pop!(stack); a = pop!(stack); push!(stack, a * b)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(a * b);",
        "caMul",
    ),
    "div": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(a / b if b != 0 else 0)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(b !== 0 ? a / b : 0); }",
        "a, b, stack := caPop2(stack); if b != 0 { stack = append(stack, a / b) } else { stack = append(stack, 0) }",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(if b != 0.0 { a / b } else { 0.0 });",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = b != 0.0 ? a / b : 0.0;",
        "b = pop!(stack); a = pop!(stack); push!(stack, b != 0 ? a / b : 0)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(if (b != 0.0) a / b else 0.0);",
        "caDiv",
    ),
    "mod": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(a % b if b != 0 else 0)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(b !== 0 ? a % b : 0); }",
        "a, b, stack := caPop2(stack); if b != 0 { stack = append(stack, math.Mod(a, b)) } else { stack = append(stack, 0) }",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(if b != 0.0 { a % b } else { 0.0 });",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = b != 0.0 ? fmod(a, b) : 0.0;",
        "b = pop!(stack); a = pop!(stack); push!(stack, b != 0 ? rem(a, b) : 0)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(if (b != 0.0) @mod(a, b) else 0.0);",
        "caMod",
    ),
    "neg": _unary(
        "a = _stack.pop(); _stack.append(-a)",
        "_stack.push(-_stack.pop()!)",
        "a, stack := caPop1(stack); stack = append(stack, -a)",
        "let a = stack.pop().unwrap(); stack.push(-a);",
        "a = stack[--sp]; stack[sp++] = -a;",
        "a = pop!(stack); push!(stack, -a)",
        "const a = stack.pop(); try stack.append(-a);",
        "caNeg",
    ),
    "abs": _unary(
        "a = _stack.pop(); _stack.append(abs(a))",
        "_stack.push(Math.abs(_stack.pop()!))",
        "a, stack := caPop1(stack); stack = append(stack, math.Abs(a))",
        "let a = stack.pop().unwrap(); stack.push(a.abs());",
        "a = stack[--sp]; stack[sp++] = fabs(a);",
        "a = pop!(stack); push!(stack, abs(a))",
        "const a = stack.pop(); try stack.append(@abs(a));",
        "caAbs",
    ),
    "inc": _unary(
        "a = _stack.pop(); _stack.append(a + 1)",
        "_stack.push(_stack.pop()! + 1)",
        "a, stack := caPop1(stack); stack = append(stack, a + 1)",
        "let a = stack.pop().unwrap(); stack.push(a + 1.0);",
        "a = stack[--sp]; stack[sp++] = a + 1.0;",
        "a = pop!(stack); push!(stack, a + 1)",
        "const a = stack.pop(); try stack.append(a + 1.0);",
        "caInc",
    ),
    "dec": _unary(
        "a = _stack.pop(); _stack.append(a - 1)",
        "_stack.push(_stack.pop()! - 1)",
        "a, stack := caPop1(stack); stack = append(stack, a - 1)",
        "let a = stack.pop().unwrap(); stack.push(a - 1.0);",
        "a = stack[--sp]; stack[sp++] = a - 1.0;",
        "a = pop!(stack); push!(stack, a - 1)",
        "const a = stack.pop(); try stack.append(a - 1.0);",
        "caDec",
    ),
    "eq": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a == b else 0)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a === b ? 1 : 0); }",
        "a, b, stack := caPop2(stack); if a == b { stack = append(stack, 1) } else { stack = append(stack, 0) }",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(if a == b { 1.0 } else { 0.0 });",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = a == b ? 1.0 : 0.0;",
        "b = pop!(stack); a = pop!(stack); push!(stack, a == b ? 1 : 0)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(if (a == b) 1.0 else 0.0);",
        "caEq",
    ),
    "lt": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a < b else 0)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a < b ? 1 : 0); }",
        "a, b, stack := caPop2(stack); if a < b { stack = append(stack, 1) } else { stack = append(stack, 0) }",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(if a < b { 1.0 } else { 0.0 });",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = a < b ? 1.0 : 0.0;",
        "b = pop!(stack); a = pop!(stack); push!(stack, a < b ? 1 : 0)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(if (a < b) 1.0 else 0.0);",
        "caLt",
    ),
    "gt": _bin(
        "b = _stack.pop(); a = _stack.pop(); _stack.append(1 if a > b else 0)",
        "{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(a > b ? 1 : 0); }",
        "a, b, stack := caPop2(stack); if a > b { stack = append(stack, 1) } else { stack = append(stack, 0) }",
        "let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(if a > b { 1.0 } else { 0.0 });",
        "b = stack[--sp]; a = stack[--sp]; stack[sp++] = a > b ? 1.0 : 0.0;",
        "b = pop!(stack); a = pop!(stack); push!(stack, a > b ? 1 : 0)",
        "const b = stack.pop(); const a = stack.pop(); try stack.append(if (a > b) 1.0 else 0.0);",
        "caGt",
    ),
}


def _camel(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def _helper_name(target: str, name: str) -> str:
    if target in {"python", "rust", "c", "julia"}:
        return f"ca_{name}"
    if target == "haskell":
        return f"ca{_camel(name)}"
    return f"ca{_camel(name)}"


def _ca_stack_in(op_id: int) -> int:
    """Read the CA table's declared operand count, bounded for code emission."""

    entry = CA_OP_TABLE[int(op_id)]
    return max(1, min(3, int(entry.feat[3])))


def _generic_template(op_id: int, name: str, stack_in: int) -> OpTemplate:
    """Fallback for CA ops without hand-written semantics.

    The emitted source calls a target-local ca_apply1/2/3 dispatcher with the
    opcode id. This keeps the compiler bijective and target-complete without
    requiring one helper function per opcode in each language.
    """

    if stack_in == 1:
        return _unary(
            f"a = _stack.pop(); _stack.append(ca_apply1(0x{op_id:02X}, a))",
            f"{{ const a = _stack.pop()!; _stack.push(caApply1(0x{op_id:02X}, a)); }}",
            f"a, stack := caPop1(stack); stack = append(stack, caApply1(0x{op_id:02X}, a))",
            f"let a = stack.pop().unwrap(); stack.push(ca_apply1(0x{op_id:02X}, a));",
            f"a = stack[--sp]; stack[sp++] = ca_apply1(0x{op_id:02X}, a);",
            f"a = pop!(stack); push!(stack, ca_apply1(0x{op_id:02X}, a))",
            f"const a = stack.pop(); try stack.append(caApply1(0x{op_id:02X}, a));",
            f"caApply1 0x{op_id:02X}",
        )
    if stack_in == 2:
        return _bin(
            f"b = _stack.pop(); a = _stack.pop(); _stack.append(ca_apply2(0x{op_id:02X}, a, b))",
            f"{{ const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(caApply2(0x{op_id:02X}, a, b)); }}",
            f"a, b, stack := caPop2(stack); stack = append(stack, caApply2(0x{op_id:02X}, a, b))",
            f"let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(ca_apply2(0x{op_id:02X}, a, b));",
            f"b = stack[--sp]; a = stack[--sp]; stack[sp++] = ca_apply2(0x{op_id:02X}, a, b);",
            f"b = pop!(stack); a = pop!(stack); push!(stack, ca_apply2(0x{op_id:02X}, a, b))",
            f"const b = stack.pop(); const a = stack.pop(); try stack.append(caApply2(0x{op_id:02X}, a, b));",
            f"caApply2 0x{op_id:02X}",
        )
    return OpTemplate(
        3,
        1,
        f"c = _stack.pop(); b = _stack.pop(); a = _stack.pop(); _stack.append(ca_apply3(0x{op_id:02X}, a, b, c))",
        f"{{ const c = _stack.pop()!; const b = _stack.pop()!; const a = _stack.pop()!; _stack.push(caApply3(0x{op_id:02X}, a, b, c)); }}",
        f"c := stack[len(stack)-1]; b := stack[len(stack)-2]; a := stack[len(stack)-3]; stack = stack[:len(stack)-3]; stack = append(stack, caApply3(0x{op_id:02X}, a, b, c))",
        f"let c = stack.pop().unwrap(); let b = stack.pop().unwrap(); let a = stack.pop().unwrap(); stack.push(ca_apply3(0x{op_id:02X}, a, b, c));",
        f"c = stack[--sp]; b = stack[--sp]; a = stack[--sp]; stack[sp++] = ca_apply3(0x{op_id:02X}, a, b, c);",
        f"c = pop!(stack); b = pop!(stack); a = pop!(stack); push!(stack, ca_apply3(0x{op_id:02X}, a, b, c))",
        f"const c = stack.pop(); const b = stack.pop(); const a = stack.pop(); try stack.append(caApply3(0x{op_id:02X}, a, b, c));",
        f"caApply3 0x{op_id:02X}",
    )


for _op_id, _entry in CA_OP_TABLE.items():
    _BIN.setdefault(_entry.name, _generic_template(_op_id, _entry.name, _ca_stack_in(_op_id)))


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
    op_trace: List[Tuple[int, str]]
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
    """Compile CA opcode bytes to target-language stack-machine source."""

    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target {target!r}; pick one of {SUPPORTED_TARGETS}")

    args = list(arg_names or [])
    body: List[str] = [_stack_init(target, args)]
    trace: List[Tuple[int, str]] = []

    sim_depth = len(args)
    for index, byte in enumerate(tokens, start=1):
        op_id, name = lookup_ca(byte)
        tpl = _template(name)
        if tpl is None:
            raise ValueError(f"opcode 0x{op_id:02X} ({name}) has no body template yet")
        if sim_depth < tpl.stack_in:
            raise ValueError(f"stack underflow at op {name}: need {tpl.stack_in}, have {sim_depth}")
        sim_depth = sim_depth - tpl.stack_in + tpl.stack_out
        body.append(_emit_line(target, tpl, op_id, name, index))
        trace.append((op_id, name))

    body.append(_stack_return(target, len(trace)))

    return CompiledProgram(
        fn_name=fn_name,
        arg_names=args,
        body_lines=body,
        op_trace=trace,
        target=target,
    )


def emit_compiled_program_source(prog: CompiledProgram, *, include_runtime: bool = True) -> str:
    """Emit runnable source for a compiled CA program.

    This is the official plumbing point for CA opcode programs. Generic CA ops
    may emit helper calls such as ``ca_apply3(...)``; those helpers live in
    ``runtime_prelude(target)``. Callers that emit CA source should use this
    helper instead of calling Code Prism directly, otherwise fallback opcodes can
    produce syntactically valid but non-runnable source.
    """

    from src.code_prism.emitter import emit_from_ir

    source = emit_from_ir(prog.to_prism_module(), target_language=prog.target)
    if not include_runtime:
        return source
    prelude = runtime_prelude(prog.target).strip()
    if not prelude:
        return source
    return prelude + "\n\n" + source


def _stack_init(target: str, args: List[str]) -> str:
    joined = ", ".join(args)
    if target == "python":
        return f"_stack: list = [{joined}]" if args else "_stack: list = []"
    if target == "typescript":
        return f"const _stack: number[] = [{joined}];" if args else "const _stack: number[] = [];"
    if target == "go":
        return f"stack := []float64{{{joined}}}" if args else "stack := []float64{}"
    if target == "rust":
        return f"let mut stack: Vec<f64> = vec![{joined}];" if args else "let mut stack: Vec<f64> = Vec::new();"
    if target == "c":
        pushes = " ".join(f"stack[sp++] = {arg};" for arg in args)
        return f"double stack[1024]; int sp = 0; {pushes}".rstrip()
    if target == "julia":
        return f"stack = Any[{joined}]" if args else "stack = Any[]"
    if target == "haskell":
        return f"stack0 = [{joined}]" if args else "stack0 = []"
    if target == "zig":
        pushes = " ".join(f"try stack.append({arg});" for arg in args)
        return f"var stack = std.ArrayList(f64).init(allocator); {pushes}".rstrip()
    raise ValueError(f"unsupported target {target!r}")


def _stack_return(target: str, step_count: int) -> str:
    if target == "python":
        return "return _stack[-1] if _stack else None"
    if target == "typescript":
        return "return _stack.length > 0 ? _stack[_stack.length - 1] : null;"
    if target == "go":
        return "if len(stack) > 0 { return stack[len(stack)-1] }; return nil"
    if target == "rust":
        return "stack.last().copied()"
    if target == "c":
        return "return sp > 0 ? stack[sp - 1] : 0.0;"
    if target == "julia":
        return "return isempty(stack) ? nothing : stack[end]"
    if target == "haskell":
        return f"result = case stack{step_count} of {{ [] -> Nothing; (x:_) -> Just x }}"
    if target == "zig":
        return "return if (stack.items.len > 0) stack.items[stack.items.len - 1] else null;"
    raise ValueError(f"unsupported target {target!r}")


def _emit_line(target: str, tpl: OpTemplate, op_id: int, name: str, step_index: int) -> str:
    if target == "haskell":
        return f"stack{step_index} = {tpl.haskell} stack{step_index - 1}  -- {name} (0x{op_id:02X})"
    body = {
        "python": tpl.py,
        "typescript": tpl.ts,
        "go": tpl.go,
        "rust": tpl.rust,
        "c": tpl.c,
        "julia": tpl.julia,
        "zig": tpl.zig,
    }[target]
    comment_open = "# " if target in {"python", "julia"} else "// "
    return f"{body}  {comment_open}{name} (0x{op_id:02X})"


def runtime_prelude(target: str) -> str:
    """Return target-language helper runtime for emitted CA programs."""

    if target == "python":
        return """import math

def _ca_bool(x):
    return 1.0 if x else 0.0

def _ca_int(x):
    return int(x)

def ca_apply1(op, a):
    if op == 0x05:
        return a
    if op == 0x06:
        return math.sqrt(a) if a >= 0 else 0.0
    if op == 0x07:
        return math.log(a) if a > 0 else 0.0
    if op == 0x08:
        return math.exp(a)
    if op == 0x0D:
        return math.floor(a)
    if op == 0x0E:
        return math.ceil(a)
    if op == 0x0F:
        return round(a)
    if op == 0x12:
        return _ca_bool(not bool(a))
    if op == 0x1A:
        return float(_ca_int(a).bit_count())
    if op == 0x1B:
        n = _ca_int(a)
        return 64.0 if n == 0 else float(64 - (n & ((1 << 64) - 1)).bit_length())
    if op == 0x1C:
        n = abs(_ca_int(a))
        if n == 0:
            return 64.0
        count = 0
        while n & 1 == 0:
            count += 1
            n >>= 1
        return float(count)
    if op == 0x2B:
        return _ca_bool(math.isnan(a))
    if op == 0x2C:
        return _ca_bool(math.isinf(a))
    if op == 0x2D:
        return _ca_bool(math.isfinite(a))
    if op == 0x2E:
        return -1.0 if a < 0 else (1.0 if a > 0 else 0.0)
    if op == 0x2F:
        if math.isnan(a):
            return 3.0
        if math.isinf(a):
            return 2.0
        return 1.0
    if op in {0x30, 0x32, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3C, 0x3D, 0x3E, 0x3F}:
        return a
    if op == 0x31:
        return a
    if op in {0x33, 0x34}:
        return 0.0
    return a

def ca_apply2(op, a, b):
    if op == 0x05:
        return a ** b
    if op == 0x10:
        return _ca_bool(bool(a) and bool(b))
    if op == 0x11:
        return _ca_bool(bool(a) or bool(b))
    if op == 0x13:
        return float(_ca_int(a) ^ _ca_int(b))
    if op == 0x14:
        return _ca_bool(not (bool(a) and bool(b)))
    if op == 0x15:
        return _ca_bool(not (bool(a) or bool(b)))
    if op == 0x16:
        return float(_ca_int(a) << max(0, _ca_int(b)))
    if op == 0x17:
        return float(_ca_int(a) >> max(0, _ca_int(b)))
    if op == 0x18:
        shift = _ca_int(b) % 64
        n = _ca_int(a) & ((1 << 64) - 1)
        return float(((n << shift) | (n >> (64 - shift))) & ((1 << 64) - 1))
    if op == 0x19:
        shift = _ca_int(b) % 64
        n = _ca_int(a) & ((1 << 64) - 1)
        return float(((n >> shift) | (n << (64 - shift))) & ((1 << 64) - 1))
    if op == 0x1D:
        return float(_ca_int(a) & _ca_int(b))
    if op == 0x1E:
        return float(_ca_int(a) | (1 << max(0, _ca_int(b))))
    if op == 0x1F:
        return float(_ca_int(a) & ~(1 << max(0, _ca_int(b))))
    if op == 0x21:
        return _ca_bool(a != b)
    if op == 0x23:
        return _ca_bool(a <= b)
    if op == 0x25:
        return _ca_bool(a >= b)
    if op == 0x26:
        return -1.0 if a < b else (1.0 if a > b else 0.0)
    if op == 0x27:
        return min(a, b)
    if op == 0x28:
        return max(a, b)
    if op == 0x30:
        return a + b
    if op == 0x31:
        return a * b
    if op == 0x32:
        return (a + b) / 2.0
    if op in {0x35, 0x36, 0x37, 0x39, 0x3A, 0x3B, 0x3F}:
        return a + b
    if op == 0x38:
        return a if bool(b) else 0.0
    if op == 0x3C:
        return min(a, b)
    if op == 0x3D:
        return a if a == b else a + b
    if op == 0x3E:
        return 2.0
    return a

def ca_apply3(op, a, b, c):
    if op == 0x29:
        lo, hi = (b, c) if b <= c else (c, b)
        return min(max(a, lo), hi)
    if op == 0x2A:
        lo, hi = (b, c) if b <= c else (c, b)
        return _ca_bool(lo <= a <= hi)
    if op == 0x33:
        m = (a + b + c) / 3.0
        return ((a - m) ** 2 + (b - m) ** 2 + (c - m) ** 2) / 3.0
    if op == 0x34:
        return math.sqrt(ca_apply3(0x33, a, b, c))
    if op in {0x35, 0x36, 0x37, 0x3A, 0x3B, 0x3F}:
        return a + b + c
    return ca_apply2(op, ca_apply2(op, a, b), c)
"""
    if target == "typescript":
        return """function caBool(x: unknown): number { return x ? 1 : 0; }
function caApply1(op: number, a: number): number { return op === 0x12 ? caBool(!a) : a; }
function caApply2(op: number, a: number, b: number): number {
  if (op === 0x10) return caBool(a && b);
  if (op === 0x11) return caBool(a || b);
  if (op === 0x21) return caBool(a !== b);
  if (op === 0x23) return caBool(a <= b);
  if (op === 0x25) return caBool(a >= b);
  if (op === 0x27) return Math.min(a, b);
  if (op === 0x28) return Math.max(a, b);
  return a + b;
}
function caApply3(op: number, a: number, b: number, c: number): number {
  if (op === 0x29) return Math.min(Math.max(a, Math.min(b, c)), Math.max(b, c));
  if (op === 0x2A) return caBool(Math.min(b, c) <= a && a <= Math.max(b, c));
  return caApply2(op, caApply2(op, a, b), c);
}
"""
    if target == "go":
        return """import (
\t"math"
\t"math/big"
\t"math/bits"
)

func caPop1(stack []float64) (float64, []float64) {
\treturn stack[len(stack)-1], stack[:len(stack)-1]
}
func caPop2(stack []float64) (float64, float64, []float64) {
\tb := stack[len(stack)-1]
\ta := stack[len(stack)-2]
\treturn a, b, stack[:len(stack)-2]
}
func caBool(v bool) float64 {
\tif v {
\t\treturn 1
\t}
\treturn 0
}

// caInt mirrors Python int(x): truncate toward zero into a 64-bit integer.
func caInt(x float64) int64 { return int64(math.Trunc(x)) }

func caApply1(op int, a float64) float64 {
\tswitch op {
\tcase 0x05:
\t\treturn a
\tcase 0x06:
\t\tif a >= 0 {
\t\t\treturn math.Sqrt(a)
\t\t}
\t\treturn 0.0
\tcase 0x07:
\t\tif a > 0 {
\t\t\treturn math.Log(a)
\t\t}
\t\treturn 0.0
\tcase 0x08:
\t\treturn math.Exp(a)
\tcase 0x0D:
\t\treturn math.Floor(a)
\tcase 0x0E:
\t\treturn math.Ceil(a)
\tcase 0x0F:
\t\treturn caRoundHalfEven(a)
\tcase 0x12:
\t\treturn caBool(a == 0)
\tcase 0x1A:
\t\t// popcount of |int(a)| (Python int.bit_count counts magnitude bits)
\t\tn := caInt(a)
\t\tif n < 0 {
\t\t\tn = -n
\t\t}
\t\treturn float64(bits.OnesCount64(uint64(n)))
\tcase 0x1B:
\t\t// count leading zeros of the unsigned 64-bit value of int(a)
\t\tn := uint64(caInt(a))
\t\tif n == 0 {
\t\t\treturn 64.0
\t\t}
\t\treturn float64(64 - bits.Len64(n))
\tcase 0x1C:
\t\t// count trailing zeros of |int(a)|
\t\tn := caInt(a)
\t\tif n < 0 {
\t\t\tn = -n
\t\t}
\t\tif n == 0 {
\t\t\treturn 64.0
\t\t}
\t\treturn float64(bits.TrailingZeros64(uint64(n)))
\tcase 0x2B:
\t\treturn caBool(math.IsNaN(a))
\tcase 0x2C:
\t\treturn caBool(math.IsInf(a, 0))
\tcase 0x2D:
\t\treturn caBool(!math.IsNaN(a) && !math.IsInf(a, 0))
\tcase 0x2E:
\t\tif a < 0 {
\t\t\treturn -1.0
\t\t}
\t\tif a > 0 {
\t\t\treturn 1.0
\t\t}
\t\treturn 0.0
\tcase 0x2F:
\t\tif math.IsNaN(a) {
\t\t\treturn 3.0
\t\t}
\t\tif math.IsInf(a, 0) {
\t\t\treturn 2.0
\t\t}
\t\treturn 1.0
\tcase 0x33, 0x34:
\t\treturn 0.0
\t}
\treturn a
}

// caRoundHalfEven mirrors Python's round(): banker's rounding to nearest even.
func caRoundHalfEven(a float64) float64 { return math.RoundToEven(a) }

func caApply2(op int, a, b float64) float64 {
\tswitch op {
\tcase 0x05:
\t\treturn math.Pow(a, b)
\tcase 0x10:
\t\treturn caBool(a != 0 && b != 0)
\tcase 0x11:
\t\treturn caBool(a != 0 || b != 0)
\tcase 0x13:
\t\treturn float64(caInt(a) ^ caInt(b))
\tcase 0x14:
\t\treturn caBool(!(a != 0 && b != 0))
\tcase 0x15:
\t\treturn caBool(!(a != 0 || b != 0))
\tcase 0x16:
\t\t// Python << is arbitrary precision; float(int(a) << s) == ldexp(int(a), s).
\t\ts := caInt(b)
\t\tif s < 0 {
\t\t\ts = 0
\t\t}
\t\treturn math.Ldexp(float64(caInt(a)), int(s))
\tcase 0x17:
\t\ts := caInt(b)
\t\tif s < 0 {
\t\t\ts = 0
\t\t}
\t\treturn float64(caInt(a) >> uint64(s))
\tcase 0x18:
\t\tshift := uint(((caInt(b) % 64) + 64) % 64)
\t\tn := uint64(caInt(a))
\t\treturn float64(bits.RotateLeft64(n, int(shift)))
\tcase 0x19:
\t\tshift := uint(((caInt(b) % 64) + 64) % 64)
\t\tn := uint64(caInt(a))
\t\treturn float64(bits.RotateLeft64(n, -int(shift)))
\tcase 0x1D:
\t\treturn float64(caInt(a) & caInt(b))
\tcase 0x1E:
\t\t// setbit: int(a) | (1 << s). Python is arbitrary precision, so the
\t\t// (1 << s) term can exceed int64; use big.Int (two's-complement Or).
\t\ts := caInt(b)
\t\tif s < 0 {
\t\t\ts = 0
\t\t}
\t\tmask := new(big.Int).Lsh(big.NewInt(1), uint(s))
\t\tz := new(big.Int).Or(big.NewInt(caInt(a)), mask)
\t\tf, _ := new(big.Float).SetInt(z).Float64()
\t\treturn f
\tcase 0x1F:
\t\t// clrbit: int(a) & ~(1 << s) == AndNot(int(a), 1 << s).
\t\ts := caInt(b)
\t\tif s < 0 {
\t\t\ts = 0
\t\t}
\t\tmask := new(big.Int).Lsh(big.NewInt(1), uint(s))
\t\tz := new(big.Int).AndNot(big.NewInt(caInt(a)), mask)
\t\tf, _ := new(big.Float).SetInt(z).Float64()
\t\treturn f
\tcase 0x21:
\t\treturn caBool(a != b)
\tcase 0x23:
\t\treturn caBool(a <= b)
\tcase 0x25:
\t\treturn caBool(a >= b)
\tcase 0x26:
\t\tif a < b {
\t\t\treturn -1.0
\t\t}
\t\tif a > b {
\t\t\treturn 1.0
\t\t}
\t\treturn 0.0
\tcase 0x27:
\t\t// Python min(a, b): keep a unless b is strictly smaller (a wins on tie/NaN).
\t\tif b < a {
\t\t\treturn b
\t\t}
\t\treturn a
\tcase 0x28:
\t\t// Python max(a, b): keep a unless b is strictly greater (a wins on tie/NaN).
\t\tif b > a {
\t\t\treturn b
\t\t}
\t\treturn a
\tcase 0x30:
\t\treturn a + b
\tcase 0x31:
\t\treturn a * b
\tcase 0x32:
\t\treturn (a + b) / 2.0
\tcase 0x35, 0x36, 0x37, 0x39, 0x3A, 0x3B, 0x3F:
\t\treturn a + b
\tcase 0x38:
\t\tif b != 0 {
\t\t\treturn a
\t\t}
\t\treturn 0.0
\tcase 0x3C:
\t\t// Python min(a, b): keep a unless b is strictly smaller (a wins on tie/NaN).
\t\tif b < a {
\t\t\treturn b
\t\t}
\t\treturn a
\tcase 0x3D:
\t\tif a == b {
\t\t\treturn a
\t\t}
\t\treturn a + b
\tcase 0x3E:
\t\treturn 2.0
\t}
\treturn a
}

func caApply3(op int, a, b, c float64) float64 {
\tswitch op {
\tcase 0x29:
\t\t// clamp: lo,hi = (b,c) if b<=c else (c,b); then min(max(a,lo),hi).
\t\tlo, hi := b, c
\t\tif !(b <= c) {
\t\t\tlo, hi = c, b
\t\t}
\t\t// max(a, lo): keep a unless lo > a; then min(that, hi): keep unless hi < it.
\t\tm := a
\t\tif lo > a {
\t\t\tm = lo
\t\t}
\t\tif hi < m {
\t\t\tm = hi
\t\t}
\t\treturn m
\tcase 0x2A:
\t\t// in_range: lo,hi = (b,c) if b<=c else (c,b); bool(lo <= a <= hi).
\t\tlo, hi := b, c
\t\tif !(b <= c) {
\t\t\tlo, hi = c, b
\t\t}
\t\treturn caBool(lo <= a && a <= hi)
\tcase 0x33:
\t\tm := (a + b + c) / 3.0
\t\treturn ((a-m)*(a-m) + (b-m)*(b-m) + (c-m)*(c-m)) / 3.0
\tcase 0x34:
\t\tm := (a + b + c) / 3.0
\t\tv := ((a-m)*(a-m) + (b-m)*(b-m) + (c-m)*(c-m)) / 3.0
\t\treturn math.Sqrt(v)
\tcase 0x35, 0x36, 0x37, 0x3A, 0x3B, 0x3F:
\t\treturn a + b + c
\t}
\treturn caApply2(op, caApply2(op, a, b), c)
}
"""
    if target == "rust":
        return """#[allow(dead_code)]
fn ca_bool(v: bool) -> f64 { if v { 1.0 } else { 0.0 } }

// Python truthiness for a float: nonzero (NaN is truthy, +/-0.0 is falsey).
#[allow(dead_code)]
fn ca_truthy(a: f64) -> bool { a != 0.0 }

// Python int(x): truncate toward zero. Matches Rust `as i64` for in-range values.
#[allow(dead_code)]
fn ca_int(a: f64) -> i64 { a as i64 }

// Python int(x) reinterpreted as 64-bit unsigned (truncate toward zero,
// mask & (2^64-1)). Used by ops whose Python reference masks to u64
// (rotate 0x18/0x19, clz 0x1B).
#[allow(dead_code)]
fn ca_u64(a: f64) -> u64 { (a as i64) as u64 }

// Python round(): round half to even (banker's rounding).
#[allow(dead_code)]
fn ca_round_half_even(a: f64) -> f64 {
    if !a.is_finite() { return a; }
    let f = a.floor();
    let diff = a - f;
    if diff < 0.5 {
        f
    } else if diff > 0.5 {
        f + 1.0
    } else {
        // Exactly halfway: pick the even neighbor.
        let half = (f * 0.5).floor() * 2.0;
        if half == f { f } else { f + 1.0 }
    }
}

// Python min()/max(): comparison-based, keep the first argument on ties.
// (Differs from f64::min/max for signed zeros and NaN.)
#[allow(dead_code)]
fn ca_min(a: f64, b: f64) -> f64 { if b < a { b } else { a } }
#[allow(dead_code)]
fn ca_max(a: f64, b: f64) -> f64 { if b > a { b } else { a } }

#[allow(dead_code)]
fn ca_apply1(op: i32, a: f64) -> f64 {
    match op {
        0x06 => if a >= 0.0 { a.sqrt() } else { 0.0 },
        0x07 => if a > 0.0 { a.ln() } else { 0.0 },
        0x08 => a.exp(),
        // floor/ceil/round go through Python int -> float, which has no -0.0;
        // `+ 0.0` normalizes Rust's -0.0 result to +0.0 to match.
        0x0D => a.floor() + 0.0,
        0x0E => a.ceil() + 0.0,
        0x0F => ca_round_half_even(a) + 0.0,
        0x12 => ca_bool(!ca_truthy(a)),
        0x1A => (ca_int(a).unsigned_abs().count_ones()) as f64,
        0x1B => {
            let u = ca_u64(a);
            if u == 0 { 64.0 } else { u.leading_zeros() as f64 }
        }
        0x1C => {
            let n = ca_int(a).unsigned_abs();
            if n == 0 { 64.0 } else { n.trailing_zeros() as f64 }
        }
        0x2B => ca_bool(a.is_nan()),
        0x2C => ca_bool(a.is_infinite()),
        0x2D => ca_bool(a.is_finite()),
        0x2E => if a < 0.0 { -1.0 } else if a > 0.0 { 1.0 } else { 0.0 },
        0x2F => if a.is_nan() { 3.0 } else if a.is_infinite() { 2.0 } else { 1.0 },
        0x33 | 0x34 => 0.0,
        // 0x05, 0x30, 0x31, 0x32, 0x35..=0x3F and unknown ops return a.
        _ => a,
    }
}

#[allow(dead_code)]
fn ca_apply2(op: i32, a: f64, b: f64) -> f64 {
    match op {
        0x05 => a.powf(b),
        0x10 => ca_bool(ca_truthy(a) && ca_truthy(b)),
        0x11 => ca_bool(ca_truthy(a) || ca_truthy(b)),
        // XOR/AND/shift/bit-set/bit-clear: Python operates on SIGNED ints and
        // returns float() of the signed result -> use i64 (two's complement).
        0x13 => (ca_int(a) ^ ca_int(b)) as f64,
        0x14 => ca_bool(!(ca_truthy(a) && ca_truthy(b))),
        0x15 => ca_bool(!(ca_truthy(a) || ca_truthy(b))),
        0x16 => {
            // Left shift within the 64-bit window; bits shifted past bit 63
            // drop out (>=64 -> 0), avoiding wrapping_shl's mod-64 masking.
            let sh = ca_int(b).max(0) as u32;
            ca_int(a).checked_shl(sh).unwrap_or(0) as f64
        }
        0x17 => {
            // Python >> on a signed int is arithmetic and saturates the sign
            // for shifts >= 64; clamp to 63 so i64 >> matches exactly.
            let sh = ca_int(b).max(0).min(63) as u32;
            (ca_int(a) >> sh) as f64
        }
        // rotate: Python masks operand to u64 first -> unsigned rotate.
        0x18 => {
            let shift = ca_int(b).rem_euclid(64) as u32;
            ca_u64(a).rotate_left(shift) as f64
        }
        0x19 => {
            let shift = ca_int(b).rem_euclid(64) as u32;
            ca_u64(a).rotate_right(shift) as f64
        }
        0x1D => (ca_int(a) & ca_int(b)) as f64,
        0x1E => {
            // Set bit `sh`; a bit >= 64 is outside the 64-bit window (no-op).
            let sh = ca_int(b).max(0) as u32;
            let bit = 1i64.checked_shl(sh).unwrap_or(0);
            (ca_int(a) | bit) as f64
        }
        0x1F => {
            // Clear bit `sh`; a bit >= 64 is outside the window (no-op).
            let sh = ca_int(b).max(0) as u32;
            let bit = 1i64.checked_shl(sh).unwrap_or(0);
            (ca_int(a) & !bit) as f64
        }
        0x21 => ca_bool(a != b),
        0x23 => ca_bool(a <= b),
        0x25 => ca_bool(a >= b),
        0x26 => if a < b { -1.0 } else if a > b { 1.0 } else { 0.0 },
        0x27 => ca_min(a, b),
        0x28 => ca_max(a, b),
        0x30 => a + b,
        0x31 => a * b,
        0x32 => (a + b) / 2.0,
        0x38 => if ca_truthy(b) { a } else { 0.0 },
        0x3C => ca_min(a, b),
        0x3D => if a == b { a } else { a + b },
        0x3E => 2.0,
        0x35 | 0x36 | 0x37 | 0x39 | 0x3A | 0x3B | 0x3F => a + b,
        _ => a,
    }
}

#[allow(dead_code)]
fn ca_apply3(op: i32, a: f64, b: f64, c: f64) -> f64 {
    match op {
        0x29 => {
            let (lo, hi) = if b <= c { (b, c) } else { (c, b) };
            ca_min(ca_max(a, lo), hi)
        }
        0x2A => {
            let (lo, hi) = if b <= c { (b, c) } else { (c, b) };
            ca_bool(lo <= a && a <= hi)
        }
        0x33 => {
            let m = (a + b + c) / 3.0;
            ((a - m).powi(2) + (b - m).powi(2) + (c - m).powi(2)) / 3.0
        }
        0x34 => ca_apply3(0x33, a, b, c).sqrt(),
        0x35 | 0x36 | 0x37 | 0x3A | 0x3B | 0x3F => a + b + c,
        _ => ca_apply2(op, ca_apply2(op, a, b), c),
    }
}
"""
    if target == "c":
        return """#include <math.h>
static double ca_bool(int v) { return v ? 1.0 : 0.0; }
static double ca_apply1(int op, double a) { return op == 0x12 ? ca_bool(a == 0.0) : a; }
static double ca_apply2(int op, double a, double b) {
    if (op == 0x10) return ca_bool(a != 0.0 && b != 0.0);
    if (op == 0x11) return ca_bool(a != 0.0 || b != 0.0);
    if (op == 0x21) return ca_bool(a != b);
    if (op == 0x23) return ca_bool(a <= b);
    if (op == 0x25) return ca_bool(a >= b);
    if (op == 0x27) return a < b ? a : b;
    if (op == 0x28) return a > b ? a : b;
    return a + b;
}
static double ca_apply3(int op, double a, double b, double c) {
    double lo = b < c ? b : c, hi = b > c ? b : c;
    if (op == 0x29) return a < lo ? lo : (a > hi ? hi : a);
    if (op == 0x2A) return ca_bool(lo <= a && a <= hi);
    return ca_apply2(op, ca_apply2(op, a, b), c);
}
"""
    if target == "julia":
        return """ca_bool(v) = v ? 1.0 : 0.0
ca_apply1(op, a) = op == 0x12 ? ca_bool(a == 0) : a
function ca_apply2(op, a, b)
    op == 0x10 && return ca_bool(a != 0 && b != 0)
    op == 0x11 && return ca_bool(a != 0 || b != 0)
    op == 0x21 && return ca_bool(a != b)
    op == 0x23 && return ca_bool(a <= b)
    op == 0x25 && return ca_bool(a >= b)
    op == 0x27 && return min(a, b)
    op == 0x28 && return max(a, b)
    return a + b
end
function ca_apply3(op, a, b, c)
    op == 0x29 && return min(max(a, min(b, c)), max(b, c))
    op == 0x2A && return ca_bool(min(b, c) <= a <= max(b, c))
    return ca_apply2(op, ca_apply2(op, a, b), c)
end
"""
    if target == "haskell":
        return """caBool v = if v then 1.0 else 0.0
caApply1 op (a:xs) = (if op == 0x12 then caBool (a == 0) else a) : xs
caApply1 _ xs = xs
caApply2 op (b:a:xs)
  | op == 0x10 = caBool (a /= 0 && b /= 0) : xs
  | op == 0x11 = caBool (a /= 0 || b /= 0) : xs
  | op == 0x21 = caBool (a /= b) : xs
  | op == 0x23 = caBool (a <= b) : xs
  | op == 0x25 = caBool (a >= b) : xs
  | op == 0x27 = min a b : xs
  | op == 0x28 = max a b : xs
  | otherwise = a + b : xs
caApply2 _ xs = xs
caApply3 op (c:b:a:xs)
  | op == 0x29 = min (max a (min b c)) (max b c) : xs
  | op == 0x2A = caBool (min b c <= a && a <= max b c) : xs
  | otherwise = caApply2 op (caApply2 op (b:a:xs))
caApply3 _ xs = xs
"""
    if target == "zig":
        return """const std = @import("std");
fn caBool(v: bool) f64 { return if (v) 1.0 else 0.0; }
fn caApply1(op: i32, a: f64) f64 { return if (op == 0x12) caBool(a == 0.0) else a; }
fn caApply2(op: i32, a: f64, b: f64) f64 {
    if (op == 0x10) return caBool(a != 0.0 and b != 0.0);
    if (op == 0x11) return caBool(a != 0.0 or b != 0.0);
    if (op == 0x21) return caBool(a != b);
    if (op == 0x23) return caBool(a <= b);
    if (op == 0x25) return caBool(a >= b);
    if (op == 0x27) return @min(a, b);
    if (op == 0x28) return @max(a, b);
    return a + b;
}
fn caApply3(op: i32, a: f64, b: f64, c: f64) f64 {
    if (op == 0x29) return @min(@max(a, @min(b, c)), @max(b, c));
    if (op == 0x2A) return caBool(@min(b, c) <= a and a <= @max(b, c));
    return caApply2(op, caApply2(op, a, b), c);
}
"""
    raise ValueError(f"unsupported target {target!r}")


_TRACE_RE = _re.compile(r"(?:#|//|--)\s*([a-z]+)\s*\(0x([0-9A-Fa-f]{2})\)")


def disassemble(source: str) -> List[Tuple[int, str]]:
    """Recover (op_id, name) trace from compiled source comments."""

    out: List[Tuple[int, str]] = []
    for line in source.splitlines():
        m = _TRACE_RE.search(line)
        if m:
            out.append((int(m.group(2), 16), m.group(1)))
    return out
