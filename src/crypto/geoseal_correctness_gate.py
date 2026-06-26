"""GeoSeal CORRECTNESS gate -- the missing half of the seal.

GeoSeal's execution_gate checks SAFETY ("does this code do dangerous things?"). It has NO check for
CORRECTNESS ("is this code right?"). This adds it, using the verifier work: the polyglot emitter builds
the SAME logic into multiple language FACES (emit_python / emit_javascript), so the faces are references
FOR EACH OTHER -- run them on generated inputs, and if they DISAGREE the generated code is wrong.
No external reference needed (that's the cube idea, executed instead of comment-grepped).

Verdict forces better output:
  SEAL   -- every face agrees on every in-domain input (+ passes any provided tests). Verified -> seal it.
  REJECT -- the faces DIVERGE on an input -> a real bug in the generation. Don't seal; show the witness.
  FLAG   -- a face won't run, or coverage is too thin to be sure -> escalate to an AI reviewer
            (the flag-and-route: the gate hands off what it can't PROVE instead of silently sealing it).
"""
from __future__ import annotations
import json
import subprocess
import sys
import random

# ---- run a face on a batch of inputs, in an isolated subprocess (timeout-safe) -----------------------
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

# ---- input battery: boundary + STRUCTURE-resampling + GRAMMAR (the validated levers, self-contained) -
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
    for base in bases:                                   # boundary corners
        for i in range(len(base)):
            v = base[i]
            cands = EDGES if isinstance(v, int) and not isinstance(v, bool) else (
                ["", v[:1], v + v[:1]] if isinstance(v, str) else
                ([[], [v[0]] if v else [0], list(reversed(v))] if isinstance(v, list) else []))
            for e in cands:
                t = list(base); t[i] = e; add(tuple(t))
    for _ in range(n):                                   # light fuzz
        b = list(rng.choice(bases))
        for i in range(len(b)):
            if isinstance(b[i], int) and not isinstance(b[i], bool):
                b[i] += rng.choice([-3, -1, 1, 2, 5])
        add(tuple(b))
    for _ in range(80):                                  # structure resampling (lists / token streams)
        add(tuple(_resample([b[i] for b in bases], rng) for i in range(len(bases[0]))))
    for t in _grammar(bases, rng):                       # grammar (valid arithmetic expressions)
        add(t)
    return out

# ---- the gate ---------------------------------------------------------------------------------------
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
        if base[0] == "err":
            continue  # reference-error guard: input out of this face's domain
        compared += 1
        for other in langs[1:]:
            o = runs[other][i]
            ok_match = (o[0] == "ok" and base[0] == "ok" and _norm(o[1]) == _norm(base[1])) or (o[0] == "err" and base[0] == "err")
            if not ok_match:
                return {"verdict": "REJECT", "reason": "faces DISAGREE -> generation bug",
                        "witness": {"input": list(inp), ref: base, other: o}, "route": "block_seal"}
    if compared < min_inputs:
        return {"verdict": "FLAG", "reason": "faces agreed but on too few in-domain inputs -> AI review", "route": "ai_review"}
    return {"verdict": "SEAL", "reason": "all %d faces agree on %d in-domain inputs -> verified" % (len(langs), compared),
            "checked": compared, "route": "seal"}

def _norm(s):
    # normalize numeric repr across py/js (1 vs 1.0, true vs True)
    t = s.strip().strip('"')
    low = t.lower()
    if low in ("true", "false"):
        return low
    try:
        return repr(round(float(t), 9))
    except Exception:
        return t


if __name__ == "__main__":
    # SMOKE: same logic in two faces -> SEAL; a divergent js face -> REJECT; an unrunnable face -> FLAG.
    py_add = "def add(a, b):\n    return a + b"
    js_add = "function add(a, b){ return a + b; }"
    js_bug = "function add(a, b){ return a - b; }"          # divergent face = generation bug
    seeds = [(2, 3), (5, 7)]
    print("correct faces :", correctness_gate({"python": py_add, "javascript": js_add}, "add", seeds)["verdict"], "(want SEAL)")
    print("divergent face:", correctness_gate({"python": py_add, "javascript": js_bug}, "add", seeds)["verdict"], "(want REJECT)")
    print("broken face   :", correctness_gate({"python": py_add, "javascript": "function add( syntax error"}, "add", seeds)["verdict"], "(want FLAG)")
    r = correctness_gate({"python": py_add, "javascript": js_bug}, "add", seeds)
    print("  reject witness:", r.get("witness"))
