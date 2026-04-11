from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from symphonic_cipher.scbe_aethermoore.turning_lane import (
    prepare_execution_packet,
    prove_execution_packet,
    run_turning_suite,
)


def test_turning_suite_passes_and_converges() -> None:
    summary = run_turning_suite()

    assert summary["status"] == "PASS"
    assert summary["convergence_score"] == 1.0
    assert summary["program_count"] >= 3
    assert all(program["status"] == "PASS" for program in summary["programs"])


def test_turning_exec_packet_proves_echo_family() -> None:
    packet = prepare_execution_packet("echo", ["turning lane"])
    proof = prove_execution_packet(packet, source_tongue="DR", witness_tongues=["KO", "AV", "UM"])

    assert packet["family"] == "echo"
    assert proof["status"] == "PASS"
    assert proof["transport"]["convergence_score"] == 1.0
    assert proof["packet_sha256"] == packet["packet_sha256"]


def test_turning_exec_rejects_python_script_outside_allowlist() -> None:
    with pytest.raises(ValueError):
        prepare_execution_packet("python-script", [str(Path(sys.executable).resolve())])


def test_scbe_cli_turning_exec_dry_run() -> None:
    cli_path = REPO_ROOT / "scbe-cli.py"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_path),
            "turning-exec",
            "--family",
            "echo",
            "--arg",
            "hello turning lane",
            "--dry-run",
            "--tongue",
            "RU",
            "--witnesses",
            "KO,AV,DR",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "DRY_RUN"
    assert payload["proof"]["status"] == "PASS"
    assert payload["proof"]["transport"]["convergence_score"] == 1.0


def test_scbe_cli_turning_test() -> None:
    cli_path = REPO_ROOT / "scbe-cli.py"
    result = subprocess.run(
        [sys.executable, str(cli_path), "turning-test"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["convergence_score"] == 1.0
