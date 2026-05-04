"""SCBE 9D State Engine

Construct and evolve the 9-dimensional state vector xi = [c(t), tau(t), eta(t), q(t)]
that drives SCBE-AETHERMOORE governance decisions.

State Vector Layout
-------------------
xi[0..5] = c(t)   — 6D Context Vector
xi[6]    = τ(t)   — Time dimension
xi[7]    = η(t)   — Entropy dimension
xi[8]    = q(t)   — Quantum state (complex)

Workflow
--------
1. Generate 6D context vector from current time t.
2. Compute Shannon entropy of context vector.
3. Evolve quantum state from initial condition.
4. Pack into 9-element numpy array (mixed dtype via object).
5. Pass to governance gate for evaluation.

@module scbe.state9d_engine
@layer L7-L9 (State evolution)
"""

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PHI = (1.0 + math.sqrt(5.0)) / 2.0
R = PHI
TAU_COH = 0.9
ETA_TARGET = 4.0
BETA = 0.1
ETA_MIN = 2.0
ETA_MAX = 6.0
DELTA_DRIFT_MAX = 0.5
OMEGA_TIME = 2.0 * math.pi / 60.0
NUM_BINS = 16
INTENT_PHASE = np.exp(1j * 2.0 * np.pi * 0.75)


# ---------------------------------------------------------------------------
# 6D Context Vector
# ---------------------------------------------------------------------------
def build_context_vector(
    t: float,
    *,
    trajectory_score: float = 0.95,
    commitment_str: str = "",
    signature_validity: float = 1.0,
) -> np.ndarray:
    """Generate the 6D context vector c(t).

    | Index | Name               | Type    | Description                        |
    |-------|--------------------|---------|------------------------------------|
    | v1    | Identity           | float   | sin(t) — identity oscillation      |
    | v2    | Intent Phase       | complex | e^(i·2π·0.75) — intent as phase    |
    | v3    | Trajectory Score   | float   | EWMA score (e.g. 0.95)            |
    | v4    | Linear Time        | float   | Raw timestamp t                    |
    | v5    | Commitment Hash    | float   | SHA-256 of commit_t normalized     |
    | v6    | Signature Validity | float   | Validity score ∈ [0, 1]           |

    Uses ``dtype=object`` to hold mixed float/complex types.
    """
    v1 = math.sin(t)
    v2 = INTENT_PHASE
    v3 = float(np.clip(trajectory_score, 0.0, 1.0))
    v4 = float(t)

    if commitment_str:
        digest = hashlib.sha256(commitment_str.encode("utf-8")).digest()
        # Normalize to [0, 1) using full 256-bit range
        v5 = int.from_bytes(digest, "big") / (2**256)
    else:
        v5 = 0.0

    v6 = float(np.clip(signature_validity, 0.0, 1.0))

    return np.array([v1, v2, v3, v4, v5, v6], dtype=object)


# ---------------------------------------------------------------------------
# Shannon Entropy
# ---------------------------------------------------------------------------
def _flatten_for_entropy(c: np.ndarray) -> np.ndarray:
    """Flatten context vector: complex → magnitude, reals → float."""
    flat = np.empty(len(c), dtype=float)
    for i, val in enumerate(c):
        if isinstance(val, (complex, np.complexfloating)):
            flat[i] = abs(val)
        else:
            flat[i] = float(val)
    return flat


def compute_shannon_entropy(
    c: np.ndarray,
    num_bins: int = NUM_BINS,
    normalize: bool = True,
) -> float:
    """Compute Shannon entropy of the context vector.

    Steps:
      1. Flatten (complex → magnitude).
      2. Optionally normalize to [0, 1] so the histogram is not dominated
         by large-magnitude components (e.g. raw Unix timestamps).
      3. Build a density-normalized histogram with *num_bins* bins.
      4. η = -Σ p·log₂(p + 1e-9) over non-zero bins.

    Args:
        c: 6D context vector (dtype=object, mixed float/complex).
        num_bins: Number of histogram bins.
        normalize: If True (default), rescale values to [0, 1] before
            binning so entropy reflects the *shape* of the distribution
            rather than absolute scale.

    Returns:
        Shannon entropy in bits.
    """
    flat = _flatten_for_entropy(c)

    # Guard against all-identical values
    min_val = float(flat.min())
    max_val = float(flat.max())
    if max_val - min_val < 1e-12:
        return 0.0

    if normalize:
        samples = (flat - min_val) / (max_val - min_val)
        hist_range = (0.0, 1.0)
    else:
        samples = flat
        hist_range = (min_val, max_val)

    hist, _ = np.histogram(
        samples, bins=num_bins, range=hist_range, density=True
    )

    # Convert density to probabilities
    bin_width = (hist_range[1] - hist_range[0]) / num_bins
    p = hist * bin_width

    p_nonzero = p[p > 1e-12]
    entropy = -np.sum(p_nonzero * np.log2(p_nonzero + 1e-9))
    return float(entropy)


# ---------------------------------------------------------------------------
# 7th Dimension — Time Flow
# ---------------------------------------------------------------------------
def evolve_time(t: float) -> float:
    r"""Evolve time dimension τ(t).

    τ̇(t) = 1.0 + DELTA_DRIFT_MAX · sin(OMEGA_TIME · t)

    Integrated analytically:
        τ(t) = t + (DELTA_DRIFT_MAX / OMEGA_TIME) · (1 - cos(OMEGA_TIME · t))

    Causality requires τ̇ > 0.  Since DELTA_DRIFT_MAX = 0.5 < 1, this holds.
    """
    tau = t + (DELTA_DRIFT_MAX / OMEGA_TIME) * (1.0 - math.cos(OMEGA_TIME * t))
    return float(tau)


def time_flow_rate(t: float) -> float:
    """Return τ̇(t) (useful for verifying causality)."""
    return 1.0 + DELTA_DRIFT_MAX * math.sin(OMEGA_TIME * t)


# ---------------------------------------------------------------------------
# 8th Dimension — Entropy Flow (ODE model)
# ---------------------------------------------------------------------------
def evolve_entropy_ode(t: float, eta0: Optional[float] = None) -> float:
    r"""Evolve entropy via Ornstein-Uhlenbeck drift with periodic perturbation.

    η̇ = BETA · (ETA_TARGET - η) + 0.1 · sin(t)

    Analytical solution for initial condition η(0) = *eta0*:

        η(t) = ETA_TARGET
               + (0.1 / (BETA² + 1)) · (BETA·sin(t) - cos(t))
               + C · exp(-BETA·t)

    where C = eta0 - ETA_TARGET + 0.1 / (BETA² + 1).

    The result is clipped to [ETA_MIN, ETA_MAX].
    """
    if eta0 is None:
        eta0 = ETA_TARGET

    denom = BETA**2 + 1.0
    particular = ETA_TARGET + (0.1 / denom) * (BETA * math.sin(t) - math.cos(t))
    C = eta0 - ETA_TARGET + (0.1 / denom)
    eta = particular + C * math.exp(-BETA * t)
    return float(np.clip(eta, ETA_MIN, ETA_MAX))


# ---------------------------------------------------------------------------
# 9th Dimension — Quantum Evolution
# ---------------------------------------------------------------------------
def evolve_quantum_state(q0: complex, H: float, t: float) -> complex:
    r"""Evolve quantum state under unitary evolution.

    q(t) = q₀ · e^(-i·H·t)

    Unitary evolution preserves normalization: |q(t)| = |q₀|.
    """
    return complex(q0 * np.exp(-1j * H * t))


def quantum_norm(q: complex) -> float:
    """Return |q|² (probability density)."""
    return abs(q) ** 2


# ---------------------------------------------------------------------------
# Full 9D Assembly
# ---------------------------------------------------------------------------
def assemble_state_vector(
    t: float,
    *,
    q0: complex = 1 + 0j,
    H: float = 1.0,
    trajectory_score: float = 0.95,
    commitment_str: str = "",
    signature_validity: float = 1.0,
    use_ode_entropy: bool = False,
    eta0: Optional[float] = None,
) -> np.ndarray:
    """Assemble the full 9D state vector xi.

    xi[0..5] = c(t)   — 6D Context Vector
    xi[6]    = τ(t)   — Time dimension
    xi[7]    = η(t)   — Entropy dimension
    xi[8]    = q(t)   — Quantum state (complex)

    Args:
        t: Current time (seconds or arbitrary continuous variable).
        q0: Initial quantum state (default 1+0j).
        H: Hamiltonian scalar (default 1.0).
        trajectory_score: EWMA trajectory score ∈ [0, 1].
        commitment_str: Commitment string to hash for v5.
        signature_validity: Signature validity ∈ [0, 1].
        use_ode_entropy: If True, use the ODE entropy model instead of
            the Shannon entropy of the context vector.
        eta0: Initial entropy for the ODE model (default ETA_TARGET).

    Returns:
        9-element numpy array with ``dtype=object``.
    """
    # 1. Generate 6D context vector
    c = build_context_vector(
        t,
        trajectory_score=trajectory_score,
        commitment_str=commitment_str,
        signature_validity=signature_validity,
    )

    # 2. Compute entropy
    if use_ode_entropy:
        eta = evolve_entropy_ode(t, eta0)
    else:
        eta = compute_shannon_entropy(c)

    # 3. Evolve quantum state
    q = evolve_quantum_state(q0, H, t)

    # 4. Evolve time
    tau = evolve_time(t)

    # 5. Pack into 9-element array
    xi = np.empty(9, dtype=object)
    xi[0:6] = c
    xi[6] = tau
    xi[7] = eta
    xi[8] = q

    return xi


# ---------------------------------------------------------------------------
# Convenience dataclass for governance integration
# ---------------------------------------------------------------------------
@dataclass
class State9D:
    """Typed wrapper around the 9D state vector."""

    xi: np.ndarray

    def __post_init__(self):
        if self.xi.shape != (9,) or self.xi.dtype != object:
            raise ValueError("State vector must be a 9-element object array")

    @property
    def context(self) -> np.ndarray:
        """6D context vector c(t)."""
        return self.xi[0:6]

    @property
    def tau(self) -> float:
        """Time dimension τ(t)."""
        return float(self.xi[6])

    @property
    def eta(self) -> float:
        """Entropy dimension η(t)."""
        return float(self.xi[7])

    @property
    def q(self) -> complex:
        """Quantum state q(t)."""
        return complex(self.xi[8])

    @property
    def is_coherent(self) -> bool:
        """Return True if quantum coherence exceeds TAU_COH."""
        return quantum_norm(self.q) >= TAU_COH

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "context": [self._serialize(v) for v in self.context],
            "tau": self.tau,
            "eta": self.eta,
            "q": {"real": self.q.real, "imag": self.q.imag, "norm": quantum_norm(self.q)},
            "coherent": self.is_coherent,
        }

    @staticmethod
    def _serialize(val: Any) -> Any:
        if isinstance(val, (complex, np.complexfloating)):
            return {"real": val.real, "imag": val.imag}
        return float(val)

    @classmethod
    def from_params(
        cls,
        t: float,
        **kwargs: Any,
    ) -> "State9D":
        """Build a State9D from evolution parameters."""
        xi = assemble_state_vector(t, **kwargs)
        return cls(xi)
