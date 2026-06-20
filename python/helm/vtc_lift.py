"""vtc_lift: does verified-trajectory training actually help? Base vs trained, on HELD-OUT problems.

The only honest proof the VTC corpus is worth anything: take the SAME benchmark, run the base model and
the fine-tuned model through the identical write->run->repair loop, score ONLY problems whose task_id is
NOT in the training set, and report the delta. Two numbers matter:

    solved lift     = trained_solved - base_solved          (raw capability)
    recovery lift   = trained_recovery_rate - base_recovery  (the real claim: did it learn to RECOVER?)

recovery_rate = of the problems a model solves, the fraction it solved only AFTER a failed attempt (i.e.
it used the loop). VTC trains on repair traces, so its specific bet is that recovery_lift > 0. We also
report regressions (base solved, trained broke) -- training that only adds is rare; surface what it cost.

    python -m python.helm.vtc_lift --base qwen2.5-coder:1.5b --trained qwen2.5-coder:1.5b-vtc \
        --corpus training-data/sft/vtc_mbpp_refined.jsonl --limit 260

Model-agnostic: pass any two ask(prompt)->str callables to measure_vtc_lift (ollama, HF transformers,
a merged adapter). Truth = execution against held-out hidden tests; nothing here trusts text.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from .verified_trajectory import solve_with_trace

Ask = Callable[[str], str]


def corpus_task_ids(corpus_path: str | Path) -> Set[int]:
    """The task_ids the corpus was built from -- everything NOT in here is fair held-out ground."""
    ids: Set[int] = set()
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tid = json.loads(line).get("meta", {}).get("task_id")
            if isinstance(tid, int):
                ids.add(tid)
    return ids


def held_out(problems: Sequence[Dict[str, Any]], trained_ids: Set[int]) -> List[Dict[str, Any]]:
    """Problems whose task_id was NOT trained on -- the only fair place to measure lift."""
    return [p for p in problems if p.get("task_id") not in trained_ids]


def _failure_class(final_code: str, problem: Dict[str, Any], public_k: int) -> str:
    """Bucket an UNSOLVED attempt so we can see HOW failure changes, not just the count."""
    from .free_generator import _diagnose

    if len(final_code.strip()) < 10:
        return "empty"
    tl = list(problem.get("test_list", []))
    imports = list(problem.get("test_imports", []))
    diags = _diagnose(final_code, tl[:public_k] or tl[:1], imports)
    blob = " ".join(str(d) for d in diags).lower()
    if "error" in blob or "exception" in blob or "traceback" in blob:
        return "exception"
    return "wrong_output"


def evaluate(ask: Ask, problems: Sequence[Dict[str, Any]], public_k: int = 1, rounds: int = 3) -> Dict[str, Any]:
    """Run a model through the verify-repair loop on each problem; verify on held-out hidden tests."""
    per_problem: List[Dict[str, Any]] = []
    solved_ids: Set[Any] = set()
    recovered = 0  # solved, but only after >1 attempt -> the model USED the loop
    first_try = 0  # solved on attempt 1
    failure_classes: Counter = Counter()
    for p in problems:
        tr = solve_with_trace(p, ask, public_k=public_k, rounds=rounds)
        tid = p.get("task_id")
        rec = {"task_id": tid, "verified": tr["verified"], "attempts": tr["attempts"], "repaired": tr["attempts"] > 1}
        per_problem.append(rec)
        if tr["verified"]:
            solved_ids.add(tid)
            if tr["attempts"] > 1:
                recovered += 1
            else:
                first_try += 1
        else:
            failure_classes[_failure_class(tr["final_code"], p, public_k)] += 1
    solved = len(solved_ids)
    return {
        "n": len(problems),
        "solved": solved,
        "solved_ids": solved_ids,
        "first_try": first_try,
        "recovered": recovered,
        "recovery_rate": round(recovered / solved, 3) if solved else 0.0,
        "failure_classes": dict(failure_classes),
        "per_problem": per_problem,
    }


def measure_vtc_lift(
    base_ask: Ask,
    trained_ask: Ask,
    problems: Sequence[Dict[str, Any]],
    public_k: int = 1,
    rounds: int = 3,
) -> Dict[str, Any]:
    """LIFT = trained - base on the SAME held-out problems. Reports solved-lift, recovery-lift (the VTC
    bet), what the trained model GAINED, and what it REGRESSED -- training rarely only adds; show the cost."""
    base = evaluate(base_ask, problems, public_k, rounds)
    trained = evaluate(trained_ask, problems, public_k, rounds)
    gained = sorted(i for i in trained["solved_ids"] - base["solved_ids"] if i is not None)
    regressed = sorted(i for i in base["solved_ids"] - trained["solved_ids"] if i is not None)
    return {
        "n": len(problems),
        "base_solved": base["solved"],
        "trained_solved": trained["solved"],
        "solved_lift": trained["solved"] - base["solved"],
        "base_recovery_rate": base["recovery_rate"],
        "trained_recovery_rate": trained["recovery_rate"],
        "recovery_lift": round(trained["recovery_rate"] - base["recovery_rate"], 3),
        "gained": gained,
        "regressed": regressed,
        "base_failure_classes": base["failure_classes"],
        "trained_failure_classes": trained["failure_classes"],
        "base": base,
        "trained": trained,
    }


def render(report: Dict[str, Any]) -> str:
    """The honest report: raw, trained, lift, regressions, failure-class change, recovery delta."""
    n = report["n"]
    lines = [
        "VTC LIFT  (held-out %d problems, base vs trained, verify-repair loop)" % n,
        "  solved      base %d/%d  ->  trained %d/%d   lift %+d"
        % (report["base_solved"], n, report["trained_solved"], n, report["solved_lift"]),
        "  recovery    base %.3f   ->  trained %.3f    lift %+.3f   (THE CLAIM: learned to recover?)"
        % (report["base_recovery_rate"], report["trained_recovery_rate"], report["recovery_lift"]),
        "  gained      %d problems: %s" % (len(report["gained"]), report["gained"][:20]),
        "  regressed   %d problems: %s" % (len(report["regressed"]), report["regressed"][:20]),
        "  failures    base %s  ->  trained %s" % (report["base_failure_classes"], report["trained_failure_classes"]),
    ]
    verdict = "PROVEN" if report["solved_lift"] > 0 or report["recovery_lift"] > 0 else "NO LIFT"
    lines.append("  verdict     %s" % verdict)
    return "\n".join(lines)


def _ollama_ask(model: str, base: Optional[str] = None, key: Optional[str] = None) -> Ask:
    """Wrap an OpenAI-compatible (ollama) chat endpoint as a plain ask(prompt)->str."""
    import os

    from .free_generator import DEFAULT_BASE, _chat, strip_to_code

    b = base or os.environ.get("SCBE_LLM_BASE", DEFAULT_BASE)
    k = key or os.environ.get("SCBE_LLM_KEY", "ollama")

    def ask(prompt: str) -> str:
        try:
            return strip_to_code(_chat([{"role": "user", "content": prompt}], base=b, key=k, model=model))
        except Exception as exc:  # fail closed: emit failing code, never confident-wrong
            return "# generation failed (%s)\ndef _f(*a, **k):\n    return None\n" % type(exc).__name__

    return ask


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-vtc-lift", description="measure VTC training lift on held-out problems")
    ap.add_argument("--base", required=True, help="ollama model id for the BASE (raw) slot")
    ap.add_argument("--trained", required=True, help="ollama model id for the TRAINED slot (e.g. base+VTC adapter)")
    ap.add_argument("--corpus", required=True, help="the training corpus jsonl (its task_ids are excluded as held-out)")
    ap.add_argument(
        "--limit", type=int, default=260, help="pull this many MBPP problems; held-out = these minus corpus"
    )
    ap.add_argument("--rounds", type=int, default=3, help="repair rounds per problem")
    ap.add_argument("--out", default=None, help="write the full report json here")
    a = ap.parse_args(list(argv) if argv is not None else None)

    from .public_bench import pull_mbpp

    trained_ids = corpus_task_ids(a.corpus)
    problems = held_out(pull_mbpp(limit=a.limit), trained_ids)
    print(
        "held-out: %d problems (pulled %d, excluded %d trained task_ids)" % (len(problems), a.limit, len(trained_ids))
    )

    report = measure_vtc_lift(_ollama_ask(a.base), _ollama_ask(a.trained), problems, rounds=a.rounds)
    print(render(report))
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        # drop the bulky id sets before serializing
        slim = {k: v for k, v in report.items() if k not in ("base", "trained")}
        slim["base"] = {k: v for k, v in report["base"].items() if k != "solved_ids"}
        slim["trained"] = {k: v for k, v in report["trained"].items() if k != "solved_ids"}
        out.write_text(json.dumps(slim, indent=2), encoding="utf-8")
        print("  wrote report -> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
