# Audit Export & Offline Integrity Verification

SCBE-AETHERMOORE now exposes a signed audit export endpoint:

```http
GET /audit/export?from=2026-01-01T00:00:00Z&to=2026-01-31T23:59:59Z
SCBE_api_key: <tenant-api-key>
```

The endpoint returns:

- `bundle`: canonical audit records for the tenant and time range.
- `manifest`: detached hash manifest with a signature.

Each exported record includes:

- `decision_input_digest`
- `policy_version`
- `layer_score_summary`
- `final_decision`
- `reason_codes`
- `previous_chain_hash`
- `chain_hash`

## What gets signed

The manifest includes:

- `bundle_hash_sha256`: SHA-256 over canonical JSON of the full bundle.
- `record_hashes`: SHA-256 for every record.
- `chain_head`: final record chain hash.
- `signature`: HMAC-SHA256 over the manifest body.

## Offline verifier steps

1. Save `bundle` and `manifest` as JSON files.
2. Recompute the bundle SHA-256 hash using canonical JSON (`sort_keys=True` and compact separators).
3. Confirm it matches `manifest.bundle_hash_sha256`.
4. Recompute each per-record hash and compare to `manifest.record_hashes`.
5. Verify chain continuity by checking each record's `previous_chain_hash` equals the prior record's `chain_hash` (first record may use `GENESIS`).
6. Recompute the HMAC-SHA256 signature of the manifest body (all fields except `signature`) using the shared export key (`SCBE_AUDIT_EXPORT_SIGNING_KEY`).
7. Compare signatures using constant-time comparison.

A helper exists in `api/audit_export.py` (`verify_manifest`) to support offline audit workflows.
