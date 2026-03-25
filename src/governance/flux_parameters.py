"""
@file flux_parameters.py
@module governance/flux_parameters
@layer Layer 12, Layer 13
@component Governance Flux Parameters — Consensus-Gated Parameter Updates

Manages the tunable governance parameters (curvature, tongue weights,
Layer 12 scaling factors, quarantine cost) with a 4-of-6 Sacred Tongue
quorum requirement for any parameter change.

No parameter update takes effect until 4 of the 6 authorized agents
(KO, AV, RU, CA, UM, DR) sign off. Illegal values are rejected at
proposal time, not at commit time.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

# The 6 Sacred Tongue agents authorized to propose and vote
AGENTS = frozenset({"KO", "AV", "RU", "CA", "UM", "DR"})

# Quorum: 4 of 6 required to commit a parameter update
QUORUM = 4

# Safe ranges for parameter validation
SAFE_RANGES: Dict[str, tuple] = {
    "layer12_R": (0.8, 1.2),
    "layer12_gamma": (0.1, 10.0),
    "curvature_kappa": (0.0, 100.0),
    "phase_coupling_eta": (0.0, 1.0),
    "entropy_noise_floor": (0.0, 1.0),
    "quarantine_cost": (0.0, 1e9),
}


@dataclass
class FluxParams:
    """Immutable governance parameter set for one epoch."""

    epoch_id: str
    lang_weights: Dict[str, float]
    curvature_kappa: float
    phase_coupling_eta: float
    entropy_noise_floor: float
    layer12_R: float
    layer12_gamma: float
    quarantine_cost: float

    def canonical_json(self) -> str:
        """Deterministic JSON serialization (sorted keys, no whitespace variance)."""
        data = {
            "curvature_kappa": self.curvature_kappa,
            "entropy_noise_floor": self.entropy_noise_floor,
            "epoch_id": self.epoch_id,
            "lang_weights": dict(sorted(self.lang_weights.items())),
            "layer12_R": self.layer12_R,
            "layer12_gamma": self.layer12_gamma,
            "phase_coupling_eta": self.phase_coupling_eta,
            "quarantine_cost": self.quarantine_cost,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        """SHA-256 of canonical JSON — used for tamper detection."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _validate_params(params: FluxParams) -> None:
    """Reject illegal parameter values at proposal time.

    Raises ValueError with a descriptive message.
    """
    if params.curvature_kappa < 0:
        raise ValueError(f"Negative curvature not allowed: curvature_kappa={params.curvature_kappa}")

    lo, hi = SAFE_RANGES["layer12_R"]
    if not (lo <= params.layer12_R <= hi):
        raise ValueError(f"Layer 12 Radius out of safe range [{lo}, {hi}]: " f"layer12_R={params.layer12_R}")

    lo, hi = SAFE_RANGES["layer12_gamma"]
    if not (lo <= params.layer12_gamma <= hi):
        raise ValueError(f"Layer 12 gamma out of safe range [{lo}, {hi}]: " f"layer12_gamma={params.layer12_gamma}")

    lo, hi = SAFE_RANGES["phase_coupling_eta"]
    if not (lo <= params.phase_coupling_eta <= hi):
        raise ValueError(
            f"Phase coupling eta out of safe range [{lo}, {hi}]: " f"phase_coupling_eta={params.phase_coupling_eta}"
        )

    lo, hi = SAFE_RANGES["entropy_noise_floor"]
    if not (lo <= params.entropy_noise_floor <= hi):
        raise ValueError(
            f"Entropy noise floor out of safe range [{lo}, {hi}]: " f"entropy_noise_floor={params.entropy_noise_floor}"
        )

    if params.quarantine_cost < 0:
        raise ValueError(f"Quarantine cost must be non-negative: {params.quarantine_cost}")


class ConsensusEngine:
    """4-of-6 quorum engine for governance parameter updates.

    Flow:
      1. An authorized agent proposes a new FluxParams via propose_update()
      2. Other agents vote via vote()
      3. When 4 votes are collected, the update commits automatically
    """

    def __init__(self, current_params: FluxParams) -> None:
        self.current_params = current_params
        self.pending_proposal: Optional[FluxParams] = None
        self.signatures: Dict[str, str] = {}

    def propose_update(self, new_params: FluxParams, proposer: str) -> None:
        """Propose a parameter update. Validates params and proposer.

        Raises:
            PermissionError: if proposer is not an authorized agent
            ValueError: if new_params contains illegal values
        """
        if proposer not in AGENTS:
            raise PermissionError(f"Unauthorized proposer: {proposer!r}. Must be one of {sorted(AGENTS)}")

        _validate_params(new_params)

        self.pending_proposal = new_params
        self.signatures = {}

    def vote(self, agent: str, approve: bool, signature: str) -> None:
        """Cast a vote on the pending proposal.

        Unknown agents are silently ignored (defense-in-depth).
        When quorum is reached, the proposal commits automatically.
        """
        if agent not in AGENTS:
            return

        if self.pending_proposal is None:
            return

        if not approve:
            return

        self.signatures[agent] = signature

        if len(self.signatures) >= QUORUM:
            self._commit()

    def _commit(self) -> None:
        """Apply the pending proposal as the new current parameters."""
        if self.pending_proposal is not None:
            self.current_params = self.pending_proposal
            self.pending_proposal = None
            self.signatures = {}


def create_voxel_header(vid: str, params: FluxParams) -> Dict[str, Any]:
    """Create a voxel header bound to the current governance epoch.

    Returns a dict with:
      - vid: voxel identifier
      - ts: current timestamp
      - epoch: epoch_id from params
      - param_hash: SHA-256 of canonical params
    """
    return {
        "vid": vid,
        "ts": time.time(),
        "epoch": params.epoch_id,
        "param_hash": params.compute_hash(),
    }
