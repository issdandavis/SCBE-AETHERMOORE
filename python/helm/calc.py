"""calc -- the fancy calculator any AI (or human) can call for what AIs are BAD at:
precise arithmetic, big numbers, combinatorics, rounding, estimation, and "where on a scale".

The division of labor: the AI does the EASY part (read the problem, simplify it to an
expression), the calculator does the HARD part (compute it EXACTLY, or round/estimate).
The model never has to math it out in its head -- it offloads to a deterministic tool.

Safe by construction: expressions are evaluated through a whitelisted AST walker, NOT eval()
-- no imports, no attribute access, no names except known math constants/functions.

  ev(expr)            -> exact value of an arithmetic expression
  estimate(expr, k)   -> the value rounded to k significant figures (the "round and estimate")
  sig(x, k)           -> round x to k significant figures
  sci(x, k)           -> scientific-notation string
  magnitude(x)        -> order of magnitude (floor log10) -- "how big is it"
  on_scale(x, lo, hi) -> where x falls between lo and hi, 0..1 (log=True for log scale)
  simplify_ratio(a,b) -> reduce a/b to lowest terms
  try_calc(text)      -> NL front door: pull a math expression out of a question, answer it, else None
"""

from __future__ import annotations
import ast, math, operator, re
from fractions import Fraction
from typing import Optional, Dict, Any

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow}
_UN = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
          "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
          "floor": math.floor, "ceil": math.ceil, "abs": abs, "round": round,
          "factorial": math.factorial, "gcd": math.gcd, "comb": math.comb,
          "perm": math.perm, "min": min, "max": max, "sum": sum, "pow": pow}
_CONST = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _node(n):
    if isinstance(n, ast.Expression):
        return _node(n.body)
    if isinstance(n, ast.Constant):
        if isinstance(n.value, (int, float)):
            return n.value
        raise ValueError("non-numeric constant")
    if isinstance(n, ast.BinOp):
        op = _BIN.get(type(n.op))
        if not op:
            raise ValueError("operator not allowed")
        return op(_node(n.left), _node(n.right))
    if isinstance(n, ast.UnaryOp):
        op = _UN.get(type(n.op))
        if not op:
            raise ValueError("unary not allowed")
        return op(_node(n.operand))
    if isinstance(n, ast.Call):
        if not isinstance(n.func, ast.Name) or n.func.id not in _FUNCS:
            raise ValueError("function not allowed")
        return _FUNCS[n.func.id](*[_node(a) for a in n.args])
    if isinstance(n, ast.Tuple):
        return tuple(_node(e) for e in n.elts)
    if isinstance(n, ast.List):
        return [_node(e) for e in n.elts]
    if isinstance(n, ast.Name):
        if n.id in _CONST:
            return _CONST[n.id]
        raise ValueError("name not allowed: %s" % n.id)
    raise ValueError("unsupported expression")


def ev(expr: str):
    """Exact value of an arithmetic expression (safe, whitelisted)."""
    return _node(ast.parse(expr.strip(), mode="eval"))


def sig(x: float, k: int = 3):
    """Round x to k significant figures."""
    if x == 0 or not math.isfinite(x):
        return 0.0 if x == 0 else x
    d = k - 1 - math.floor(math.log10(abs(x)))
    r = round(x, d)
    return int(r) if d <= 0 and float(r).is_integer() else r


def sci(x: float, k: int = 3) -> str:
    return "%.*e" % (k - 1, x)


def magnitude(x: float) -> Optional[int]:
    if x == 0:
        return None
    return math.floor(math.log10(abs(x)))


def estimate(expr: str, k: int = 2):
    """Evaluate, then round to k significant figures -- 'simplify and estimate'."""
    return sig(ev(expr), k)


def on_scale(x: float, lo: float, hi: float, log: bool = False) -> float:
    """Where x falls between lo and hi as a fraction 0..1 (log=True for a log scale)."""
    if log:
        return (math.log10(x) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    return (x - lo) / (hi - lo)


def simplify_ratio(a: int, b: int):
    f = Fraction(a, b)
    return (f.numerator, f.denominator)


# --- natural-language front door ---------------------------------------------
_WORD_OPS = [
    (r"\bto the power of\b", "**"), (r"\braised to(?: the power of)?\b", "**"),
    (r"\bmultiplied by\b", "*"), (r"\bdivided by\b", "/"),
    (r"\bplus\b", "+"), (r"\bminus\b", "-"), (r"\btimes\b", "*"),
    (r"\bmod(?:ulo)?\b", "%"), (r"\bsquared\b", "**2"), (r"\bcubed\b", "**3"),
    (r"\bx\b", "*"), (r"\bover\b", "/"),
]
_STRIP = re.compile(
    r"\b(what(?:'s| is| are)|whats|calculate|compute|evaluate|the value of|how much is|equals?|please)\b",
    re.I)


def try_calc(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort: turn a math question into an expression and answer it deterministically.
    Returns {answer, how} or None (then a more specific tool / the model handles it)."""
    if not text:
        return None
    t = text.strip().rstrip("?.! ").lower()

    # magnitude / scale phrasings
    m = re.match(r"order of magnitude of (.+)", t)
    if m:
        try:
            return {"answer": magnitude(ev(_translate(m.group(1)))), "how": "magnitude"}
        except Exception:
            return None

    estimating = bool(re.match(r"(estimate|roughly|approximately|about|around)\b", t))
    t = re.sub(r"^(estimate|roughly|approximately|about|around)\b", "", t).strip()
    t = _STRIP.sub("", t).strip()
    expr = _translate(t)
    # require something that actually looks computational: a digit AND an op/func
    if not re.search(r"\d", expr) or not re.search(r"[-+*/%()]|sqrt|log|factorial|comb|perm|abs|exp", expr):
        return None
    try:
        val = ev(expr)
    except Exception:
        return None
    if estimating:
        return {"answer": estimate(expr, 2), "how": "estimate(2 sig figs)"}
    return {"answer": val, "how": "exact"}


def _translate(s: str) -> str:
    for pat, rep in _WORD_OPS:
        s = re.sub(pat, rep, s, flags=re.I)
    s = s.replace("^", "**").replace(",", "")
    return s.strip()


if __name__ == "__main__":
    # exact arithmetic the model fumbles
    assert ev("2**10") == 1024
    assert ev("factorial(20)") == 2432902008176640000
    assert ev("(1+2)*3 - 4/2") == 7.0
    assert ev("comb(52, 5)") == 2598960
    assert ev("sqrt(144)") == 12.0
    # rounding / estimation
    assert sig(123456, 2) == 120000
    assert sig(0.00314159, 3) == 0.00314
    assert estimate("123456 * 789012", 2) == 97000000000
    assert magnitude(6582952005840035281) == 18
    # scale + ratio
    assert on_scale(50, 0, 100) == 0.5
    assert abs(on_scale(100, 1, 10000, log=True) - 0.5) < 1e-9
    assert simplify_ratio(8, 12) == (2, 3)
    # NL front door
    assert try_calc("what is 37 to the power of 12")["answer"] == 37 ** 12
    assert try_calc("calculate (15 + 9) * 3")["answer"] == 72
    assert try_calc("estimate 123456 times 789012")["answer"] == 97000000000
    assert try_calc("order of magnitude of 9 billion".replace("billion", "* 10**9"))["answer"] == 9
    assert try_calc("how do you reverse a linked list") is None  # not math -> fall through
    # safety: no imports / attributes / names
    for bad in ["__import__('os')", "x + 1", "(1).__class__", "open('f')"]:
        try:
            ev(bad); raise AssertionError("should have rejected: " + bad)
        except ValueError:
            pass
    print("calc self-test: PASS (exact, estimate/round, magnitude, scale, NL front door, sandboxed)")
