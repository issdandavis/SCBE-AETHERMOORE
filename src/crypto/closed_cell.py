"""Correct-by-construction verification cell -- a self-contained hull, no external life-support.

Cohabits with the geoseal gates (the verification surface) but is NOT crypto: it is the pure-Python
correct-by-construction verifier. No network, no ollama, no node, no external import. Every vessel real:
  * BRICK     -- fn + spec + finite domain; PROVEN by exhausting the domain (enumeration = real oracle).
  * JOINT     -- conservation-checked bond (emits subset of accepts); a non-conserving joint is REJECTED.
  * COMPILER  -- joint-search that assembles bricks into a frame meeting a spec.
  * CELL LOOP -- spec -> compiled frame + a COMPLETE PROOF (every brick proven, every joint conserved).
A fake (brick whose fn != its spec) cannot survive: it fails its own exhaustive proof.
"""
from __future__ import annotations

from collections import deque


class ContractError(Exception):
    pass


class Brick:
    """A verification vessel: fn over a finite domain, PROVEN against its spec by exhaustion."""

    def __init__(self, name, fn, domain, spec=None):
        self.name = name
        self.fn = fn
        self.domain = frozenset(domain)
        self.emits = frozenset(fn(x) for x in domain)     # a-hinge: exhaustively-computed output range
        self.spec = spec
        self.proven = self._prove()

    def _prove(self):
        if self.spec is None:
            return ("primitive", None)                    # a trusted definition (no spec to check against)
        for x in sorted(self.domain):
            if self.fn(x) != self.spec(x):
                return (False, x)                         # exhaustion found a counterexample -> NOT proven
        return (True, None)

    def __repr__(self):
        return f"{self.name}[in={_rng(self.domain)} out={_rng(self.emits)}]"


def _rng(s):
    s = sorted(s)
    return f"{s[0]}..{s[-1]}" if s and s[-1] - s[0] + 1 == len(s) else str(s)


def joint_ok(a, b):
    return a.emits <= b.domain                            # conservation: every emitted color is accepted


def bond(a, b):
    if not joint_ok(a, b):
        raise ContractError(f"{a.name}->{b.name}: emits {sorted(a.emits - b.domain)} not accepted")
    return Brick(f"({a.name}>>{b.name})", lambda x, a=a, b=b: b.fn(a.fn(x)), a.domain)


def compile_frame(library, start, goal, max_len=6):
    q = deque([(start, [start])])
    seen = {frozenset(start.emits)}
    while q:
        cur, path = q.popleft()
        if goal(cur.emits):
            return cur, path
        if len(path) >= max_len:
            continue
        for b in library:
            if joint_ok(cur, b):
                comp = bond(cur, b)
                key = frozenset(comp.emits)
                if key not in seen:
                    seen.add(key)
                    q.append((comp, path + [b]))
    return None, None


def run_cell(library, start, goal):
    """The closed loop: spec -> verified frame + complete proof. Correct by construction, no oracle, no dep."""
    frame, path = compile_frame(library, start, goal)
    if frame is None:
        return {"ok": False, "reason": "no conserving arrangement reaches the goal"}
    proof = {"bricks": [], "joints": []}
    for b in path:
        ok, ce = b.proven
        proof["bricks"].append({"brick": b.name, "proven": ok, "counterexample": ce})
        if ok is False:                                   # a fake cannot survive the cell
            return {"ok": False, "reason": f"brick {b.name} FAILS its spec at input {ce}", "proof": proof}
    for a, b in zip(path, path[1:]):
        proof["joints"].append({"joint": f"{a.name}->{b.name}", "conserved": True})
    return {"ok": True, "frame": frame, "path": [b.name for b in path], "proof": proof}


def standard_library():
    """A sealed-in library of PROVEN vessels (each fn checked against an independent spec)."""
    return [
        Brick("inc4", lambda x: (x + 1) & 15, range(16), spec=lambda x: (x + 1) % 16),
        Brick("clamp7", lambda x: min(x, 7), range(16), spec=lambda x: x if x <= 7 else 7),
        Brick("half", lambda x: x // 2, range(8), spec=lambda x: int(x / 2)),
        Brick("dbl", lambda x: (x * 2) & 15, range(8), spec=lambda x: (2 * x) % 16),
        Brick("dec", lambda x: max(x - 1, 0), range(16), spec=lambda x: x - 1 if x > 0 else 0),
    ]
