"""Regression: the `scbe` version flag must print the package version and exit 0,
and must NEVER route into the AI/catalog/default-command path.

A version flag that emits a system overview is the exact "feels unprofessional"
bug this guards against.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Read the expected version from pyproject rather than hard-coding it. A literal here went
# stale at 4.3.0 across the 4.3.1 bump and failed three tests against correct code, which
# points the blame at the package instead of the test. Deriving it means a bump cannot
# desynchronise this file. pyproject is the single source of truth (see scbe._resolve_version).
with (REPO / "pyproject.toml").open("rb") as _fh:
    EXPECTED = tomllib.load(_fh)["project"]["version"]


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
