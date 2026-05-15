from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def test_parallel_web_capture_fails_closed_as_unsupported() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(ROOT),
            "--json",
            "web",
            "--json",
            "--engine",
            "parallel",
            "capture",
            "--url",
            "https://example.com",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_parallel_web_error_v1"
    assert payload["engine"] == "parallel"
    assert "supports only" in payload["error"]
