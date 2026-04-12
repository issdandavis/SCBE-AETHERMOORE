from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "scripts" / "system" / "octoarms_dispatch.py"


def _run_dispatch(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, str(DISPATCH), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def test_octoarms_dispatch_accepts_skill_level_formation_alias() -> None:
    result = _run_dispatch(
        "--task",
        "dispatch alias regression",
        "--formation",
        "hexagonal-ring",
        "--lane",
        "octoarmor-triage",
        "--no-action-map",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "octoarms_dispatch_v1"
    assert payload["flow"]["requested_formation"] == "hexagonal-ring"
    assert payload["flow"]["formation"] == "hexagonal"
    assert payload["lane"]["name"] == "octoarmor-triage"
    assert payload["lane"]["status"] == "completed"


def test_octoarms_dispatch_prefers_qwen_for_hf_triage() -> None:
    result = _run_dispatch(
        "--task",
        "hf model routing regression",
        "--formation",
        "hexagonal-ring",
        "--lane",
        "octoarmor-triage",
        "--provider",
        "hf",
        "--no-action-map",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["routing"]["recommended_provider"] == "hf"
    assert payload["routing"]["recommended_model"] == "Qwen/Qwen2.5-7B-Instruct"


def test_octoarms_dispatch_runs_without_inherited_pythonpath() -> None:
    result = _run_dispatch(
        "--task",
        "ollama runtime regression",
        "--formation",
        "hexagonal-ring",
        "--lane",
        "hydra-swarm",
        "--provider",
        "ollama",
        "--dry-run",
        "--no-action-map",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["routing"]["recommended_provider"] == "ollama"
    assert payload["lane"]["name"] == "hydra-swarm"
    assert payload["lane"]["returncode"] == 0
