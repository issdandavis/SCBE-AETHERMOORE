"""verified_trajectory: the Verified-Trajectory Curriculum (VTC) engine.

The training regime's core idea: the agent's OWN execution-verified solving becomes its training data.
Run graded problems through a generator (a model), VERIFY each by execution (hidden tests via
public_bench), and keep ONLY the trajectories that actually pass. Rejection-sampling SFT (STaR/RFT) --
established -- but the differentiator is REAL execution verification, not a reward model that can be
gamed. Truth = the tests ran and passed, never text.

    harvest(problems, generator) -> {records: [verified SFT], attempted, verified, verified_rate}

Each kept record teaches a verified solution; pair the generator with free_generator.make_repair_generator
to harvest POST-repair (write->run->fix->verified) code, so the agent learns the loop that produced the
lift, not just final answers. Grade with curriculum.py; track measure_lift(base, trained) on the held-out
hidden tests -- a real scoreboard. v1 emits final verified code; multi-turn repair traces are v1.1.

    python -m python.helm.verified_trajectory                 # reference solver (validates the engine)
    python -m python.helm.verified_trajectory --model qwen2.5-coder:1.5b --out training-data/sft/vtc.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from .public_bench import _verify

Generator = Callable[[Dict[str, Any]], str]

SYSTEM = (
    "You are an SCBE coding agent. Write a complete, correct solution that passes the tests. "
    "Output only the code. Correctness is verified by execution against held-out tests."
)


def to_sft(problem: Dict[str, Any], code: str, public_k: int, system: str = SYSTEM) -> Dict[str, Any]:
    """One verified record: system + user(problem + the public example) + assistant(verified code)."""
    prompt = (problem.get("prompt") or problem.get("text") or "").strip()
    public = "\n".join(list(problem.get("test_list", []))[:public_k])
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt + ("\n\nIt must pass:\n" + public if public else "")},
            {"role": "assistant", "content": code},
        ],
        "meta": {"verified": True, "task_id": problem.get("task_id"), "source": "verified_trajectory"},
    }


def harvest(
    problems: Sequence[Dict[str, Any]],
    generator: Generator,
    public_k: int = 1,
    system: str = SYSTEM,
) -> Dict[str, Any]:
    """Solve each problem, VERIFY by execution (hidden tests), keep ONLY verified trajectories."""
    records: List[Dict[str, Any]] = []
    attempted = 0
    for p in problems:
        tl = list(p.get("test_list", []))
        imports = list(p.get("test_imports", []))
        attempted += 1
        try:
            code = generator(p)
        except Exception:
            continue
        res = _verify(code, tl[:public_k], tl[public_k:], imports)  # TRUTH = execution
        if res.get("hidden_passed") and res.get("public_passed"):
            records.append(to_sft(p, code, public_k, system))
    n = len(problems) or 1
    return {
        "records": records,
        "attempted": attempted,
        "verified": len(records),
        "verified_rate": round(len(records) / n, 3),
    }


def reference_generator(problem: Dict[str, Any]) -> str:
    """The answer key -- validates the engine: every reference solution must verify and be harvested."""
    return problem.get("code", "")


def naive_generator(problem: Dict[str, Any]) -> str:
    """The floor: emits a stub that fails -- nothing should be harvested from it."""
    return "def _f(*a, **k):\n    return None\n"


def write_dataset(result: Dict[str, Any], out_path: str) -> Dict[str, Any]:
    """Write the verified SFT records + a manifest next to them. Returns the manifest."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in result["records"]:
            f.write(json.dumps(rec) + "\n")
    manifest = {
        "schema": "verified_trajectory_manifest_v1",
        "dataset": str(out),
        "attempted": result["attempted"],
        "verified": result["verified"],
        "verified_rate": result["verified_rate"],
        "note": "Every record passed held-out hidden tests by execution (rejection-sampled). No unverified data.",
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-vtc", description="harvest execution-verified training trajectories")
    ap.add_argument("--model", default=None, help="Ollama model id (omit for the reference solver)")
    ap.add_argument("--repair", action="store_true", help="use the repair loop (harvest post-repair verified code)")
    ap.add_argument("--limit", type=int, default=None, help="cap number of MBPP problems (else use the curriculum)")
    ap.add_argument("--out", default=None, help="write SFT jsonl here (+ a .manifest.json)")
    a = ap.parse_args(list(argv) if argv is not None else None)

    if a.limit:
        from .public_bench import pull_mbpp

        problems = pull_mbpp(limit=a.limit)
    else:
        from .curriculum import CURRICULUM

        problems = [p for tier in CURRICULUM for p in tier["problems"]]

    if a.model:
        from .free_generator import make_generator, make_repair_generator

        gen: Generator = make_repair_generator(model=a.model) if a.repair else make_generator(model=a.model)
    else:
        gen = reference_generator

    result = harvest(problems, gen)
    who = a.model or "reference"
    print("VERIFIED-TRAJECTORY HARVEST  solver=%s  problems=%d" % (who, len(problems)))
    print(
        "  verified (hidden tests passed): %d/%d  rate=%.3f"
        % (result["verified"], result["attempted"], result["verified_rate"])
    )
    if a.out:
        m = write_dataset(result, a.out)
        print("  wrote %d records -> %s (+ manifest)" % (m["verified"], m["dataset"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
