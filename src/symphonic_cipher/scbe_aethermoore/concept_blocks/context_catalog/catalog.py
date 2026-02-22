"""
Context Catalog — Task Archetype Registry
============================================

Maps complex task patterns from multiple domains into SCBE-AETHERMOORE
governance categories.  Each archetype defines:

- **Source domain**: Which real system inspired this pattern
  (Endless Sky, Spiralverse, PHDM brain, web agent, etc.)
- **PHDM polyhedron**: Which cognitive region handles this task type
- **Sacred Tongue**: Which denomination/neurotransmitter governs it
- **SCBE layers**: Which governance layers must be active
- **Credit parameters**: Energy cost range, complexity tier, legibility
- **Governance constraints**: What conditions must hold

Derived from:
- Endless Sky (issdandavis/endless-sky): economy, factions, AI, missions
- PHDM v3.0.0: 16 polyhedral cognitive regions
- Spiralverse Protocol: fleet coordination, 6D navigation
- Six Tongues + GeoSeal: tokenization, context-aware encryption
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Enums
# ---------------------------------------------------------------------------

class PolyhedronType(str, Enum):
    """16 PHDM cognitive polyhedra mapped to task archetypes."""
    # Core: Limbic System (5 Platonic Solids) — r < 0.2
    TETRAHEDRON = "tetrahedron"                     # Fundamental truth
    CUBE = "cube"                                    # Stable facts
    OCTAHEDRON = "octahedron"                       # Binary decisions
    DODECAHEDRON = "dodecahedron"                   # Complex rules
    ICOSAHEDRON = "icosahedron"                     # Multi-modal integration

    # Cortex: Processing Layer (3 Archimedean) — 0.3 < r < 0.6
    TRUNCATED_ICOSAHEDRON = "truncated_icosahedron" # Multi-step planning
    RHOMBICUBOCTAHEDRON = "rhombicuboctahedron"     # Concept bridging
    SNUB_DODECAHEDRON = "snub_dodecahedron"         # Creative synthesis

    # Subconscious: Risk Zone (2 Kepler-Poinsot) — 0.8 < r < 0.95
    SMALL_STELLATED = "small_stellated_dodecahedron"  # High-risk abstract
    GREAT_STELLATED = "great_stellated_dodecahedron"  # Adversarial detection

    # Cerebellum: Recursive (2 Toroidal)
    SZILASSI = "szilassi"                           # Self-diagnostic
    CSASZAR = "csaszar"                             # Recursive processing

    # Connectome: Neural Bridges (4 Johnson/Rhombic)
    RHOMBIC_DODECAHEDRON = "rhombic_dodecahedron"   # Space-filling logic
    RHOMBIC_TRIACONTAHEDRON = "rhombic_triacontahedron"  # Pattern matching
    JOHNSON_A = "johnson_a"                         # Domain transition A
    JOHNSON_B = "johnson_b"                         # Domain transition B


class ComplexityTier(str, Enum):
    """How many SCBE layers are typically involved."""
    TRIVIAL = "trivial"       # 1-3 layers, r < 0.3
    STANDARD = "standard"     # 4-7 layers, r < 0.5
    COMPLEX = "complex"       # 8-11 layers, r < 0.7
    EXTREME = "extreme"       # 12-14 layers, r < 0.9
    FORBIDDEN = "forbidden"   # Wall zone, r → 1.0


class SourceDomain(str, Enum):
    """Where the task pattern was derived from."""
    ENDLESS_SKY = "endless_sky"
    PHDM_BRAIN = "phdm_brain"
    SPIRALVERSE = "spiralverse"
    SIX_TONGUES = "six_tongues"
    WEB_AGENT = "web_agent"
    MMCCL = "mmccl"
    GOVERNANCE = "governance"


# ---------------------------------------------------------------------------
#  Task Archetype
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaskArchetype:
    """
    A reusable template for a complex task category.

    Maps a real-world task pattern to SCBE governance structures.
    """
    # Identity
    archetype_id: str                    # e.g. "TRADE_ARBITRAGE"
    name: str                            # Human-readable name
    description: str                     # What this task pattern does
    source_domain: SourceDomain          # Where it came from

    # PHDM mapping
    polyhedron: PolyhedronType           # Which brain region
    radial_zone: Tuple[float, float]     # (min_r, max_r) in Poincaré ball

    # Sacred Tongue / MMCCL
    denomination: str                    # KO/AV/RU/CA/UM/DR
    tongue_weight: float                 # Golden ratio weight

    # Governance
    required_layers: FrozenSet[int]      # Which SCBE layers must be active
    complexity_tier: ComplexityTier      # How complex
    min_governance_verdict: str          # ALLOW / QUARANTINE needed

    # Credit parameters
    energy_range: Tuple[float, float]    # (min_H, max_H) Hamiltonian range
    base_legibility: float               # Default legibility [0,1]

    # Endless Sky analog (if applicable)
    es_system: str = ""                  # Which ES system maps here
    es_commodities: Tuple[str, ...] = () # Related ES commodities

    # Spiralverse analog
    sv_tongue: str = ""                  # Which SV tongue applies
    sv_dimension: str = ""               # Which 6D dimension

    # Tags for search
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype_id": self.archetype_id,
            "name": self.name,
            "description": self.description,
            "source_domain": self.source_domain.value,
            "polyhedron": self.polyhedron.value,
            "radial_zone": list(self.radial_zone),
            "denomination": self.denomination,
            "tongue_weight": self.tongue_weight,
            "required_layers": sorted(self.required_layers),
            "complexity_tier": self.complexity_tier.value,
            "energy_range": list(self.energy_range),
            "base_legibility": self.base_legibility,
            "es_system": self.es_system,
            "sv_tongue": self.sv_tongue,
            "tags": list(self.tags),
        }


# ---------------------------------------------------------------------------
#  Archetype Registry — the catalog
# ---------------------------------------------------------------------------

ARCHETYPE_REGISTRY: Dict[str, TaskArchetype] = {}


def _register(a: TaskArchetype) -> TaskArchetype:
    ARCHETYPE_REGISTRY[a.archetype_id] = a
    return a


# ═══════════════════════════════════════════════════════════════════════════
#  ECONOMY / TRADE archetypes (from Endless Sky commodity system)
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="TRADE_BASIC",
    name="Basic Commodity Trade",
    description="Transport standard goods between locations. Low risk, high volume. "
                "Maps to ES commodity trading (Food, Clothing, Metal, Plastic).",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.CUBE,
    radial_zone=(0.0, 0.2),
    denomination="KO", tongue_weight=1.0,
    required_layers=frozenset({1, 2}),
    complexity_tier=ComplexityTier.TRIVIAL,
    min_governance_verdict="ALLOW",
    energy_range=(0.5, 1.0), base_legibility=1.0,
    es_system="Trade", es_commodities=("Food", "Clothing", "Metal", "Plastic"),
    sv_tongue="status", sv_dimension="C",
    tags=("economy", "transport", "low-risk", "high-volume"),
))

_register(TaskArchetype(
    archetype_id="TRADE_ARBITRAGE",
    name="Cross-System Price Arbitrage",
    description="Exploit price differentials across systems/contexts. Requires "
                "multi-step planning and market analysis. Maps to ES luxury/heavy metal "
                "trading with price range optimization.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.RHOMBIC_DODECAHEDRON,
    radial_zone=(0.2, 0.5),
    denomination="CA", tongue_weight=4.236,
    required_layers=frozenset({1, 2, 5, 8}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.7), base_legibility=0.9,
    es_system="Trade", es_commodities=("Luxury Goods", "Heavy Metals", "Electronics"),
    sv_tongue="negotiation", sv_dimension="P",
    tags=("economy", "optimization", "multi-step", "market-analysis"),
))

_register(TaskArchetype(
    archetype_id="TRADE_CONTRABAND",
    name="Illegal/Restricted Cargo Handling",
    description="Handle sensitive, restricted, or illegal content/data. Requires "
                "maximum governance scrutiny. Maps to ES illegal cargo system with "
                "government fines, atrocity detection, and enforcement zones.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.SMALL_STELLATED,
    radial_zone=(0.7, 0.95),
    denomination="UM", tongue_weight=6.854,
    required_layers=frozenset({1, 2, 3, 5, 7, 8, 10, 12, 13, 14}),
    complexity_tier=ComplexityTier.EXTREME,
    min_governance_verdict="QUARANTINE",
    energy_range=(0.01, 0.15), base_legibility=0.3,
    es_system="Trade", es_commodities=("Illegal Substances", "Illegal Cargo", "Highly Illegal Cargo"),
    sv_tongue="emergency", sv_dimension="P",
    tags=("restricted", "governance-heavy", "audit-required", "high-risk"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  FACTION / GOVERNMENT archetypes (from ES government system)
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="FACTION_REPUTATION",
    name="Reputation Management",
    description="Track and modify reputation across multiple factions/agents. "
                "Actions affect allied and enemy faction scores. Maps to ES "
                "government reputation system with penalties, bribes, trust.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.DODECAHEDRON,
    radial_zone=(0.1, 0.4),
    denomination="AV", tongue_weight=1.618,
    required_layers=frozenset({1, 2, 5, 10}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.4, 0.8), base_legibility=0.95,
    es_system="Government",
    sv_tongue="negotiation", sv_dimension="C",
    tags=("social", "reputation", "multi-agent", "diplomacy"),
))

_register(TaskArchetype(
    archetype_id="FACTION_ENFORCEMENT",
    name="Governance Enforcement Zone",
    description="Enforce rules within a defined zone. Scan for violations, "
                "issue fines, trigger atrocity responses. Maps to ES government "
                "enforcement zones with scanning, fining, and death sentences.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.OCTAHEDRON,
    radial_zone=(0.0, 0.3),
    denomination="DR", tongue_weight=11.09,
    required_layers=frozenset({1, 2, 3, 5, 8, 10, 12, 13}),
    complexity_tier=ComplexityTier.COMPLEX,
    min_governance_verdict="ALLOW",
    energy_range=(0.2, 0.5), base_legibility=1.0,
    es_system="Government",
    sv_tongue="command", sv_dimension="P",
    tags=("governance", "enforcement", "scanning", "rules"),
))

_register(TaskArchetype(
    archetype_id="FACTION_DIPLOMACY",
    name="Multi-Faction Negotiation",
    description="Negotiate between hostile/allied factions. Balance competing "
                "interests, manage trust networks. Maps to ES inter-government "
                "attitudes, trust sets, and penalty delegation.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.ICOSAHEDRON,
    radial_zone=(0.1, 0.5),
    denomination="AV", tongue_weight=1.618,
    required_layers=frozenset({1, 2, 5, 8, 10}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.7), base_legibility=0.85,
    es_system="Government",
    sv_tongue="negotiation", sv_dimension="C",
    tags=("diplomacy", "multi-agent", "trust", "conflict-resolution"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  AI / FLEET COORDINATION archetypes (from ES AI + Spiralverse)
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="FLEET_FORMATION",
    name="Fleet Formation Control",
    description="Coordinate multiple agents into formation patterns. Assign "
                "positions, handle stragglers, reform after disruption. Maps to "
                "ES formation positioner + Spiralverse fleet coordination.",
    source_domain=SourceDomain.SPIRALVERSE,
    polyhedron=PolyhedronType.TRUNCATED_ICOSAHEDRON,
    radial_zone=(0.3, 0.6),
    denomination="CA", tongue_weight=4.236,
    required_layers=frozenset({1, 2, 5, 8, 10}),
    complexity_tier=ComplexityTier.COMPLEX,
    min_governance_verdict="ALLOW",
    energy_range=(0.2, 0.6), base_legibility=0.9,
    es_system="AI",
    sv_tongue="command", sv_dimension="T",
    tags=("fleet", "coordination", "multi-agent", "formation"),
))

_register(TaskArchetype(
    archetype_id="FLEET_PATHFINDING",
    name="Multi-System Route Planning",
    description="Plan optimal routes through a graph of connected systems. "
                "Handle jump gates, wormholes, fuel constraints. Maps to ES "
                "DistanceMap + RoutePlan + WormholeStrategy.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.RHOMBIC_TRIACONTAHEDRON,
    radial_zone=(0.2, 0.5),
    denomination="CA", tongue_weight=4.236,
    required_layers=frozenset({1, 2, 5}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.4, 0.8), base_legibility=1.0,
    es_system="AI",
    sv_tongue="query", sv_dimension="T",
    tags=("navigation", "pathfinding", "graph", "optimization"),
))

_register(TaskArchetype(
    archetype_id="FLEET_COMBAT",
    name="Combat Engagement Protocol",
    description="Coordinate attack/defense during adversarial encounters. "
                "Target selection, weapon management, damage assessment. Maps to "
                "ES AI combat + FireCommand + Armament + DamageProfile.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.GREAT_STELLATED,
    radial_zone=(0.6, 0.9),
    denomination="RU", tongue_weight=2.618,
    required_layers=frozenset({1, 2, 3, 5, 7, 8, 10, 12}),
    complexity_tier=ComplexityTier.EXTREME,
    min_governance_verdict="QUARANTINE",
    energy_range=(0.05, 0.3), base_legibility=0.7,
    es_system="AI",
    sv_tongue="emergency", sv_dimension="P",
    tags=("combat", "adversarial", "high-risk", "real-time"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  MISSION / QUEST archetypes (from ES mission system)
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="MISSION_DELIVERY",
    name="Cargo Delivery Mission",
    description="Transport specific items from origin to destination within "
                "constraints (deadline, cargo type, route restrictions). Maps to "
                "ES mission system with conditions, NPCs, and actions.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.CUBE,
    radial_zone=(0.0, 0.3),
    denomination="KO", tongue_weight=1.0,
    required_layers=frozenset({1, 2, 5}),
    complexity_tier=ComplexityTier.TRIVIAL,
    min_governance_verdict="ALLOW",
    energy_range=(0.5, 0.9), base_legibility=1.0,
    es_system="Mission",
    sv_tongue="command", sv_dimension="T",
    tags=("mission", "delivery", "cargo", "deadline"),
))

_register(TaskArchetype(
    archetype_id="MISSION_CAMPAIGN",
    name="Multi-Stage Campaign",
    description="Chain of dependent missions with branching outcomes. "
                "Conditions unlock next stages. Maps to ES campaign missions "
                "(Free Worlds storyline, Hai missions, etc.).",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.TRUNCATED_ICOSAHEDRON,
    radial_zone=(0.3, 0.6),
    denomination="DR", tongue_weight=11.09,
    required_layers=frozenset({1, 2, 3, 5, 7, 8, 10, 12, 13}),
    complexity_tier=ComplexityTier.COMPLEX,
    min_governance_verdict="ALLOW",
    energy_range=(0.1, 0.5), base_legibility=0.8,
    es_system="Mission",
    sv_tongue="command", sv_dimension="T",
    tags=("campaign", "multi-stage", "branching", "narrative"),
))

_register(TaskArchetype(
    archetype_id="MISSION_CONDITION_GATE",
    name="Conditional Access Gate",
    description="Evaluate complex conditions to determine access/progression. "
                "Maps to ES ConditionSet with boolean expressions, reputation "
                "thresholds, visited-system checks, and date constraints.",
    source_domain=SourceDomain.ENDLESS_SKY,
    polyhedron=PolyhedronType.DODECAHEDRON,
    radial_zone=(0.1, 0.4),
    denomination="RU", tongue_weight=2.618,
    required_layers=frozenset({1, 2, 5, 8, 10}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.7), base_legibility=1.0,
    es_system="Mission",
    sv_tongue="query", sv_dimension="C",
    tags=("conditions", "access-control", "boolean-logic", "gates"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  PHDM BRAIN archetypes (from PHDM v3.0.0 spec)
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="BRAIN_SELF_DIAGNOSTIC",
    name="Self-Diagnostic Loop",
    description="AI runtime introspection — verify own state integrity, "
                "check for drift, validate polyhedral lattice. Maps to PHDM "
                "Szilassi toroidal self-check.",
    source_domain=SourceDomain.PHDM_BRAIN,
    polyhedron=PolyhedronType.SZILASSI,
    radial_zone=(0.0, 0.3),
    denomination="UM", tongue_weight=6.854,
    required_layers=frozenset({1, 2, 7, 8, 12, 13, 14}),
    complexity_tier=ComplexityTier.COMPLEX,
    min_governance_verdict="ALLOW",
    energy_range=(0.2, 0.6), base_legibility=0.95,
    sv_tongue="status", sv_dimension="C",
    tags=("introspection", "self-check", "integrity", "diagnostic"),
))

_register(TaskArchetype(
    archetype_id="BRAIN_RECURSIVE_PLAN",
    name="Recursive Planning",
    description="Fractal/nested planning — plans that contain sub-plans that "
                "contain sub-sub-plans. Maps to PHDM Csaszar recursive processor.",
    source_domain=SourceDomain.PHDM_BRAIN,
    polyhedron=PolyhedronType.CSASZAR,
    radial_zone=(0.3, 0.6),
    denomination="DR", tongue_weight=11.09,
    required_layers=frozenset({1, 2, 3, 5, 8, 10, 12}),
    complexity_tier=ComplexityTier.COMPLEX,
    min_governance_verdict="ALLOW",
    energy_range=(0.1, 0.5), base_legibility=0.75,
    sv_tongue="query", sv_dimension="T",
    tags=("planning", "recursive", "fractal", "nested"),
))

_register(TaskArchetype(
    archetype_id="BRAIN_CREATIVE_SYNTHESIS",
    name="Novel Solution Generation",
    description="Generate novel solutions by combining concepts from different "
                "domains. Temporarily visits risk zone but must return. Maps to "
                "PHDM Snub Dodecahedron creative synthesis.",
    source_domain=SourceDomain.PHDM_BRAIN,
    polyhedron=PolyhedronType.SNUB_DODECAHEDRON,
    radial_zone=(0.4, 0.7),
    denomination="RU", tongue_weight=2.618,
    required_layers=frozenset({1, 2, 5, 7, 8}),
    complexity_tier=ComplexityTier.COMPLEX,
    min_governance_verdict="ALLOW",
    energy_range=(0.15, 0.5), base_legibility=0.6,
    sv_tongue="learning", sv_dimension="C",
    tags=("creative", "synthesis", "novel", "cross-domain"),
))

_register(TaskArchetype(
    archetype_id="BRAIN_PHASON_SHIFT",
    name="Defensive Key Rotation",
    description="Rotate the quasicrystal projection to scramble neural pathways. "
                "Instant defense against mapped attacks. Maps to PHDM phason "
                "shifting — 6D projection rotation.",
    source_domain=SourceDomain.PHDM_BRAIN,
    polyhedron=PolyhedronType.TETRAHEDRON,
    radial_zone=(0.0, 0.1),
    denomination="DR", tongue_weight=11.09,
    required_layers=frozenset({1, 2, 3, 5, 7, 8, 10, 12, 13, 14}),
    complexity_tier=ComplexityTier.EXTREME,
    min_governance_verdict="ALLOW",
    energy_range=(0.05, 0.2), base_legibility=1.0,
    sv_tongue="emergency", sv_dimension="P",
    tags=("defense", "key-rotation", "phason", "emergency"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  SIX TONGUES / GEOSEAL archetypes
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="TONGUE_ENCODE",
    name="Sacred Tongue Encoding",
    description="Encode context payload into Sacred Tongue token stream. "
                "Bijective 256-token mapping. Maps to six-tongues-cli encode.",
    source_domain=SourceDomain.SIX_TONGUES,
    polyhedron=PolyhedronType.JOHNSON_A,
    radial_zone=(0.0, 0.2),
    denomination="KO", tongue_weight=1.0,
    required_layers=frozenset({1, 2}),
    complexity_tier=ComplexityTier.TRIVIAL,
    min_governance_verdict="ALLOW",
    energy_range=(0.7, 1.0), base_legibility=1.0,
    sv_tongue="status", sv_dimension="C",
    tags=("encoding", "tokenization", "sacred-tongue", "bijective"),
))

_register(TaskArchetype(
    archetype_id="TONGUE_CROSS_TRANSLATE",
    name="Cross-Tongue Translation",
    description="Re-encode token stream from one tongue to another without "
                "touching underlying bytes. Preserves payload. Maps to xlate.",
    source_domain=SourceDomain.SIX_TONGUES,
    polyhedron=PolyhedronType.RHOMBICUBOCTAHEDRON,
    radial_zone=(0.2, 0.5),
    denomination="AV", tongue_weight=1.618,
    required_layers=frozenset({1, 2, 5}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.4, 0.8), base_legibility=0.95,
    sv_tongue="negotiation", sv_dimension="C",
    tags=("translation", "cross-tongue", "protocol-bridge"),
))

_register(TaskArchetype(
    archetype_id="GEOSEAL_ENCRYPT",
    name="Context-Aware Encryption",
    description="Seal payload with geographic and context metadata. PQC-ready "
                "encryption (ML-KEM-768 / ML-DSA-65). Maps to GeoSeal.",
    source_domain=SourceDomain.SIX_TONGUES,
    polyhedron=PolyhedronType.JOHNSON_B,
    radial_zone=(0.1, 0.4),
    denomination="UM", tongue_weight=6.854,
    required_layers=frozenset({1, 2, 5, 8, 12}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.6), base_legibility=0.5,
    sv_tongue="command", sv_dimension="C",
    tags=("encryption", "geoseal", "pqc", "context-aware"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  WEB AGENT archetypes
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="WEB_NAVIGATE",
    name="Autonomous Web Navigation",
    description="Navigate web pages using SENSE+PLAN+STEER+DECIDE loop. "
                "Kalman-filtered progress, PID error correction. Maps to "
                "SCBE web agent navigation engine.",
    source_domain=SourceDomain.WEB_AGENT,
    polyhedron=PolyhedronType.TRUNCATED_ICOSAHEDRON,
    radial_zone=(0.2, 0.5),
    denomination="KO", tongue_weight=1.0,
    required_layers=frozenset({1, 2, 5, 8}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.7), base_legibility=0.9,
    sv_tongue="query", sv_dimension="T",
    tags=("web", "navigation", "autonomous", "kalman"),
))

_register(TaskArchetype(
    archetype_id="WEB_PUBLISH",
    name="Multi-Platform Content Publishing",
    description="Publish content across 9+ platforms with governance scanning, "
                "rate limiting, and tongue-encoded transport. Maps to SCBE "
                "ContentBuffer + publishers.",
    source_domain=SourceDomain.WEB_AGENT,
    polyhedron=PolyhedronType.ICOSAHEDRON,
    radial_zone=(0.1, 0.4),
    denomination="AV", tongue_weight=1.618,
    required_layers=frozenset({1, 2, 5, 8, 10}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.7), base_legibility=0.85,
    sv_tongue="status", sv_dimension="C",
    tags=("publishing", "multi-platform", "content", "buffer"),
))

_register(TaskArchetype(
    archetype_id="WEB_ANTIVIRUS",
    name="Semantic Antivirus Scan",
    description="Scan content for prompt injection, malware patterns, and "
                "compound threats. Escalate injection+malware combo. Maps to "
                "SCBE SemanticAntivirus.",
    source_domain=SourceDomain.WEB_AGENT,
    polyhedron=PolyhedronType.GREAT_STELLATED,
    radial_zone=(0.5, 0.9),
    denomination="DR", tongue_weight=11.09,
    required_layers=frozenset({1, 2, 3, 5, 7, 8, 10, 12, 13}),
    complexity_tier=ComplexityTier.EXTREME,
    min_governance_verdict="ALLOW",
    energy_range=(0.1, 0.3), base_legibility=1.0,
    sv_tongue="emergency", sv_dimension="P",
    tags=("security", "antivirus", "scanning", "threat-detection"),
))


# ═══════════════════════════════════════════════════════════════════════════
#  MMCCL archetypes (compute exchange)
# ═══════════════════════════════════════════════════════════════════════════

_register(TaskArchetype(
    archetype_id="CREDIT_MINT",
    name="Context Credit Minting",
    description="Mint new credits from context interactions via proof-of-context. "
                "Find nonce where hash has prefix zeros. Maps to MMCCL mint_credit.",
    source_domain=SourceDomain.MMCCL,
    polyhedron=PolyhedronType.TETRAHEDRON,
    radial_zone=(0.0, 0.2),
    denomination="KO", tongue_weight=1.0,
    required_layers=frozenset({1, 2}),
    complexity_tier=ComplexityTier.TRIVIAL,
    min_governance_verdict="ALLOW",
    energy_range=(0.5, 1.0), base_legibility=1.0,
    tags=("minting", "proof-of-context", "credit", "blockchain"),
))

_register(TaskArchetype(
    archetype_id="CREDIT_EXCHANGE",
    name="Compute Exchange Transaction",
    description="Agent-to-agent compute trade: offer → match → escrow → "
                "deliver → settle. Maps to MMCCL ComputeExchange.",
    source_domain=SourceDomain.MMCCL,
    polyhedron=PolyhedronType.RHOMBIC_DODECAHEDRON,
    radial_zone=(0.2, 0.5),
    denomination="CA", tongue_weight=4.236,
    required_layers=frozenset({1, 2, 5, 8, 10}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.7), base_legibility=0.9,
    tags=("exchange", "compute", "agent-to-agent", "escrow"),
))

_register(TaskArchetype(
    archetype_id="CREDIT_VAULT",
    name="BitLocker Vault Operation",
    description="Lock/unlock/escrow credits in PQC-ready cryptographic vaults. "
                "Time-locks prevent deadlock. Maps to MMCCL BitLockerVault.",
    source_domain=SourceDomain.MMCCL,
    polyhedron=PolyhedronType.JOHNSON_B,
    radial_zone=(0.1, 0.4),
    denomination="UM", tongue_weight=6.854,
    required_layers=frozenset({1, 2, 5, 8, 12}),
    complexity_tier=ComplexityTier.STANDARD,
    min_governance_verdict="ALLOW",
    energy_range=(0.3, 0.6), base_legibility=0.8,
    tags=("vault", "escrow", "encryption", "bitlocker"),
))


# ---------------------------------------------------------------------------
#  Context Catalog — the query interface
# ---------------------------------------------------------------------------

class ContextCatalog:
    """
    Query interface over the archetype registry.

    Usage::

        catalog = ContextCatalog()
        catalog.get("TRADE_ARBITRAGE")
        catalog.by_polyhedron(PolyhedronType.CUBE)
        catalog.by_denomination("DR")
        catalog.by_complexity(ComplexityTier.EXTREME)
        catalog.search("fleet coordination")
    """

    def __init__(self) -> None:
        self._registry = ARCHETYPE_REGISTRY

    def get(self, archetype_id: str) -> Optional[TaskArchetype]:
        return self._registry.get(archetype_id)

    def all(self) -> List[TaskArchetype]:
        return list(self._registry.values())

    def by_polyhedron(self, poly: PolyhedronType) -> List[TaskArchetype]:
        return [a for a in self._registry.values() if a.polyhedron == poly]

    def by_denomination(self, denom: str) -> List[TaskArchetype]:
        return [a for a in self._registry.values() if a.denomination == denom]

    def by_complexity(self, tier: ComplexityTier) -> List[TaskArchetype]:
        return [a for a in self._registry.values() if a.complexity_tier == tier]

    def by_source(self, source: SourceDomain) -> List[TaskArchetype]:
        return [a for a in self._registry.values() if a.source_domain == source]

    def by_es_system(self, system: str) -> List[TaskArchetype]:
        return [a for a in self._registry.values() if a.es_system == system]

    def search(self, query: str) -> List[TaskArchetype]:
        """Fuzzy search across names, descriptions, and tags."""
        q = query.lower()
        results = []
        for a in self._registry.values():
            score = 0
            if q in a.name.lower():
                score += 3
            if q in a.description.lower():
                score += 2
            for tag in a.tags:
                if q in tag:
                    score += 1
            if score > 0:
                results.append((score, a))
        return [a for _, a in sorted(results, key=lambda x: -x[0])]

    def for_radial_distance(self, r: float) -> List[TaskArchetype]:
        """Find archetypes valid at a given radial distance in Poincaré ball."""
        return [
            a for a in self._registry.values()
            if a.radial_zone[0] <= r <= a.radial_zone[1]
        ]

    def summary(self) -> Dict[str, Any]:
        by_poly: Dict[str, int] = {}
        by_denom: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        by_tier: Dict[str, int] = {}

        for a in self._registry.values():
            by_poly[a.polyhedron.value] = by_poly.get(a.polyhedron.value, 0) + 1
            by_denom[a.denomination] = by_denom.get(a.denomination, 0) + 1
            by_source[a.source_domain.value] = by_source.get(a.source_domain.value, 0) + 1
            by_tier[a.complexity_tier.value] = by_tier.get(a.complexity_tier.value, 0) + 1

        return {
            "total_archetypes": len(self._registry),
            "by_polyhedron": by_poly,
            "by_denomination": by_denom,
            "by_source_domain": by_source,
            "by_complexity_tier": by_tier,
        }
