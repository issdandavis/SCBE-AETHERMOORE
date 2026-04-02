"""Energy-Aware Compute Authorization API
=========================================

/authorize_compute — The core SCBE Sentinel product endpoint.

Takes a workload description + energy state, returns:
  - Inference tier (TINY / MEDIUM / FULL / DENY)
  - Estimated compute cost
  - Go/no-go decision
  - Energy budget impact

This is the same harmonic cost function (H(d*,R) = pi^(phi*d*))
applied to compute governance instead of security governance.
Safe/cheap operations stay in Layer 0 (TinyML).
Expensive/risky operations escalate to Layer 3 (full compute).

Maps to:
  - Layer 0: Always-on monitor (TinyML, milliwatts)
  - Layer 1: Threshold MPC controller (sensors + forecasts)
  - Layer 2: Medium local brain (edge transformer)
  - Layer 3: Full compute / cloud assist (GPU inference)
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

compute_router = APIRouter(prefix="/v1/compute", tags=["compute-governance"])

PHI = 1.618033988749895
PI = math.pi


# ---------------------------------------------------------------------------
#  Models
# ---------------------------------------------------------------------------


class InferenceTier(str, Enum):
    TINY = "TINY"  # Layer 0: always-on, milliwatts, MCU/NPU
    MEDIUM = "MEDIUM"  # Layer 1-2: edge transformer, watts
    FULL = "FULL"  # Layer 3: GPU/cloud, kilowatts
    DENY = "DENY"  # Over budget or unsafe


class EnergySource(str, Enum):
    GRID = "grid"
    SOLAR = "solar"
    BATTERY = "battery"
    HARVESTED = "harvested"
    UNKNOWN = "unknown"


class EnergyState(BaseModel):
    """Current energy availability across sources."""

    available_wh: float = Field(..., ge=0, description="Available energy in watt-hours")
    source: EnergySource = Field(default=EnergySource.UNKNOWN)
    battery_pct: Optional[float] = Field(default=None, ge=0, le=100)
    solar_forecast_wh: Optional[float] = Field(
        default=None, ge=0, description="Forecasted solar generation next hour (Wh)"
    )
    grid_price_per_kwh: Optional[float] = Field(
        default=None, ge=0, description="Current grid electricity price ($/kWh)"
    )
    cooling_available: bool = Field(default=True, description="Is cooling capacity available?")


class WorkloadRequest(BaseModel):
    """Workload description for compute authorization."""

    workload_id: Optional[str] = Field(default=None, description="Client-provided workload ID")
    description: str = Field(..., min_length=1, max_length=2000, description="What computation to perform")
    model_size_params: Optional[float] = Field(default=None, ge=0, description="Model size in billions of parameters")
    estimated_tokens: Optional[int] = Field(default=None, ge=0, description="Estimated tokens to process")
    latency_requirement_ms: Optional[float] = Field(default=None, ge=0, description="Max acceptable latency (ms)")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1 (lowest) to 10 (critical)")
    allow_cloud_escalation: bool = Field(default=True, description="Allow escalation to cloud compute?")
    energy_state: EnergyState = Field(..., description="Current energy availability")


class ComputeDecision(BaseModel):
    """Authorization decision for a compute workload."""

    decision_id: str
    workload_id: str
    tier: InferenceTier
    authorized: bool
    harmonic_cost: float
    energy_cost_wh: float
    energy_remaining_wh: float
    reason: str
    tier_justification: str
    estimated_latency_ms: float
    estimated_power_w: float
    timestamp: str
    signals: List[str] = []


# ---------------------------------------------------------------------------
#  Tier estimation logic
# ---------------------------------------------------------------------------

# Compute profiles per tier (approximate)
TIER_PROFILES = {
    InferenceTier.TINY: {
        "max_params_b": 0.1,  # Up to 100M params
        "power_w": 0.5,  # 500mW
        "latency_ms": 50,  # 50ms
        "energy_per_1k_tokens_wh": 0.001,
    },
    InferenceTier.MEDIUM: {
        "max_params_b": 3.0,  # Up to 3B params
        "power_w": 15.0,  # 15W
        "latency_ms": 500,  # 500ms
        "energy_per_1k_tokens_wh": 0.05,
    },
    InferenceTier.FULL: {
        "max_params_b": 400.0,  # Up to 400B+ params
        "power_w": 300.0,  # 300W (GPU)
        "latency_ms": 5000,  # 5s
        "energy_per_1k_tokens_wh": 0.5,
    },
}


def _estimate_workload_energy(tokens: int, tier: InferenceTier) -> float:
    """Estimate energy consumption in Wh for a workload at a given tier."""
    profile = TIER_PROFILES[tier]
    return (tokens / 1000.0) * profile["energy_per_1k_tokens_wh"]


def _select_tier(
    model_size_b: float,
    tokens: int,
    latency_req_ms: float,
    priority: int,
    energy: EnergyState,
    allow_cloud: bool,
) -> tuple[InferenceTier, float, list[str]]:
    """Select the optimal inference tier based on workload + energy state.

    Uses the same harmonic cost function as the security gate:
      H(d*, R) = pi^(phi * d*)

    where d* is the "distance" between what's requested and what's available.
    Higher distance = higher cost = escalate or deny.
    """
    signals: list[str] = []

    # Compute the request "distance" from baseline
    # Factors: model size, token count, latency pressure, priority
    size_factor = min(model_size_b / 3.0, 5.0)  # Normalized to 3B baseline
    token_factor = min(tokens / 1000.0, 5.0)  # Normalized to 1K baseline
    latency_pressure = max(0, 1.0 - latency_req_ms / 5000.0) if latency_req_ms > 0 else 0.0
    priority_factor = priority / 10.0

    d_star = size_factor * 0.4 + token_factor * 0.2 + latency_pressure * 0.2 + priority_factor * 0.2
    d_star = min(d_star, 5.0)

    harmonic_cost = PI ** (PHI * d_star)
    signals.append(f"harmonic_cost={harmonic_cost:.2f}")

    # Energy budget check
    energy_headroom = energy.available_wh

    # Solar forecast bonus: if solar is coming, we have more headroom
    if energy.solar_forecast_wh and energy.solar_forecast_wh > 0:
        energy_headroom += energy.solar_forecast_wh * 0.5  # Conservative 50% credit
        signals.append(f"solar_bonus={energy.solar_forecast_wh * 0.5:.1f}Wh")

    # Battery penalty: below 20% = reduce headroom
    if energy.battery_pct is not None and energy.battery_pct < 20:
        energy_headroom *= energy.battery_pct / 20.0
        signals.append(f"battery_low={energy.battery_pct:.0f}%")

    # Cooling penalty: no cooling = can't run full compute
    if not energy.cooling_available:
        signals.append("no_cooling")

    # Grid price awareness: expensive grid = prefer local/deferred
    if energy.grid_price_per_kwh and energy.grid_price_per_kwh > 0.15:
        signals.append(f"grid_expensive=${energy.grid_price_per_kwh:.3f}/kWh")

    # --- Tier selection ---

    # Try TINY first (always preferred if sufficient)
    if model_size_b <= TIER_PROFILES[InferenceTier.TINY]["max_params_b"]:
        est_energy = _estimate_workload_energy(tokens, InferenceTier.TINY)
        if est_energy <= energy_headroom:
            signals.append("tier=TINY(model_fits)")
            return InferenceTier.TINY, harmonic_cost, signals

    # Try MEDIUM
    if model_size_b <= TIER_PROFILES[InferenceTier.MEDIUM]["max_params_b"]:
        est_energy = _estimate_workload_energy(tokens, InferenceTier.MEDIUM)
        if est_energy <= energy_headroom:
            latency_ok = latency_req_ms == 0 or TIER_PROFILES[InferenceTier.MEDIUM]["latency_ms"] <= latency_req_ms
            if latency_ok:
                signals.append("tier=MEDIUM(fits_energy+latency)")
                return InferenceTier.MEDIUM, harmonic_cost, signals

    # Try FULL (only if cloud escalation allowed + cooling available)
    if allow_cloud and energy.cooling_available:
        est_energy = _estimate_workload_energy(tokens, InferenceTier.FULL)
        if est_energy <= energy_headroom:
            signals.append("tier=FULL(escalated)")
            return InferenceTier.FULL, harmonic_cost, signals

    # DENY: not enough energy or cooling for any tier
    deny_reason = []
    if not energy.cooling_available:
        deny_reason.append("no_cooling")
    if not allow_cloud:
        deny_reason.append("cloud_blocked")
    deny_reason.append(f"energy_headroom={energy_headroom:.1f}Wh")
    signals.append(f"tier=DENY({','.join(deny_reason)})")
    return InferenceTier.DENY, harmonic_cost, signals


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------


@compute_router.post("/authorize", response_model=ComputeDecision)
async def authorize_compute(req: WorkloadRequest):
    """Authorize a compute workload based on energy state and workload requirements.

    Returns the optimal inference tier and go/no-go decision.
    """
    workload_id = req.workload_id or str(uuid.uuid4())[:12]

    # Defaults
    model_size = req.model_size_params or 1.0
    tokens = req.estimated_tokens or 500
    latency_req = req.latency_requirement_ms or 0

    tier, harmonic_cost, signals = _select_tier(
        model_size_b=model_size,
        tokens=tokens,
        latency_req_ms=latency_req,
        priority=req.priority,
        energy=req.energy_state,
        allow_cloud=req.allow_cloud_escalation,
    )

    authorized = tier != InferenceTier.DENY

    # Compute energy cost for selected tier
    if authorized:
        energy_cost = _estimate_workload_energy(tokens, tier)
        profile = TIER_PROFILES[tier]
        est_latency = profile["latency_ms"]
        est_power = profile["power_w"]
    else:
        energy_cost = 0.0
        est_latency = 0.0
        est_power = 0.0

    energy_remaining = max(0, req.energy_state.available_wh - energy_cost)

    # Build justification
    if authorized:
        justification = (
            f"{tier.value} tier selected: {model_size:.1f}B model, "
            f"{tokens} tokens, {energy_cost:.3f}Wh cost, "
            f"{energy_remaining:.1f}Wh remaining"
        )
    else:
        justification = "Denied: insufficient energy or cooling for workload"

    reason = "authorized" if authorized else "denied_energy_budget"

    return ComputeDecision(
        decision_id=str(uuid.uuid4())[:12],
        workload_id=workload_id,
        tier=tier,
        authorized=authorized,
        harmonic_cost=round(harmonic_cost, 4),
        energy_cost_wh=round(energy_cost, 4),
        energy_remaining_wh=round(energy_remaining, 2),
        reason=reason,
        tier_justification=justification,
        estimated_latency_ms=est_latency,
        estimated_power_w=est_power,
        timestamp=datetime.now(timezone.utc).isoformat(),
        signals=signals,
    )


@compute_router.get("/tiers")
async def list_tiers():
    """List available inference tiers and their profiles."""
    return {
        tier.value: {
            "max_model_params_b": profile["max_params_b"],
            "typical_power_w": profile["power_w"],
            "typical_latency_ms": profile["latency_ms"],
            "energy_per_1k_tokens_wh": profile["energy_per_1k_tokens_wh"],
        }
        for tier, profile in TIER_PROFILES.items()
    }


@compute_router.post("/batch_authorize")
async def batch_authorize(workloads: List[WorkloadRequest]):
    """Authorize multiple workloads, scheduling them by priority and energy budget."""
    if len(workloads) > 50:
        raise HTTPException(status_code=400, detail="Max 50 workloads per batch")

    # Sort by priority (highest first)
    sorted_workloads = sorted(workloads, key=lambda w: w.priority, reverse=True)

    results = []
    running_energy = sorted_workloads[0].energy_state.available_wh if sorted_workloads else 0

    for wl in sorted_workloads:
        # Update energy state with running total
        wl.energy_state.available_wh = running_energy
        decision = await authorize_compute(wl)
        results.append(decision)
        if decision.authorized:
            running_energy -= decision.energy_cost_wh

    return {
        "total_workloads": len(results),
        "authorized": sum(1 for r in results if r.authorized),
        "denied": sum(1 for r in results if not r.authorized),
        "total_energy_cost_wh": round(sum(r.energy_cost_wh for r in results), 4),
        "energy_remaining_wh": round(running_energy, 2),
        "decisions": results,
    }
