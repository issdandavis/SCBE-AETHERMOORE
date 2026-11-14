from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

import pytest

from scripts.tokenizer.watch_prime_query_family_components import (
    AUTHORITY,
    REPORT_INVALID,
    REPORT_UNDERPOWERED,
    REPORT_VERIFIED,
    run_cycle,
)


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(str(value), encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _fixture(tmp_path: Path, *, ready: bool = True, labels: bool = True) -> dict[str, Any]:
    scan = tmp_path / "scan"
    packet = tmp_path / "packet"
    queue = _write(scan / "REVIEW_QUEUE.json", {"queue": "sealed"})
    inventory = _write(packet / "CATALOG_SOURCE_SUFFIXES.json", {"sources": []})
    source_audit = _write(tmp_path / "SOURCE_FAMILY_AUDIT.json", {"families": []})
    auditor = _write(tmp_path / "audit.py", "# pinned component auditor\n")
    labels_path = tmp_path / "REVIEW_LABELS.json"
    if labels:
        _write(labels_path, {"labels": []})
    preparer = {
        "schema": "clay.prime-token-preparer-watcher.v1",
        "status": "PACKET_READY_NO_SCORING" if ready else "WAITING_FOR_PROSPECTIVE_QUEUE",
        "candidate_count": 30 if ready else 4,
        "output_dir": str(packet),
        "queue": str(queue),
        "queue_file_sha256": _sha(queue),
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


def _values(command: list[str], flag: str) -> list[str]:
    return [command[index + 1] for index, value in enumerate(command[:-1]) if value == flag]


def _fake_auditor(
    report_status: str,
    *,
    returncode: int | None = None,
    tamper_report_hash: bool = False,
) -> Callable[[list[str]], subprocess.CompletedProcess[str]]:
    expected_codes = {REPORT_VERIFIED: 0, REPORT_INVALID: 1, REPORT_UNDERPOWERED: 2}

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        output = Path(_values(command, "--output")[0])
        queue = Path(_values(command, "--review-queue")[0])
        labels = Path(_values(command, "--review-labels")[0])
        inventory = Path(_values(command, "--source-inventory")[0])
        source_audit = Path(_values(command, "--source-family-audit")[0])
        folds = _values(command, "--fold-name")
        minimum_queries = int(_values(command, "--minimum-accepted-queries")[0])
        minimum_sessions = int(_values(command, "--minimum-sessions")[0])
        minimum_families = int(_values(command, "--minimum-families")[0])
        maximum_share = float(_values(command, "--maximum-component-share")[0])
        split = {
            "fold_names": folds,
            "components": [{"component_id": "component-0", "fold": folds[0], "query_count": minimum_queries}],
            "folds": {name: {"component_count": 1, "query_count": minimum_queries} for name in folds},
        }
        gates = {
            "minimum_accepted_queries": True,
            "minimum_query_sessions": True,
            "minimum_manifest_bound_families": True,
            "minimum_indivisible_components": True,
            "all_folds_nonempty": True,
            "maximum_component_share": True,
            "zero_query_session_overlap": True,
            "zero_target_family_overlap": True,
        }
        errors: list[str] = []
        if report_status == REPORT_UNDERPOWERED:
            gates["minimum_accepted_queries"] = False
        elif report_status == REPORT_INVALID:
            errors.append("synthetic invalid fixture")
        report = {
            "schema": "scbe.prime-token-query-session-family-components.v1",
            "created_at_utc": "2026-11-14T00:00:00+00:00",
            "status": report_status,
            "error_count": len(errors),
            "errors": errors,
            "inputs": {
                "review_queue_sha256": _sha(queue),
                "review_labels_sha256": _sha(labels),
                "source_inventory_sha256": _sha(inventory),
                "source_family_audit_sha256": _sha(source_audit),
            },
            "thresholds": {
                "minimum_accepted_queries": minimum_queries,
                "minimum_query_sessions": minimum_sessions,
                "minimum_manifest_bound_families": minimum_families,
                "minimum_indivisible_components": len(folds),
                "maximum_component_share": maximum_share,
            },
            "observed": {"accepted_query_count": minimum_queries},
            **split,
            "component_split_sha256": _canonical(split),
            "gates": gates,
            "authority": dict(AUTHORITY),
            "claim_boundary": "test fixture",
        }
        report["report_sha256"] = _canonical(report)
        if tamper_report_hash:
            report["observed"]["accepted_query_count"] += 1
        _write(output, report)
        code = expected_codes[report_status] if returncode is None else returncode
        return subprocess.CompletedProcess(command, code, "ok", "")

    return run


def _must_not_run(command: list[str]) -> subprocess.CompletedProcess[str]:
    raise AssertionError(f"auditor unexpectedly ran: {command}")


def test_waits_without_opening_labels_until_both_upstreams_are_ready(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, ready=False, labels=True)

    status = run_cycle(**kwargs, run_command=_must_not_run)

    assert status["status"] == "WAITING_FOR_PREPARATION_PACKET"
    assert status["labels"] == "NOT_OPENED"
    assert status["training_intake"] == "NOT_AUTHORIZED"


def test_waits_for_missing_independent_labels(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path, labels=False)

    status = run_cycle(**kwargs, run_command=_must_not_run)

    assert status["status"] == "WAITING_FOR_INDEPENDENT_LABELS"
    assert status["labels"] == "NOT_PRESENT"
    assert status["promotion"] == "NOT_AUTHORIZED"


def test_runs_pinned_component_auditor_and_seals_verified_report(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)

    status = run_cycle(**kwargs, run_command=_fake_auditor(REPORT_VERIFIED))

    assert status["status"] == "QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED"
    assert status["gate_result"] == REPORT_VERIFIED
    assert status["authority"] == AUTHORITY
    assert status["training_intake"] == "NOT_AUTHORIZED"
    assert status["partial_unfreeze"] == "NONE"
    assert (kwargs["state_dir"] / "QUERY_SESSION_FAMILY_COMPONENTS.json").is_file()
    assert not (kwargs["state_dir"] / ".QUERY_SESSION_FAMILY_COMPONENTS.pending.json").exists()


@pytest.mark.parametrize(
    ("report_status", "watcher_status"),
    [
        (REPORT_UNDERPOWERED, "QUERY_SESSION_FAMILY_COMPONENT_GATE_UNDERPOWERED"),
        (REPORT_INVALID, "QUERY_SESSION_FAMILY_COMPONENT_GATE_INVALID_NEEDS_REVIEW"),
    ],
)
def test_preserves_nonpassing_terminal_evidence(
    tmp_path: Path,
    report_status: str,
    watcher_status: str,
) -> None:
    kwargs = _fixture(tmp_path)

    status = run_cycle(**kwargs, run_command=_fake_auditor(report_status))

    assert status["status"] == watcher_status
    assert status["promotion"] == "NOT_AUTHORIZED"
    assert status["scoring"] == "NOT_AUTHORIZED"


def test_hash_drift_fails_before_component_auditor_runs(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)
    kwargs["auditor"].write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="component auditor hash mismatch"):
        run_cycle(**kwargs, run_command=_must_not_run)


def test_pending_report_stops_without_overwrite_or_auditor_call(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)
    pending = kwargs["state_dir"] / ".QUERY_SESSION_FAMILY_COMPONENTS.pending.json"
    _write(pending, {"partial": True})

    status = run_cycle(**kwargs, run_command=_must_not_run)

    assert status["status"] == "PENDING_COMPONENT_REPORT_REQUIRES_AUDIT"
    assert json.loads(pending.read_text(encoding="utf-8")) == {"partial": True}


def test_existing_report_is_revalidated_and_label_drift_fails_closed(tmp_path: Path) -> None:
    kwargs = _fixture(tmp_path)
    first = run_cycle(**kwargs, run_command=_fake_auditor(REPORT_VERIFIED))

    second = run_cycle(**kwargs, run_command=_must_not_run)
    assert second["gate_report_sha256"] == first["gate_report_sha256"]

    _write(kwargs["labels_path"], {"labels": [], "changed": True})
    with pytest.raises(RuntimeError, match="review_labels_sha256"):
        run_cycle(**kwargs, run_command=_must_not_run)


def test_report_digest_and_return_code_mismatches_fail_closed(tmp_path: Path) -> None:
    digest_kwargs = _fixture(tmp_path / "digest")
    with pytest.raises(RuntimeError, match="report digest"):
        run_cycle(**digest_kwargs, run_command=_fake_auditor(REPORT_VERIFIED, tamper_report_hash=True))

    code_kwargs = _fixture(tmp_path / "code")
    with pytest.raises(RuntimeError, match="return code disagrees"):
        run_cycle(**code_kwargs, run_command=_fake_auditor(REPORT_VERIFIED, returncode=2))
