from api.audit_export import build_signed_bundle, filter_records_by_range, verify_manifest


def test_signed_bundle_and_manifest_verification_roundtrip():
    records = [
        {
            "decision_id": "dec_1",
            "timestamp": "2026-01-01T00:10:00Z",
            "decision_input_digest": "abc",
            "policy_version": "scbe-policy-v1",
            "layer_score_summary": {"layer_12_harmonic_score": 0.87},
            "final_decision": "ALLOW",
            "reason_codes": ["DECISION_ALLOW"],
            "previous_chain_hash": "GENESIS",
            "chain_hash": "hash1",
        }
    ]

    bundle, manifest = build_signed_bundle(
        tenant_id="tenant_0",
        from_ts="2026-01-01T00:00:00Z",
        to_ts="2026-01-01T01:00:00Z",
        records=records,
        signing_key="test-signing-key",
    )

    assert bundle["record_count"] == 1
    assert manifest["chain_head"] == "hash1"
    assert verify_manifest(bundle, manifest, "test-signing-key") is True


def test_filter_records_by_range_inclusive():
    records = [
        {"decision_id": "dec_a", "timestamp": "2026-01-01T00:00:00Z"},
        {"decision_id": "dec_b", "timestamp": "2026-01-01T01:00:00Z"},
        {"decision_id": "dec_c", "timestamp": "2026-01-01T02:00:00Z"},
    ]

    selected = filter_records_by_range(
        records,
        from_ts="2026-01-01T00:30:00Z",
        to_ts="2026-01-01T02:00:00Z",
    )

    assert [record["decision_id"] for record in selected] == ["dec_b", "dec_c"]
