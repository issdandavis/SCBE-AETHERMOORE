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

    def __init__(self):
        path = PHDMHamiltonianPath()
        self._detector = PHDMDeviationDetector(path)

    def check_hamiltonian_path(self, message: str, tongue_code: str) -> float:
        """Return a reproducible text-shape heuristic, never an authorization.

        Message words are caller-controlled. No keyword may bypass the detector
        or establish that an actual control-flow path is valid.
        """
        normalized = (message or "").lower()
        # These counts are proxies, not observed graph vertices or Euler data.
        observed_vertices = len(re.findall(r"[A-Za-z]", normalized))
        observed_euler = len(normalized) + len(tongue_code or "")
        return self._detector.detect_manifold_deviation(observed_vertices, observed_euler)
