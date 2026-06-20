from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION = "scbe.operation.v1"

DecisionKind = Literal["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]
ZoneKind = Literal["GREEN", "YELLOW", "RED"]


class OperationOrigin(BaseModel):
    kind: Literal["app", "workflow", "agent"]
    id: str


class OperationWorkspace(BaseModel):
    id: str
    root: str


class OperationRequest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    op: str
    args: dict[str, Any] = Field(default_factory=dict)
    request_id: str
    origin: OperationOrigin
    workspace: OperationWorkspace | None = None
    privacy: Literal["local_only", "external_api"] = "local_only"
    budget_cents: float | None = None
    dry_run: bool = False


class OperationDecision(BaseModel):
    request_id: str
    decision: DecisionKind
    zone: ZoneKind
    reason: str
    policy: str
    latency_ms: float


class OperationError(BaseModel):
    code: str
    message: str


class ArtifactRef(BaseModel):
    kind: str
    ref: str


class OperationResult(BaseModel):
    request_id: str
    ok: bool
    output: dict[str, Any] | None = None
    error: OperationError | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    duration_ms: float = 0.0


class AuditResultSummary(BaseModel):
    ok: bool
    error_code: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    output_shape: str | None = None


class AuditRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    request_id: str
    ts_request: str
    op: str
    origin: OperationOrigin
    privacy: str
    decision: OperationDecision
    ts_result: str | None = None
    result_summary: AuditResultSummary | None = None
