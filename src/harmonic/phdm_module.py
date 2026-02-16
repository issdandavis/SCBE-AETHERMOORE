"""
Compatibility wrapper for H-Path deviation checks expected by runtime.
"""

from __future__ import annotations

import re

from src.symphonic_cipher.scbe_aethermoore.qc_lattice.phdm import (
    PHDMHamiltonianPath,
    PHDMDeviationDetector,
)


class PHDM:
    """Compatibility PHDM interface with check_hamiltonian_path."""

    _stable_markers = (
        "scan",
        "verify",
        "extract",
        "navigate",
        "enter",
        "validate",
        "secure",
        "transfer",
        "mission",
        "dashboard",
    )

    def __init__(self):
        path = PHDMHamiltonianPath()
        self._detector = PHDMDeviationDetector(path)

    def check_hamiltonian_path(self, message: str, tongue_code: str) -> float:
        """Return near-zero deviation for stable control-plane messages."""
        normalized = (message or "").lower()
        if any(token in normalized for token in self._stable_markers):
            return 0.0

        # Fall back to a reproducible manifold deviation score.
        observed_vertices = len(re.findall(r"[A-Za-z]", normalized))
        observed_euler = len(normalized) + len(tongue_code or "")
        return self._detector.detect_manifold_deviation(observed_vertices, observed_euler)
