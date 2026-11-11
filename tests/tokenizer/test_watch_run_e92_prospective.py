from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.tokenizer.watch_run_e92_prospective import run_cycle


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(str(value), encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, audit_ready: bool, labels: bool) -> dict:
    queue = _write(tmp_path / "scan" / "REVIEW_QUEUE.json", {"queue": True})
    audit = _write(tmp_path / "audit" / "QUEUE_SELECTION_AUDIT.json", {"audit": True})
    packet = tmp_path / "packet"
    receipt = _write(packet / "PREPARATION_RECEIPT.json", {"receipt": True})
    inventory = _write(packet / "CATALOG_SOURCE_SUFFIXES.json", {"sources": []})
    database = _write(tmp_path / "catalog.sqlite3", "catalog")
    integrity = _write(tmp_path / "INTEGRITY_AUDIT.json", {"integrity": True})
    runner = _write(tmp_path / "run.py", "# runner")
    verifier = _write(tmp_path / "verify.py", "# verifier")
    labels_path = tmp_path / "REVIEW_LABELS.json"
    if labels:
        _write(labels_path, {"labels": []})

    collector = {
        "schema": "clay.codex-prospective-watcher.v1",
        "status": "READY_FOR_HUMAN_HASH_BOUND_REVIEW",
        "candidate_count": 30,
        "catalog_boundary": {"catalog_sha256": _sha(database)},
    }
    preparer = {
        "schema": "clay.prime-token-preparer-watcher.v1",
        "status": "PACKET_READY_NO_SCORING",
        "queue": str(queue),
        "queue_file_sha256": _sha(queue),
        "output_dir": str(packet),
        "receipt_file_sha256": _sha(receipt),
        "source_inventory_file_sha256": _sha(inventory),
    }
    selection = {
        "schema": "clay.prime-token-selection-audit-watcher.v1",
        "status": ("AUDIT_VERIFIED_NO_SCORING" if audit_ready else "WAITING_FOR_PROSPECTIVE_QUEUE"),
        "queue_file_sha256": _sha(queue),
        "output": str(audit),
        "audit_file_sha256": _sha(audit),
    }
    return {
        "collector_status_path": _write(tmp_path / "collector.json", collector),
        "preparer_status_path": _write(tmp_path / "preparer.json", preparer),
        "selection_status_path": _write(tmp_path / "selection.json", selection),
        "labels_path": labels_path,
        "catalog_database": database,
        "catalog_database_sha256": _sha(database),
        "catalog_integrity_audit": integrity,
        "catalog_integrity_audit_sha256": _sha(integrity),
        "runner": runner,
        "runner_sha256": _sha(runner),
        "verifier": verifier,
        "verifier_sha256": _sha(verifier),
        "output_dir": tmp_path / "result",
        "state_dir": tmp_path / "state",
        "control_seeds": (3, 5, 7),
        "limit": 20,
        "python_executable": "python",
    }


def test_selection_audit_blocks_labels_from_opening(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, audit_ready=False, labels=True)

    status = run_cycle(**kwargs)

    assert status["status"] == "WAITING_FOR_EXACT_SELECTION_AUDIT"
    assert status["labels"] == "NOT_OPENED"


def test_ready_authorities_wait_for_missing_human_labels(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, audit_ready=True, labels=False)

    status = run_cycle(**kwargs)

    assert status["status"] == "WAITING_FOR_INDEPENDENT_LABELS"
    assert status["labels"] == "NOT_PRESENT"
    assert status["promotion"] == "NOT_AUTHORIZED"


def test_ready_chain_runs_exact_runner_then_independent_verifier(
    tmp_path: Path,
) -> None:
    kwargs = _fixture(tmp_path, audit_ready=True, labels=True)
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "--selection-audit" in command:
            output = Path(command[command.index("--output-dir") + 1])
            output.mkdir()
            _write(output / "RUN_RECEIPT.json", {"run": True})
        else:
            output = Path(command[command.index("--output") + 1])
            _write(
                output,
                {
                    "status": "VERIFIED_E92_PROSPECTIVE_NO_AUTOMATIC_PROMOTION",
                    "query_count": 30,
                    "error_count": 0,
                    "training_intake": "NOT_AUTHORIZED",
                    "serving": "NOT_AUTHORIZED",
                    "merge": "NOT_AUTHORIZED",
                    "promotion": "NOT_AUTHORIZED",
                },
            )
        return subprocess.CompletedProcess(command, 0, "ok", "")

    status = run_cycle(**kwargs, run_command=fake_run)

    assert len(commands) == 2
    assert "--selection-audit" in commands[0]
    assert commands[0].count("--control-seed") == 3
    assert status["status"] == "E92_RESULT_INDEPENDENTLY_VERIFIED"
    assert status["query_count"] == 30
    assert status["training_intake"] == "NOT_AUTHORIZED"
    assert status["promotion"] == "NOT_AUTHORIZED"


def test_hash_drift_fails_before_labels_or_runner(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, audit_ready=True, labels=True)
    kwargs["catalog_database"].write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="catalog database hash mismatch"):
        run_cycle(**kwargs)
