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
        return """func caPop1(stack []float64) (float64, []float64) {
\treturn stack[len(stack)-1], stack[:len(stack)-1]
}
func caPop2(stack []float64) (float64, float64, []float64) {
\tb := stack[len(stack)-1]
\ta := stack[len(stack)-2]
\treturn a, b, stack[:len(stack)-2]
}
func caBool(v bool) float64 { if v { return 1 }; return 0 }
func caApply1(op int, a float64) float64 { if op == 0x12 { return caBool(a == 0) }; return a }
func caApply2(op int, a, b float64) float64 {
\tif op == 0x10 { return caBool(a != 0 && b != 0) }
\tif op == 0x11 { return caBool(a != 0 || b != 0) }
\tif op == 0x21 { return caBool(a != b) }
\tif op == 0x23 { return caBool(a <= b) }
\tif op == 0x25 { return caBool(a >= b) }
\tif op == 0x27 { if a < b { return a }; return b }
\tif op == 0x28 { if a > b { return a }; return b }
\treturn a + b
}
func caApply3(op int, a, b, c float64) float64 {
\tif op == 0x29 { lo, hi := b, c; if lo > hi { lo, hi = hi, lo }; if a < lo { return lo }; if a > hi { return hi }; return a }
\tif op == 0x2A { lo, hi := b, c; if lo > hi { lo, hi = hi, lo }; return caBool(lo <= a && a <= hi) }
\treturn caApply2(op, caApply2(op, a, b), c)
}
"""
    if target == "rust":
        return """fn ca_bool(v: bool) -> f64 { if v { 1.0 } else { 0.0 } }
fn ca_apply1(op: i32, a: f64) -> f64 { if op == 0x12 { ca_bool(a == 0.0) } else { a } }
fn ca_apply2(op: i32, a: f64, b: f64) -> f64 {
    match op {
        0x10 => ca_bool(a != 0.0 && b != 0.0),
        0x11 => ca_bool(a != 0.0 || b != 0.0),
        0x21 => ca_bool(a != b),
        0x23 => ca_bool(a <= b),
        0x25 => ca_bool(a >= b),
        0x27 => a.min(b),
        0x28 => a.max(b),
        _ => a + b,
    }
}
fn ca_apply3(op: i32, a: f64, b: f64, c: f64) -> f64 {
    if op == 0x29 { a.max(b.min(c)).min(b.max(c)) }
    else if op == 0x2A { ca_bool(b.min(c) <= a && a <= b.max(c)) }
    else { ca_apply2(op, ca_apply2(op, a, b), c) }
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
