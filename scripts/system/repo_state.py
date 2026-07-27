#!/usr/bin/env python3
"""Emit machine-readable repo hygiene state: docs/repo-state.json + an append-only history.

    python scripts/system/repo_state.py                 # write both
    python scripts/system/repo_state.py --print         # stdout only, write nothing

Two consumers, one source:

  docs/repo-state.json           latest snapshot -- the dashboard renders this
  docs/repo-state-history.jsonl  append-only, one row per run -- Clay ingests this

The metrics are not generic repo stats. Each one is a failure that was live and INVISIBLE
in this repo on 2026-07-27, chosen because a number would have surfaced it:

  publish drift      pip install was broken for weeks. The repo said 4.3.0, PyPI served a
                     4.2.1 wheel containing no source packages. Nothing compared them.
  version coherence  pyproject said 4.3.0 while __init__ said 3.3.0 -- and 3.3.0 is a real
                     past release, so it read as plausible rather than broken.
  nightly load       100 workflow runs fired on one branch in an evening; one guard ran 16
                     times. Nobody counts runs, so nobody noticed.
  hook reachability  core.hooksPath pointed at a subpackage, so the credential scanner had
                     never executed while reporting "installed".
  history weight     .git is 515 MB against 86 MB of live blobs.

The history file is the point for Clay. A single snapshot says "44 workflows"; a series says
"workflows grew every week and nothing was ever retired", which is the shape upkeep work
actually has. Rows are append-only and never rewritten, so a metric that improves cannot
erase the evidence that it was once bad.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "docs" / "repo-state.json"
HISTORY = ROOT / "docs" / "repo-state-history.jsonl"
SCHEMA_VERSION = 1


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=120
        ).stdout.strip()
    except Exception:
        return ""


def _pypi_version(pkg: str) -> str | None:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=15) as r:
            return json.load(r)["info"]["version"]
    except Exception:
        return None  # offline is unknown, NOT "in sync"


def _npm_version(pkg: str) -> str | None:
    try:
        out = subprocess.run(["npm", "view", pkg, "version"], capture_output=True, text=True, timeout=60).stdout.strip()
        return out or None
    except Exception:
        return None


def collect_versions() -> dict:
    """Declared vs published. The single highest-value check in this file."""
    with (ROOT / "pyproject.toml").open("rb") as fh:
        declared = tomllib.load(fh)["project"]["version"]
    init = (ROOT / "src" / "scbe_aethermoore" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', init, re.M)
    dunder = m.group(1) if m else None
    npm_declared = json.loads((ROOT / "package.json").read_text(encoding="utf-8")).get("version")

    pypi, npm = _pypi_version("scbe-aethermoore"), _npm_version("scbe-aethermoore")
    coherent = declared == dunder == npm_declared
    drift = [
        f"pypi {pypi} != declared {declared}" if pypi and pypi != declared else None,
        f"npm {npm} != declared {npm_declared}" if npm and npm != declared else None,
    ]
    return {
        "declared_pyproject": declared,
        "declared_dunder": dunder,
        "declared_package_json": npm_declared,
        "published_pypi": pypi,
        "published_npm": npm,
        "internally_coherent": coherent,
        "publish_drift": [d for d in drift if d],
        # unknown when offline -- refuse to report "in sync" without having checked
        "checked_registries": bool(pypi or npm),
    }


def collect_workflows() -> dict:
    import yaml

    wf = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    daily, weekly, on_push, no_concurrency = [], [], 0, 0
    for f in wf:
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        on = d.get(True) or d.get("on") or {}
        if not isinstance(on, dict):
            continue
        for s in on.get("schedule") or []:
            (daily if str(s.get("cron", "")).endswith("* * *") else weekly).append(f.name)
        push = on.get("push")
        if push is not None:
            push = push or {}
            if not (isinstance(push, dict) and push.get("tags") and not push.get("branches")):
                on_push += 1
                if "concurrency" not in json.dumps(d):
                    no_concurrency += 1
    return {
        "total": len(wf),
        "nightly": sorted(daily),
        "nightly_count": len(daily),
        "weekly_count": len(weekly),
        "branch_push_triggered": on_push,
        "missing_concurrency": no_concurrency,
    }


def collect_git() -> dict:
    """Live weight vs history weight. Only history-only blobs are reclaimable by a rewrite."""
    tracked = _git("ls-files").splitlines()
    head_blobs = set(_git("ls-tree", "-r", "HEAD", "--format=%(objectname)").split())
    counts = _git("count-objects", "-vH")
    packed = re.search(r"size-pack: (.+)", counts)
    return {
        "tracked_files": len(tracked),
        "head_blob_count": len(head_blobs),
        "pack_size": packed.group(1).strip() if packed else None,
        "head_sha": _git("rev-parse", "--short", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
    }


def collect_hooks() -> dict:
    """A hook git never executes is worse than no hook: it reports success and blocks nothing."""
    hooks_path = _git("config", "core.hooksPath")
    repo_hook = ROOT / "scripts" / "hooks" / "pre-commit"
    effective = ROOT / hooks_path / "pre-commit" if hooks_path else ROOT / ".git" / "hooks" / "pre-commit"
    chained = False
    if hooks_path and effective.exists():
        chained = "scripts/hooks/pre-commit" in effective.read_text(encoding="utf-8", errors="replace")
    return {
        "core_hooks_path": hooks_path or None,
        "repo_hook_present": repo_hook.exists(),
        "effective_hook_present": effective.exists(),
        # the actual question: will the repo's checks run on a commit?
        "repo_hook_reachable": (not hooks_path) or chained,
    }


def collect_tests() -> dict:
    t = ROOT / "tests"
    return {
        "test_files": len(list(t.rglob("test_*.py"))) if t.exists() else 0,
        "workflow_gate_tests": len(list(t.glob("test_*packaging*.py")) + list(t.glob("test_*precommit*.py"))),
    }


def build() -> dict:
    state = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": collect_versions(),
        "workflows": collect_workflows(),
        "git": collect_git(),
        "hooks": collect_hooks(),
        "tests": collect_tests(),
    }
    v, w, h = state["versions"], state["workflows"], state["hooks"]
    # Findings are stated as problems, never as a score. A score invites tuning the score.
    findings = []
    if not v["internally_coherent"]:
        findings.append(
            {"severity": "high", "area": "versions", "detail": "declared versions disagree with each other"}
        )
    for d in v["publish_drift"]:
        findings.append({"severity": "high", "area": "publish", "detail": d})
    if not h["repo_hook_reachable"]:
        findings.append(
            {"severity": "high", "area": "hooks", "detail": "core.hooksPath bypasses the repo pre-commit hook"}
        )
    if w["missing_concurrency"]:
        findings.append(
            {
                "severity": "medium",
                "area": "ci",
                "detail": f"{w['missing_concurrency']} push workflows lack a concurrency group",
            }
        )
    if w["nightly_count"] > 5:
        findings.append(
            {"severity": "low", "area": "ci", "detail": f"{w['nightly_count']} nightly workflows (target <=5)"}
        )
    state["findings"] = findings
    state["clean"] = not findings
    return state


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="stdout only; write no files")
    args = ap.parse_args()

    state = build()
    if args.print:
        print(json.dumps(state, indent=2))
        return 0

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as fh:  # append-only: a fixed metric must not erase its own history
        fh.write(json.dumps(state, separators=(",", ":")) + "\n")

    print(f"{STATE.relative_to(ROOT)}: {len(state['findings'])} finding(s), clean={state['clean']}")
    for f in state["findings"]:
        print(f"  [{f['severity']}] {f['area']}: {f['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
