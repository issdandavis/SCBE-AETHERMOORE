"""self_repair_corpus: synthesize execution-VERIFIED self-repair trajectories to rebalance a corpus.

retry_corpus_validate showed the v3 retry-teacher corpus is ~100% teacher-bailout -> it trains teacher-
DEPENDENCE, not self-repair. This builds the missing half: SELF_REPAIR_SUCCESS trajectories (bad attempt ->
REAL test failure -> critique + fix -> PASS), synthesized from already-verified solutions by deterministically
MUTATING the good code into a failing variant and KEEPING only mutations that genuinely fail the example
while the good code genuinely passes -- both checked by RUNNING them. No model, no network: $0 and honest --
every emitted trajectory's failure and its recovery are real executions, not asserted ([[train-on-becoming]]).

SECURITY: this exec()s code from a LOCAL, already-verified corpus (trusted input), never network input --
unlike an MCP surface. Do not point it at untrusted code.

    python -m python.helm.self_repair_corpus --corpus teacher_heavy.jsonl --pool vtc_fixture.jsonl \\
        --out balanced.jsonl --target 0.4
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import retry_corpus_validate as rcv

SYSTEM = "You are an SCBE coding agent. Write a complete, correct solution. Correctness is verified by execution."


def extract_example(user_text: str) -> Optional[str]:
    """Pull the single `assert ...` example line out of a VTC user prompt."""
    for line in user_text.splitlines():
        if line.strip().startswith("assert "):
            return line.strip()
    return None


def runs_ok(code: str, assert_line: str) -> Tuple[bool, str]:
    """Run `code` then the assert in a fresh namespace. Returns (passed, error_text). A crash or failed
    assert => (False, message). This is the execution oracle that keeps the synthesis honest."""
    ns: Dict[str, Any] = {}
    try:
        exec(compile(code, "<cand>", "exec"), ns)  # noqa: S102 -- trusted local corpus, see module docstring
        exec(compile(assert_line, "<assert>", "exec"), ns)  # noqa: S102
        return True, ""
    except Exception as exc:  # noqa: BLE001 -- any failure is a (legitimate) test failure
        return False, "%s: %s" % (type(exc).__name__, exc)


# deterministic mutators: good code -> a plausible WRONG variant (one targeted edit). Each returns the
# mutated source or None if its pattern is absent. make_failing_variant keeps the first that actually fails.
def _swap_first(code: str, a: str, b: str) -> Optional[str]:
    if a not in code:
        return None
    return code.replace(a, b, 1)


_MUTATORS: List[Tuple[str, Any]] = [
    ("flip ==/!=", lambda c: _swap_first(c, "==", "!=")),
    ("flip <=/>", lambda c: _swap_first(c, "<=", ">")),
    ("flip >=/<", lambda c: _swap_first(c, ">=", "<")),
    ("flip </>", lambda c: _swap_first(re.sub(r"(?<![<>=!])<(?!=)", "\x00", c, count=1), "\x00", ">")),
    ("flip +/-", lambda c: _swap_first(c, " + ", " - ")),
    ("flip -/+", lambda c: _swap_first(c, " - ", " + ")),
    ("off-by-one + 1 -> + 2", lambda c: _swap_first(c, "+ 1", "+ 2")),
    ("return -> return None", lambda c: re.sub(r"return .+", "return None", c, count=1)),
    ("flip and/or", lambda c: _swap_first(c, " and ", " or ")),
    ("flip True/False", lambda c: _swap_first(c, "True", "False")),
]


def make_failing_variant(good_code: str, assert_line: str) -> Optional[Tuple[str, str, str]]:
    """Return (bad_code, mutator_name, fail_msg) for the first mutation that COMPILES, genuinely FAILS the
    example, and differs from the good code. None if no mutator yields a clean failing variant."""
    for name, mut in _MUTATORS:
        bad = mut(good_code)
        if not bad or bad == good_code:
            continue
        try:
            ast.parse(bad)  # a realistic near-miss is valid code that fails, not a syntax error
        except SyntaxError:
            continue
        passed, msg = runs_ok(bad, assert_line)
        if not passed:
            return bad, name, msg or "AssertionError"
    return None


def make_self_repair_record(problem: str, good: str, bad: str, mutator: str, fail_msg: str, task_id: Any) -> Dict:
    """One SELF_REPAIR_SUCCESS trajectory: bad attempt -> real failure -> critique+fix -> PASS (no teacher)."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": problem},
            {"role": "assistant", "content": bad},
            {"role": "user", "content": "Test run FAILED: %s" % fail_msg},
            {"role": "assistant", "content": "The bug was '%s'. Corrected solution:\n%s" % (mutator, good)},
            {"role": "user", "content": "All tests passed."},
        ],
        "meta": {"grade": "manager", "final_source": "self", "repaired": True,
                 "source": "self_repair_synth", "task_id": task_id},
    }


def verified_pool_from_vtc(records: Sequence[Dict]) -> List[Tuple[str, str, str, Any]]:
    """Extract (problem, good_code, assert_line, task_id) from VTC station records that carry an example."""
    pool = []
    for r in records:
        msgs = r.get("messages") or []
        user = next((m for m in msgs if m.get("role") == "user"), None)
        good = next((m for m in reversed(msgs) if m.get("role") == "assistant"), None)
        if not user or not good:
            continue
        assert_line = extract_example(str(user.get("content", "")))
        if assert_line:
            pool.append((str(user["content"]), str(good["content"]), assert_line, (r.get("meta") or {}).get("task_id")))
    return pool


def synthesize(pool: Sequence[Tuple[str, str, str, Any]], limit: Optional[int] = None) -> List[Dict]:
    """Build execution-verified self-repair records from a verified pool (good code must pass; a mutation must
    genuinely fail). Skips entries where the good code does not pass or no mutator produces a clean failure."""
    out: List[Dict] = []
    for problem, good, assert_line, task_id in pool:
        ok, _ = runs_ok(good, assert_line)
        if not ok:
            continue  # cannot vouch for a "fix" that does not actually pass
        variant = make_failing_variant(good, assert_line)
        if not variant:
            continue
        bad, mutator, fail_msg = variant
        out.append(make_self_repair_record(problem, good, bad, mutator, fail_msg, task_id))
        if limit and len(out) >= limit:
            break
    return out


def augment(corpus: Sequence[Dict], pool: Sequence[Tuple[str, str, str, Any]], target_self_ratio: float = 0.4) -> Tuple[List[Dict], Dict]:
    """Append synthesized self-repair records until the corpus's self_repair_success_ratio reaches the target
    (or the pool is exhausted). Returns (new_corpus, report{before, after, added})."""
    before = rcv.validate(corpus)
    added: List[Dict] = []
    candidates = synthesize(pool)
    new = list(corpus)
    for rec in candidates:
        if rcv.validate(new)["self_repair_success_ratio"] >= target_self_ratio:
            break
        new.append(rec)
        added.append(rec)
    after = rcv.validate(new)
    return new, {
        "before_self_ratio": before["self_repair_success_ratio"],
        "after_self_ratio": after["self_repair_success_ratio"],
        "added": len(added),
        "pool_available": len(candidates),
        "target": target_self_ratio,
        "reached_target": after["self_repair_success_ratio"] >= target_self_ratio,
    }


def load_jsonl(path: str) -> List[Dict]:
    return [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def write_jsonl(path: str, records: Sequence[Dict]) -> None:
    Path(path).write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="rebalance a teacher-heavy retry corpus with verified self-repair traces")
    ap.add_argument("--corpus", required=True, help="the teacher-bailout-heavy retry corpus jsonl to rebalance")
    ap.add_argument("--pool", required=True, help="a verified-solution corpus (e.g. vtc_fixture.jsonl) to synth from")
    ap.add_argument("--out", default=None, help="write the rebalanced corpus here")
    ap.add_argument("--target", type=float, default=0.4, help="target self_repair_success_ratio")
    a = ap.parse_args(argv)
    pool = verified_pool_from_vtc(load_jsonl(a.pool))
    new, report = augment(load_jsonl(a.corpus), pool, a.target)
    print("self-repair augmentation: %.3f -> %.3f (added %d of %d available; target %.2f %s)" % (
        report["before_self_ratio"], report["after_self_ratio"], report["added"], report["pool_available"],
        report["target"], "REACHED" if report["reached_target"] else "POOL EXHAUSTED"))
    if a.out:
        write_jsonl(a.out, new)
        print("wrote %d records -> %s" % (len(new), a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
