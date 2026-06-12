"""Single witness sink for every enforcement decision.

Born from the detector-coverage audit (docs/DETECTOR_COVERAGE_AUDIT.md): a rule's
failure mode is not violation but UNDETECTED violation. Every gate that denies,
quarantines, escalates, honeypots, or runs under a permissive bypass flag calls
``gate_witness()`` so a durable record exists regardless of what the caller does
with the verdict.

Design constraints:
    - stdlib only: must be importable from agents/, hydra/, src/api/, src/crypto/
      without dragging in optional dependencies.
    - never raises: a broken witness must not turn a working gate into a crash.
      Failures emit one stderr warning per process and return False.
    - never stores secrets: hash anything sensitive with ``hash_subject()`` before
      passing it in (CodeQL py/clear-text-storage applies to witnesses too).

Records are JSON lines (schema ``scbe_gate_witness_v1``) appended to
``artifacts/runtime/gate_witness.jsonl`` (override: ``SCBE_GATE_WITNESS_PATH``;
disable entirely: ``SCBE_GATE_WITNESS_DISABLE=1``).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

SCHEMA = "scbe_gate_witness_v1"

#: Canonical event vocabulary. Free-form strings are accepted (forward compat),
#: but wired gates should prefer these so the witness log is queryable.
EVENTS = (
    "deny",
    "quarantine",
    "escalate",
    "honeypot",
    "block",
    "auth_reject",
    "rate_limit",
    "bypass_flag",
    "unsealed_audit",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _REPO_ROOT / "artifacts" / "runtime" / "gate_witness.jsonl"

_lock = threading.Lock()
_warned = False


def _witness_path() -> Path:
    override = os.environ.get("SCBE_GATE_WITNESS_PATH", "").strip()
    return Path(override) if override else _DEFAULT_PATH


def hash_subject(value: str) -> str:
    """Return a short stable digest for sensitive subjects (API keys, tokens).

    Witness rows must locate repeat offenders without ever storing replayable
    material: 16 hex chars of SHA-256 is enough to correlate, useless to replay.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def gate_witness(
    gate: str,
    event: str,
    subject: str = "",
    detail: Optional[Dict[str, Any]] = None,
) -> bool:
    """Append one durable witness record for an enforcement decision.

    Args:
        gate: Which enforcement point fired (e.g. ``"kernel_antivirus"``,
            ``"api.auth"``, ``"stripe.webhook"``).
        event: What happened — prefer a value from :data:`EVENTS`.
        subject: Short identifier for what was gated. Hash anything sensitive
            with :func:`hash_subject` BEFORE passing it here.
        detail: Small JSON-safe dict of gate-specific context. Same rule: no
            raw secrets, no full payloads.

    Returns:
        True if the record was durably written, False otherwise (disabled via
        env, or write failed — a warning is emitted once per process).
    """
    global _warned
    if os.environ.get("SCBE_GATE_WITNESS_DISABLE", "").strip() in {"1", "true", "yes"}:
        return False
    record = {
        "schema": SCHEMA,
        "ts": datetime.now(timezone.utc).isoformat(),
        "gate": str(gate),
        "event": str(event),
        "subject": str(subject),
        "detail": detail or {},
    }
    try:
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        path = _witness_path()
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return True
    except Exception as exc:  # noqa: BLE001 — witness must never break a gate
        if not _warned:
            _warned = True
            print(f"[gate_witness] WARNING: witness write failed ({exc}); gates run UNWITNESSED", file=sys.stderr)
        return False
