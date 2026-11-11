from __future__ import annotations

import hashlib
import json
from pathlib import Path

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
    "selection_audit": ["VERIFIED_SELECTION_AUDIT"],
    "e92_result": ["COMPLETE"],
    "e92_independent_verification": ["VERIFIED"],
    "source_family_gate": ["VERIFIED_SOURCE_FAMILY_DIVERSITY"],
    "source_disjoint_split": ["VERIFIED_SOURCE_DISJOINT_SPLIT"],
    "preregistration": ["FROZEN"],
    "runner_implementation": ["TESTED"],
    "independent_replay_implementation": ["TESTED"],
}


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


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
        artifact = _write(tmp_path / f"{evidence_id}.json", {"status": statuses[0]})
        evidence[evidence_id] = {
            "status": statuses[0],
            "path": str(artifact),
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "immutable": True,
        }
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


def test_waits_for_closed_query_sources_and_candidates(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    value["observed"]["accepted_final_test_queries"] = 0
    value["observed"]["closed_query_source_sessions"] = 0
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "WAITING_FOR_RELEASE_REQUIREMENTS"
    assert report["error_count"] == 0
    assert any("accepted_final_test_queries" in blocker for blocker in report["blockers"])
    assert any("closed_query_source_sessions" in blocker for blocker in report["blockers"])


def test_rejects_mutated_immutable_evidence(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    artifact = Path(value["evidence"]["preregistration"]["path"])
    artifact.write_text('{"status":"CHANGED"}', encoding="utf-8")

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert "sha256 mismatch for preregistration" in report["errors"]


def test_rejects_authority_drift(tmp_path: Path) -> None:
    contract, state = _fixture(tmp_path)
    value = json.loads(state.read_text(encoding="utf-8"))
    value["authority"]["training_intake"] = "AUTHORIZED"
    _write(state, value)

    report = audit_release(contract_path=contract, state_path=state)

    assert report["status"] == "INVALID_RELEASE_STATE"
    assert "state authority drifted for training_intake" in report["errors"]
