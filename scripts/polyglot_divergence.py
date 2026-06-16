#!/usr/bin/env python3
"""The mirror hallway, made inspectable.

One CA-opcode blueprint -> every language face -> run them all -> show where they
agree and where they diverge. Because the blueprint is held constant, any
difference is the LANGUAGE, not the intent.

Reuses the proven per-language runners from tests/test_polyglot_execution.py, so
"how to run a face" has a single source of truth. Faces whose toolchain isn't
installed locally are marked ABSENT (they're verified on the polyglot-faces CI job).

Honest scope: the emitter's runnable `main` calls the function with fixed inputs
(2, 3, 4). Some documented seams (e.g. round-on-exact-.5, modulo sign) only appear
with inputs the current emitter can't supply, so they show as ABSENT-here / CI, not
DIVERGE. What this proves at fixed inputs: cross-build/ship conformance — does the
identical blueprint build and run to the same number in every available language.

Usage:
    python scripts/polyglot_divergence.py            # table
    python scripts/polyglot_divergence.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python.scbe.polyglot as P  # noqa: E402
from tests.test_polyglot_execution import RUNNERS, _AVAILABLE  # noqa: E402

PROGRAMS = [(op, [op]) for op in sorted(P.SCALAR_OPS)] + [
    ("chain_mix", ["add", "mul", "sqrt", "inc"]),
    ("roundabout_div0", ["eq", "div"]),
    ("roundabout_sqrtneg", ["sub", "sqrt"]),
    ("neg_then_mod", ["sub", "mod"]),  # reaches a negative operand: probes mod-sign
]


def ref_value(prog: list[str]) -> float:
    src = P.emit(P.program_bytes(*prog), "python", runnable=False, safe=True)
    ns: dict = {}
    exec(compile(src, "ref.py", "exec"), ns)  # noqa: S102 - local oracle
    return float(ns["tongue_fn"](2.0, 3.0, 4.0))


def run_lang(lang: str, prog: list[str]) -> float:
    src = P.emit(P.program_bytes(*prog), lang, runnable=True, safe=True)
    with tempfile.TemporaryDirectory() as td:
        return RUNNERS[lang](src, td)


def reason_for(ops: list[str]) -> str:
    s = set(ops)
    if "round" in s:
        return "native rounding (banker's vs half-up)"
    if "mod" in s:
        return "modulo sign on negative operands"
    if "div" in s:
        return "float division / divide-by-zero handling"
    if "pow" in s:
        return "pow precision / domain"
    return "language-intrinsic numeric behavior"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--tol", type=float, default=1e-9)
    args = ap.parse_args()

    langs = list(_AVAILABLE)
    all_langs = sorted(RUNNERS)
    absent = [x for x in all_langs if x not in langs]

    rows = []
    n_agree = n_div = n_fail = 0
    divergences = []
    for name, prog in PROGRAMS:
        ref = ref_value(prog)
        cells = {}
        for lang in langs:
            try:
                v = run_lang(lang, prog)
                if (abs(v - ref) <= args.tol) or (math.isnan(v) and math.isnan(ref)):
                    cells[lang] = {"status": "agree", "value": v}
                    n_agree += 1
                else:
                    cells[lang] = {"status": "DIVERGE", "value": v}
                    n_div += 1
                    divergences.append({"program": name, "lang": lang, "value": v, "ref": ref, "reason": reason_for(prog)})
            except Exception as exc:  # build/run failure = a real ship problem
                cells[lang] = {"status": "BUILDFAIL", "detail": str(exc).splitlines()[0][:70]}
                n_fail += 1
        rows.append({"program": name, "ops": prog, "ref": ref, "cells": cells})

    summary = {
        "available_languages": langs,
        "absent_languages": absent,
        "programs": len(PROGRAMS),
        "agree": n_agree,
        "diverge": n_div,
        "buildfail": n_fail,
    }

    if args.as_json:
        print(json.dumps({"summary": summary, "rows": rows, "divergences": divergences}, indent=2))
        return 0

    print("MIRROR HALLWAY — polyglot divergence view (inputs fixed at 2,3,4)")
    print(f"available faces: {', '.join(langs) or '(none)'}")
    print(f"absent here (CI proves these): {', '.join(absent) or '(none)'}\n")
    header = f"{'program':<20} {'ref':>12}  per-language"
    print(header)
    print("-" * len(header))
    for r in rows:
        marks = []
        for lang in langs:
            c = r["cells"][lang]
            tag = {"agree": "ok", "DIVERGE": "DIVERGE", "BUILDFAIL": "BUILD-FAIL"}[c["status"]]
            marks.append(f"{lang}:{tag}")
        print(f"{r['program']:<20} {r['ref']:>12.6g}  {'  '.join(marks)}")
    print()
    print(f"SUMMARY  programs={summary['programs']}  faces={len(langs)}  "
          f"agree={n_agree}  diverge={n_div}  build-fail={n_fail}")
    if divergences:
        print("\nDIVERGENCES (language-intrinsic, intent held constant):")
        for d in divergences:
            print(f"  {d['program']:<18} {d['lang']:<10} got {d['value']!r} vs ref {d['ref']!r}  — {d['reason']}")
    else:
        print("\nNo divergence at fixed inputs — every available face builds, runs, and agrees.")
        print("Documented seams (round-on-.5, mod-sign) need inputs the emitter's fixed main")
        print("can't supply yet; that's a known limit, not a pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
