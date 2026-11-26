"""verify_cli -- a $0 CLI/CI gate over the abstaining verifier.

Ships the proven trust/reject/ABSTAIN verdict as a tool. Primary use today (no LLM needed):
REFACTOR / EQUIVALENCE verification -- does a rewritten function behave identically to the
original on inputs beyond the visible tests? It fuzzes past the shown tests, runs both in an
isolated subprocess, and emits a forwardable report.json. It never certifies in the dangerous
direction: trust (agrees everywhere) / reject (diverges) / abstain (can't verify -- fail-safe).

Usage:
    python -m python.helm.verify_cli --old old.py --new new.py --tests tests.txt [--func name] [--out report.json]

  --old / --new : files each defining the target function (the reference = --old, candidate = --new)
  --tests       : a file of `assert ...` lines (the visible tests; also the fuzz seed source)
  --func        : function name (default: first def found in --old)
  --out         : where to write report.json (default: report.json)

Exit codes (so CI can gate): 0 = trust, 1 = reject, 2 = abstain, 3 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys

from .abstaining_verifier import differential, _func_name


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify_cli", description="Abstaining verifier as a CI gate.")
    ap.add_argument("--old", "--ref", dest="old", required=True, help="reference (known-good) implementation file")
    ap.add_argument("--new", "--candidate", dest="new", required=True, help="candidate implementation file")
    ap.add_argument("--tests", required=True, help="file of `assert ...` lines (visible tests + fuzz seeds)")
    ap.add_argument("--func", default=None, help="function name (default: first def in --old)")
    ap.add_argument("--fuzz", type=int, default=40, help="fuzz inputs beyond the visible tests")
    ap.add_argument("--out", default="report.json", help="where to write the verdict")
    args = ap.parse_args(argv)

    try:
        ref = open(args.old, encoding="utf-8").read()
        cand = open(args.new, encoding="utf-8").read()
        tests = [ln for ln in open(args.tests, encoding="utf-8").read().splitlines() if ln.strip()]
    except OSError as e:
        print("usage error: " + str(e), file=sys.stderr)
        return 3

    func = args.func or _func_name(ref) or _func_name(cand)
    if not func:
        print("usage error: no function name found (pass --func)", file=sys.stderr)
        return 3

    verdict = differential(cand, ref, tests, func=func, n_fuzz=args.fuzz)
    report = {
        "func": func,
        "verdict": verdict["verdict"],
        "reason": verdict.get("reason", ""),
        "fuzz_checked": verdict.get("fuzz_checked"),
        "divergence": verdict.get("divergence"),
        "honest_note": "trust/reject by execution beyond visible tests; abstain = cannot verify (fail-safe, not a correctness proof)",
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    return {"trust": 0, "reject": 1, "abstain": 2}.get(verdict["verdict"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
