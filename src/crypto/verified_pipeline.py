"""Unified verification pipeline: verified composition -> portable code, with TWO independent proofs.

A brick can be logic-proven yet have an UNFAITHFUL cross-language emit -- so portable verified code needs:
  PROOF 1 (logic):  each brick fn == its spec, by exhaustion over its finite domain.
  PROOF 2 (emit):   the cross-compiled py and js faces AGREE with each other AND with fn, by execution.
A frame ships as portable verified code only if BOTH hold. (Cross-face needs node; callers/tests guard it.)
"""
from __future__ import annotations
import json
import subprocess
import sys
from collections import deque


class ContractError(Exception):
    pass


class Brick:
    """fn over a finite domain + spec (logic proof) + py/js emits (portable faces)."""

    def __init__(self, name, fn, domain, spec, py, js):
        self.name, self.fn, self.domain = name, fn, frozenset(domain)
        self.emits = frozenset(fn(x) for x in domain)
        self.spec, self.py, self.js = spec, py, js
        self.proven = self._prove()

    def _prove(self):
        for x in sorted(self.domain):
            if self.fn(x) != self.spec(x):
                return (False, x)
        return (True, None)


def joint_ok(a, b):
    return a.emits <= b.domain


def bond(a, b):
    if not joint_ok(a, b):
        raise ContractError(f"{a.name}->{b.name}: emits {sorted(a.emits - b.domain)} not accepted")
    c = Brick(f"({a.name}>>{b.name})", lambda x, a=a, b=b: b.fn(a.fn(x)), a.domain,
              spec=lambda x, a=a, b=b: b.fn(a.fn(x)), py=None, js=None)
    c._path = getattr(a, "_path", [a]) + [b]
    return c


def compile_frame(library, start, goal, max_len=6):
    start._path = [start]
    q = deque([start])
    seen = {frozenset(start.emits)}
    while q:
        cur = q.popleft()
        if goal(cur.emits):
            return cur
        if len(cur._path) >= max_len:
            continue
        for b in library:
            if joint_ok(cur, b):
                comp = bond(cur, b)
                key = frozenset(comp.emits)
                if key not in seen:
                    seen.add(key)
                    q.append(comp)
    return None


def cross_compile(path):
    py = js = "x"
    for b in path:
        py = b.py.format(x=py)
        js = b.js.format(x=js)
    return f"def f(x):\n    return {py}", f"function f(x){{ return {js}; }}"


def cross_face(py_src, js_src, fn, domain):
    xs = sorted(domain)
    pc = py_src + "\nimport json\nprint(json.dumps([f(x) for x in %r]))" % xs
    jc = js_src + "\nconsole.log(JSON.stringify(%s.map(f)));" % json.dumps(xs)
    rp = json.loads(subprocess.run([sys.executable, "-c", pc], capture_output=True, text=True, timeout=10).stdout)
    rj = json.loads(subprocess.run(["node", "-e", jc], capture_output=True, text=True, timeout=10).stdout)
    ref = [fn(x) for x in xs]
    return {"py_js_agree": rp == rj, "py_fn_agree": rp == ref, "all_agree": rp == rj == ref,
            "witness": next(({"x": x, "py": p, "js": j, "fn": r}
                             for x, p, j, r in zip(xs, rp, rj, ref) if not (p == j == r)), None)}


def pipeline(library, start, goal):
    frame = compile_frame(library, start, goal)
    if frame is None:
        return {"ok": False, "reason": "no conserving arrangement reaches the goal"}
    path = frame._path
    for b in path:
        if b.proven[0] is False:                                 # PROOF 1: logic
            return {"ok": False, "reason": f"brick {b.name} fails its spec at {b.proven[1]}"}
    py_src, js_src = cross_compile(path)
    cf = cross_face(py_src, js_src, frame.fn, frame.domain)       # PROOF 2: emit faithfulness
    if not cf["all_agree"]:
        return {"ok": False, "reason": "emit UNFAITHFUL -- faces/fn diverge", "witness": cf["witness"],
                "path": [b.name for b in path]}
    return {"ok": True, "path": [b.name for b in path], "py": py_src, "js": js_src,
            "logic_proven": True, "emit_faithful": True}


def good_library():
    return [
        Brick("inc4", lambda x: (x + 1) & 15, range(16), lambda x: (x + 1) % 16, "(({x}+1)%16)", "((({x})+1)%16)"),
        Brick("clamp7", lambda x: min(x, 7), range(16), lambda x: x if x <= 7 else 7, "min({x},7)", "Math.min({x},7)"),
        Brick("half", lambda x: x // 2, range(8), lambda x: int(x / 2), "({x}//2)", "Math.floor({x}/2)"),
        Brick("dbl", lambda x: (x * 2) & 15, range(8), lambda x: (2 * x) % 16, "(({x}*2)%16)", "((({x})*2)%16)"),
    ]
