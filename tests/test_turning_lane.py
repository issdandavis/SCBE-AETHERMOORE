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
    build_atomic_execution_bundle,
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
    assert proof["atomic_precheck"]["status"] in {"PASS", "WARN"}
    assert proof["atomic_precheck"]["token_count"] >= 1
    assert proof["atomic_precheck"]["rhombic"]["score"] >= 0.0
    assert proof["atomic_precheck"]["history_reducer"]["trust_level"] > 0.0
    assert proof["atomic_precheck"]["history_reducer"]["drift_norm"] >= 0.0


def test_turning_exec_atomic_bundle_emits_features_and_trits() -> None:
    packet = prepare_execution_packet("pytest-targeted", ["tests/test_turning_lane.py"])
    bundle = build_atomic_execution_bundle(packet)

    assert bundle["status"] in {"PASS", "WARN"}
    assert bundle["token_count"] == len(bundle["tokens"])
    assert len(bundle["atomic_features"]) == bundle["token_count"]
    assert len(bundle["trit_vectors"]) == bundle["token_count"]
    assert all(len(row) == 8 for row in bundle["atomic_features"])
    assert all(len(row) == 6 for row in bundle["trit_vectors"])
    assert "tau_hat" in bundle["chemical_fusion"]
    assert "score" in bundle["rhombic"]
    assert "history_reducer" in bundle
    assert bundle["history_reducer"]["trust_level"] > 0.0
    assert bundle["history_reducer"]["drift_norm"] >= 0.0
    assert "drift_components" in bundle["history_reducer"]
    assert "lane_alignment" in bundle["history_reducer"]
    assert "checkpoint" in bundle["history_reducer"]
    assert "negative_states" in bundle
    assert "dual_states" in bundle
    assert bundle["history_reducer"]["lane_alignment"]["failure_mode"] in {
        "none",
        "no_code_lane_bound",
    }


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
    assert payload["proof"]["atomic_precheck"]["status"] in {"PASS", "WARN"}


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
