"""GeoSeed geometry helpers.

The package keeps imports lazy so `python -m src.geoseed.orbital_model` can run
without re-import warnings.
"""

from typing import Any

__all__ = [
    "PHI",
    "TONGUES",
    "GeoSeedOrbital",
    "build_geoseed_orbitals",
    "hyperbolic_distance",
    "inter_shell_geodesic",
    "orbital_summary",
    "phi_to_poincare_r",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import orbital_model

        return getattr(orbital_model, name)
    raise AttributeError(name)
