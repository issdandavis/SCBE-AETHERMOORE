"""Utilities for exporting signed audit bundles."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def canonical_json(data: Any) -> str:
    """Render stable JSON for hashing/signatures."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: str) -> str:
    """SHA-256 helper for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 datetime into UTC."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def filter_records_by_range(records: List[Dict[str, Any]], from_ts: str, to_ts: str) -> List[Dict[str, Any]]:
    """Return records where timestamp is in [from_ts, to_ts]."""
    start = parse_iso8601(from_ts)
    end = parse_iso8601(to_ts)
    selected: List[Dict[str, Any]] = []

    for record in records:
        raw_ts = record.get("timestamp")
        if not raw_ts:
            continue
        try:
            current = parse_iso8601(str(raw_ts))
        except ValueError:
            continue
        if start <= current <= end:
            selected.append(record)

    selected.sort(key=lambda item: item.get("timestamp", ""))
    return selected


def build_signed_bundle(
    tenant_id: str,
    from_ts: str,
    to_ts: str,
    records: List[Dict[str, Any]],
    signing_key: str,
    signer: str = "hmac-sha256",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build bundle payload and detached hash manifest + signature."""
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    export_payload = {
        "schema": "scbe.audit.export.v1",
        "tenant_id": tenant_id,
        "from": from_ts,
        "to": to_ts,
        "generated_at": generated_at,
        "record_count": len(records),
        "records": records,
    }

    canonical_payload = canonical_json(export_payload)
    payload_hash = sha256_hex(canonical_payload)

    record_hashes = [
        {
            "decision_id": record.get("decision_id"),
            "record_hash": sha256_hex(canonical_json(record)),
        }
        for record in records
    ]

    manifest_body = {
        "schema": "scbe.audit.manifest.v1",
        "tenant_id": tenant_id,
        "generated_at": generated_at,
        "bundle_hash_sha256": payload_hash,
        "record_hashes": record_hashes,
        "chain_head": records[-1].get("chain_hash") if records else None,
        "signature_algorithm": signer,
    }

    signature = hmac.new(
        signing_key.encode("utf-8"),
        canonical_json(manifest_body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    manifest = {
        **manifest_body,
        "signature": signature,
    }
    return export_payload, manifest


def verify_manifest(bundle: Dict[str, Any], manifest: Dict[str, Any], signing_key: str) -> bool:
    """Offline verification helper for auditors."""
    expected_bundle_hash = sha256_hex(canonical_json(bundle))
    if expected_bundle_hash != manifest.get("bundle_hash_sha256"):
        return False

    manifest_body = dict(manifest)
    signature = manifest_body.pop("signature", None)
    if not signature:
        return False

    expected_sig = hmac.new(
        signing_key.encode("utf-8"),
        canonical_json(manifest_body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature)
