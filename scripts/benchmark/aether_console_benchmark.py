#!/usr/bin/env python3
"""Aether Console capability benchmark.

Honest, measurable question: of the console's 50 advertised choices, how many of
the LOCAL ENGINE capabilities actually run, and how fast? (Network/AI/destructive
choices are reported separately -- they're integrations, not engine capability,
and shouldn't be "run" in a benchmark.)

Output: a human summary + a scbe_benchmark_score_v1-style JSON to
research/benchmarks/results/aether-console-<stamp>.json  (stamp via --stamp).

    python scripts/benchmark/aether_console_benchmark.py
    python scripts/benchmark/aether_console_benchmark.py --json
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / "scripts" / "powershell" / "AetherMenu.catalog.json"
TIMEOUT = 40


def dummy_input(prompt: str, command: str) -> str | None:
    """A safe stand-in value for a {input} choice, or None if it needs a real id we can't fake."""
    p = (prompt or "").lower()
    c = command.lower()
    if c.strip() == "python scbe.py enc {input}":
        return "ko hi"  # this choice is "tongue + text" -> two args by design
    if c.strip().startswith("python scbe.py dec"):
        return "nav'or nav'uu"  # decode needs REAL tokens, not plain text
    if "smiles" in p or "smiles" in c:
        return "CCO"
    if "file" in p:
        return "scbe.py"
    if "operation" in p:
        return "release"
    if "tongue code" in p or "ko, av" in p:
        return "ko hello world"
    if "text" in p or "writing" in p or "question" in p or "ask" in p:
        return "hello world"
    if "run id" in p or "pull request" in p or p.strip().startswith("which"):
        return None  # needs a real GitHub id -- can't fake meaningfully
    return "hello world"


def classify(action: dict) -> str:
    cmd = action["command"]
    if action.get("run_mode") == "confirm":
        return "skip:destructive"
    if cmd.strip().startswith("gh ") or cmd.strip().startswith("git "):
        return "skip:network"
    # AI verbs need a model backend, not an engine capability
    if (
        cmd.startswith("python scbe.py ask")
        or cmd.startswith("python scbe.py do")
        or cmd.startswith("python scbe.py chat")
    ):
        return "skip:ai-backend"
    return "run"


def run_one(action: dict):
    cmd = action["command"]
    if action.get("needs_input"):
        val = dummy_input(action.get("input_prompt", ""), cmd)
        if val is None:
            return {"status": "skip:needs-real-id", "ms": 0}
        cmd = cmd.replace("{input}", val)
    env = dict(os.environ, PYTHONPATH=".")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(REPO),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
        ms = (time.perf_counter() - t0) * 1000.0
        # exit 0 = pass; exit 3 = graceful "optional dependency missing" (still a real capability boundary)
        if proc.returncode == 0:
            return {"status": "pass", "ms": ms}
        if proc.returncode == 3:
            return {"status": "skip:optional-dep", "ms": ms}
        return {"status": "fail", "ms": ms, "code": proc.returncode, "err": (proc.stderr or proc.stdout or "")[-200:]}
    except subprocess.TimeoutExpired:
        return {"status": "fail", "ms": TIMEOUT * 1000.0, "err": "timeout"}
    except Exception as e:  # pragma: no cover
        return {"status": "fail", "ms": 0, "err": str(e)}


def main():
    cats = json.loads(CATALOG.read_text(encoding="utf-8"))["categories"]
    rows = []
    for cat in cats:
        for a in cat["actions"]:
            kind = classify(a)
            if kind != "run":
                rows.append({"category": cat["category"], "label": a["label"], "status": kind, "ms": 0})
                continue
            res = run_one(a)
            rows.append({"category": cat["category"], "label": a["label"], **res})
            mark = {"pass": "OK", "fail": "XX"}.get(res["status"], "--")
            print(
                f"  [{mark}] {cat['category']:<24} {a['label'][:40]:<40} "
                f"{res['status']:<18} {res.get('ms', 0):6.0f} ms"
            )

    run_rows = [r for r in rows if r["status"] in ("pass", "fail")]
    passed = [r for r in run_rows if r["status"] == "pass"]
    skipped = [r for r in rows if r["status"].startswith("skip")]
    lat = [r["ms"] for r in passed]
    summary = {
        "total_choices": len(rows),
        "engine_capabilities_tested": len(run_rows),
        "passed": len(passed),
        "failed": len(run_rows) - len(passed),
        "pass_rate_pct": round(100.0 * len(passed) / max(1, len(run_rows)), 1),
        "skipped_integration_or_destructive": len(skipped),
        "latency_ms_mean": round(sum(lat) / max(1, len(lat)), 1),
        "latency_ms_max": round(max(lat) if lat else 0, 1),
    }
    print("\n" + "=" * 64)
    print(
        f"  Engine capabilities: {summary['passed']}/{summary['engine_capabilities_tested']} pass "
        f"({summary['pass_rate_pct']}%)   mean {summary['latency_ms_mean']}ms"
    )
    print(f"  Skipped (network/AI/destructive, not engine): {summary['skipped_integration_or_destructive']}")
    print("=" * 64)

    result = {
        "schema_version": "scbe_benchmark_score_v1",
        "benchmark": "aether-console-capability",
        "goal": "capability-coverage",
        "metric": {"name": "engine_capability_pass_rate", "unit": "pct", "lower_is_better": False},
        "summary": summary,
        "rows": rows,
    }
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    out = REPO / "research" / "benchmarks" / "results"
    out.mkdir(parents=True, exist_ok=True)
    stamp = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--stamp=")), "local")
    (out / f"aether-console-{stamp}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    main()
