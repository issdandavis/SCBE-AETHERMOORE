#!/usr/bin/env python3
"""INDEPENDENT audit of a tool-use corpus -- verify the verifier.

The harvester labels a record verified=True using python.helm.public_bench._verify. This auditor does
NOT import that code: it re-extracts each record's FINAL answer code with its own parser and re-runs it
against the HELD-BACK MBPP tests in a fresh subprocess with a separate runner. If the harness's
"verified" claim disagrees with this independent re-execution, that is a verifier bug and the audit
fails. It also checks the structural promises of the corpus:

  * no few-shot demo leaked into a saved record (the triple(n) example must never appear)
  * every kept record actually contains a TOOL result turn (the call->use->answer loop is present)
  * no duplicate task_ids (each problem contributes at most one trajectory)

    python scripts/training/audit_tool_corpus.py training/sft_records/tool_trajectory_mbpp.jsonl

Exit code is nonzero if ANY mismatch, demo leak, or duplicate is found. $0; deterministic; no model.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from python.helm.public_bench import pull_mbpp  # noqa: E402  (data source only, not the verifier)

_CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def _final_code(messages):
    """Extract the answer code from the LAST assistant turn -- independent of the harvester's parser."""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            blocks = _CODE_RE.findall(m.get("content", ""))
            if blocks:
                return blocks[-1].strip()
    return ""


def _independent_holdback_pass(code, held, imports):
    """Run code + ALL held-back asserts together in a subprocess; pass iff the process exits 0.

    Deliberately a DIFFERENT shape from _verify (which execs asserts one-by-one and collects failures):
    here a single failing assert aborts the process, so agreement is meaningful cross-checking."""
    if not code.strip() or not held:
        return False
    src = "\n".join(list(imports) + [code, ""] + list(held))
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(src)
        path = f.name
    try:
        return subprocess.run([sys.executable, path], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False
    finally:
        try:
            Path(path).unlink()
        except OSError:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="independently audit a tool-use corpus")
    ap.add_argument("corpus", help="path to the tool_trajectory jsonl corpus")
    ap.add_argument("--public-k", type=int, default=1, help="tests shown during harvest; the rest were held back")
    args = ap.parse_args(argv)

    corpus = Path(args.corpus)
    if not corpus.exists():
        print("corpus not found: %s" % corpus, file=sys.stderr)
        return 2
    records = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {p["task_id"]: p for p in pull_mbpp()}

    total = len(records)
    indep_pass = mismatch = no_tool_turn = demo_leak = missing_problem = 0
    repair = confirm = multi_call = 0
    task_ids = []
    tool_counter = Counter()
    mismatches = []

    for rec in records:
        meta = rec.get("meta", {})
        tid = meta.get("task_id")
        task_ids.append(tid)
        msgs = rec.get("messages", [])

        # structural checks
        if "triple(n)" in json.dumps(rec):
            demo_leak += 1
        tool_turns = [
            str(m.get("content", ""))
            for m in msgs
            if m.get("role") == "user" and str(m.get("content", "")).startswith("TOOL ")
        ]
        if not tool_turns:
            no_tool_turn += 1
        for t in meta.get("tools_used", []):
            tool_counter[t] += 1

        # trajectory SHAPE -- not whether the answer is right (the re-verify covers that), but whether the
        # trajectory teaches the deep loop. repair = a tool returned FAIL and the model still reached a
        # verified answer (the 'becoming' loop); confirm = tool only rubber-stamped already-correct code.
        if any("FAIL" in t for t in tool_turns):
            repair += 1
        elif tool_turns:
            confirm += 1
        if len(tool_turns) > 1:
            multi_call += 1

        # INDEPENDENT held-back re-verification
        problem = by_id.get(tid)
        if problem is None:
            missing_problem += 1
            continue
        held = list(problem.get("test_list", []))[args.public_k :]
        imports = list(problem.get("test_imports", []))
        ok = _independent_holdback_pass(_final_code(msgs), held, imports)
        if ok:
            indep_pass += 1
        if meta.get("verified") is True and not ok:
            mismatch += 1
            mismatches.append(tid)

    dupes = [tid for tid, n in Counter(task_ids).items() if n > 1]

    print("=" * 64)
    print("TOOL-USE CORPUS AUDIT (independent re-verification)")
    print("  corpus                : %s" % corpus)
    print("  records               : %d" % total)
    print("  independently verified: %d / %d  (held-back tests re-run, separate checker)" % (indep_pass, total))
    print("  harness/indep MISMATCH: %d  %s" % (mismatch, mismatches[:20] if mismatches else ""))
    print("  records w/ TOOL turn  : %d / %d" % (total - no_tool_turn, total))
    print("  demo leaks            : %d" % demo_leak)
    print("  duplicate task_ids    : %d  %s" % (len(dupes), dupes[:20] if dupes else ""))
    print("  problems unresolved   : %d" % missing_problem)
    print("  tool-call distribution: %s" % dict(tool_counter))
    print("  -- trajectory shape (teaching depth, not correctness) --")
    print("  repair (FAIL->fix->pass): %d  [the 'becoming' loop]" % repair)
    print("  confirm (tool PASS only): %d  [tool rubber-stamped correct code]" % confirm)
    print("  multi-call (>1 tool)    : %d  [iterative tool use]" % multi_call)
    ok = mismatch == 0 and demo_leak == 0 and not dupes
    print("  VERDICT               : %s" % ("PASS -- numbers are real" if ok else "FAIL -- see above"))
    print("=" * 64)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
