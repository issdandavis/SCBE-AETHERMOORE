"""Attestation verification API — metered, billable endpoint.

Provides:
- POST /v1/attest/verify  — Validate an egg-attest@v1 packet (metered)
- POST /v1/attest/batch   — Batch-verify up to 50 packets (metered per packet)
- GET  /v1/attest/schema   — Return the canonical JSON schema
- GET  /v1/attest/stats    — Verification stats for the caller's tenant

Each successful call to /verify or /batch increments the
`attestation_verifications` billable metric in the metering store.

Auth: x-api-key header, validated against billing + SaaS key stores.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.metering import (
    ATTESTATION_VERIFICATIONS,
    MeteringStore,
    metering_store,
)

attest_router = APIRouter(prefix="/v1/attest", tags=["Attestation"])

# ---------------------------------------------------------------------------
# Auth — accepts both SaaS demo keys and billing-provisioned keys
# ---------------------------------------------------------------------------

# Lazy imports to avoid circular deps at module load
_saas_keys: Optional[Dict] = None
_billing_keys: Optional[Dict] = None


def _get_saas_keys() -> Dict:
    global _saas_keys
    if _saas_keys is None:
        from src.api.saas_routes import VALID_API_KEYS
        _saas_keys = VALID_API_KEYS
    return _saas_keys


def _get_billing_keys() -> Dict:
    global _billing_keys
    if _billing_keys is None:
        from src.api.stripe_billing import BILLING_API_KEYS
        _billing_keys = BILLING_API_KEYS
    return _billing_keys


def _resolve_tenant(api_key: str) -> str:
    """Return tenant_id for the given API key, or raise 401."""
    saas = _get_saas_keys()
    if api_key in saas:
        return saas[api_key]

    billing = _get_billing_keys()
    if api_key in billing:
        return billing[api_key].get("customer_id", api_key)

    raise HTTPException(status_code=401, detail="Invalid API key")


# ---------------------------------------------------------------------------
# Metering store (injectable for tests)
# ---------------------------------------------------------------------------

_attest_metering: MeteringStore = metering_store


def set_attest_metering_store(store: MeteringStore) -> None:
    global _attest_metering
    _attest_metering = store


# ---------------------------------------------------------------------------
# Free tier limit enforcement
# ---------------------------------------------------------------------------

FREE_TIER_MONTHLY_ATTESTATIONS = 100


def _get_tenant_plan(api_key: str) -> Optional[str]:
    """Return the plan name for a billing API key, or None if not a billing key."""
    billing = _get_billing_keys()
    record = billing.get(api_key)
    if record:
        return record.get("plan")
    return None


def _get_monthly_attestation_count(tenant_id: str) -> int:
    """Return the current month's attestation verification count for a tenant."""
    now = datetime.now(timezone.utc)
    rows = _attest_metering.export_monthly_usage(now.year, now.month, tenant_id)
    return sum(r.count for r in rows if r.metric_name == ATTESTATION_VERIFICATIONS)


def _check_free_tier_limit(tenant_id: str, api_key: str, additional: int = 1) -> None:
    """Raise HTTP 429 if the tenant is on the free plan and has exceeded the monthly cap.

    Args:
        tenant_id: The resolved tenant identifier.
        api_key: The raw API key (used to look up plan).
        additional: Number of verifications about to be consumed.
    """
    plan = _get_tenant_plan(api_key)
    if plan != "free":
        return

    current = _get_monthly_attestation_count(tenant_id)
    if current + additional > FREE_TIER_MONTHLY_ATTESTATIONS:
        raise HTTPException(
            status_code=429,
            detail="Free tier limit reached (100/mo). Upgrade at /billing/plans",
        )


# ---------------------------------------------------------------------------
# Pydantic models (mirrors TypeScript EggAttestPacket)
# ---------------------------------------------------------------------------

class TongueQuorum(BaseModel):
    k: int = Field(..., ge=1)
    n: int = Field(..., ge=1)
    phi_weights: List[float]


class GeoSeal(BaseModel):
    scheme: str
    region: str
    proof: str


class Timebox(BaseModel):
    t0: str
    delta_s: float = Field(..., gt=0)


class Ritual(BaseModel):
    intent_sha256: str
    tongue_quorum: TongueQuorum
    geoseal: GeoSeal
    timebox: Timebox


class PQSig(BaseModel):
    alg: str
    signer: str
    sig: str


class H2External(BaseModel):
    sigstore_bundle: Optional[str] = None
    sbom_digest: Optional[str] = None

    class Config:
        extra = "allow"


class Anchors(BaseModel):
    H0_envelope: str
    H1_merkle_root: str
    pq_sigs: List[PQSig] = Field(..., min_length=1)
    h2_external: Optional[H2External] = None


class QuorumResult(BaseModel):
    # Note: field name "pass" is a Python keyword, use alias
    passed: bool = Field(..., alias="pass")
    k: int
    weighted_phi: float

    class Config:
        populate_by_name = True


class PolicyResult(BaseModel):
    decision: str
    risk: float = Field(..., ge=0, le=1)


class GateResults(BaseModel):
    syntax: str
    integrity: str
    quorum: QuorumResult
    geo_time: str
    policy: PolicyResult


class Hatch(BaseModel):
    boot_epoch: int = Field(..., ge=0)
    kdf: str
    boot_key_fp: str
    attestation_A0: str


class Signature(BaseModel):
    alg: str
    signers: List[str] = Field(..., min_length=1)
    sig: str


class EggAttestPacket(BaseModel):
    spec: str
    agent_id: str
    ritual: Ritual
    anchors: Anchors
    gates: GateResults
    hatch: Hatch
    signature: Signature


# ---------------------------------------------------------------------------
# Validation logic (Python port of eggAttestValidator.ts)
# ---------------------------------------------------------------------------

class ValidationError(BaseModel):
    path: str
    message: str


class VerifyResponse(BaseModel):
    valid: bool
    errors: List[ValidationError]
    verification_id: str
    verified_at: str
    gates_summary: Optional[Dict[str, Any]] = None


def _validate_packet(packet: EggAttestPacket, now_ms: Optional[float] = None) -> List[ValidationError]:
    errors: List[ValidationError] = []
    ref = now_ms if now_ms is not None else time.time() * 1000

    # spec version
    if packet.spec != "SCBE-AETHERMOORE/egg-attest@v1":
        errors.append(ValidationError(path="spec", message=f"Unknown spec: {packet.spec}"))

    # agent_id prefix
    if not packet.agent_id.startswith("hkdf://"):
        errors.append(ValidationError(path="agent_id", message="Must start with hkdf://"))

    # tongue quorum: k <= n
    q = packet.ritual.tongue_quorum
    if q.k > q.n:
        errors.append(ValidationError(
            path="ritual.tongue_quorum",
            message=f"k ({q.k}) must be <= n ({q.n})",
        ))

    # phi_weights length
    if len(q.phi_weights) != q.n:
        errors.append(ValidationError(
            path="ritual.tongue_quorum.phi_weights",
            message=f"Expected {q.n} weights, got {len(q.phi_weights)}",
        ))

    # phi_weights sum
    w_sum = sum(q.phi_weights)
    if w_sum > q.n:
        errors.append(ValidationError(
            path="ritual.tongue_quorum.phi_weights",
            message=f"Weight sum {w_sum:.3f} exceeds n={q.n}",
        ))

    # timebox expiry
    tb = packet.ritual.timebox
    try:
        t0_str = tb.t0.replace("Z", "+00:00") if tb.t0.endswith("Z") else tb.t0
        t0_dt = datetime.fromisoformat(t0_str)
        t0_ms = t0_dt.timestamp() * 1000
        expiry_ms = t0_ms + tb.delta_s * 1000
        if ref > expiry_ms:
            errors.append(ValidationError(
                path="ritual.timebox",
                message=f"Timebox expired at {datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc).isoformat()}",
            ))
    except (ValueError, OSError):
        errors.append(ValidationError(path="ritual.timebox.t0", message="Invalid ISO 8601 timestamp"))

    # unique signers
    signers = [s.signer for s in packet.anchors.pq_sigs]
    if len(set(signers)) != len(signers):
        errors.append(ValidationError(path="anchors.pq_sigs", message="Duplicate signers detected"))

    # gates consistency
    g = packet.gates
    gates_passed = (
        g.syntax == "pass"
        and g.integrity == "pass"
        and g.quorum.passed
        and g.geo_time == "pass"
    )
    if g.policy.decision == "allow" and not gates_passed:
        errors.append(ValidationError(
            path="gates",
            message='Policy decision is "allow" but not all gates passed',
        ))

    # quorum k match
    if g.quorum.k != q.k:
        errors.append(ValidationError(
            path="gates.quorum.k",
            message=f"Gate quorum k={g.quorum.k} differs from ritual k={q.k}",
        ))

    # hatch prefixes
    if not packet.hatch.boot_key_fp.startswith("fp:"):
        errors.append(ValidationError(path="hatch.boot_key_fp", message="Must start with fp:"))
    if not packet.hatch.attestation_A0.startswith("cose-sign1:"):
        errors.append(ValidationError(path="hatch.attestation_A0", message="Must start with cose-sign1:"))

    return errors


# ---------------------------------------------------------------------------
# Schema loader
# ---------------------------------------------------------------------------

_schema_cache: Optional[Dict] = None


def _load_schema() -> Dict:
    global _schema_cache
    if _schema_cache is None:
        schema_path = Path(__file__).resolve().parent.parent.parent / "schemas" / "egg_attest_v1.schema.json"
        if not schema_path.exists():
            raise HTTPException(500, "Schema file not found")
        _schema_cache = json.loads(schema_path.read_text())
    return _schema_cache


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@attest_router.post("/verify", response_model=VerifyResponse)
async def verify_attestation(
    packet: EggAttestPacket,
    x_api_key: str = Header(...),
) -> VerifyResponse:
    """Validate a single egg-attest@v1 packet.

    Returns validation result with error details. Each call is metered
    as one `attestation_verifications` unit.
    """
    tenant_id = _resolve_tenant(x_api_key)

    # Enforce free tier hard cap before metering
    _check_free_tier_limit(tenant_id, x_api_key)

    errors = _validate_packet(packet)
    verification_id = f"av_{uuid.uuid4().hex[:16]}"

    # Meter the call
    _attest_metering.increment_metric(tenant_id, ATTESTATION_VERIFICATIONS)

    return VerifyResponse(
        valid=len(errors) == 0,
        errors=errors,
        verification_id=verification_id,
        verified_at=datetime.now(timezone.utc).isoformat(),
        gates_summary={
            "syntax": packet.gates.syntax,
            "integrity": packet.gates.integrity,
            "quorum": packet.gates.quorum.passed,
            "geo_time": packet.gates.geo_time,
            "policy_decision": packet.gates.policy.decision,
            "risk": packet.gates.policy.risk,
        },
    )


class BatchVerifyRequest(BaseModel):
    packets: List[EggAttestPacket] = Field(..., min_length=1, max_length=50)


class BatchVerifyItem(BaseModel):
    index: int
    valid: bool
    errors: List[ValidationError]
    agent_id: str


class BatchVerifyResponse(BaseModel):
    total: int
    passed: int
    failed: int
    results: List[BatchVerifyItem]
    verification_id: str
    verified_at: str


@attest_router.post("/batch", response_model=BatchVerifyResponse)
async def batch_verify(
    body: BatchVerifyRequest,
    x_api_key: str = Header(...),
) -> BatchVerifyResponse:
    """Batch-verify up to 50 attestation packets.

    Metered per packet (not per request).
    """
    tenant_id = _resolve_tenant(x_api_key)

    # Enforce free tier hard cap before metering (check full batch size)
    _check_free_tier_limit(tenant_id, x_api_key, additional=len(body.packets))

    results: List[BatchVerifyItem] = []
    passed_count = 0

    for i, pkt in enumerate(body.packets):
        errs = _validate_packet(pkt)
        is_valid = len(errs) == 0
        if is_valid:
            passed_count += 1
        results.append(BatchVerifyItem(
            index=i,
            valid=is_valid,
            errors=errs,
            agent_id=pkt.agent_id,
        ))

    # Meter all packets in one increment
    _attest_metering.increment_metric(
        tenant_id, ATTESTATION_VERIFICATIONS, amount=len(body.packets)
    )

    return BatchVerifyResponse(
        total=len(body.packets),
        passed=passed_count,
        failed=len(body.packets) - passed_count,
        results=results,
        verification_id=f"ab_{uuid.uuid4().hex[:16]}",
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


@attest_router.get("/schema")
async def get_schema() -> Dict:
    """Return the canonical egg-attest@v1 JSON Schema."""
    return _load_schema()


class AttestStatsResponse(BaseModel):
    tenant_id: str
    total_verifications: int
    month: str


@attest_router.get("/stats", response_model=AttestStatsResponse)
async def get_stats(
    x_api_key: str = Header(...),
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
) -> AttestStatsResponse:
    """Return attestation verification count for the current month."""
    tenant_id = _resolve_tenant(x_api_key)
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    rows = _attest_metering.export_monthly_usage(y, m, tenant_id)
    total = sum(r.count for r in rows if r.metric_name == ATTESTATION_VERIFICATIONS)

    return AttestStatsResponse(
        tenant_id=tenant_id,
        total_verifications=total,
        month=f"{y:04d}-{m:02d}",
    )
