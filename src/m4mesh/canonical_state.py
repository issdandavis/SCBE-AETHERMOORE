from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import torch

CANONICAL_DIM = 21
TONGUE_POSITION_DIMS = slice(0, 6)
TONGUE_PHASE_DIMS = slice(6, 12)
TELEMETRY_DIMS = slice(12, 21)


def harmonic_energy_from_radial(radial: torch.Tensor, d_hyp: int = 6, eps: float = 1e-12) -> torch.Tensor:
    """Harmonic wall cache term from radial norm."""
    if torch.any(radial >= 1.0):
        raise ValueError("Radial norm must satisfy r < 1 in Poincare ball")
    r_eff = 1.0 / torch.clamp(1.0 - radial, min=eps)
    return torch.pow(r_eff, d_hyp * d_hyp)


@dataclass(frozen=True)
class CanonicalState:
    vector: torch.Tensor

    def __post_init__(self) -> None:
        if self.vector.ndim != 1 or self.vector.shape[0] != CANONICAL_DIM:
            raise ValueError(f"Canonical state must be 1D with {CANONICAL_DIM} dims")

    @property
    def tongue_position(self) -> torch.Tensor:
        return self.vector[TONGUE_POSITION_DIMS]

    @property
    def tongue_phase(self) -> torch.Tensor:
        return self.vector[TONGUE_PHASE_DIMS]

    @property
    def telemetry(self) -> torch.Tensor:
        return self.vector[TELEMETRY_DIMS]


def validate_canonical_state(states: torch.Tensor, eps: float = 1e-6) -> Dict[str, float]:
    """Validate canonical 21D vectors and return summary metrics."""
    if states.ndim == 1:
        states = states.unsqueeze(0)
    if states.ndim != 2 or states.shape[1] != CANONICAL_DIM:
        raise ValueError(f"Expected state tensor shape (N, {CANONICAL_DIM}), got {tuple(states.shape)}")

    u = states[:, TONGUE_POSITION_DIMS]
    u_norm = torch.linalg.norm(u, dim=1)
    if torch.any(u_norm >= 1.0):
        max_norm = float(torch.max(u_norm).item())
        raise ValueError(f"Invalid Poincare tongue position norm >= 1: max={max_norm:.6f}")

    coherence = states[:, 13:16]
    if torch.any(coherence < -eps) or torch.any(coherence > 1.0 + eps):
        raise ValueError("coherence channels must be in [0,1]")

    risk = states[:, 16]
    if torch.any(risk < -eps) or torch.any(risk > 1.0 + eps):
        raise ValueError("risk_aggregate must be in [0,1]")

    entropy = states[:, 17]
    if torch.any(entropy < -eps):
        raise ValueError("entropy_density must be >= 0")

    stabilization = states[:, 18]
    if torch.any(stabilization < -eps):
        raise ValueError("stabilization must be >= 0")

    radial_cached = states[:, 19]
    radial_true = u_norm
    radial_err = torch.abs(radial_cached - radial_true)

    harmonic_cached = states[:, 20]
    harmonic_true = harmonic_energy_from_radial(radial_true)
    harmonic_err = torch.abs(harmonic_cached - harmonic_true)

    return {
        "max_u_norm": float(torch.max(u_norm).item()),
        "max_radial_abs_err": float(torch.max(radial_err).item()),
        "max_harmonic_abs_err": float(torch.max(harmonic_err).item()),
    }

