from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO_ROOT
    / "skills"
    / "scbe-playwright-ops-extension"
    / "scripts"
    / "playwright_extension_runner.py"
)


def _load_runner_module():
    spec = importlib.util.spec_from_file_location(
        "playwright_extension_runner", RUNNER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runner_help_smoke() -> None:
    result = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--url" in result.stdout
    assert "--skip-crosstalk" in result.stdout
    assert "--emit-notion-payload" in result.stdout


def test_handoff_writer_creates_expected_sections(tmp_path: Path) -> None:
    module = _load_runner_module()
    handoff_path = tmp_path / "handoff.md"
    module._write_handoff(
        path=handoff_path,
        task_id="PWX-UNIT",
        url="https://example.com",
        summary="unit",
        files_touched=[tmp_path / "a.json"],
        crosstalk_packet_id="pkt-1",
    )

    content = handoff_path.read_text(encoding="utf-8")
    assert "# Handoff: PWX-UNIT" in content
    assert "## Files Touched" in content
    assert "## Next Steps" in content
