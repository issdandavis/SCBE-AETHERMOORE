from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TASKS = {
    "research",
    "monitor",
    "ask",
    "scrape",
    "web_search",
    "coding",
    "system_build",
    "agentic_ladder",
    "pair_benchmark",
    "poly_coding_seed",
}


def test_vercel_bridge_allowed_tasks_match_router_and_page() -> None:
    common = (REPO_ROOT / "api" / "_agent_common.js").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "agent-router.yml").read_text(encoding="utf-8")
    page = (REPO_ROOT / "docs" / "agents.html").read_text(encoding="utf-8")

    allowed_match = re.search(r"ALLOWED_TASKS\s*=\s*new Set\(\[(.*?)\]\)", common, re.DOTALL)
    assert allowed_match, "ALLOWED_TASKS declaration not found"
    allowed = set(re.findall(r'"([^"]+)"', allowed_match.group(1)))
    assert EXPECTED_TASKS <= allowed

    for task in EXPECTED_TASKS:
        assert f'value="{task}"' in page
        assert task in workflow


def test_agent_router_coding_smoke_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/system/agent_router_smoke.py", "coding"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=240,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["benchmark"]["decision"] == "PASS"


def test_agent_router_system_build_smoke_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/system/agent_router_smoke.py", "system_build"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=240,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["package_scripts"]["ok"] is True


def test_agent_router_pair_benchmark_smoke_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/system/agent_router_smoke.py", "pair_benchmark"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=240,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["benchmark"]["summary"]["pair_pass_rate"] >= payload["benchmark"]["summary"]["solo_pass_rate"]


def test_agent_router_poly_coding_seed_smoke_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/system/agent_router_smoke.py", "poly_coding_seed"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=240,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["builder"]["summary"]["train_count"] > 0
    assert payload["builder"]["summary"]["holdout_count"] > 0
