"""
Aethermoore Math Library
========================

Core mathematical primitives for SCBE-AETHERMOORE:
- Hyperbolic geometry (Poincare ball model)
- Sacred Eggs (cryptographic containers with ritual hatching)
- GeoSeal (geographic + geometric sealing)
- Sacred Tongues tokenization and cross-translation
"""

from .sacred_eggs import SacredEgg, SacredEggIntegrator, HatchResult

__all__ = ["SacredEgg", "SacredEggIntegrator", "HatchResult"]
