"""Behavioural-portability regression for the TypeScript emitter.

In JavaScript/TypeScript a bare ``//`` starts a line comment. If ``emit_typescript``
passes a Python floor-division operator through verbatim, ``return a // b;`` is read
by the runtime as ``return a;`` -- the function silently returns the left operand
instead of the floored quotient (e.g. ``idiv(7, 2)`` yields ``7`` in TS vs ``3`` in
Python). The shape-only parity test cannot catch this because signatures are
unaffected. These tests pin the divergence closed.
"""

from src.code_prism.emitter import emit_typescript
from src.code_prism.models import PrismFunction, PrismModule


def _idiv_module() -> PrismModule:
    return PrismModule(
        module_name="idiv_mod",
        source_language="python",
        functions=[
            PrismFunction(name="idiv", args=["a", "b"], body=["return a // b"], returns="int"),
        ],
    )


def test_typescript_never_leaks_bare_floor_division_comment():
    code = emit_typescript(_idiv_module())
    # A bare `a // b` in emitted TS is parsed as a line comment -> silent wrong result.
    assert "a // b" not in code


def test_typescript_floor_division_uses_math_floor():
    code = emit_typescript(_idiv_module())
    # The floor-division must be rewritten to an explicit, behaviourally-faithful form.
    assert "Math.floor((a) / (b))" in code


def test_typescript_floor_division_semantics_match_python():
    code = emit_typescript(_idiv_module())
    body_line = next(line for line in code.splitlines() if "return" in line)
    expr = body_line.strip()[len("return ") : -1].strip()
    # Evaluate the emitted expression with a==7, b==2 using math.floor for Math.floor.
    import math

    value = eval(expr.replace("Math.floor", "math.floor"), {"math": math, "a": 7, "b": 2})
    assert value == 3  # matches Python's 7 // 2


def _module(body):
    return PrismModule(
        module_name="m",
        source_language="python",
        functions=[PrismFunction(name="f", args=["a", "b", "c"], body=body, returns="int")],
    )


def test_floor_division_inside_string_literal_is_not_rewritten():
    # regression: a `//` inside a string literal must NOT be rewritten to Math.floor.
    code = emit_typescript(_module(['return "a // b"']))
    assert 'return "a // b";' in code
    assert "Math.floor" not in code


def test_chained_floor_division_is_left_associative():
    # a // b // c == (a // b) // c in Python; the rewrite must nest left, not right.
    code = emit_typescript(_module(["return a // b // c"]))
    assert "Math.floor((Math.floor((a) / (b))) / (c))" in code
    import math

    expr = next(l for l in code.splitlines() if "return" in l).strip()[len("return ") : -1]
    assert eval(expr.replace("Math.floor", "math.floor"), {"math": math, "a": 20, "b": 3, "c": 2}) == 20 // 3 // 2
