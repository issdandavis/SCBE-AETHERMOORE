"""The verified+portable ALPHABET -- the legal moves verified_pipeline composes from.

Every op carries BOTH proofs: logic (fn==spec, exhaustively) AND a cross-language emit faithful by
execution (py==js==fn). Python and JS disagree on `%` for negatives, so dec/sub use a guarded emit
`((v%16)+16)%16` -- the cross-face faithfulness check is exactly what catches a naive emit.
"""
from __future__ import annotations

import shutil

from src.crypto import verified_pipeline as V


def B(name, fn, spec, py, js, dom=range(16)):
    return V.Brick(name, fn, dom, spec, py, js)


def _jsmod(expr, m=16):
    return f"((({expr})%{m})+{m})%{m}"


ALPHABET = [
    B("inc",   lambda x: (x + 1) % 16,  lambda x: (x + 1) % 16,  "(({x}+1)%16)",  "((({x})+1)%16)"),
    B("dec",   lambda x: (x - 1) % 16,  lambda x: (x - 1) % 16,  "(({x}-1)%16)",  _jsmod("({x})-1")),
    B("add3",  lambda x: (x + 3) % 16,  lambda x: (x + 3) % 16,  "(({x}+3)%16)",  "((({x})+3)%16)"),
    B("sub2",  lambda x: (x - 2) % 16,  lambda x: (x - 2) % 16,  "(({x}-2)%16)",  _jsmod("({x})-2")),
    B("dbl",   lambda x: (x * 2) % 16,  lambda x: (x * 2) % 16,  "(({x}*2)%16)",  "((({x})*2)%16)"),
    B("half",  lambda x: x // 2,         lambda x: x // 2,        "({x}//2)",      "Math.floor({x}/2)"),
    B("mod5",  lambda x: x % 5,          lambda x: x % 5,         "({x}%5)",       "(({x})%5)"),
    B("and12", lambda x: x & 12,         lambda x: x & 12,        "({x}&12)",      "(({x})&12)"),
    B("or1",   lambda x: x | 1,          lambda x: x | 1,         "({x}|1)",       "(({x})|1)"),
    B("xor5",  lambda x: x ^ 5,          lambda x: x ^ 5,         "({x}^5)",       "(({x})^5)"),
    B("shr1",  lambda x: x >> 1,         lambda x: x >> 1,        "({x}>>1)",      "(({x})>>1)"),
    B("shl1",  lambda x: (x << 1) & 15,  lambda x: (x << 1) % 16, "(({x}<<1)&15)", "((({x})<<1)&15)"),
    B("sq",    lambda x: (x * x) % 16,   lambda x: (x * x) % 16,  "(({x}*{x})%16)", "((({x})*({x}))%16)"),
    B("clamp7", lambda x: min(x, 7),     lambda x: x if x <= 7 else 7, "min({x},7)", "Math.min({x},7)"),
]


def verify_alphabet():
    """Each op must be logic-proven AND emit-faithful. Returns the per-op report."""
    rep = []
    have_node = shutil.which("node") is not None
    for b in ALPHABET:
        logic = b.proven[0] is True
        if have_node:
            cf = V.cross_face(f"def f(x):\n    return {b.py.format(x='x')}",
                              f"function f(x){{ return {b.js.format(x='x')}; }}", b.fn, b.domain)
            emit, wit = cf["all_agree"], cf["witness"]
        else:
            emit, wit = None, "node-absent"
        rep.append({"op": b.name, "logic_proven": logic, "emit_faithful": emit, "witness": wit})
    return rep
