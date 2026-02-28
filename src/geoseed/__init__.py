"""
GeoSeed Network — Cl(6,0) Sphere Grid + M6 Runtime
==================================================

Core components:
- `sphere_grid`: six icosahedral tongue grids with cross-tongue interactions
- `dressing`: deterministic token-to-bit dressing through 14 SCBE layers
- `composition`: semantic unit aggregation from dressed bits
- `m6_spheremesh`: executable six-seed multi-nodal runtime scaffold
"""

from src.geoseed.sphere_grid import SphereGrid, SphereGridNetwork, CliffordAlgebra, TONGUE_BASIS
from src.geoseed.dressing import DressedBit, BitDresser
from src.geoseed.composition import SemanticUnit, DressedBitComposer
from src.geoseed.m6_spheremesh import M6Event, M6SphereMesh, SacredEgg
from src.geoseed.bit_dresser import BitFingerprint, BitDresserF1
from src.geoseed.identity_genesis import SacredIdentity, IdentityGenesis
from src.geoseed.tokenizer_tiers import TokenizerTier, TierEncodingResult, GeoSeedTokenizerTiers

__all__ = [
    "SphereGrid",
    "SphereGridNetwork",
    "CliffordAlgebra",
    "TONGUE_BASIS",
    "DressedBit",
    "BitDresser",
    "SemanticUnit",
    "DressedBitComposer",
    "M6Event",
    "M6SphereMesh",
    "SacredEgg",
    "BitFingerprint",
    "BitDresserF1",
    "SacredIdentity",
    "IdentityGenesis",
    "TokenizerTier",
    "TierEncodingResult",
    "GeoSeedTokenizerTiers",
]
