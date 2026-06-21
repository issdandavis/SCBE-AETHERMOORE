"""retry_corpus_validate: validate a retry-teacher SFT corpus and measure its teacher-dependence.

The v3 corpus is shaped bad attempt -> tool fail -> critique + retry -> tool fail -> teacher correction. That
trains the repair TRAJECTORY (train-on-becoming), which is right -- but if EVERY record ends with a teacher
bailing the model out, it learns teacher-dependence, not self-repair. This validator checks each record has
the repair shape and reports the load-bearing ratio: teacher-bailout vs the model's OWN retry succeeding.
(Substantiates the recommendation to mix self-repair successes into the corpus.)

PER-RECORD CATEGORY:
  MALFORMED            - missing the repair shape (< 2 assistant attempts, or no tool-fail between them)
  SELF_REPAIR_SUCCESS  - a retry PASSED before any teacher correction (the model recovered on its own)
  TEACHER_BAILOUT      - ends with a teacher correction (the model did not recover itself)
  REPAIR_UNRESOLVED    - well-formed repair shape but neither a self-pass nor a teacher correction detected

INPUT SCHEMA (tolerant; documented). Records are {"messages": [{role, content}...], "meta": {...}} (the VTC
shape). Detection is HEURISTIC over roles + content markers + meta, in this order:
  - assistant attempts = messages with role 'assistant'
  - tool-fail          = a post-problem message whose content hits a FAIL marker (assertion/error/fail/...)
  - teacher correction = meta flag (teacher_correction / final_source=='teacher' / source~='teacher' /
                         grade=='teacher') OR a turn with role 'teacher' / a TEACHER content marker
  - self-repair pass   = a PASS marker (passed/verified/all tests passed) after >=2 assistant turns with no
                         teacher correction; or meta.repaired and meta.final_source != 'teacher'
If your corpus marks stages explicitly in meta, the meta path takes precedence -- point it there.

    python -m python.helm.retry_corpus_validate corpus.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

MALFORMED = "MALFORMED"
SELF_REPAIR_SUCCESS = "SELF_REPAIR_SUCCESS"
TEACHER_BAILOUT = "TEACHER_BAILOUT"
REPAIR_UNRESOLVED = "REPAIR_UNRESOLVED"
CATEGORIES = [SELF_REPAIR_SUCCESS, TEACHER_BAILOUT, REPAIR_UNRESOLVED, MALFORMED]

FAIL_MARKERS = ("assertionerror", "traceback", "did not pass", "test failed", "error:", "failed", "fail", "❌")
PASS_MARKERS = ("all tests passed", "tests passed", "verified", "passed", "✓", "ok:")
TEACHER_MARKERS = ("teacher correction", "reference solution", "correct solution", "here is the correct")
_TEACHER_BAILOUT_WARN = 0.8  # above this fraction the corpus is teaching teacher-dependence


def _content(m: Any) -> str:
    if isinstance(m, dict):
        return str(m.get("content", "")).lower()
    return str(m).lower()


def _role(m: Any) -> str:
    return str(m.get("role", "")).lower() if isinstance(m, dict) else ""


def _hits(text: str, markers: Sequence[str]) -> bool:
    return any(mk in text for mk in markers)


def _meta_says_teacher(meta: Dict[str, Any]) -> bool:
    if meta.get("teacher_correction") or meta.get("teacher"):
        return True
    src = str(meta.get("final_source", meta.get("source", ""))).lower()
    return "teacher" in src or str(meta.get("grade", "")).lower() == "teacher"


def analyze_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    messages = rec.get("messages") or []
    meta = rec.get("meta") or {}
    assistant_turns = [m for m in messages if _role(m) == "assistant"]
    # tool-fails: failure markers in any message after the first user (the problem statement)
    seen_problem = False
    fail_signals = 0
    self_pass = False
    teacher_turn = _meta_says_teacher(meta)
    for m in messages:
        role, text = _role(m), _content(m)
        if role == "user" and not seen_problem:
            seen_problem = True
            continue
        if role == "teacher" or _hits(text, TEACHER_MARKERS):
            teacher_turn = True
        if role in ("tool", "user", "system", "ipython") and _hits(text, FAIL_MARKERS):
            fail_signals += 1
        if role in ("tool", "user", "system", "ipython") and _hits(text, PASS_MARKERS) and len(assistant_turns) >= 2:
            self_pass = True
    if meta.get("repaired") and str(meta.get("final_source", "")).lower() not in ("teacher", ""):
        self_pass = True

    well_formed = len(assistant_turns) >= 2 and fail_signals >= 1 and len(messages) >= 4
    if not well_formed:
        reasons = []
        if len(assistant_turns) < 2:
            reasons.append("only %d assistant attempt(s)" % len(assistant_turns))
        if fail_signals < 1:
            reasons.append("no tool-fail signal")
        if len(messages) < 4:
            reasons.append("too few turns")
        category = MALFORMED
    else:
        reasons = []
        if self_pass and not teacher_turn:
            category = SELF_REPAIR_SUCCESS
        elif teacher_turn:
            category = TEACHER_BAILOUT
        else:
            category = REPAIR_UNRESOLVED
    return {
        "category": category,
        "assistant_attempts": len(assistant_turns),
        "fail_signals": fail_signals,
        "teacher": teacher_turn,
        "self_repair_pass": self_pass,
        "reasons": reasons,
    }


def validate(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    analyses = [analyze_record(r) for r in records]
    counts = {c: 0 for c in CATEGORIES}
    attempts = fails = 0
    for a in analyses:
        counts[a["category"]] += 1
        attempts += a["assistant_attempts"]
        fails += a["fail_signals"]
    total = len(analyses)
    well_formed = total - counts[MALFORMED]
    bailout_ratio = round(counts[TEACHER_BAILOUT] / well_formed, 3) if well_formed else 0.0
    self_ratio = round(counts[SELF_REPAIR_SUCCESS] / well_formed, 3) if well_formed else 0.0
    return {
        "total": total,
        "counts": counts,
        "well_formed": well_formed,
        "avg_assistant_attempts": round(attempts / total, 2) if total else 0.0,
        "avg_fail_signals": round(fails / total, 2) if total else 0.0,
        "teacher_bailout_ratio": bailout_ratio,
        "self_repair_success_ratio": self_ratio,
        "teacher_dependence_warning": bailout_ratio > _TEACHER_BAILOUT_WARN,
        "malformed_examples": [a["reasons"] for a in analyses if a["category"] == MALFORMED][:5],
    }


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def render(v: Dict[str, Any]) -> str:
    lines = ["RETRY-TEACHER CORPUS VALIDATION  (total %d, well-formed %d)" % (v["total"], v["well_formed"]), ""]
    for cat in CATEGORIES:
        lines.append("  %-22s %4d" % (cat, v["counts"][cat]))
    lines += [
        "",
        "  avg assistant attempts : %.2f" % v["avg_assistant_attempts"],
        "  avg tool-fail signals  : %.2f" % v["avg_fail_signals"],
        "  teacher_bailout_ratio  : %.3f   (of well-formed records)" % v["teacher_bailout_ratio"],
        "  self_repair_success    : %.3f   <- the model recovering on its OWN" % v["self_repair_success_ratio"],
    ]
    if v["teacher_dependence_warning"]:
        lines.append(
            "  WARNING: teacher-bailout > %.0f%% -> this corpus teaches teacher-DEPENDENCE. Mix in "
            "self-repair successes (retry -> PASS), not only teacher corrections." % (_TEACHER_BAILOUT_WARN * 100)
        )
    if v["malformed_examples"]:
        lines.append("  malformed reasons (sample): %s" % v["malformed_examples"])
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="validate a retry-teacher SFT corpus + measure teacher-dependence")
    ap.add_argument("corpus", help="the SFT corpus jsonl (messages + meta records)")
    a = ap.parse_args(argv)
    print(render(validate(load_jsonl(a.corpus))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
