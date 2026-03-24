"""
Cross-Domain Dimensional Mapping (CDDM) Framework
===================================================

Category-theoretic library for mapping structural forms across domains.

Maps energy <-> motivation <-> incentive, entropy <-> plot chaos <-> policy
breakdown, momentum <-> organizational inertia, etc. through rigorous
mathematical morphisms with bounds validation, invertibility checks,
and categorical composition.

Pure stdlib. No external dependencies.

@module cddm
@layer Layer 1, Layer 5, Layer 9
@component Cross-Domain Dimensional Mapping
@version 1.0.0
"""

from .domain import Domain, DomainError
from .morphism import Morphism, MorphismError
from .functor import (
    CompositionChain,
    DomainGraph,
    GraphIsomorphism,
    compose,
    identity_morphism,
)
from .tongue_domains import (
    TONGUE_DOMAINS,
    CROSS_DOMAIN_MAP,
    tongue_domain,
    all_tongue_morphisms,
)

__all__ = [
    "Domain",
    "DomainError",
    "Morphism",
    "MorphismError",
    "CompositionChain",
    "DomainGraph",
    "GraphIsomorphism",
    "compose",
    "identity_morphism",
    "TONGUE_DOMAINS",
    "CROSS_DOMAIN_MAP",
    "tongue_domain",
    "all_tongue_morphisms",
]
