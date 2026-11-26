"""Execution correctness gate -- the front door's trust lane (folded in from verifier-bench).

The structural badge (bijective_dna.faces_agree) only checks that each language face emits+decodes
back to the same opcode strand -- a round-trip, not a run. This gate is the EXECUTING half: it emits
the SAME program into multiple language faces, RUNS them on a fuzzed input battery, and the faces are
references FOR EACH OTHER. If they DIVERGE on any in-domain input, the generation is wrong.

  SEAL   -- every face agrees on every in-domain input -> verified, light the badge.
  REJECT -- faces DIVERGE on an input -> a real bug (e.g. Python `%` vs JS `%` on negatives); show witness.
  FLAG   -- a face won't run, or coverage too thin -> escalate to review (hand off what it can't PROVE).

This is the load-bearing fix: the front door's "verified" badge must light from EXECUTION (this gate),
not a structural round-trip -- for a user who judges by badges and cannot read the code, a badge that
never runs anything is false trust. Self-contained (stdlib + node); no model in the trust path.

COMPARISON HARDENING (verified by execution; see `_norm` + the symmetric loop below):
  * integers/bitwise -- EXACT; floats -- canonicalized (round 9dp, and -0.0 == 0.0); strings --
    quote-style agnostic (py repr "'x'" == js JSON '"x"'), kept DISTINCT from numbers; bool 'True'=='true'.
  * SYMMETRIC errors -- an input is out-of-domain only if ALL faces error; if the reference RAISES but
    another face SUCCEEDS (div-by-zero, type-coercion) that IS a divergence, caught regardless of order.
KNOWN py<->js divergences this catches (idiomatic translations that silently differ -- the talk->code
traps): `a%b` sign on negatives (-7%3 = 2 vs -1); floor-div via `(a/b)|0` truncation (use Math.floor);
`a<<b` 32-bit overflow + `a>>b` JS-masks-shift-count-mod-32; div-by-zero (py raises vs js Infinity);
`"5"+3` and `str*int` coercion (py TypeError/repeat vs js). PORTABLE (idiomatic faces agree): + - *,
floor-div via Math.floor, & | ^, abs, min/max, comparisons (int-coerced), string concat, len.
"""
from __future__ import annotations
import json
import subprocess
import sys
import random

_PY_HARNESS = (
    "%s\nimport json,sys\n_f=%s\n_out=[]\n"
    "for _a in %s:\n"
    " try:_out.append(['ok',repr(_f(*_a))])\n"
    " except Exception as _e:_out.append(['err',type(_e).__name__])\n"
    "print(json.dumps(_out))\n"
)
_JS_HARNESS = (
    "%s\nconst _f=%s;const _in=%s;const _o=[];\n"
    "for(const _a of _in){try{_o.push(['ok',JSON.stringify(_f(..._a))]);}catch(e){_o.push(['err',e.constructor.name]);}}\n"
    "console.log(JSON.stringify(_o));\n"
)

def _run(face_src, entry, inputs, lang, timeout=8):
    if lang == "python":
        src = _PY_HARNESS % (face_src, entry, repr([list(i) for i in inputs]))
        cmd = [sys.executable, "-c", src]
    else:
        src = _JS_HARNESS % (face_src, entry, json.dumps([list(i) for i in inputs]))
        cmd = ["node", "-e", src]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None

_OPS = ["+", "-", "*", "/"]

def _resample(col, rng, d=0):
    v = col[0]
    if isinstance(v, list) and d < 3:
        elems = [e for x in col if isinstance(x, list) for e in x]
        if not elems:
            return []
        ml = max((len(x) for x in col if isinstance(x, list)), default=3)
        return [_resample(elems, rng, d + 1) for _ in range(rng.randint(0, min(2 * ml + 1, 12)))]
    if isinstance(v, bool):
        return rng.choice([True, False])
    if isinstance(v, int):
        nums = [x for x in col if isinstance(x, int) and not isinstance(x, bool)]
        return rng.choice(nums + [0, 1, -1, 2]) if nums else rng.choice([0, 1, 2])
    if isinstance(v, float):
        nums = [x for x in col if isinstance(x, float)]
        return rng.choice(nums) if nums and rng.random() < 0.6 else round(rng.uniform(-5, 5), 3)
    if isinstance(v, str):
        toks = [x for x in col if isinstance(x, str)]
        return rng.choice(toks) if toks else ""
    return v

def _grammar(bases, rng, cap=60):
    out = []
    arity = len(bases[0])
    for i in range(arity):
        col = [b[i] for b in bases]
        if not any(isinstance(v, list) and any(isinstance(e, (int, float)) and not isinstance(e, bool) for e in v) for v in col):
            continue
        nums = [e for v in col if isinstance(v, list) for e in v if isinstance(e, (int, float)) and not isinstance(e, bool)] or [1.0, 2.0, 3.0]
        def tree(d=0):
            if d >= 4 or (d > 0 and rng.random() < 0.45):
                return ("n", rng.choice(nums))
            return ("o", rng.choice(_OPS), tree(d + 1), tree(d + 1))
        def rpn(t): return [t[1]] if t[0] == "n" else rpn(t[2]) + rpn(t[3]) + [t[1]]
        def infx(t): return [t[1]] if t[0] == "n" else infx(t[2]) + [t[1]] + infx(t[3])
        for _ in range(cap):
            t = tree()
            for toks in (rpn(t), infx(t)):
                b = list(bases[rng.randrange(len(bases))]); b[i] = toks; out.append(tuple(b))
            if len(out) >= cap:
                break
    return out

def _battery(seeds, n=40, rng_seed=0):
    rng = random.Random(rng_seed)
    bases = [tuple(s) for s in seeds if s]
    if not bases:
        return []
    out, seen = list(bases), set(repr(b) for b in bases)
    def add(t):
        try:
            k = repr(t)
        except Exception:
            return
        if k not in seen:
            seen.add(k); out.append(t)
    EDGES = [0, 1, -1, 2, 10, -10, 100]
    for base in bases:
        for i in range(len(base)):
            v = base[i]
            cands = EDGES if isinstance(v, int) and not isinstance(v, bool) else (
                ["", v[:1], v + v[:1]] if isinstance(v, str) else
                ([[], [v[0]] if v else [0], list(reversed(v))] if isinstance(v, list) else []))
            for e in cands:
                t = list(base); t[i] = e; add(tuple(t))
    for _ in range(n):
        b = list(rng.choice(bases))
        for i in range(len(b)):
            if isinstance(b[i], int) and not isinstance(b[i], bool):
                b[i] += rng.choice([-3, -1, 1, 2, 5])
        add(tuple(b))
    for _ in range(80):
        add(tuple(_resample([b[i] for b in bases], rng) for i in range(len(bases[0]))))
    for t in _grammar(bases, rng):
        add(t)
    return out

def correctness_gate(faces, entry, seeds, min_inputs=6):
    """faces = {'python': src, 'javascript': src, ...}. Returns SEAL / REJECT / FLAG with a reason."""
    inputs = _battery(seeds)
    if len(inputs) < min_inputs:
        return {"verdict": "FLAG", "reason": "too few inputs to verify (low coverage) -> AI review", "route": "ai_review"}
    runs = {}
    for lang, src in faces.items():
        out = _run(src, entry, inputs, lang)
        if out is None:
            return {"verdict": "FLAG", "reason": "face '%s' failed to run -> AI review" % lang, "route": "ai_review"}
        runs[lang] = out
    langs = list(runs)
    if len(langs) < 2:
        return {"verdict": "FLAG", "reason": "need >=2 faces to cross-verify -> AI review", "route": "ai_review"}
    ref = langs[0]
    compared = 0
    for i, inp in enumerate(inputs):
        base = runs[ref][i]
        others = [runs[o][i] for o in langs[1:]]
        # symmetric: skip ONLY if ALL faces error (genuinely out-of-domain). If the reference errors
        # but another face is OK, that IS a divergence (e.g. py raises ZeroDivisionError vs js Infinity)
        # and must be caught -- the old `if base[0]=='err': continue` missed it (face-order dependent).
        if base[0] == "err" and all(o[0] == "err" for o in others):
            continue
        compared += 1
        for other, o in zip(langs[1:], others):
            ok_match = (o[0] == "ok" and base[0] == "ok" and _norm(o[1]) == _norm(base[1])) or (o[0] == "err" and base[0] == "err")
            if not ok_match:
                return {"verdict": "REJECT", "reason": "faces DISAGREE -> generation bug",
                        "witness": {"input": list(inp), ref: base, other: o}, "route": "block_seal"}
    if compared < min_inputs:
        return {"verdict": "FLAG", "reason": "faces agreed but on too few in-domain inputs -> AI review", "route": "ai_review"}
    return {"verdict": "SEAL", "reason": "all %d faces agree on %d in-domain inputs -> verified" % (len(langs), compared),
            "checked": compared, "route": "seal"}

def _norm(s):
    t = s.strip()
    low = t.lower()
    if low in ("true", "false"):
        return low
    if len(t) >= 2 and t[0] in "\"'" and t[-1] == t[0]:   # a quoted string (py repr ' vs js JSON ") -> quote-agnostic inner
        return "str:" + t[1:-1]                            # ('5' the string stays DISTINCT from number 5 -> no conflation)
    try:
        return repr(round(float(t), 9) + 0.0)   # +0.0 canonicalizes -0.0 -> 0.0 (py repr '-0.0' vs js '0' was a false REJECT)
    except Exception:
        return t
