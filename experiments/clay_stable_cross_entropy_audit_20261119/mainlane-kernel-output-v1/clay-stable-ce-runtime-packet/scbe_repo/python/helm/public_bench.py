"""Public benchmark runner for the forge loop: pull MBPP, split public/hidden, run + verify.

tool_forge_bench.py runs the create -> verify -> repair -> keep loop on 4 hand-written tasks.
THIS pulls a real public benchmark -- MBPP sanitized (427 problems, google-research) -- and runs
the same loop over real problems. Each problem ships its own asserts; we split them into PUBLIC
checks (what the forger is allowed to see) and HIDDEN checks (held out), so a tool that overfits
the public checks is caught.

The forger is a pluggable `generator(problem) -> source`:
  * reference_generator (default) returns the dataset's own solution -- this validates the
    HARNESS end-to-end on real data ($0, no model): we pulled N real problems, ran them, and the
    public/hidden split works. It does NOT measure model capability (the solver is the answer key).
  * naive_generator returns a stub -- a sanity floor that should fail.
  * plug a real model into the same slot to measure actual forging capability. That swap is the
    only missing piece; everything else (pull, split, sandboxed verify, receipts) is real here.

Candidates run in a subprocess with a timeout (curated data, but still isolated).

    python -m python.helm.public_bench --limit 20            # reference solver (harness check)
    python -m python.helm.public_bench --limit 20 --naive    # the failing floor
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

MBPP_URL = "https://raw.githubusercontent.com/google-research/google-research/master/mbpp/sanitized-mbpp.json"
FIXTURE = Path(__file__).with_name("mbpp_sample.json")
CACHE = Path(tempfile.gettempdir()) / "scbe_mbpp_sanitized.json"

Generator = Callable[[Dict[str, Any]], str]


def pull_mbpp(limit: Optional[int] = None, force: bool = False) -> List[Dict[str, Any]]:
    """Download (and cache) the MBPP sanitized public benchmark; return its problems."""
    if force or not CACHE.exists():
        req = urllib.request.Request(MBPP_URL, headers={"User-Agent": "scbe-bench/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - fixed https public dataset URL
            CACHE.write_bytes(r.read())
    problems = json.loads(CACHE.read_text(encoding="utf-8"))
    return problems[:limit] if limit else problems


def load_fixture() -> List[Dict[str, Any]]:
    """The hermetic 3-problem MBPP sample bundled for offline tests."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["problems"]


def func_name(problem: Dict[str, Any]) -> str:
    m = re.search(r"def\s+(\w+)\s*\(", problem.get("code", ""))
    if not m:
        raise ValueError("no function definition found in problem %s" % problem.get("task_id"))
    return m.group(1)


def reference_generator(problem: Dict[str, Any]) -> str:
    """The dataset's own solution -- forges nothing, validates the harness on real data."""
    return problem["code"]


def naive_generator(problem: Dict[str, Any]) -> str:
    """A stub that defines the function but returns None -- the failing floor."""
    return "def %s(*args, **kwargs):\n    return None\n" % func_name(problem)


def _verify(source: str, public: Sequence[str], hidden: Sequence[str], imports: Sequence[str]) -> Dict[str, Any]:
    """Run public then hidden asserts against the candidate source, isolated in a subprocess."""
    runner = "\n".join(
        list(imports)
        + [
            source,
            "import json as _json",
            "_PUBLIC = " + repr(list(public)),
            "_HIDDEN = " + repr(list(hidden)),
            "def _run(_xs):",
            "    _f = []",
            "    for _a in _xs:",
            "        try:",
            "            exec(_a, globals())",
            "        except Exception as _e:",
            "            _f.append(repr(_e) or _a)",
            "    return _f",
            'print(_json.dumps({"pub": _run(_PUBLIC), "hid": _run(_HIDDEN)}))',
        ]
    )
    try:
        proc = subprocess.run([sys.executable, "-c", runner], capture_output=True, text=True, timeout=15)
        out = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.returncode == 0 and proc.stdout.strip() else None
    except Exception:
        out = None
    if out is None:
        return {
            "public_passed": False,
            "hidden_passed": False,
            "public_failures": ["did-not-run"],
            "hidden_failures": ["did-not-run"],
        }
    return {
        "public_passed": not out["pub"],
        "hidden_passed": not out["hid"],
        "public_failures": out["pub"],
        "hidden_failures": out["hid"],
    }


def run_problem(problem: Dict[str, Any], generator: Generator, public_k: int, workspace: Path) -> Dict[str, Any]:
    name = func_name(problem)
    asserts = list(problem.get("test_list", []))
    public, hidden = asserts[:public_k], asserts[public_k:]
    source = generator(problem)
    v = _verify(source, public, hidden, problem.get("test_imports", []))
    verified = v["public_passed"] and v["hidden_passed"]
    kept_path = None
    if verified:
        lib = workspace / "tool_library"
        lib.mkdir(parents=True, exist_ok=True)
        kept_path = str(lib / f"{name}.py")
        Path(kept_path).write_text(source, encoding="utf-8")
    receipt = {
        "task_id": problem.get("task_id"),
        "function": name,
        "public": len(public),
        "hidden": len(hidden),
        "verified": verified,
        "kept_path": kept_path,
        **v,
    }
    rdir = workspace / str(problem.get("task_id"))
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return receipt


def run_public_bench(
    problems: Sequence[Dict[str, Any]],
    generator: Generator = reference_generator,
    public_k: int = 1,
    workspace: Optional[Path] = None,
) -> Dict[str, Any]:
    root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="helm-public-bench-"))
    root.mkdir(parents=True, exist_ok=True)
    rows = [run_problem(p, generator, public_k, root) for p in problems if len(p.get("test_list", [])) > public_k]
    verified = [r for r in rows if r["verified"]]
    overfit = [r for r in rows if r["public_passed"] and not r["hidden_passed"]]  # passed public, failed hidden
    summary = {
        "benchmark": "MBPP-sanitized",
        "workspace": str(root),
        "generator": generator.__name__,
        "public_k": public_k,
        "attempted": len(rows),
        "verified": len(verified),
        "public_pass": sum(1 for r in rows if r["public_passed"]),
        "hidden_pass": sum(1 for r in rows if r["hidden_passed"]),
        "overfit_caught": len(overfit),
        "pass_rate": round(len(verified) / len(rows), 3) if rows else 0.0,
        "results": rows,
    }
    (root / "public_bench_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def render(summary: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "Helm Public Bench (pull a real benchmark, run the forge loop)",
            f"  benchmark: {summary['benchmark']}  gen: {summary['generator']}  public_k: {summary['public_k']}",
            f"  attempted: {summary['attempted']}   verified (public+hidden): {summary['verified']}"
            f"   pass_rate: {summary['pass_rate']}",
            f"  public_pass: {summary['public_pass']}   hidden_pass: {summary['hidden_pass']}"
            f"   overfit_caught (public-pass, hidden-fail): {summary['overfit_caught']}",
            f"  workspace: {summary['workspace']}",
        ]
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-public-bench", description="pull MBPP and run the forge loop")
    ap.add_argument("--limit", type=int, default=20, help="number of problems to pull (0 = all 427)")
    ap.add_argument("--public-k", type=int, default=1, help="how many asserts are public (rest are hidden)")
    ap.add_argument("--naive", action="store_true", help="use the failing stub generator instead of the reference")
    ap.add_argument("--fixture", action="store_true", help="use the bundled 3-problem sample (offline)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    gen = naive_generator if a.naive else reference_generator
    try:
        problems = load_fixture() if a.fixture else pull_mbpp(limit=a.limit or None)
    except Exception as e:  # network down, etc. -- be honest, do not fake
        print("could not pull MBPP (%s: %s); try --fixture for the offline sample" % (type(e).__name__, e))
        return 1
    print(render(run_public_bench(problems, generator=gen, public_k=a.public_k)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
