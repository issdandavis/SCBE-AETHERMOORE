"""Web Reconnaissance Engine for the Obsidian Researcher Agent.

Provides site profiling, semantic page analysis, visual minimap rendering,
in-memory caching, adaptive extraction, and SCBE-governed orchestration
for ethical, structured web research.

All modules are pure stdlib -- no external dependencies.
"""

from .site_recon import RateLimitState, SiteProfile, SiteProfileBuilder
from .recon_goggles import SemanticNode, SemanticSkeleton, ReconGoggles
from .pixel_scanner import PixelScanner
from .site_skimmer import CachedPage, DomainCache, SiteSkimmer
from .site_adapter import ExtractionRule, SiteAdapter, AdaptiveToolBuilder, KNOWN_ADAPTERS
from .governed_recon import GovernedRecon, SENSITIVITY_MAP

__all__ = [
    "RateLimitState", "SiteProfile", "SiteProfileBuilder",
    "SemanticNode", "SemanticSkeleton", "ReconGoggles",
    "PixelScanner",
    "CachedPage", "DomainCache", "SiteSkimmer",
    "ExtractionRule", "SiteAdapter", "AdaptiveToolBuilder", "KNOWN_ADAPTERS",
    "GovernedRecon", "SENSITIVITY_MAP",
]
