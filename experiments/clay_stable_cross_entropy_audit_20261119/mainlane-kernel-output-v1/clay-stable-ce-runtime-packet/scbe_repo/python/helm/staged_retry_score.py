"""staged_retry_score: score a staged retry-loop eval and report the per-category LIFT vs a baseline.

The Colab lane proved plain solved/failed is too flat -- the signal is in the PATH. This is the durable,
versioned, tested repo-side scorer for that staged eval (the /content/*.jsonl artifacts are ephemeral). It
classifies each problem's run into the four stages and, given a baseline run, reports the category
transitions -- automating the manual "newly repaired [...] / regression [...]" call.

THE FOUR STAGES (what the harness emits):
  SOLVED_FIRST_TRY                     - first attempt passed the hidden oracle
  SOLVE_FAILED_FIX_ATTEMPT_SOLVED      - first attempt failed, the retry recovered it (the becoming win)
  SOLVE_FAILED_FIX_ATTEMPT_FAILED      - first attempt failed, the retry did NOT recover it
  PUBLIC_PASS_HIDDEN_FAIL_NO_RETRY     - passed the PUBLIC tests, failed the HIDDEN oracle, and never
                                         retried because it thought it had passed = the circular-trust /
                                         overfit residual (same failure mode as los_codegen_bench).

DERIVED METRICS:
  solve_rate            = (first-try + fix-solved) / total
  repair_conversion     = fix-solved / (fix-solved + fix-failed)   -- how often the retry LOOP actually works
  overfit_no_retry_rate = public-pass-hidden-fail / total          -- the residual a stronger local face closes

INPUT SCHEMA (tolerant; documented so you can adapt). Each jsonl record is one problem run. classify() uses,
in order: (1) an explicit category field -- any of category/status/outcome/label/stage/result whose value is
one of the four stage names; else (2) raw signals -- first-try hidden pass, first-try public pass, whether a
retry was attempted, and retry hidden pass (flat aliases like first_try_hidden_pass / first_hidden_pass /
retried / retry_hidden_pass, or nested first_try.hidden_pass / retry.attempted / retry.hidden_pass). A record
that fits neither is UNCLASSIFIED (counted + warned, never force-fit into a stage). Per-problem identity for
deltas uses task_id / id / problem_id / name.

    python -m python.helm.staged_retry_score run.jsonl --baseline base.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SOLVED_FIRST_TRY = "SOLVED_FIRST_TRY"
FIX_SOLVED = "SOLVE_FAILED_FIX_ATTEMPT_SOLVED"
FIX_FAILED = "SOLVE_FAILED_FIX_ATTEMPT_FAILED"
PUBLIC_PASS_HIDDEN_FAIL = "PUBLIC_PASS_HIDDEN_FAIL_NO_RETRY"
UNCLASSIFIED = "UNCLASSIFIED"
CATEGORIES = [SOLVED_FIRST_TRY, FIX_SOLVED, FIX_FAILED, PUBLIC_PASS_HIDDEN_FAIL]
_SOLVED = {SOLVED_FIRST_TRY, FIX_SOLVED}

_CATEGORY_FIELDS = ("category", "status", "outcome", "label", "stage", "result")
_KEY_FIELDS = ("task_id", "id", "problem_id", "name", "task")


def _get(rec: Dict[str, Any], *aliases: str) -> Any:
    """Fetch the first present alias; supports dotted nesting (e.g. 'first_try.hidden_pass')."""
    for a in aliases:
        cur: Any = rec
        ok = True
        for part in a.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok:
            return cur
    return None


def _norm(value: Any) -> str:
    return str(value).strip().upper().replace(" ", "_").replace("-", "_")


def classify(rec: Dict[str, Any], category_field: Optional[str] = None) -> str:
    """Return one of CATEGORIES, or UNCLASSIFIED. Prefers an explicit category field (the caller can name it
    via category_field if it is not one of the defaults); else derives from the raw first-try / retry signals.
    A value that is one of the four stage names is matched even when nested under an unexpected key."""
    fields = (category_field,) + _CATEGORY_FIELDS if category_field else _CATEGORY_FIELDS
    explicit = _get(rec, *fields)
    if explicit is not None:
        norm = _norm(explicit)
        if norm in CATEGORIES:
            return norm
    # broadened raw-signal aliases (covers solved/passed/correct booleans + nested blocks)
    first_hidden = _get(
        rec,
        "first_try_hidden_pass",
        "first_hidden_pass",
        "first_hidden",
        "first_try.hidden_pass",
        "solved_first_try",
        "first_solved",
        "solved",
        "passed",
        "correct",
        "first_try.hidden",
    )
    first_public = _get(
        rec,
        "first_try_public_pass",
        "first_public_pass",
        "first_public",
        "first_try.public_pass",
        "public_pass",
        "first_try.public",
    )
    retried = _get(rec, "retried", "fix_attempted", "retry_attempted", "retry.attempted", "did_retry", "fix.attempted")
    retry_hidden = _get(
        rec,
        "retry_hidden_pass",
        "fix_hidden_pass",
        "retry.hidden_pass",
        "fix_solved",
        "retry_solved",
        "retry.hidden",
        "fix.hidden_pass",
    )
    if first_hidden is None:
        return UNCLASSIFIED
    if first_hidden:
        return SOLVED_FIRST_TRY
    if first_public and not retried:
        return PUBLIC_PASS_HIDDEN_FAIL  # thought it passed (public) -> never entered the retry loop
    if retried:
        return FIX_SOLVED if retry_hidden else FIX_FAILED
    return UNCLASSIFIED  # first-try failed, no public pass, no retry -> not one of the four; do not force-fit


def _counts(records: Sequence[Dict[str, Any]], category_field: Optional[str] = None) -> Dict[str, int]:
    out = {c: 0 for c in CATEGORIES + [UNCLASSIFIED]}
    for r in records:
        out[classify(r, category_field)] += 1
    return out


def score(records: Sequence[Dict[str, Any]], category_field: Optional[str] = None) -> Dict[str, Any]:
    c = _counts(records, category_field)
    total = sum(c.values())
    solved = c[SOLVED_FIRST_TRY] + c[FIX_SOLVED]
    fix_total = c[FIX_SOLVED] + c[FIX_FAILED]
    return {
        "total": total,
        "counts": c,
        "solve_rate": round(solved / total, 3) if total else 0.0,
        "repair_conversion": round(c[FIX_SOLVED] / fix_total, 3) if fix_total else 0.0,
        "overfit_no_retry_rate": round(c[PUBLIC_PASS_HIDDEN_FAIL] / total, 3) if total else 0.0,
        "unclassified": c[UNCLASSIFIED],
    }


def _key(rec: Dict[str, Any], key_field: Optional[str] = None) -> Optional[Any]:
    fields = (key_field,) + _KEY_FIELDS if key_field else _KEY_FIELDS
    return _get(rec, *fields)


def diagnose(records: Sequence[Dict[str, Any]], category_field: Optional[str] = None, n: int = 3) -> List[Dict]:
    """Self-diagnosis: for the first n records that DON'T classify, report their real structure so the user
    can see which field to map (top-level keys + one level of nested-dict keys). This is what makes the tool
    'just work' on an unknown schema -- run it and it tells you exactly what it could not read."""
    out = []
    for r in records:
        if classify(r, category_field) != UNCLASSIFIED:
            continue
        nested = {k: sorted(v.keys()) for k, v in r.items() if isinstance(v, dict)}
        out.append({"top_level_keys": sorted(r.keys()), "nested_keys": nested})
        if len(out) >= n:
            break
    return out


def delta(
    baseline: Sequence[Dict[str, Any]],
    candidate: Sequence[Dict[str, Any]],
    category_field: Optional[str] = None,
    key_field: Optional[str] = None,
) -> Dict[str, Any]:
    """Per-problem transitions baseline -> candidate (the fair-baseline comparison). Reproduces the manual
    'newly repaired / regression' call and adds the full transition list + per-category count deltas."""
    b = {_key(r, key_field): r for r in baseline if _key(r, key_field) is not None}
    c = {_key(r, key_field): r for r in candidate if _key(r, key_field) is not None}
    common = sorted(set(b) & set(c), key=str)
    transitions: List[Tuple[Any, str, str]] = []
    newly_solved, regressed, newly_repaired = [], [], []
    for k in common:
        bc, cc = classify(b[k], category_field), classify(c[k], category_field)
        if bc != cc:
            transitions.append((k, bc, cc))
        if cc in _SOLVED and bc not in _SOLVED:
            newly_solved.append(k)
        if bc in _SOLVED and cc not in _SOLVED:
            regressed.append(k)
        if bc == FIX_FAILED and cc == FIX_SOLVED:
            newly_repaired.append(k)
    bcnt, ccnt = _counts(baseline, category_field), _counts(candidate, category_field)
    return {
        "compared": len(common),
        "only_in_baseline": sorted(set(b) - set(c), key=str),
        "only_in_candidate": sorted(set(c) - set(b), key=str),
        "count_delta": {cat: ccnt[cat] - bcnt[cat] for cat in CATEGORIES + [UNCLASSIFIED]},
        "net_solved_delta": len(newly_solved) - len(regressed),
        "newly_solved": newly_solved,
        "regressed": regressed,
        "newly_repaired": newly_repaired,
        "transitions": transitions,
    }


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def render(s: Dict[str, Any], d: Optional[Dict[str, Any]] = None) -> str:
    lines = ["STAGED RETRY-LOOP SCORE  (total %d)" % s["total"], ""]
    for cat in CATEGORIES:
        lines.append("  %-34s %4d" % (cat, s["counts"][cat]))
    if s["unclassified"]:
        lines.append("  %-34s %4d  <- did not match the schema (check field names)" % (UNCLASSIFIED, s["unclassified"]))
    lines += [
        "",
        "  solve_rate            %.3f   (first-try + fix-solved)" % s["solve_rate"],
        "  repair_conversion     %.3f   (fix-solved / fix-attempts) <- does the retry LOOP actually work"
        % s["repair_conversion"],
        "  overfit_no_retry_rate %.3f   (public-pass hidden-fail) <- the circular-trust residual"
        % s["overfit_no_retry_rate"],
    ]
    if d is not None:
        lines += [
            "",
            "DELTA vs baseline (%d problems compared):" % d["compared"],
            "  net solved delta : %+d" % d["net_solved_delta"],
            "  newly repaired   : %s" % (d["newly_repaired"] or "[]"),
            "  newly solved     : %s" % (d["newly_solved"] or "[]"),
            "  regressed        : %s" % (d["regressed"] or "[]"),
            "  count delta      : %s" % {k: v for k, v in d["count_delta"].items() if v},
        ]
        if d["only_in_baseline"] or d["only_in_candidate"]:
            lines.append(
                "  WARNING unmatched ids: baseline-only=%d candidate-only=%d (deltas use the intersection)"
                % (len(d["only_in_baseline"]), len(d["only_in_candidate"]))
            )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="score a staged retry-loop eval jsonl (+ optional baseline delta)")
    ap.add_argument("run", help="candidate run jsonl (one staged record per problem)")
    ap.add_argument("--baseline", default=None, help="baseline run jsonl for the fair per-category delta")
    ap.add_argument("--category-field", default=None, help="name of your explicit stage/category field, if non-default")
    ap.add_argument("--key-field", default=None, help="name of your per-problem id field, if non-default")
    a = ap.parse_args(argv)
    cand = load_jsonl(a.run)
    s = score(cand, a.category_field)
    d = delta(load_jsonl(a.baseline), cand, a.category_field, a.key_field) if a.baseline else None
    print(render(s, d))
    if s["unclassified"]:  # self-diagnose so an unknown schema is actionable, not a silent zero
        print(
            "\nDIAGNOSTIC -- %d record(s) did not classify. Sample structure(s) below; map a field with"
            " --category-field, or rename to a documented alias:" % s["unclassified"]
        )
        for sample in diagnose(cand, a.category_field):
            print("  top-level keys: %s" % sample["top_level_keys"])
            for blk, keys in sample["nested_keys"].items():
                print("    %s.{%s}" % (blk, ", ".join(keys)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
