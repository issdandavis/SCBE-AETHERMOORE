"""better_corpus: BETTER data, not more -- execution-verified pitfall->diagnosis->fix traces.

The lift experiment showed that training on more MBPP trajectories does not raise capability. The
hypothesis this tests is that *better-structured* data does: a small set of high-quality traces that
teach the COMMON PITFALLS and how to avoid them -- the "blow-and-go + radar detector" idea (verify by
running, and anticipate the specific way each approach fails).

Each pitfall is a verified manager-style trajectory: the problem, a plausible WRONG attempt (the
pitfall), the real got-vs-expected diagnosis from RUNNING it, and the fix. Both halves are
execution-verified -- the buggy code actually FAILS the hidden test and the fix actually PASSES -- so
this is teaching data the verifier vouches for, not asserted lore. The traces use the same
{messages, meta} schema as verified_trajectory, so they UNION straight into the VTC corpus.

    from python.helm.better_corpus import build, PITFALLS
    res = build("/path/to/vtc_mbpp_refined.jsonl", "/path/to/better.jsonl")  # union MBPP + pitfalls
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import public_bench as pb
from .free_generator import _diagnose

SYSTEM = (
    "You are an SCBE coding agent. Write a complete, correct solution that passes the tests. Output only "
    "the code. Correctness is verified by execution against held-out tests."
)

# Each pitfall: a real, common Python mistake. `buggy` must FAIL `tests`; `fix` must PASS them. Verified.
PITFALLS: List[Dict[str, Any]] = [
    {
        "name": "mutable_default_arg",
        "prompt": "Write append_to(item, lst) that appends item to lst and returns it; lst defaults to [].",
        "buggy": "def append_to(item, lst=[]):\n    lst.append(item)\n    return lst",
        "fix": "def append_to(item, lst=None):\n    if lst is None:\n        lst = []\n"
        "    lst.append(item)\n    return lst",
        "tests": ["assert append_to(1) == [1]", "assert append_to(2) == [2]"],
    },
    {
        "name": "off_by_one_range",
        "prompt": "Write upto(n) returning the list of integers from 1 to n INCLUSIVE.",
        "buggy": "def upto(n):\n    return list(range(1, n))",
        "fix": "def upto(n):\n    return list(range(1, n + 1))",
        "tests": ["assert upto(3) == [1, 2, 3]", "assert upto(1) == [1]"],
    },
    {
        "name": "integer_vs_float_division",
        "prompt": "Write avg(a, b) returning the arithmetic mean of a and b (may be fractional).",
        "buggy": "def avg(a, b):\n    return (a + b) // 2",
        "fix": "def avg(a, b):\n    return (a + b) / 2",
        "tests": ["assert avg(1, 2) == 1.5", "assert avg(2, 2) == 2.0"],
    },
    {
        "name": "modify_list_while_iterating",
        "prompt": "Write drop_evens(xs) returning xs with every even number removed.",
        "buggy": "def drop_evens(xs):\n    for x in xs:\n        if x % 2 == 0:\n"
        "            xs.remove(x)\n    return xs",
        "fix": "def drop_evens(xs):\n    return [x for x in xs if x % 2 != 0]",
        "tests": ["assert drop_evens([1, 2, 3, 4]) == [1, 3]", "assert drop_evens([2, 4, 6]) == []"],
    },
    {
        "name": "dict_keyerror_vs_get",
        "prompt": "Write lookup(d, k) returning d[k], or 0 if k is not present.",
        "buggy": "def lookup(d, k):\n    return d[k]",
        "fix": "def lookup(d, k):\n    return d.get(k, 0)",
        "tests": ["assert lookup({'a': 1}, 'a') == 1", "assert lookup({'a': 1}, 'b') == 0"],
    },
    {
        "name": "empty_string_index",
        "prompt": "Write first_char(s) returning the first character of s, or '' if s is empty.",
        "buggy": "def first_char(s):\n    return s[0]",
        "fix": "def first_char(s):\n    return s[0] if s else ''",
        "tests": ["assert first_char('hi') == 'h'", "assert first_char('') == ''"],
    },
    {
        "name": "float_equality",
        "prompt": "Write sums_to(a, b, target) returning True iff a + b equals target (handle float rounding).",
        "buggy": "def sums_to(a, b, target):\n    return a + b == target",
        "fix": "def sums_to(a, b, target):\n    return abs((a + b) - target) < 1e-9",
        "tests": ["assert sums_to(0.1, 0.2, 0.3) == True", "assert sums_to(1, 1, 3) == False"],
    },
    {
        "name": "late_binding_closure",
        "prompt": "Write make_adders() returning a list of 3 functions where the i-th returns i (for i in 0,1,2).",
        "buggy": "def make_adders():\n    return [lambda: i for i in range(3)]",
        "fix": "def make_adders():\n    return [lambda i=i: i for i in range(3)]",
        "tests": ["assert [f() for f in make_adders()] == [0, 1, 2]"],
    },
    {
        "name": "list_multiplication_shared_rows",
        "prompt": "Write make_grid(rows, cols) returning a rows x cols grid of 0s where setting grid[0][0]=1 "
        "changes ONLY grid[0][0].",
        "buggy": "def make_grid(rows, cols):\n    return [[0] * cols] * rows",
        "fix": "def make_grid(rows, cols):\n    return [[0] * cols for _ in range(rows)]",
        "tests": ["g = make_grid(2, 2)\ng[0][0] = 1\nassert g == [[1, 0], [0, 0]]"],
    },
    {
        "name": "sort_returns_none",
        "prompt": "Write sorted_copy(xs) returning a NEW sorted list of xs WITHOUT modifying xs.",
        "buggy": "def sorted_copy(xs):\n    return xs.sort()",
        "fix": "def sorted_copy(xs):\n    return sorted(xs)",
        "tests": ["assert sorted_copy([3, 1, 2]) == [1, 2, 3]", "a = [3, 1, 2]\nsorted_copy(a)\nassert a == [3, 1, 2]"],
    },
    {
        "name": "dedup_loses_order",
        "prompt": "Write dedup(xs) returning xs with duplicates removed, PRESERVING first-seen order.",
        "buggy": "def dedup(xs):\n    return list(set(xs))",
        "fix": "def dedup(xs):\n    return list(dict.fromkeys(xs))",
        "tests": ["assert dedup([3, 1, 3, 2, 1]) == [3, 1, 2]"],
    },
    {
        "name": "string_immutable_inplace",
        "prompt": "Write set_first(s, c) returning s with its first character replaced by c (s is non-empty).",
        "buggy": "def set_first(s, c):\n    s[0] = c\n    return s",
        "fix": "def set_first(s, c):\n    return c + s[1:]",
        "tests": ["assert set_first('cat', 'b') == 'bat'"],
    },
    {
        "name": "shallow_copy_nested",
        "prompt": "Write copy_grid(g) returning an INDEPENDENT copy of the 2D list g (mutating the copy must "
        "not change g).",
        "buggy": "def copy_grid(g):\n    return g[:]",
        "fix": "def copy_grid(g):\n    return [row[:] for row in g]",
        "tests": ["g = [[1, 2], [3, 4]]\nc = copy_grid(g)\nc[0][0] = 9\nassert g == [[1, 2], [3, 4]]"],
    },
    {
        "name": "chained_comparison_misuse",
        "prompt": "Write in_range(x) returning True iff 1 <= x <= 10.",
        "buggy": "def in_range(x):\n    return 1 <= x <= 10 == True",
        "fix": "def in_range(x):\n    return 1 <= x <= 10",
        "tests": ["assert in_range(5) == True", "assert in_range(11) == False"],
    },
    {
        "name": "recursion_missing_base_case",
        "prompt": "Write factorial(n) returning n! for n >= 0 (factorial(0) == 1).",
        "buggy": "def factorial(n):\n    return n * factorial(n - 1)",
        "fix": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
        "tests": ["assert factorial(0) == 1", "assert factorial(5) == 120"],
    },
]


def _passes(code: str, tests: List[str]) -> bool:
    return pb._verify(code, [], tests, [])["hidden_passed"]


def verify_pitfall(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Both halves must hold for the trace to be honest: buggy FAILS, fix PASSES."""
    return {"buggy_fails": not _passes(spec["buggy"], spec["tests"]), "fix_passes": _passes(spec["fix"], spec["tests"])}


def pitfall_trace(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a verified manager-style trajectory: problem -> buggy attempt -> real got-vs-expected
    diagnosis -> fix. Returns None if the pair is not actually a real bug-and-fix (so nothing unverified
    enters the corpus)."""
    v = verify_pitfall(spec)
    if not (v["buggy_fails"] and v["fix_passes"]):
        return None
    visible = spec["tests"][0]
    diag = "\n".join(str(d) for d in _diagnose(spec["buggy"], spec["tests"], []))[:700]
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": spec["prompt"] + "\n\nIt must pass:\n" + visible + "\nReturn ONLY the code.",
            },
            {"role": "assistant", "content": spec["buggy"]},
            {
                "role": "user",
                "content": "Your code failed these checks (got vs expected):\n"
                + diag
                + "\nFix it. Return ONLY corrected Python code.",
            },
            {"role": "assistant", "content": spec["fix"]},
        ],
        "meta": {
            "verified": True,
            "task_id": "pitfall_" + spec["name"],
            "attempts": 2,
            "repaired": True,
            "source": "better_corpus_pitfall",
            "grade": "manager",
        },
    }


def pitfall_traces() -> List[Dict[str, Any]]:
    return [t for t in (pitfall_trace(s) for s in PITFALLS) if t is not None]


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def build(mbpp_corpus: Optional[str], out_path: str) -> Dict[str, Any]:
    """Union the existing MBPP corpus (if given) with the verified pitfall traces; write {messages,meta}
    JSONL. 'Better data, not more' -- a few execution-verified pitfall traces grafted onto the base."""
    base = _load_jsonl(mbpp_corpus) if mbpp_corpus else []
    pits = pitfall_traces()
    records = base + pits
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps({"messages": r["messages"], "meta": r.get("meta", {})}, ensure_ascii=False) + "\n")
    return {"path": str(p), "total": len(records), "from_mbpp": len(base), "pitfalls": len(pits)}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="scbe-better-corpus", description="verified pitfall traces + union with MBPP corpus"
    )
    ap.add_argument("--mbpp", default=None, help="existing vtc_mbpp_refined.jsonl to union with (optional)")
    ap.add_argument("--out", default="better_corpus.jsonl")
    a = ap.parse_args(list(argv) if argv is not None else None)
    pits = pitfall_traces()
    print("BETTER CORPUS  %d/%d pitfall traces verified (buggy fails + fix passes)" % (len(pits), len(PITFALLS)))
    for s in PITFALLS:
        v = verify_pitfall(s)
        print("  %-28s buggy_fails=%-5s fix_passes=%s" % (s["name"], v["buggy_fails"], v["fix_passes"]))
    res = build(a.mbpp, a.out)
    print(
        "\n  wrote %d records (%d MBPP + %d pitfalls) -> %s"
        % (res["total"], res["from_mbpp"], res["pitfalls"], res["path"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
