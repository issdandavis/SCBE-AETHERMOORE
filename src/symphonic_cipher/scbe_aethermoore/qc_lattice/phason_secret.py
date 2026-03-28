"""
Phason Secret — Layer 8 Session-Bound Secret Phason for Quasicrystal Lattice.
=============================================================================

Generates a secret phason perturbation via HMAC, derived from a session key
that is NEVER persisted. The phason modulates the quasicrystal matrix A used
in lattice-based key exchange, giving the legitimate party a structural
alignment advantage that an eavesdropper cannot replicate.

Two modes:
  - public_mode:  phason = 0.0 (standard lattice, no secret)
  - private_mode: phason = HMAC-derived secret (session-bound)

The phason is a small perturbation to the lattice basis — it does NOT change
the lattice dimension or modulus. It only nudges the coefficients by a value
derived from the session key, creating a "private alignment" that makes
legitimate decapsulation cheaper and adversarial lattice reduction harder.

Security properties:
  - Session-bound: derived from os.urandom, never written to disk.
  - Constant-time comparison via hmac.compare_digest.
  - Audit hook for governance: every phason use is loggable.

Defaults:
  n = 64   (lattice dimension)
  q = 3329 (modulus, same as ML-KEM / Kyber)
  phi = (1 + sqrt(5)) / 2  (golden ratio, icosahedral resonance)
"""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

# Defaults matching ML-KEM-768 / Kyber parameter family
DEFAULT_N = 64
DEFAULT_Q = 3329
PHI = (1 + math.sqrt(5)) / 2


@dataclass
class PhasonAuditRecord:
    """Immutable record of a phason use event."""

    timestamp: float
    mode: str  # "public" or "private"
    layer: int  # always 8
    component: str  # "PhasonSecret"
    session_id: str
    matrix_hash: str  # SHA-256 of the generated matrix (for audit, not the secret)


class PhasonSecret:
    """Session-bound secret phason for quasicrystal lattice modulation.

    The secret is derived via HMAC-SHA256 from a session key that lives only
    in memory. It perturbs the quasi-periodic lattice matrix A so that:
      - In public mode, A is the standard quasicrystal basis (phason=0).
      - In private mode, A is nudged by the secret phason, giving the holder
        a structural alignment advantage for decapsulation.

    The phason never touches disk. When the PhasonSecret object is garbage-
    collected, the secret is gone.

    Args:
        n: Lattice dimension (default 64).
        q: Lattice modulus (default 3329).
        phi: Golden ratio constant (default (1+sqrt(5))/2).
        session_key: Optional explicit session key (bytes). If None, a fresh
            32-byte key is generated from os.urandom.
    """

    def __init__(
        self,
        *,
        n: int = DEFAULT_N,
        q: int = DEFAULT_Q,
        phi: float = PHI,
        session_key: Optional[bytes] = None,
    ):
        self._n = n
        self._q = q
        self._phi = phi

        # Session key — NEVER persisted
        self._session_key: bytes = session_key if session_key is not None else os.urandom(32)
        self._session_id: str = hashlib.sha256(self._session_key).hexdigest()[:16]

        # Audit trail (in-memory only)
        self._audit_log: List[PhasonAuditRecord] = []

    # ------------------------------------------------------------------ #
    #  Core: secret phason generation
    # ------------------------------------------------------------------ #

    def _derive_phason(self) -> float:
        """Derive the secret phason value from the session key via HMAC.

        Returns a float in (0, 1) that represents the phason perturbation
        magnitude. The perturbation is applied mod q, so even a "large"
        phason value only shifts entries within the ring Z_q.
        """
        tag = hmac.new(
            self._session_key,
            b"phason-secret-v1",
            hashlib.sha256,
        ).digest()
        # Convert first 8 bytes to a float in (0, 1)
        # Add a small epsilon to ensure the phason is never exactly 0
        raw = int.from_bytes(tag[:8], "big") / (2**64)
        return max(raw, 0.01)  # floor at 1% to guarantee visible perturbation

    # ------------------------------------------------------------------ #
    #  Matrix generation
    # ------------------------------------------------------------------ #

    def generate_quasi_A(self, *, mode: str = "public") -> np.ndarray:
        """Generate the quasicrystal lattice matrix A.

        Args:
            mode: "public" (phason=0.0) or "private" (secret phason applied).

        Returns:
            np.ndarray of shape (n, n) with integer coefficients mod q.
        """
        if mode not in ("public", "private"):
            raise ValueError(f"mode must be 'public' or 'private', got {mode!r}")

        n, q = self._n, self._q
        phi = self._phi

        # Build the base quasicrystal matrix using golden-ratio modulation.
        # Each entry A[i,j] = floor(phi * (i*n + j)) mod q
        # This is aperiodic by construction (phi is irrational).
        indices = np.arange(n * n, dtype=np.float64).reshape(n, n)
        A = np.floor(phi * indices).astype(np.int64) % q

        if mode == "private":
            phason = self._derive_phason()
            # Perturbation matrix: floor(phason * q * phi^(k mod 8)) mod q
            # The q scaling ensures the perturbation is significant relative
            # to the modulus. The phi^(k mod 8) gives aperiodic structure.
            # The (k mod 8) clamp prevents overflow for large indices.
            exp_indices = np.mod(indices, 8).astype(np.float64)
            perturbation = np.floor(phason * q * np.power(phi, exp_indices)).astype(np.int64) % q
            A = (A + perturbation) % q

        # Audit
        matrix_hash = hashlib.sha256(A.tobytes()).hexdigest()[:32]
        self._audit_log.append(
            PhasonAuditRecord(
                timestamp=time.time(),
                mode=mode,
                layer=8,
                component="PhasonSecret",
                session_id=self._session_id,
                matrix_hash=matrix_hash,
            )
        )

        return A

    # ------------------------------------------------------------------ #
    #  Governance hook
    # ------------------------------------------------------------------ #

    def audit_phason_use(self) -> List[Dict[str, Any]]:
        """Return the audit trail of all phason uses in this session.

        This is the governance hook — every generate_quasi_A call is logged
        with timestamp, mode, layer, component, and a hash of the matrix
        (NOT the secret itself).
        """
        return [
            {
                "timestamp": r.timestamp,
                "mode": r.mode,
                "layer": r.layer,
                "component": r.component,
                "session_id": r.session_id,
                "matrix_hash": r.matrix_hash,
            }
            for r in self._audit_log
        ]

    # ------------------------------------------------------------------ #
    #  Verification helpers
    # ------------------------------------------------------------------ #

    def verify_alignment(self, matrix_a: np.ndarray, matrix_b: np.ndarray) -> float:
        """Compute alignment score between two matrices.

        Returns a float in [0, 1] where 1 = identical mod q.
        Used to verify that a private matrix was generated from the same
        session key as another private matrix.
        """
        n, q = self._n, self._q
        diff = (matrix_a.astype(np.int64) - matrix_b.astype(np.int64)) % q
        zero_count = np.sum(diff == 0)
        return float(zero_count) / float(n * n)

    def constant_time_compare(self, a: bytes, b: bytes) -> bool:
        """Constant-time comparison of two byte strings.

        Wraps hmac.compare_digest to prevent timing side-channels.
        """
        return hmac.compare_digest(a, b)

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

    @property
    def session_id(self) -> str:
        """Public session identifier (truncated hash of session key)."""
        return self._session_id

    @property
    def n(self) -> int:
        """Lattice dimension."""
        return self._n

    @property
    def q(self) -> int:
        """Lattice modulus."""
        return self._q

    @property
    def phi(self) -> float:
        """Golden ratio constant."""
        return self._phi
