# SCBE Kernel v1 API Contract

This document defines stable request/response contracts for SCBE Kernel v1.

## Global contract guarantees

### Deterministic decision enum
All decision-producing endpoints MUST use:

- `ALLOW`
- `QUARANTINE`
- `DENY`

### Stable error codes
All error responses MUST use one of these stable values in `error.code`:

- `HF_TOKEN_MISSING`
- `HF_TOKEN_INVALID`
- `POLICY_VIOLATION`
- `REQUEST_INVALID`
- `REQUEST_CONFLICT`
- `DECISION_NOT_FOUND`
- `RATE_LIMITED`
- `INTERNAL_ERROR`

### Idempotency and traceability
- `request_id` is required in all mutating requests and echoed in all responses.
- `correlation_id` is required in every response.
- `audit_hash` is required in every response.

---

## `POST /authorize`

Determines whether a request is permitted.

### Request body schema
`schemas/kernel-v1/post_authorize.request.schema.json`

```json
{
  "request_id": "req_01J9X9ABCD1234",
  "subject": {
    "subject_id": "agent_42",
    "roles": ["operator"]
  },
  "resource": {
    "resource_id": "memory://tenant-alpha/shard-17",
    "resource_type": "memory_shard"
  },
  "action": "seal",
  "context": {
    "hf_token": "hf_***",
    "policy_tags": ["production"]
  }
}
```

### Success response schema
`schemas/kernel-v1/post_authorize.response.schema.json`

```json
{
  "request_id": "req_01J9X9ABCD1234",
  "correlation_id": "corr_90f0e8f1-4ef3-4e07-b2e3-6f5afce1bd8f",
  "audit_hash": "sha256:0f6a6b6d7f...",
  "decision_id": "dec_01J9X9ANM8R8P",
  "decision": "ALLOW",
  "reason": "policy checks passed",
  "policy_version": "kernel-v1.0.0",
  "evaluated_at": "2026-02-18T12:00:00Z"
}
```

### Error response schema
`schemas/kernel-v1/error.response.schema.json`

---

## `POST /memory/seal`

Seals a memory payload after authorization.

### Request body schema
`schemas/kernel-v1/post_memory_seal.request.schema.json`

```json
{
  "request_id": "req_01J9X9AQWXYZ",
  "decision_id": "dec_01J9X9ANM8R8P",
  "memory": {
    "memory_id": "mem_123",
    "content": "sensitive payload",
    "content_type": "text/plain"
  },
  "seal_options": {
    "algorithm": "spiral-seal-v1",
    "ttl_seconds": 3600
  }
}
```

### Success response schema
`schemas/kernel-v1/post_memory_seal.response.schema.json`

```json
{
  "request_id": "req_01J9X9AQWXYZ",
  "correlation_id": "corr_37d18dc7-d3a9-41ec-b8a8-8df34aa4eb2b",
  "audit_hash": "sha256:b89f2c4f2b...",
  "decision_id": "dec_01J9X9ANM8R8P",
  "decision": "ALLOW",
  "memory_id": "mem_123",
  "sealed": true,
  "seal_id": "seal_88A",
  "sealed_at": "2026-02-18T12:00:05Z"
}
```

### Error response schema
`schemas/kernel-v1/error.response.schema.json`

---

## `GET /audit/{decision_id}`

Retrieves immutable audit details for a decision.

### Request params schema
`schemas/kernel-v1/get_audit_decision_id.request.schema.json`

```json
{
  "request_id": "req_01J9X9AS",
  "decision_id": "dec_01J9X9ANM8R8P"
}
```

### Success response schema
`schemas/kernel-v1/get_audit_decision_id.response.schema.json`

```json
{
  "request_id": "req_01J9X9AS",
  "correlation_id": "corr_8f7cc108-ef13-4d6a-b112-0c6471aa79a1",
  "audit_hash": "sha256:8dd13f...",
  "decision_id": "dec_01J9X9ANM8R8P",
  "decision": "QUARANTINE",
  "reason": "policy requires manual review",
  "policy_version": "kernel-v1.0.0",
  "recorded_at": "2026-02-18T12:00:00Z",
  "evidence": {
    "risk_score": 0.82,
    "triggered_rules": ["restricted-domain"]
  }
}
```

### Error response schema
`schemas/kernel-v1/error.response.schema.json`

---

## `GET /health`

Liveness/readiness and compatibility signal.

### Request params schema
`schemas/kernel-v1/get_health.request.schema.json`

```json
{
  "request_id": "req_health_01"
}
```

### Success response schema
`schemas/kernel-v1/get_health.response.schema.json`

```json
{
  "request_id": "req_health_01",
  "correlation_id": "corr_64782f59-fd7d-4e16-b4f7-4136e62d92bc",
  "audit_hash": "sha256:14eac6...",
  "status": "ok",
  "service": "scbe-kernel",
  "version": "1.0.0",
  "uptime_seconds": 7342,
  "timestamp": "2026-02-18T12:00:10Z"
}
```

### Error response schema
`schemas/kernel-v1/error.response.schema.json`

---

## Schema index

- `schemas/kernel-v1/post_authorize.request.schema.json`
- `schemas/kernel-v1/post_authorize.response.schema.json`
- `schemas/kernel-v1/post_memory_seal.request.schema.json`
- `schemas/kernel-v1/post_memory_seal.response.schema.json`
- `schemas/kernel-v1/get_audit_decision_id.request.schema.json`
- `schemas/kernel-v1/get_audit_decision_id.response.schema.json`
- `schemas/kernel-v1/get_health.request.schema.json`
- `schemas/kernel-v1/get_health.response.schema.json`
- `schemas/kernel-v1/error.response.schema.json`
