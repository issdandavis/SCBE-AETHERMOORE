"""
Dynosphere — 3D Sphere ↔ Sacred Tongue ↔ 21D Canonical State Mapper
====================================================================

Maps between three coordinate systems:
  1. 3D unit sphere (dynosphere surface)
  2. 6 Sacred Tongue projections (phi-weighted)
  3. 21D Canonical Brain State (UnifiedBrainState)

@layer L5, L6, L9, L12
@component Dynosphere.Mapper
"""

from .mapper import (
    DynosphereMapper,
    DynospherePoint,
    TongueProjection,
    CanonicalLift,
    DynosphereState21Payload,
    project_to_tongues,
    state21_payload_from_point,
    lift_to_21d,
    round_trip_3d,
)

__all__ = [
    "DynosphereMapper",
    "DynospherePoint",
    "TongueProjection",
    "CanonicalLift",
    "DynosphereState21Payload",
    "project_to_tongues",
    "state21_payload_from_point",
    "lift_to_21d",
    "round_trip_3d",
]
