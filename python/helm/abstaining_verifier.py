"""abstaining_verifier -- catch overfitting/buggy patches that pass the VISIBLE tests but are wrong.

The trust-without-reading failure mode (the one a "tests passed = correct" verifier ships):
a candidate passes the shown tests yet is incorrect on inputs nobody showed -- overfit to those
tests, or just buggy off the example path. This verifier does NOT certify on visible tests alone.
It fuzzes inputs BEYOND the visible tests and compares the candidate against an independent oracle
(a trusted reference, or the majority vote of independently-generated peers), and it ABSTAINS when
it cannot be confident -- it never returns a false "trust".

Design notes mapped to the high-stakes error-recovery research:
  * out-of-sandbox execution: every candidate runs in a fresh subprocess, so a candidate cannot
    monkey-patch the grader or leak state into the comparison (defeats reward-hacking the checker).
  * graded verdicts: 'trust' | 'reject' | 'abstain'. Abstain is a first-class, honest outcome.
  * independent instrument: the oracle is a reference or a peer-majority, never the candidate itself.

Public API:
  differential(candidate, reference, tests, func=None, n_fuzz=40) -> verdict dict
  consensus(candidate, peers, tests, func=None, n_fuzz=40)        -> verdict dict
"""

from __future__ import annotations

import ast
import json
import random
import re
import subprocess
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

_TIMEOUT = 20


def _func_name(code: str) -> Optional[str]:
    try:
        for node in ast.parse(code or "").body:
            if isinstance(node, ast.FunctionDef):
                return node.name
    except Exception:
        pass
    m = re.search(r"def\s+(\w+)\s*\(", code or "")
    return m.group(1) if m else None


def _extract_call_args(tests: List[str], func: str) -> List[str]:
    """Pull the literal arg-strings of every func(...) call seen in the visible tests."""
    found = []
    blob = "\n".join(tests)
    for m in re.finditer(re.escape(func) + r"\s*\(", blob):
        start = m.end() - 1
        depth, i = 0, start
        while i < len(blob):
            if blob[i] == "(":
                depth += 1
            elif blob[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        found.append(blob[start + 1:i])
    return found


def _eval_args(arg_str: str) -> Optional[Tuple]:
    try:
        return ast.literal_eval("(" + arg_str + ",)")
    except Exception:
        return None


def _mutate(val: Any, rng: random.Random) -> Any:
    if isinstance(val, bool):
        return rng.choice([True, False])
    if isinstance(val, int):
        return val + rng.choice([-10, -3, -1, 1, 2, 5, 11, 100])
    if isinstance(val, float):
        return round(val + rng.uniform(-3, 3), 4)
    if isinstance(val, str):
        if not val:
            return rng.choice(["x", "ab", "Q9"])
        l = list(val)
        op = rng.choice(["swap", "drop", "dup", "char", "empty"])
        if op == "empty":
            return ""
        if op == "drop" and len(l) > 1:
            l.pop(rng.randrange(len(l)))
        elif op == "dup":
            l.insert(rng.randrange(len(l) + 1), rng.choice(l))
        elif op == "char":
            l[rng.randrange(len(l))] = rng.choice("abcxyzABZ019 ")
        elif len(l) > 1:
            i, j = rng.randrange(len(l)), rng.randrange(len(l))
            l[i], l[j] = l[j], l[i]
        return "".join(l)
    if isinstance(val, list):
        if not val:
            return [rng.randint(0, 5)]
        l = list(val)
        op = rng.choice(["perturb", "drop", "dup", "grow", "empty"])
        if op == "empty":
            return []
        if op == "drop" and len(l) > 1:
            l.pop(rng.randrange(len(l)))
        elif op == "dup":
            l.insert(rng.randrange(len(l) + 1), rng.choice(l))
        elif op == "grow":
            l.append(_mutate(rng.choice(l), rng))
        else:
            i = rng.randrange(len(l))
            l[i] = _mutate(l[i], rng)
        return l
    if isinstance(val, tuple):
        return tuple(_mutate(list(val), rng))
    if isinstance(val, dict):
        if not val:
            return {0: 1}
        d = dict(val)
        k = rng.choice(list(d))
        d[k] = _mutate(d[k], rng)
        return d
    return val


def _fuzz_inputs(seeds: List[Optional[Tuple]], n: int, rng: random.Random) -> List[Tuple]:
    bases = [s for s in seeds if s is not None]
    if not bases:
        return []
    out = []
    for _ in range(n):
        base = rng.choice(bases)
        out.append(tuple(_mutate(v, rng) for v in base))
    return out


def _run_batch(code: str, func: str, inputs: List[Tuple]) -> Optional[List[List[str]]]:
    """Run func over inputs in an ISOLATED subprocess; return [['ok', repr(result)] | ['err', Type]]."""
    src = (
        code + "\n"
        + "def _canon(x):\n"
        + "    if callable(x): return '<CALLABLE>'\n"
        + "    if isinstance(x, dict): return ('d', sorted((repr(k), repr(_canon(v))) for k, v in x.items()))\n"
        + "    if isinstance(x, (set, frozenset)): return ('s', sorted(repr(_canon(v)) for v in x))\n"
        + "    if isinstance(x, (list, tuple)): return (type(x).__name__, [_canon(v) for v in x])\n"
        + "    return x\n"
        + "_func = " + func + "\n"
        + "_inputs = " + repr(inputs) + "\n"
        + "import json as _json\n"
        + "_out = []\n"
        + "for _a in _inputs:\n"
        + "    try:\n"
        + "        _out.append(['ok', repr(_canon(_func(*_a)))])\n"
        + "    except Exception as _e:\n"
        + "        _out.append(['err', type(_e).__name__])\n"
        + "print(_json.dumps(_out))\n"
    )
    try:
        import os as _os
        _env = {**_os.environ, "PYTHONHASHSEED": "0"}
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, timeout=_TIMEOUT, env=_env)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def _passes_visible(code: str, tests: List[str]) -> bool:
    src = code + "\n" + "\n".join(tests) + "\n"
    try:
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, timeout=_TIMEOUT)
        return r.returncode == 0
    except Exception:
        return False


def _setup(candidate, reference_or_peer, tests, func, n_fuzz, seed):
    func = func or _func_name(reference_or_peer) or _func_name(candidate)
    if not func:
        return None, {"verdict": "abstain", "reason": "no function name found"}
    if not _passes_visible(candidate, tests):
        return None, {"verdict": "reject", "reason": "candidate fails the visible tests"}
    seeds = [_eval_args(a) for a in _extract_call_args(tests, func)]
    rng = random.Random(seed)
    fuzz = _fuzz_inputs(seeds, n_fuzz, rng)
    if len(fuzz) < 5:
        return None, {"verdict": "abstain", "reason": "cannot synthesize enough fuzz inputs from visible tests"}
    return (func, fuzz), None


def differential(candidate: str, reference: str, tests: List[str], func: Optional[str] = None,
                 n_fuzz: int = 40, seed: int = 0) -> Dict[str, Any]:
    """Compare candidate vs a TRUSTED reference on fuzzed inputs. Never trusts on visible tests alone."""
    ctx, early = _setup(candidate, reference, tests, func, n_fuzz, seed)
    if early:
        return early
    func, fuzz = ctx
    cout = _run_batch(candidate, func, fuzz)
    rout = _run_batch(reference, func, fuzz)
    if cout is None or rout is None:
        return {"verdict": "abstain", "reason": "execution failed (could not run candidate or reference)"}
    if any(r[0] == "ok" and "<CALLABLE>" in r[1] for r in rout):
        return {"verdict": "abstain", "reason": "output is function-valued -- needs invoke-and-compare (one dimension up), not repr comparison"}
    diverge = 0
    for c, r in zip(cout, rout):
        if c[0] == "ok" and r[0] == "ok":
            if c[1] != r[1]:
                diverge += 1
        elif c[0] != r[0]:
            diverge += 1
        # err-vs-err: both reject the input -> agree
    n = min(len(cout), len(rout))
    if diverge == 0:
        return {"verdict": "trust", "reason": "agrees with reference on %d fuzzed inputs beyond the visible tests" % n,
                "fuzz_checked": n}
    return {"verdict": "reject", "reason": "passes visible tests but DIVERGES from reference on %d/%d fuzzed inputs" % (diverge, n),
            "divergence": round(diverge / n, 3), "fuzz_checked": n}


def consensus(candidate: str, peers: List[str], tests: List[str], func: Optional[str] = None,
              n_fuzz: int = 40, seed: int = 0, reject_frac: float = 0.1) -> Dict[str, Any]:
    """Compare candidate vs the MAJORITY output of independently-generated peers (no reference needed)."""
    base_peer = peers[0] if peers else candidate
    ctx, early = _setup(candidate, base_peer, tests, func, n_fuzz, seed)
    if early:
        return early
    func, fuzz = ctx
    good = [p for p in peers if _passes_visible(p, tests)]
    if len(good) < 2:
        return {"verdict": "abstain", "reason": "fewer than 2 peers pass the visible tests -- no consensus to check against"}
    cout = _run_batch(candidate, func, fuzz)
    pouts = [p for p in (_run_batch(g, func, fuzz) for g in good) if p is not None]
    if cout is None or len(pouts) < 2:
        return {"verdict": "abstain", "reason": "execution failed for candidate or peers"}
    diverge = compared = 0
    for i in range(len(fuzz)):
        votes = Counter(tuple(p[i]) for p in pouts)
        maj, cnt = votes.most_common(1)[0]
        if cnt < 0.5 * len(pouts):
            continue  # peers themselves disagree -> not a usable oracle for this input
        compared += 1
        if tuple(cout[i]) != maj:
            diverge += 1
    if compared < 3:
        return {"verdict": "abstain", "reason": "peers did not reach consensus on enough fuzzed inputs"}
    if diverge == 0:
        return {"verdict": "trust", "reason": "matches peer consensus on %d fuzzed inputs" % compared, "fuzz_checked": compared}
    if diverge > reject_frac * compared:
        return {"verdict": "reject", "reason": "diverges from peer consensus on %d/%d fuzzed inputs" % (diverge, compared),
                "divergence": round(diverge / compared, 3)}
    return {"verdict": "abstain", "reason": "minor divergence from consensus (%d/%d) -- not confident either way" % (diverge, compared)}
