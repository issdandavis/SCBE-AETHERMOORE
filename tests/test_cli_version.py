"""Regression: the `scbe` version flag must print the package version and exit 0,
and must NEVER route into the AI/catalog/default-command path.

A version flag that emits a system overview is the exact "feels unprofessional"
bug this guards against.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPECTED = "4.2.1"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scbe.py", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )


def test_version_short_flag() -> None:
    result = _run("-V")
    assert result.returncode == 0
    assert EXPECTED in result.stdout
    # must short-circuit, not fall through to the assistant / `systems` catalog path
    assert "tongue" not in result.stdout.lower()
    assert "system" not in result.stdout.lower()


def test_version_long_flag() -> None:
    result = _run("--version")
    assert result.returncode == 0
    assert EXPECTED in result.stdout


def test_version_constant_matches() -> None:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    import scbe

    assert scbe.VERSION == EXPECTED
