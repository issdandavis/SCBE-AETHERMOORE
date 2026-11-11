from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.tokenizer.watch_audit_e92_source_family_gate import run_cycle


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(str(value), encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, ready: bool = True, labels: bool = True) -> dict:
    packet = tmp_path / "packet"
    inventory = _write(packet / "CATALOG_SOURCE_SUFFIXES.json", {"sources": []})
    source_audit = _write(tmp_path / "SOURCE_FAMILY_AUDIT.json", {"verified": True})
    auditor = _write(tmp_path / "audit.py", "# auditor")
    labels_path = tmp_path / "REVIEW_LABELS.json"
    if labels:
        _write(labels_path, {"labels": []})
    preparer = {
        "schema": "clay.prime-token-preparer-watcher.v1",
        "status": "PACKET_READY_NO_SCORING" if ready else "WAITING_FOR_PROSPECTIVE_QUEUE",
        "candidate_count": 30 if ready else 0,
        "output_dir": str(packet),
        "source_inventory_file_sha256": _sha(inventory),
    }
    selection = {
        "schema": "clay.prime-token-selection-audit-watcher.v1",
        "status": "AUDIT_VERIFIED_NO_SCORING" if ready else "WAITING_FOR_PROSPECTIVE_QUEUE",
    }
    return {
        "preparer_status_path": _write(tmp_path / "preparer.json", preparer),
        "selection_status_path": _write(tmp_path / "selection.json", selection),
        "labels_path": labels_path,
        "source_family_audit": source_audit,
        "source_family_audit_sha256": _sha(source_audit),
        "auditor": auditor,
        "auditor_sha256": _sha(auditor),
        "state_dir": tmp_path / "state",
        "python_executable": "python",
    }


def _fake_auditor(status: str, returncode: int):
    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        output = Path(command[command.index("--output") + 1])
        source_audit = Path(command[command.index("--source-family-audit") + 1])
        inventory = Path(command[command.index("--source-inventory") + 1])
        labels = Path(command[command.index("--labels") + 1])
        _write(
            output,
            {
                "schema": "clay.e92-source-family-gate.v1",
                "status": status,
                "error_count": 0,
                "inputs": {
                    "source_family_audit_sha256": _sha(source_audit),
                    "source_inventory_sha256": _sha(inventory),
                    "labels_sha256": _sha(labels),
                },
                "observed": {"canonical_source_count": 6 if returncode == 0 else 1},
                "authority": {
                    "scoring": "NOT_AUTHORIZED",
                    "training_intake": "NOT_AUTHORIZED",
                    "merge": "NOT_AUTHORIZED",
                    "promotion": "NOT_AUTHORIZED",
                },
            },
        )
        return subprocess.CompletedProcess(command, returncode, "ok", "")

    return run


def test_waits_without_opening_labels_until_preparation_and_selection(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, ready=False, labels=True)

    status = run_cycle(**kwargs)

    assert status["status"] == "WAITING_FOR_PREPARATION_PACKET"
    assert status["labels"] == "NOT_OPENED"


def test_waits_for_missing_independent_labels(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, labels=False)

    status = run_cycle(**kwargs)

    assert status["status"] == "WAITING_FOR_INDEPENDENT_LABELS"
    assert status["promotion"] == "NOT_AUTHORIZED"


def test_runs_pinned_gate_and_closes_verified_without_authority(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)

    status = run_cycle(
        **kwargs,
        run_command=_fake_auditor("VERIFIED_SOURCE_FAMILY_DIVERSITY", 0),
    )

    assert status["status"] == "SOURCE_FAMILY_GATE_VERIFIED"
    assert status["observed"]["canonical_source_count"] == 6
    assert status["training_intake"] == "NOT_AUTHORIZED"
    assert status["promotion"] == "NOT_AUTHORIZED"


def test_preserves_underpowered_result_as_terminal_evidence(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)

    status = run_cycle(
        **kwargs,
        run_command=_fake_auditor("SOURCE_FAMILY_DIVERSITY_UNDERPOWERED", 2),
    )

    assert status["status"] == "SOURCE_FAMILY_GATE_UNDERPOWERED"
    assert status["observed"]["canonical_source_count"] == 1
    assert status["training_intake"] == "NOT_AUTHORIZED"


def test_hash_drift_fails_before_auditor_runs(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)
    kwargs["source_family_audit"].write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="source-family audit hash mismatch"):
        run_cycle(**kwargs)
