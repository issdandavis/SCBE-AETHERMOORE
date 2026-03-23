from datetime import datetime, timezone

from scripts.aetherbrowse_swarm_runner import (
    _build_layer14_telemetry,
    _build_packet_rails,
    _chunk_actions,
    _jobs,
    _normalize_lease,
    _page_lock_id,
    _pqc_audit,
    _verify,
)


def test_chunk_actions_splits_large_sequences() -> None:
    actions = [{"action": "extract", "target": f"#{i}"} for i in range(105)]
    chunks = _chunk_actions(actions, 40)
    assert len(chunks) == 3
    assert len(chunks[0]) == 40
    assert len(chunks[1]) == 40
    assert len(chunks[2]) == 25


def test_page_lock_id_normalizes_empty() -> None:
    assert _page_lock_id({}) is None
    assert _page_lock_id({"page_lock": ""}) is None
    assert _page_lock_id({"page_lock": "example.com:pricing"}) == "example.com:pricing"


def test_jobs_accepts_id_alias_for_job_id() -> None:
    parsed = _jobs(
        {
            "jobs": [
                {
                    "id": "paper-001",
                    "actions": [{"action": "navigate", "target": "https://example.com"}],
                }
            ]
        }
    )
    assert parsed[0]["job_id"] == "paper-001"


def test_verify_exact_navigate_detects_url_drift() -> None:
    job = {
        "actions": [{"action": "navigate", "target": "https://arxiv.org/abs/2402.05930"}],
        "verify": {"exact_navigate": True},
    }
    response = {
        "status": "success",
        "results": [
            {
                "action": "navigate",
                "target": "https://arxiv.org/abs/2402.05930",
                "success": True,
                "data": {"url": "https://arxiv.org/abs/2402.13718"},
                "containment": {"risk_score": 0.2, "radius": 0.4},
            }
        ],
    }
    verification = _verify(job, response)
    exact = next(check for check in verification["checks"] if check["check"] == "exact_navigate")
    assert exact["passed"] is False
    assert exact["mismatches"]


def test_verify_exact_navigate_passes_when_urls_match() -> None:
    job = {
        "actions": [{"action": "navigate", "target": "https://arxiv.org/abs/2402.05930"}],
        "verify": {"exact_navigate": True},
    }
    response = {
        "status": "success",
        "results": [
            {
                "action": "navigate",
                "target": "https://arxiv.org/abs/2402.05930",
                "success": True,
                "data": {"url": "https://arxiv.org/abs/2402.05930"},
                "containment": {"risk_score": 0.2, "radius": 0.4},
            }
        ],
    }
    verification = _verify(job, response)
    exact = next(check for check in verification["checks"] if check["check"] == "exact_navigate")
    assert exact["passed"] is True


def test_pqc_audit_enforces_missing_key_ids() -> None:
    result = _pqc_audit({"pqc": {"kyber_id": "", "dilithium_id": ""}}, {"workflow_id": "x"}, "DELIBERATION")
    assert result["status"] == "QUARANTINE"


def test_pqc_audit_enforces_rotation_policy() -> None:
    result = _pqc_audit(
        {
            "pqc": {
                "kyber_id": "kyber-1",
                "dilithium_id": "dili-1",
                "last_rotated_hours": 800,
                "rotation_hours": 720,
            }
        },
        {"workflow_id": "x"},
        "DELIBERATION",
    )
    assert result["status"] == "QUARANTINE"


def test_pqc_audit_allows_valid_metadata() -> None:
    result = _pqc_audit(
        {
            "pqc": {
                "kyber_id": "kyber-1",
                "dilithium_id": "dili-1",
                "last_rotated_hours": 1,
                "rotation_hours": 720,
                "drift_threshold": 0.999,
            }
        },
        {"workflow_id": "x"},
        "DELIBERATION",
    )
    assert result["status"] == "ALLOW"
    assert "key_fingerprint" in result


def test_normalize_lease_derives_owner_and_expiry() -> None:
    claimed_at = datetime(2026, 3, 18, 1, 30, tzinfo=timezone.utc)
    lease = _normalize_lease(
        {"job_id": "j1", "lease": {"provider": "colab", "resource_class": "t4", "lease_seconds": 600}},
        "worker-7",
        claimed_at=claimed_at,
    )
    assert lease is not None
    assert lease["owner"] == "worker-7"
    assert lease["provider"] == "colab"
    assert lease["resource_class"] == "t4"
    assert lease["claimed_at_utc"] == "2026-03-18T01:30:00Z"
    assert lease["expires_at_utc"] == "2026-03-18T01:40:00Z"


def test_build_packet_rails_splits_positive_and_negative_paths() -> None:
    job = {
        "actions": [
            {"action": "navigate", "target": "https://example.com"},
            {"action": "extract", "target": "#main"},
        ]
    }
    out = {
        "request_error": "chunk 1 status=request_error",
        "response": {"status": "request_error", "blocked_actions": 1, "total_actions": 2, "executed_actions": 1},
        "pqc_audit": {"status": "QUARANTINE", "reason": "rotation overdue"},
    }
    verification = {
        "verification_score": 0.5,
        "metrics": {"coherence": 0.8},
        "checks": [
            {"check": "action_success_1", "passed": True},
            {"check": "must_contain::ready", "passed": False},
        ],
    }
    antivirus_report = {"turnstile_action": "HOLD"}
    rails = _build_packet_rails(job, out, verification, "QUARANTINE", "trace-123", antivirus_report)
    assert rails["P+"][0]["action"] == "navigate"
    assert any(item["type"] == "request_error" for item in rails["P-"])
    assert any(item["type"] == "decision" for item in rails["D+"])
    assert any(item["type"] == "pqc_audit" for item in rails["D-"])
    assert any(item["type"] == "antivirus_turnstile" for item in rails["D-"])


def test_build_layer14_telemetry_projects_verification_state() -> None:
    response = {"total_actions": 4, "executed_actions": 3, "blocked_actions": 1}
    verification = {"verification_score": 0.75, "metrics": {"coherence": 0.9}}
    rails = {
        "P+": [{"type": "action"}],
        "P-": [{"type": "blocked_actions"}],
        "D+": [{"type": "decision"}, {"type": "trace_hash"}],
        "D-": [{"type": "verification_mismatch"}],
    }
    layer14 = _build_layer14_telemetry(response, verification, rails, "QUARANTINE")
    assert layer14["energy"] == 0.75
    assert layer14["centroid"] == 0.75
    assert layer14["hf_ratio"] == 0.25
    assert layer14["stability"] == 0.9
    assert layer14["signal_class"] == "quarantine"

