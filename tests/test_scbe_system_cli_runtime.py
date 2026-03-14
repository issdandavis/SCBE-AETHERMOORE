from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def _run_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_runtime_run_executes_inline_python_and_writes_artifact(tmp_path: Path) -> None:
    out_dir = tmp_path / "runtime-out"
    result = _run_cli(
        "runtime",
        "run",
        "--language",
        "python",
        "--tongue",
        "CA",
        "--code",
        "print('hello-runtime')",
        "--output-dir",
        str(out_dir),
    )

    assert result.returncode == 0, result.stderr
    assert "hello-runtime" in result.stdout

    artifacts = list(out_dir.glob("*_runtime.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["tongue"] == "CA"
    assert payload["command_metadata"]["lexicon_attestation"]
    assert payload["source_metadata"]["kind"] == "inline"


def test_runtime_run_rejects_external_source_paths(tmp_path: Path) -> None:
    external_dir = Path.home() / "AppData" / "Local" / "Temp"
    external_dir.mkdir(parents=True, exist_ok=True)
    external_file = external_dir / f"scbe-external-{uuid.uuid4().hex[:8]}.py"
    external_file.write_text("print('outside')\n", encoding="utf-8")

    try:
        result = _run_cli(
            "runtime",
            "run",
            "--language",
            "python",
            "--file",
            str(external_file),
            "--output-dir",
            str(tmp_path / "runtime-out"),
        )

        assert result.returncode == 2
        assert "outside the controlled SCBE workspace" in result.stdout
    finally:
        external_file.unlink(missing_ok=True)


def test_pollypad_app_run_executes_installed_local_script(tmp_path: Path) -> None:
    pad_root = tmp_path / "pads"
    out_dir = tmp_path / "runtime-out"
    script_path = tmp_path / "hello_app.py"
    script_path.write_text("print('pad-app-ok')\n", encoding="utf-8")

    init_result = _run_cli(
        "pollypad",
        "--agent-root",
        str(pad_root),
        "init",
        "--agent-id",
        "agent-1",
        "--name",
        "Agent One",
    )
    assert init_result.returncode == 0, init_result.stderr

    install_result = _run_cli(
        "pollypad",
        "--agent-root",
        str(pad_root),
        "app",
        "install",
        "--agent-id",
        "agent-1",
        "--name",
        "hello",
        "--entrypoint",
        "python",
        "--script",
        str(script_path),
    )
    assert install_result.returncode == 0, install_result.stderr

    run_result = _run_cli(
        "pollypad",
        "--agent-root",
        str(pad_root),
        "app",
        "run",
        "--agent-id",
        "agent-1",
        "--name",
        "hello",
        "--output-dir",
        str(out_dir),
    )
    assert run_result.returncode == 0, run_result.stderr
    assert "pad-app-ok" in run_result.stdout

    artifacts = list(out_dir.glob("*_runtime.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert payload["app"]["name"] == "hello"
    assert payload["mode"] == "app"
