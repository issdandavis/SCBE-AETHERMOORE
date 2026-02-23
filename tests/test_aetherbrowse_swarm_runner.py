from scripts.aetherbrowse_swarm_runner import _chunk_actions, _page_lock_id, _pqc_audit


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

