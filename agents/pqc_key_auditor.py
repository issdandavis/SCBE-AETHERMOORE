"""PQC key rotation/drift auditor for SCBE governance flows.

Designed for runtime gating (ALLOW/REVIEW/QUARANTINE) with deterministic,
tamper-evident scoring from key identifiers + action context.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict


def _hash_to_unit(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    as_int = int.from_bytes(digest[:8], "big", signed=False)
    return as_int / float(2**64 - 1)


def audit_pqc_keyset(
    keyset: Dict[str, Any],
    context_payload: Dict[str, Any] | None = None,
    *,
    drift_threshold: float = 0.82,
    rotation_hours: int = 720,
) -> Dict[str, Any]:
    """Audit PQC key material metadata for governance decisions.

    Expected keyset keys (metadata, not raw secrets):
      - kyber_id: stable key identifier
      - dilithium_id: stable key identifier
      - last_rotated_hours: numeric age in hours (optional)
    """

    kyber_id = str(keyset.get("kyber_id", "")).strip()
    dilithium_id = str(keyset.get("dilithium_id", "")).strip()
    age_hours = float(keyset.get("last_rotated_hours", keyset.get("age_hours", 0)) or 0)

    if not kyber_id or not dilithium_id:
        return {
            "status": "QUARANTINE",
            "reason": "missing kyber_id or dilithium_id",
            "drift_score": 1.0,
            "rotation_due": True,
            "recommended_action": "block_until_key_metadata_present",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    context = context_payload or {}
    action_fingerprint = json.dumps(
        {
            "actions": context.get("actions", []),
            "workflow_id": context.get("workflow_id"),
            "session_id": context.get("session_id"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    seed = f"{kyber_id}|{dilithium_id}|{action_fingerprint}"
    drift_score = _hash_to_unit(seed)
    rotation_due = age_hours >= float(rotation_hours)

    if drift_score >= float(drift_threshold):
        status = "QUARANTINE"
        reason = f"pqc drift score {drift_score:.4f} >= threshold {drift_threshold:.4f}"
        action = "rotate_keys_and_revalidate"
    elif rotation_due:
        status = "REVIEW"
        reason = f"key age {age_hours:.1f}h >= rotation policy {rotation_hours}h"
        action = "rotate_keys_soon"
    else:
        status = "ALLOW"
        reason = "pqc keyset within drift/age policy"
        action = "none"

    return {
        "status": status,
        "reason": reason,
        "drift_score": round(float(drift_score), 6),
        "drift_threshold": float(drift_threshold),
        "rotation_due": bool(rotation_due),
        "age_hours": round(float(age_hours), 3),
        "recommended_action": action,
        "key_fingerprint": hashlib.sha256(f"{kyber_id}|{dilithium_id}".encode("utf-8")).hexdigest()[:20],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

