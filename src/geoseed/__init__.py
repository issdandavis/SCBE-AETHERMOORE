"""GeoSeed geometry helpers.

The package keeps imports lazy so `python -m src.geoseed.orbital_model` can run
without re-import warnings.
"""

from typing import Any

__all__ = [
    "AtomTransferRecorder",
    "PHI",
    "LN_PHI",
    "TONGUES",
    "GeoSeedOrbital",
    "TransferEvent",
    "TransferMatrix",
    "build_geoseed_orbitals",
    "hyperbolic_distance",
    "inter_shell_geodesic",
    "normalize_tongue",
    "orbital_summary",
    "phi_to_poincare_r",
    "transfer_cost",
]


def __getattr__(name: str) -> Any:
    if name in {
        "PHI",
        "TONGUES",
        "GeoSeedOrbital",
        "build_geoseed_orbitals",
        "hyperbolic_distance",
        "inter_shell_geodesic",
        "orbital_summary",
        "phi_to_poincare_r",
    }:
        from . import orbital_model

        return getattr(orbital_model, name)
    if name in {
        "AtomTransferRecorder",
        "LN_PHI",
        "TransferEvent",
        "TransferMatrix",
        "normalize_tongue",
        "transfer_cost",
    }:
        from . import transfer_recorder

        return getattr(transfer_recorder, name)
    raise AttributeError(name)
