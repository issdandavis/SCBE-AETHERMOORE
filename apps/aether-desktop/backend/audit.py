from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import AuditRecord, AuditResultSummary, OperationDecision, OperationRequest, OperationResult

_REDACTED_KEYS: frozenset[str] = frozenset(
    {"api_key", "secret", "password", "token", "bearer", "credential"}
)


def _redact_args(args: dict) -> dict:
    return {k: "[REDACTED]" if k.lower() in _REDACTED_KEYS else v for k, v in args.items()}


class AuditWriter:
    def __init__(self, audit_dir: Path | None = None) -> None:
        if audit_dir is None:
            audit_dir = Path(".scbe")
        self._log_path = Path(audit_dir) / "audit.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def write_request(self, req: OperationRequest, decision: OperationDecision) -> None:
        record = AuditRecord(
            request_id=req.request_id,
            ts_request=datetime.now(timezone.utc).isoformat(),
            op=req.op,
            origin=req.origin,
            privacy=req.privacy,
            decision=decision,
        )
        row = record.model_dump()
        # Redact sensitive fields from args before persisting.
        row["args_redacted"] = _redact_args(req.args)
        self._append(row)

    def complete(self, request_id: str, result: OperationResult) -> None:
        summary = AuditResultSummary(
            ok=result.ok,
            error_code=result.error.code if result.error else None,
            artifact_refs=[a.ref for a in result.artifacts],
            output_shape=str(type(result.output).__name__) if result.output else None,
        )
        completion = {
            "schema_version": "scbe.operation.v1",
            "request_id": request_id,
            "ts_result": datetime.now(timezone.utc).isoformat(),
            "result_summary": summary.model_dump(),
        }
        self._append(completion)

    def _append(self, record: dict) -> None:
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
