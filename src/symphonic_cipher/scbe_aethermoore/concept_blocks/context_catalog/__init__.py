"""
SCBE Context Catalog
=====================

Maps complex task archetypes (derived from Endless Sky game systems,
PHDM brain architecture, and Spiralverse fleet coordination) to
MMCCL credit categories and PHDM polyhedral regions.

The catalog serves as a **reusable template library** for AI agents:
- Each entry describes a complex task pattern
- Maps to a PHDM polyhedron (cognitive region)
- Assigns a Sacred Tongue denomination (neurotransmitter type)
- Defines credit cost parameters (energy, complexity, legibility)
- Links to governance constraints (which SCBE layers must be active)

Usage::

    from .catalog import ContextCatalog, TaskArchetype
    catalog = ContextCatalog()
    archetype = catalog.get("TRADE_ARBITRAGE")
    print(archetype.denomination)  # "CA" (Cassisivadan — math/bitcraft)
    print(archetype.polyhedron)    # "rhombic_dodecahedron" (space-filling logic)
"""

from .catalog import (
    ContextCatalog,
    TaskArchetype,
    PolyhedronType,
    ComplexityTier,
    SourceDomain,
    ARCHETYPE_REGISTRY,
)

__all__ = [
    "ContextCatalog",
    "TaskArchetype",
    "PolyhedronType",
    "ComplexityTier",
    "SourceDomain",
    "ARCHETYPE_REGISTRY",
]
