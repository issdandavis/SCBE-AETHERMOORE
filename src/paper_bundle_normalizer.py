"""
Paper Bundle Normalizer
=======================

GeoSeal-adjacent normalization for aggregated bundles using existing
quasicrystal gate validation primitives.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, Mapping, Sequence

from src.symphonic_cipher.scbe_aethermoore.qc_lattice.quasicrystal import (
    QuasicrystalLattice,
    ValidationStatus,
)


def _gate_vector_from_value(value: Any, width: int = 6) -> Sequence[int]:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    # Keep bounded integer gates in [0, 15]
    return [int(digest[i] % 16) for i in range(width)]


def _bounded_cost(norm_ratio: float) -> float:
    exponent = min(20.0, float(norm_ratio * norm_ratio * 8.0))
    return float(math.exp(exponent))


def normalize_bundle(
    bundle: Mapping[str, Any],
    norm_threshold: float = 0.95,
) -> Dict[str, Any]:
    lattice = QuasicrystalLattice()
    sections: Dict[str, Dict[str, Any]] = {}
    quarantined = []

    for key, value in bundle.items():
        gates = _gate_vector_from_value(value)
        result = lattice.validate_gates(list(gates))
        point = result.lattice_point
        norm_ratio = point.distance_to_window / max(lattice.acceptance_radius, 1e-9)
        cost = _bounded_cost(norm_ratio)

        is_quarantine = (
            result.status != ValidationStatus.VALID or norm_ratio > norm_threshold
        )
        if is_quarantine:
            quarantined.append(key)

        sections[key] = {
            "gate_vector": list(gates),
            "validation_status": result.status.value,
            "distance_to_window": float(point.distance_to_window),
            "norm_ratio": float(norm_ratio),
            "cost": cost,
        }

    bundle_hash = hashlib.sha256(
        json.dumps(bundle, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    return {
        "status": "QUARANTINE" if quarantined else "ALLOW",
        "bundle_hash": bundle_hash,
        "quarantined": quarantined,
        "sections": sections,
    }
