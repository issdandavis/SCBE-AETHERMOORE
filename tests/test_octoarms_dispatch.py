from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "scripts" / "system" / "octoarms_dispatch.py"


def _run_dispatch(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DISPATCH), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
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
