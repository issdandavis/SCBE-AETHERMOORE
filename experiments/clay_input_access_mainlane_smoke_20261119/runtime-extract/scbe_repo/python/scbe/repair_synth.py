"""repair_synth: deterministically SYNTHESIZE verified DEEP "becoming" trajectories.

The harvested tool-use corpus (PR #2538) is 95% "confirm" (write correct code -> run -> PASS -> answer;
the tool is a rubber stamp) and only 5% "repair" -- because a weak 1.5B rarely fails-then-recovers on
its own. But the repair loop (tool returns FAIL -> the model still reaches a verified answer) is exactly
what the "train on becoming" doctrine most wants. A weak model can't reliably GENERATE it; this
SYNTHESIZES it -- guaranteed-repair-shaped, deterministic, and execution-verified.

The trick reuses my own machinery: analog_solve._op_swap_variants turns a CORRECT MBPP solution into a
PLAUSIBLE bug (one operator flipped, e.g. + -> -). If the bugged version actually FAILS the example test
and the original PASSES, that is a verified buggy->fix repair pair -- at scale, for free. Plus the 8
hand-verified pitfalls (better_corpus). Each becomes a tool dialogue in the harvester's EXACT format:

    system
    user      : problem + example test
    assistant : <buggy code>  CALL run_code
    user      : TOOL run_code: FAIL: <real got-vs-expected diagnosis>   <- the failure
    assistant : <fixed code>  CALL run_code                              <- the repair
    user      : TOOL run_code: PASS (example test)
    assistant : ANSWER: <fixed code>

Every record is independently AUDITED (audit() re-parses the messages and re-runs buggy+fix in a fresh
verify, never trusting the synthesizer's own claim). Records union into the tool-use corpus unchanged
({messages, meta}); training + eval on the corpus stays Codex's lane.

    from python.scbe.repair_synth import build
    res = build("training/sft_records/repair_trajectory_synth.jsonl")  # pitfalls + MBPP-derived, audited
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from python.helm import public_bench as pb
from python.helm.free_generator import _diagnose, strip_to_code
from python.scbe.analog_solve import _op_swap_variants

try:  # match the harvester's system prompt exactly so the records union into one homogeneous corpus
    from python.helm.tool_trajectory import SYSTEM as SYSTEM
except Exception:  # pragma: no cover - fallback keeps the synthesizer standalone
    SYSTEM = (
        "You are a coding agent with tools. To use a tool, end a turn with 'CALL <tool> <arg>' "
        "(tools: run_code, calc, is_prime, factor). The harness runs it and replies 'TOOL <tool>: <result>'. "
        "Prefer to run_code at least once before answering. When done, reply 'ANSWER:' then a code block."
    )


def _code_block(code: str) -> str:
    return "```python\n" + strip_to_code(code).strip() + "\n```"


def _parse_asserts(text: str) -> List[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip().startswith("assert ")]


def _run_code_result(code: str, public: Sequence[str], imports: Sequence[str]) -> str:
    """The run_code tool's verbatim reply string (matches the harvester): PASS or FAIL + real diagnosis."""
    if pb._verify(code, list(public), [], list(imports))["public_passed"]:
        return "PASS (example test)"
    diags = _diagnose(code, list(public), list(imports))
    return "FAIL: " + (" | ".join(str(d) for d in diags))[:400]


def repair_trajectory(
    task_id: str,
    problem_text: str,
    buggy: str,
    fix: str,
    public: Sequence[str],
    held: Sequence[str],
    imports: Sequence[str] = (),
    source: str = "repair_synth",
) -> Optional[Dict[str, Any]]:
    """Build ONE verified repair dialogue, or None if it is not a real buggy->fix repair: the buggy code
    must FAIL the shown (public) test and the fix must PASS public AND any held-back tests. Nothing
    unverified is ever emitted."""
    buggy, fix = strip_to_code(buggy), strip_to_code(fix)
    public, held, imports = list(public), list(held), list(imports)
    buggy_fails = not pb._verify(buggy, public, [], imports)["public_passed"]
    fix_v = pb._verify(fix, public, held, imports)
    fix_passes = fix_v["public_passed"] and (not held or fix_v["hidden_passed"])
    if not (buggy_fails and fix_passes):
        return None
    fail = _run_code_result(buggy, public, imports)
    if not fail.startswith("FAIL"):  # belt-and-suspenders: the tool must actually report FAIL
        return None
    user0 = problem_text.strip() + "\n\nExample test (you may run_code against it):\n" + "\n".join(public)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user0},
        {"role": "assistant", "content": _code_block(buggy) + "\nCALL run_code"},
        {"role": "user", "content": "TOOL run_code: " + fail},
        {"role": "assistant", "content": _code_block(fix) + "\nCALL run_code"},
        {"role": "user", "content": "TOOL run_code: PASS (example test)"},
        {"role": "assistant", "content": "ANSWER:\n" + _code_block(fix)},
    ]
    return {
        "messages": messages,
        "meta": {
            "verified": True,
            "task_id": task_id,
            "source": source,
            "grade": "repair",
            "shape": "repair",
            "attempts": 2,
            "tool_calls": 2,
            "tools_used": ["run_code"],
            "public_tests": public,
            "held_tests": held,
            "imports": imports,
        },
    }


def from_pitfalls() -> List[Dict[str, Any]]:
    """The 8 hand-verified common-pitfall buggy->fix pairs (better_corpus) as repair dialogues. Both tests
    are shown so the buggy visibly fails (some pitfalls, e.g. mutable-default, only fail on a later call)."""
    from python.helm.better_corpus import PITFALLS

    out: List[Dict[str, Any]] = []
    for spec in PITFALLS:
        tr = repair_trajectory(
            "pitfall_" + spec["name"],
            spec["prompt"],
            spec["buggy"],
            spec["fix"],
            spec["tests"],  # public = all tests (so the bug shows)
            [],
            source="repair_synth_pitfall",
        )
        if tr:
            out.append(tr)
    return out


def from_mbpp(limit: int = 120, public_k: int = 1, max_per_problem: int = 1) -> List[Dict[str, Any]]:
    """Mine repairs from MBPP at scale: for each problem with a correct reference (the FIX), flip ONE
    operator (analog_solve._op_swap_variants) to make a plausible BUGGY draft; keep it only if the bug
    fails the public test and the fix passes held-back. Deterministic, guaranteed-repair-shaped."""
    out: List[Dict[str, Any]] = []
    for p in pb.pull_mbpp()[:limit]:
        tl = list(p.get("test_list", []))
        if not tl:
            continue
        public, held, imports = tl[:public_k], tl[public_k:], list(p.get("test_imports", []))
        fix = strip_to_code(p["code"])
        if not pb._verify(fix, public, held, imports)["hidden_passed"]:
            continue  # only mine from a reference that is actually correct
        made = 0
        for buggy in _op_swap_variants(fix):
            if made >= max_per_problem:
                break
            tr = repair_trajectory(
                str(p["task_id"]),
                (p.get("prompt") or p.get("text") or "").strip(),
                buggy,
                fix,
                public,
                held,
                imports,
                source="repair_synth_mbpp",
            )
            if tr:
                out.append(tr)
                made += 1
    return out


def audit(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The INDEPENDENT instrument: re-parse each record's messages and re-run buggy+fix in a fresh verify,
    NEVER trusting the synthesizer's own label. A record is clean iff the buggy really fails the shown
    tests and the fix really passes them. Mirrors Codex's separate auditor -- don't grade your own work."""
    clean = 0
    bad: List[str] = []
    for r in records:
        msgs = r.get("messages", [])
        m = r.get("meta", {})
        public = m.get("public_tests")
        held = m.get("held_tests", [])
        imports = m.get("imports", [])
        if public is None:  # fallback for foreign records: parse ONLY the example-test section, not prose
            ut = next((x["content"] for x in msgs if x["role"] == "user"), "")
            public, held = _parse_asserts(ut.split("Example test", 1)[-1]), []
        assistants = [x["content"] for x in msgs if x["role"] == "assistant"]
        if not public or len(assistants) < 2:
            bad.append(str(m.get("task_id")))
            continue
        buggy, fix = strip_to_code(assistants[0]), strip_to_code(assistants[-1])
        buggy_fails = not pb._verify(buggy, list(public), [], list(imports))["public_passed"]
        fv = pb._verify(fix, list(public), list(held), list(imports))
        fix_passes = fv["public_passed"] and (not held or fv["hidden_passed"])
        if buggy_fails and fix_passes:
            clean += 1
        else:
            bad.append(str(m.get("task_id")))
    return {"audited": len(records), "verified": clean, "mismatches": len(bad), "bad_ids": bad[:10]}


def build(
    out_path: str = "training/sft_records/repair_trajectory_synth.jsonl",
    mbpp_limit: int = 120,
    public_k: int = 1,
    max_per_problem: int = 1,
) -> Dict[str, Any]:
    """Union the pitfall + MBPP-derived repair dialogues, AUDIT them independently, and write only the
    audit-clean records as {messages, meta} JSONL (the tool-use corpus format)."""
    pit = from_pitfalls()
    mbpp = from_mbpp(mbpp_limit, public_k, max_per_problem)
    records = pit + mbpp
    a = audit(records)
    clean = [r for r in records if audit([r])["verified"] == 1]  # write only what re-verifies
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in clean:
            f.write(json.dumps({"messages": r["messages"], "meta": r["meta"]}, ensure_ascii=False) + "\n")
    return {
        "path": str(p),
        "total": len(clean),
        "from_pitfalls": len(pit),
        "from_mbpp": len(mbpp),
        "audit": a,
        "all_repair_shape": all(r["meta"]["shape"] == "repair" for r in clean),
    }


def demo() -> Dict[str, Any]:
    pit = from_pitfalls()
    a = audit(pit)
    sample = pit[0]["messages"] if pit else []
    return {
        "pitfall_repairs": len(pit),
        "audit_clean": a["verified"] == a["audited"] and a["audited"] > 0,
        "roles": [m["role"] for m in sample],
        "fail_turn": next((m["content"] for m in sample if m["role"] == "user" and "FAIL" in m["content"]), ""),
    }


def main(argv: Optional[List[str]] = None) -> int:
    out = demo()
    print("REPAIR-TRAJECTORY SYNTHESIZER (deep 'becoming' data, verified + independently audited)")
    print("  pitfall repairs : %d  (audit clean: %s)" % (out["pitfall_repairs"], out["audit_clean"]))
    print("  trajectory roles: %s" % " -> ".join(out["roles"]))
    print("  the FAIL turn   : %s" % out["fail_turn"][:90])
    mb = from_mbpp(limit=60)
    print("  MBPP-mined repairs (limit 60): %d  (audit clean: %s)" % (len(mb), audit(mb)["mismatches"] == 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
