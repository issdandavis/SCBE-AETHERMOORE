from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional

import torch

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2

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


# ---------------------------------------------------------------------------
# Layer 4: Gacha Floor & Monster Embedding
# ---------------------------------------------------------------------------

# Monster type -> system bug mapping (from Isekai Game Design)
MONSTER_BUG_MAP = {
    "glitchling": "null_pointer",
    "drift_maw": "float_precision",
    "echo_wraith": "race_condition",
    "leak_slime": "memory_leak",
    "phantom_fork": "forked_state",
    "hollow_sprite": "cross_boundary_exploit",
}


def embed_gacha_floor(
    floor_id: int,
    monster_bug: Dict[str, float],
    seed: Optional[int] = None,
) -> torch.Tensor:
    """Embed a gacha tower floor + monster into 21D canonical state.

    The floor_id determines base tongue-subspace position in B^6.
    The monster bug coefficients perturb the embedding — near-boundary
    bugs (high coefficients) produce high harmonic wall cost, making
    edge-case failures expensive to exploit.

    Args:
        floor_id: Tower floor number (1-indexed).
        monster_bug: Dict with keys 'a', 'b', 'c' (quadratic coefficients
                     representing the math-monster) and 'type' (bug name).
        seed: Optional RNG seed for reproducibility.

    Returns:
        21D canonical state tensor for this floor encounter.
    """
    gen = torch.Generator()
    if seed is not None:
        gen.manual_seed(seed)
    else:
        gen.manual_seed(floor_id * 7919)  # Deterministic per floor

    # Base tongue position — small norm, inside Poincaré ball
    u = torch.randn(6, generator=gen) * 0.08
    # Scale by floor depth — deeper floors drift closer to boundary
    floor_scale = min(0.9, 0.05 * math.log1p(floor_id))
    u = u * (1.0 + floor_scale)

    # Monster bug perturbation — quadratic coefficients as Hamiltonian path offset
    a = monster_bug.get("a", 1.0)
    b = monster_bug.get("b", 0.0)
    c = monster_bug.get("c", 0.0)
    delta = torch.tensor([a, b, c, 0.0, 0.0, 0.0], dtype=torch.float32)
    u = u + delta * 0.05  # A4: Clamping — small perturbation

    # Clamp inside Poincaré ball (r < 1)
    u_norm = torch.linalg.norm(u)
    if u_norm >= 0.95:
        u = u * (0.94 / u_norm)
    u_norm = torch.linalg.norm(u)

    # Tongue phase — floor-dependent oscillation
    phase = torch.zeros(6)
    for i in range(6):
        phase[i] = math.sin(floor_id * PHI ** i) * 0.5

    # Telemetry dims [12-20] — 9 dimensions total
    # dim 12: intent signal (floor difficulty normalized)
    intent = torch.tensor([min(1.0, floor_id / 100.0)])
    # dims 13-15: coherence (spectral/spin/temporal)
    coherence = torch.tensor([0.8, 0.7, 0.9])
    # dim 16: risk aggregate
    risk = torch.tensor([min(1.0, floor_id / 100.0)])
    # dim 17: entropy density (bug complexity -> entropy)
    entropy = torch.tensor([abs(a * 0.1 + b * 0.05)])
    # dim 18: stabilization
    stabilization = torch.tensor([max(0.0, 1.0 - floor_id / 50.0)])
    # dim 19: radial cache
    radial = torch.tensor([float(u_norm)])
    # dim 20: harmonic energy cache
    harmonic = harmonic_energy_from_radial(radial)

    vector = torch.cat([u, phase, intent, coherence, risk, entropy, stabilization, radial, harmonic])

    bug_type = monster_bug.get("type", "unknown")
    logger.info(
        "Layer 4 floor %d embedded: norm=%.3f, bug_type=%s",
        floor_id, float(u_norm), bug_type,
    )
    return vector


def compute_squad_ds_squared(
    state_a: torch.Tensor,
    state_b: torch.Tensor,
    eps: float = 1e-12,
) -> Dict[str, float]:
    """Compute ds² between two 21D canonical states for squad path integrity.

    Used by Layer 11 squad combat to validate Hamiltonian paths between
    squad members and enemies.
    """
    u = state_a[TONGUE_POSITION_DIMS]
    v = state_b[TONGUE_POSITION_DIMS]
    diff = u - v
    eucl_sq = float(torch.sum(diff * diff))
    u_norm_sq = float(torch.sum(u * u))
    v_norm_sq = float(torch.sum(v * v))

    # Poincaré distance
    denom = max(eps, (1.0 - u_norm_sq) * (1.0 - v_norm_sq))
    arg = 1.0 + 2.0 * eucl_sq / denom
    d_h = float(math.acosh(max(1.0, arg)))

    # Boundary amplification
    boundary_r = max(math.sqrt(u_norm_sq), math.sqrt(v_norm_sq))
    amp = 1.0 / max(eps, 1.0 - boundary_r * boundary_r)

    total = amp * d_h * d_h
    return {
        "total": total,
        "hyperbolic_distance": d_h,
        "boundary_amplification": amp,
    }


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

