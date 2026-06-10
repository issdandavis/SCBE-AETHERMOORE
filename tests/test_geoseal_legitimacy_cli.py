from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_legitimacy_trial_cli_emits_json_allow_for_scoped_user_command() -> None:
    proc = _run(
        "legitimacy-trial",
        "--goal",
        "run tests",
        "--tool",
        "terminal.command.request",
        "--workspace",
        str(ROOT),
        "--location-source",
        "user_confirmed",
        "--location-label",
        "local dev workstation",
        "--location-confidence",
        "0.95",
        "--network-state",
        "local",
        "--json",
        "--",
        "python",
        "--version",
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal-legitimacy-result-v1"
    assert payload["decision"]["decision"] == "ALLOW_CLI"
    assert payload["decision"]["allowed_cli"] is True


def test_legitimacy_trial_cli_returns_nonzero_for_denied_command() -> None:
    proc = _run(
        "legitimacy-trial",
        "--goal",
        "cleanup",
        "--tool",
        "terminal.command.request",
        "--workspace",
        str(ROOT),
        "--location-source",
        "user_confirmed",
        "--location-confidence",
        "0.95",
        "--json",
        "--",
        "powershell",
        "Remove-Item",
        ".env",
        "-Recurse",
    )

    assert proc.returncode == 3
    assert "Traceback (most recent call last)" not in proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["decision"]["decision"] == "DENY"
