import json

from backend.audit import AuditWriter
from backend.models import (
    OperationDecision,
    OperationOrigin,
    OperationRequest,
    OperationResult,
)


def _make_req(request_id: str = "audit-test-001") -> OperationRequest:
    return OperationRequest(
        op="echo",
        args={"msg": "hello"},
        request_id=request_id,
        origin=OperationOrigin(kind="app", id="test"),
        privacy="local_only",
    )


def _make_decision(req: OperationRequest) -> OperationDecision:
    return OperationDecision(
        request_id=req.request_id,
        decision="ALLOW",
        zone="GREEN",
        reason="test",
        policy="test",
        latency_ms=0.5,
    )


def test_write_request_creates_file(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    req = _make_req()
    decision = _make_decision(req)
    writer.write_request(req, decision)
    log = tmp_path / "audit.jsonl"
    assert log.exists()
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["request_id"] == "audit-test-001"
    assert rows[0]["decision"]["decision"] == "ALLOW"


def test_complete_appends_result_row(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    req = _make_req()
    decision = _make_decision(req)
    writer.write_request(req, decision)
    result = OperationResult(request_id=req.request_id, ok=True, output={"echo": "hello"}, duration_ms=12.0)
    writer.complete(req.request_id, result)
    rows = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    assert rows[1]["result_summary"]["ok"] is True


def test_audit_never_records_raw_secrets(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    req = OperationRequest(
        op="llm.chat",
        args={"messages": [{"role": "user", "content": "hello"}], "api_key": "sk-secret-value"},
        request_id="audit-secret-test",
        origin=OperationOrigin(kind="app", id="test"),
        privacy="local_only",
    )
    decision = _make_decision(req)
    writer.write_request(req, decision)
    content = (tmp_path / "audit.jsonl").read_text()
    assert "sk-secret-value" not in content


def test_audit_rows_are_append_only(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    for i in range(3):
        req = _make_req(request_id=f"req-{i}")
        writer.write_request(req, _make_decision(req))
    rows = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(rows) == 3
