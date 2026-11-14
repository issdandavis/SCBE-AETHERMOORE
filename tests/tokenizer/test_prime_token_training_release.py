from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.tokenizer.audit_prime_token_training_release import audit_release

ARMS = [
    "no_intervention",
    "lexical_only_reader",
    "canonical_six_view_reader",
    "random_fixed_reader",
    "shuffled_binding_reader",
    "single_frame_reader",
]
METRICS = [
    "accuracy",
    "relationship",
    "function",
    "ordinary_false_activation",
    "frozen_parent_retention",
    "throughput",
    "peak_memory",
    "checkpoint_bytes",
]
EVIDENCE = {
    "storage_envelope": ["SPACE_ENVELOPE_OPEN"],
    "prospective_collector": ["READY_FOR_REVIEW"],
    "query_session_family_component_gate": [
        "QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED"
    ],
    "selection_audit": ["VERIFIED_SELECTION_AUDIT"],
    "e92_result": ["COMPLETE"],
    "e92_independent_verification": ["VERIFIED"],
    "source_family_gate": ["VERIFIED_SOURCE_FAMILY_DIVERSITY"],
    "source_disjoint_split": ["VERIFIED_SOURCE_DISJOINT_SPLIT"],
    "preregistration": ["FROZEN"],
    "runner_implementation": ["TESTED"],
    "independent_replay_implementation": ["TESTED"],
    "evidence_aggregator_implementation": ["TESTED"],
    "material_runtime_implementation": ["TESTED"],
}
COMPONENT_AUTHORITY = {
    "scoring": "NOT_AUTHORIZED",
    "training_intake": "NOT_AUTHORIZED",
    "execution": "NONE",
    "merge": "NOT_AUTHORIZED",
    "promotion": "NOT_AUTHORIZED",
    "partial_unfreeze": "NONE",
}


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _canonical(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _component_watcher(tmp_path: Path) -> Path:
    split = {
        "fold_names": ["fold-0", "fold-1", "fold-2"],
        "components": [
            {"component_id": "component-0", "fold": "fold-0", "query_count": 10},
            {"component_id": "component-1", "fold": "fold-1", "query_count": 10},
            {"component_id": "component-2", "fold": "fold-2", "query_count": 10},
        ],
        "folds": {
            "fold-0": {"component_count": 1, "query_count": 10},
            "fold-1": {"component_count": 1, "query_count": 10},
            "fold-2": {"component_count": 1, "query_count": 10},
        },
    }
    report = {
        "schema": "scbe.prime-token-query-session-family-components.v1",
        "status": "VERIFIED_QUERY_SESSION_FAMILY_COMPONENT_SPLIT",
        "error_count": 0,
        **split,
        "component_split_sha256": _canonical(split),
        "gates": {
            "minimum_accepted_queries": True,
            "minimum_query_sessions": True,
            "minimum_manifest_bound_families": True,
            "minimum_indivisible_components": True,
            "all_folds_nonempty": True,
            "maximum_component_share": True,
            "zero_query_session_overlap": True,
            "zero_target_family_overlap": True,
        },
        "authority": dict(COMPONENT_AUTHORITY),
    }
    report["report_sha256"] = _canonical(report)
    report_path = _write(tmp_path / "component-report.json", report)
    watcher = {
        "schema": "scbe.prime-token-query-session-family-component-watcher.v1",
        "status": "QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED",
        "gate_result": "VERIFIED_QUERY_SESSION_FAMILY_COMPONENT_SPLIT",
        "gate_report": str(report_path),
        "gate_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "component_split_sha256": report["component_split_sha256"],
        "authority": dict(COMPONENT_AUTHORITY),
        **COMPONENT_AUTHORITY,
    }
    return _write(tmp_path / "query_session_family_component_gate.json", watcher)


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    contract = _write(
        tmp_path / "contract.json",
        {
            "schema": "scbe.prime-token-frozen-input-access-release-contract.v1",
            "contract_id": "contract-v1",
            "minimums": {
                "accepted_final_test_queries": 30,
                "canonical_catalog_sources": 6,
                "closed_query_source_sessions": 3,
                "fresh_seeds": 3,
                "manifest_bound_catalog_families": 3,
            },
            "required_arms": ARMS,
            "required_metrics": METRICS,
            "required_evidence": EVIDENCE,
        },
    )
    evidence = {}
    for evidence_id, statuses in EVIDENCE.items():
        artifact = (
            _component_watcher(tmp_path)
            if evidence_id == "query_session_family_component_gate"
            else _write(tmp_path / f"{evidence_id}.json", {"status": statuses[0]})
        )
        entry = {
            "status": statuses[0],
            "path": str(artifact),
        }
        if evidence_id == "query_session_family_component_gate":
            entry["read_status_from_artifact"] = True
        else:
            entry["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            entry["immutable"] = True
        evidence[evidence_id] = entry
    state = _write(
        tmp_path / "state.json",
        {
            "schema": "scbe.prime-token-frozen-input-access-release-state.v1",
            "contract_id": "contract-v1",
            "observed": {
                "accepted_final_test_queries": 30,
                "canonical_catalog_sources": 6,
                "closed_query_source_sessions": 3,
                "fresh_seeds": 3,
                "manifest_bound_catalog_families": 3,
            },
            "seeds": [101, 102, 103],
            "arms": ARMS,
            "metrics": METRICS,
            "evidence": evidence,
            "authority": {
                "training_intake": "NOT_AUTHORIZED",
                "merge": "NOT_AUTHORIZED",
                "promotion": "NOT_AUTHORIZED",
                "partial_unfreeze": "NONE",
                "tool_dispatch": "DISABLED",
            },
        },
    )
    return contract, state


def test_ready_state_still_grants_no_authority(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW"
    assert report["error_count"] == 0
    assert report["blocker_count"] == 0
    assert report["authority"]["training_intake"] == "NOT_AUTHORIZED"
    assert report["authority"]["partial_unfreeze"] == "NONE"


def test_shipped_contract_requires_query_session_family_component_gate() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            repo_root
            / "config/training/prime_token_frozen_input_access_release_v1.json"
        ).read_text(encoding="utf-8")
    )

    assert contract["required_evidence"]["query_session_family_component_gate"] == [
        "QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED"
    ]


def test_waits_for_closed_query_sources_and_candidates(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    value["observed"]["accepted_final_test_queries"] = 0
    value["observed"]["closed_query_source_sessions"] = 0
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "WAITING_FOR_RELEASE_REQUIREMENTS"
    assert report["error_count"] == 0
    assert any(
        "accepted_final_test_queries" in blocker for blocker in report["blockers"]
    )
    assert any(
        "closed_query_source_sessions" in blocker for blocker in report["blockers"]
    )


def test_rejects_mutated_immutable_evidence(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    artifact = Path(value["evidence"]["preregistration"]["path"])
    artifact.write_text('{"status":"CHANGED"}', encoding="utf-8")

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert "sha256 mismatch for preregistration" in report["errors"]


def test_rejects_state_status_that_disagrees_with_hashed_artifact(
    tmp_path: Path,
) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    evidence = value["evidence"]["independent_replay_implementation"]
    artifact = Path(evidence["path"])
    artifact.write_text('{"status":"TESTED_NO_PROMOTION"}', encoding="utf-8")
    evidence["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert (
        "state/artifact status mismatch for independent_replay_implementation"
        in report["errors"]
    )
    gate = report["gates"]["evidence"]["independent_replay_implementation"]
    assert gate["status"] == "TESTED_NO_PROMOTION"
    assert gate["passed"] is False


def test_requires_material_runtime_and_evidence_aggregator(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    del value["evidence"]["material_runtime_implementation"]
    del value["evidence"]["evidence_aggregator_implementation"]
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "WAITING_FOR_RELEASE_REQUIREMENTS"
    assert report["error_count"] == 0
    assert "missing evidence: material_runtime_implementation" in report["blockers"]
    assert "missing evidence: evidence_aggregator_implementation" in report["blockers"]


def test_requires_query_session_family_component_gate(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    del value["evidence"]["query_session_family_component_gate"]
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "WAITING_FOR_RELEASE_REQUIREMENTS"
    assert report["error_count"] == 0
    assert "missing evidence: query_session_family_component_gate" in report["blockers"]


@pytest.mark.parametrize(
    "dynamic_status",
    [
        "WAITING_FOR_PREPARATION_PACKET",
        "QUERY_SESSION_FAMILY_COMPONENT_GATE_UNDERPOWERED",
        "QUERY_SESSION_FAMILY_COMPONENT_GATE_INVALID_NEEDS_REVIEW",
    ],
)
def test_reads_component_gate_status_from_dynamic_artifact(
    tmp_path: Path, dynamic_status: str
) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    evidence = value["evidence"]["query_session_family_component_gate"]
    artifact = Path(evidence["path"])
    artifact_value = json.loads(artifact.read_text(encoding="utf-8"))
    artifact_value["status"] = dynamic_status
    artifact.write_text(json.dumps(artifact_value), encoding="utf-8")
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "WAITING_FOR_RELEASE_REQUIREMENTS"
    assert report["error_count"] == 0
    gate = report["gates"]["evidence"]["query_session_family_component_gate"]
    assert gate["status"] == dynamic_status
    assert gate["passed"] is False
    assert (
        f"query_session_family_component_gate status is {dynamic_status}"
        in report["blockers"]
    )


def test_rejects_component_verified_status_without_report_binding(
    tmp_path: Path,
) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    artifact = Path(value["evidence"]["query_session_family_component_gate"]["path"])
    watcher = json.loads(artifact.read_text(encoding="utf-8"))
    watcher.pop("gate_report_sha256")
    artifact.write_text(json.dumps(watcher), encoding="utf-8")

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert "component gate component report file hash mismatch" in report["errors"]


def test_rejects_component_report_or_split_digest_drift(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    artifact = Path(value["evidence"]["query_session_family_component_gate"]["path"])
    watcher = json.loads(artifact.read_text(encoding="utf-8"))
    component_report = Path(watcher["gate_report"])
    component_value = json.loads(component_report.read_text(encoding="utf-8"))
    component_value["folds"]["fold-0"]["query_count"] = 11
    component_report.write_text(json.dumps(component_value), encoding="utf-8")
    watcher["gate_report_sha256"] = hashlib.sha256(
        component_report.read_bytes()
    ).hexdigest()
    artifact.write_text(json.dumps(watcher), encoding="utf-8")

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert "component gate component split digest does not replay" in report["errors"]
    assert "component gate component report digest does not replay" in report["errors"]


def test_rejects_component_watcher_authority_drift(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    artifact = Path(value["evidence"]["query_session_family_component_gate"]["path"])
    watcher = json.loads(artifact.read_text(encoding="utf-8"))
    watcher["authority"]["training_intake"] = "AUTHORIZED"
    artifact.write_text(json.dumps(watcher), encoding="utf-8")

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert (
        "component gate watcher authority differs from the fail-closed contract"
        in report["errors"]
    )


def test_rejects_authority_drift(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    value["authority"]["training_intake"] = "AUTHORIZED"
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert "state authority drifted for training_intake" in report["errors"]
