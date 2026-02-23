#!/usr/bin/env python3
"""
Ecology-Topology Tributary — Maps ecological relationships to CDDM domains.

Real-world ecology provides a parallel ontology that maps cleanly onto the
SCBE-AETHERMOORE CDDM framework:

  Food webs       -> Directed graphs (DomainGraph)
  Trophic levels  -> Layer hierarchy (14-layer architecture)
  Ecological niches -> Manifold regions (tongue domains)
  Keystone species -> Hub nodes (high centrality)
  Invasive species -> Rogue agents (adversarial injection)
  Carrying capacity -> Resource bounds (Domain.bounds)

Ecological relationship -> Sacred Tongue mapping:
  Predator/Prey     -> KO (energy transfer, authority hierarchy)
  Symbiosis/Mutualism -> AV (mutual flow, communication channels)
  Parasitism        -> UM (threat, security vulnerability)
  Decomposition     -> RU (entropy increase, policy breakdown)
  Competition       -> CA (complexity, computational arms race)
  Succession/Memory -> DR (structure, pattern evolution)

Usage:
  python scripts/ecology_topology_to_sft.py [--output PATH]
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_OUT = PROJECT_ROOT / "training-data"
TRAINING_OUT.mkdir(parents=True, exist_ok=True)


@dataclass
class SFTPair:
    instruction: str
    response: str
    category: str = "ecology-topology"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "response": self.response,
            "category": self.category,
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "author": "Issac Davis",
                **self.metadata,
            },
            "id": f"sft-{self.category[:4]}-{uuid.uuid4().hex[:8]}",
        }


# ═══════════════════════════════════════════════════════════════
# Ecological Relationship -> Sacred Tongue Mapping
# ═══════════════════════════════════════════════════════════════

TONGUE_ECOLOGY_MAP = {
    "KO": {
        "relationship": "Predation / Energy Transfer",
        "description": (
            "KO (Kor'aelin) maps to predator-prey dynamics: energy flows upward "
            "through trophic levels via consumption. The apex predator holds "
            "authority over the food web, just as KO holds command authority "
            "in the governance stack. Energy is neither created nor destroyed — "
            "it transfers through the morphism chain."
        ),
        "examples": [
            ("Wolf", "Elk", "tertiary -> secondary consumer energy transfer"),
            ("Orca", "Seal", "apex predator energy extraction from marine mammals"),
            ("Eagle", "Rabbit", "raptor strike as instantaneous energy transfer"),
            ("Lion", "Zebra", "savanna apex authority assertion"),
            ("Spider", "Fly", "web-based trap as passive energy harvesting"),
        ],
    },
    "AV": {
        "relationship": "Symbiosis / Mutualism",
        "description": (
            "AV (Avali) maps to mutualistic symbiosis: bidirectional flow where "
            "both organisms benefit. Mycorrhizal networks are the ecological "
            "equivalent of AV's data transport — underground fungal highways "
            "connecting trees in a Wood Wide Web, sharing nutrients and signals. "
            "Communication flow is inherently mutualistic."
        ),
        "examples": [
            ("Clownfish", "Sea Anemone", "protection <-> cleaning mutualism"),
            ("Bee", "Flower", "pollination <-> nectar exchange"),
            ("Mycorrhiza", "Oak Tree", "nutrient transport via fungal network"),
            ("Oxpecker", "Rhino", "parasite removal <-> food source"),
            ("Lichen", "Algae+Fungus", "composite organism via mutual transport"),
        ],
    },
    "RU": {
        "relationship": "Decomposition / Entropy",
        "description": (
            "RU (Runethic) maps to decomposition and entropy increase: the "
            "breakdown of complex organic matter into simpler compounds. "
            "Decomposers are the policy enforcement of the ecosystem — they "
            "ensure that accumulated structure doesn't persist beyond its "
            "useful lifetime. Entropy increases, nutrients recycle, the "
            "system stays in dynamic equilibrium."
        ),
        "examples": [
            ("Mushroom", "Dead Tree", "lignocellulose breakdown by basidiomycetes"),
            ("Earthworm", "Leaf Litter", "soil turnover as entropy processing"),
            ("Bacteria", "Carcass", "microbial decomposition cascade"),
            ("Dung Beetle", "Manure", "waste recycling as nutrient policy"),
            ("Vulture", "Carrion", "scavenging as cleanup governance"),
        ],
    },
    "CA": {
        "relationship": "Competition / Arms Race",
        "description": (
            "CA (Cassisivadan) maps to competitive coevolution: the Red Queen "
            "hypothesis where organisms must constantly evolve just to maintain "
            "relative fitness. This is computational complexity in biology — "
            "each adaptation forces counter-adaptation, like an encryption "
            "arms race. Immune systems vs pathogens, camouflage vs detection, "
            "speed vs stealth."
        ),
        "examples": [
            ("Cheetah", "Gazelle", "speed arms race (108 km/h vs 97 km/h)"),
            ("Immune System", "Influenza", "antibody diversification vs antigen drift"),
            ("Rough-Skinned Newt", "Garter Snake", "tetrodotoxin escalation"),
            ("Cuckoo", "Reed Warbler", "egg mimicry vs host discrimination"),
            ("Ant Colony A", "Ant Colony B", "resource competition as territorial compute"),
        ],
    },
    "UM": {
        "relationship": "Parasitism / Threat",
        "description": (
            "UM (Umbroth) maps to parasitism: one organism benefits at the "
            "other's expense. Parasites are the security threats of ecosystems — "
            "they exploit hosts, evade immune defenses (security layers), and "
            "can cascade through populations. Cordyceps fungi hijacking ant "
            "brains is biological prompt injection."
        ),
        "examples": [
            ("Cordyceps", "Ant", "fungal neural hijack (biological prompt injection)"),
            ("Cuckoo", "Warbler Nest", "brood parasitism as identity spoofing"),
            ("Tapeworm", "Mammal Host", "internal resource drain, evading immune detection"),
            ("Mistletoe", "Host Tree", "vascular parasite siphoning nutrients"),
            ("Toxoplasma", "Mouse->Cat", "behavioral manipulation for lifecycle completion"),
        ],
    },
    "DR": {
        "relationship": "Succession / Pattern Memory",
        "description": (
            "DR (Draumric) maps to ecological succession: the structured, "
            "predictable sequence of community change over time. Pioneer "
            "species -> intermediate -> climax community follows a schema. "
            "The forest remembers its pattern — even after fire, succession "
            "replays the same structural template. Seed banks are ecological "
            "persistent memory. DNA is the ultimate schema."
        ),
        "examples": [
            ("Lichen", "Bare Rock", "primary succession pioneer (schema seed)"),
            ("Birch Forest", "Grassland", "secondary succession intermediate stage"),
            ("Old Growth Forest", "Climax Community", "stable structural pattern"),
            ("Coral Reef", "Calcium Carbonate", "biogenic structure building over millennia"),
            ("Seed Bank", "Soil", "dormant pattern memory awaiting activation"),
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
# Real Species -> CDDM Domain Signatures
# ═══════════════════════════════════════════════════════════════

SPECIES_SIGNATURES: List[Dict[str, Any]] = [
    {
        "species": "Gray Wolf (Canis lupus)",
        "kingdom": "Animalia",
        "trophic_level": 4,
        "role": "Apex predator, keystone species",
        "tongue_primary": "KO",
        "tongue_secondary": "CA",
        "domain_scores": {"KO": 0.9, "AV": 0.3, "RU": 0.1, "CA": 0.6, "UM": 0.2, "DR": 0.4},
        "scbe_analog": "Governance gate — controls ecosystem structure from top down",
        "governance_insight": (
            "Wolves regulate elk populations, preventing overgrazing. "
            "Removing the apex predator (disabling the governance gate) "
            "triggers trophic cascade — the ecological equivalent of "
            "a security policy breakdown. Yellowstone reintroduction proves "
            "that keystone governance is not optional."
        ),
    },
    {
        "species": "Mycorrhizal Network (Glomeromycota)",
        "kingdom": "Fungi",
        "trophic_level": 0,
        "role": "Nutrient transport, inter-tree communication",
        "tongue_primary": "AV",
        "tongue_secondary": "DR",
        "domain_scores": {"KO": 0.1, "AV": 0.95, "RU": 0.3, "CA": 0.2, "UM": 0.1, "DR": 0.7},
        "scbe_analog": "Data transport layer — the Wood Wide Web as neural network",
        "governance_insight": (
            "Mycorrhizal fungi connect 90% of plant species underground, "
            "transferring carbon, nitrogen, phosphorus, and chemical warning "
            "signals between trees. Mother trees allocate more resources to "
            "their offspring through the network. This is AV transport with "
            "DR structural memory — the network remembers which trees are kin."
        ),
    },
    {
        "species": "Honey Bee (Apis mellifera)",
        "kingdom": "Animalia",
        "trophic_level": 2,
        "role": "Pollinator, swarm intelligence, colony superorganism",
        "tongue_primary": "AV",
        "tongue_secondary": "KO",
        "domain_scores": {"KO": 0.5, "AV": 0.9, "RU": 0.6, "CA": 0.4, "UM": 0.3, "DR": 0.5},
        "scbe_analog": "Swarm browser — distributed consensus through waggle dance",
        "governance_insight": (
            "Bees achieve distributed consensus through the waggle dance: "
            "scouts report resource locations, the colony votes with attendance. "
            "This is BFT consensus in biology — no single bee decides, the swarm "
            "converges. Queen pheromones (KO authority signals) modulate colony "
            "behavior but don't dictate individual decisions."
        ),
    },
    {
        "species": "Cordyceps (Ophiocordyceps unilateralis)",
        "kingdom": "Fungi",
        "trophic_level": 0,
        "role": "Parasitic mind controller, behavioral hijacker",
        "tongue_primary": "UM",
        "tongue_secondary": "CA",
        "domain_scores": {"KO": 0.3, "AV": 0.2, "RU": 0.1, "CA": 0.7, "UM": 0.95, "DR": 0.4},
        "scbe_analog": "Prompt injection attack — hijacks host decision-making",
        "governance_insight": (
            "Cordyceps fungus infiltrates an ant's body, then produces "
            "chemicals that override the ant's neural decision-making, "
            "forcing it to climb to an optimal spore-dispersal height before "
            "killing it. This is the biological equivalent of prompt injection: "
            "the attacker bypasses the host's governance (immune system + behavior) "
            "and reprograms its actions. The SCBE semantic antivirus is the "
            "immune system that should detect this manipulation."
        ),
    },
    {
        "species": "Giant Sequoia (Sequoiadendron giganteum)",
        "kingdom": "Plantae",
        "trophic_level": 1,
        "role": "Climax species, carbon store, structural anchor",
        "tongue_primary": "DR",
        "tongue_secondary": "RU",
        "domain_scores": {"KO": 0.3, "AV": 0.4, "RU": 0.5, "CA": 0.2, "UM": 0.6, "DR": 0.95},
        "scbe_analog": "Schema integrity — 3000-year persistent structure",
        "governance_insight": (
            "Sequoias are living schemas that persist for millennia. Their "
            "fire-resistant bark (UM security), massive root systems (AV transport), "
            "and ability to regenerate from fire (RU entropy cycling) make them "
            "the DR archetype: structure that remembers and persists. Their growth "
            "rings are a literal time-series database encoded in wood."
        ),
    },
    {
        "species": "Tardigrade (Tardigrada)",
        "kingdom": "Animalia",
        "trophic_level": 2,
        "role": "Extremophile, cryptobiosis master",
        "tongue_primary": "UM",
        "tongue_secondary": "DR",
        "domain_scores": {"KO": 0.1, "AV": 0.1, "RU": 0.8, "CA": 0.3, "UM": 0.9, "DR": 0.85},
        "scbe_analog": "Hardened security module — survives vacuum, radiation, extreme temps",
        "governance_insight": (
            "Tardigrades enter cryptobiosis when threatened: they replace cell "
            "water with trehalose glass, fold their DNA into protective proteins, "
            "and essentially pause their biological clock. They survive space vacuum, "
            "1000x lethal radiation, and temperatures from -272C to 150C. This is "
            "the ultimate UM defense: when the threat exceeds all thresholds, "
            "enter a hardened state that preserves DR schema integrity until "
            "conditions improve."
        ),
    },
    {
        "species": "Slime Mold (Physarum polycephalum)",
        "kingdom": "Protista",
        "trophic_level": 1,
        "role": "Distributed problem solver, network optimizer",
        "tongue_primary": "CA",
        "tongue_secondary": "AV",
        "domain_scores": {"KO": 0.2, "AV": 0.7, "RU": 0.4, "CA": 0.9, "UM": 0.1, "DR": 0.5},
        "scbe_analog": "Pathfinding engine — solves mazes and optimizes transport networks",
        "governance_insight": (
            "Physarum polycephalum can solve shortest-path problems, recreate "
            "Tokyo's rail network, and balance exploration vs exploitation — "
            "all without a brain. It computes through physical flow dynamics: "
            "cytoplasm streams toward food, unused tubes atrophy. This is CA "
            "computation via AV transport: the medium IS the computer. "
            "The SCBE PLAN concept block (A* pathfinding) does the same thing digitally."
        ),
    },
    {
        "species": "Lichen (Composite Organism)",
        "kingdom": "Fungi+Algae",
        "trophic_level": 1,
        "role": "Pioneer species, primary succession initiator",
        "tongue_primary": "DR",
        "tongue_secondary": "AV",
        "domain_scores": {"KO": 0.1, "AV": 0.6, "RU": 0.3, "CA": 0.2, "UM": 0.4, "DR": 0.8},
        "scbe_analog": "Bootstrap loader — first code that runs on bare metal",
        "governance_insight": (
            "Lichen colonizes bare rock, breaking it down through chemical "
            "weathering to create the first soil. Without lichen, succession "
            "cannot begin. This is the DR bootstrap: the initial schema that "
            "makes all subsequent structure possible. In SCBE terms, lichen is "
            "the kernel manifest — the minimum viable governance that enables "
            "everything else to load."
        ),
    },
    {
        "species": "Dung Beetle (Scarabaeidae)",
        "kingdom": "Animalia",
        "trophic_level": 2,
        "role": "Decomposer, nutrient recycler, entropy processor",
        "tongue_primary": "RU",
        "tongue_secondary": "AV",
        "domain_scores": {"KO": 0.2, "AV": 0.5, "RU": 0.9, "CA": 0.1, "UM": 0.1, "DR": 0.3},
        "scbe_analog": "Garbage collector — processes entropy back into usable resources",
        "governance_insight": (
            "Dung beetles process waste matter back into soil nutrients, "
            "completing the nutrient cycle. They are RU policy enforcement: "
            "accumulated entropy (waste) must be processed back into order "
            "(fertile soil) or the system collapses. In software, this is "
            "garbage collection — the RU tongue ensures resources are reclaimed."
        ),
    },
    {
        "species": "Leafcutter Ant (Atta cephalotes)",
        "kingdom": "Animalia",
        "trophic_level": 2,
        "role": "Fungal farmer, division of labor, caste system",
        "tongue_primary": "KO",
        "tongue_secondary": "CA",
        "domain_scores": {"KO": 0.8, "AV": 0.5, "RU": 0.7, "CA": 0.6, "UM": 0.4, "DR": 0.6},
        "scbe_analog": "Fleet orchestrator — specialized castes execute coordinated tasks",
        "governance_insight": (
            "Leafcutter colonies have 4 castes (minima, media, majors, soldiers) "
            "each specializing in different tasks — exactly like SCBE's Fleet "
            "where each drone specializes in a tongue domain. The colony farms "
            "fungus gardens (CA compute), defends against parasites (UM security), "
            "maintains trails (AV transport), and recycles waste (RU entropy). "
            "No single ant knows the plan; governance emerges from local rules."
        ),
    },
    {
        "species": "Venus Flytrap (Dionaea muscipula)",
        "kingdom": "Plantae",
        "trophic_level": 1,
        "role": "Carnivorous plant, sensory trap, action potential",
        "tongue_primary": "UM",
        "tongue_secondary": "KO",
        "domain_scores": {"KO": 0.6, "AV": 0.2, "RU": 0.1, "CA": 0.5, "UM": 0.7, "DR": 0.3},
        "scbe_analog": "Honeypot trap — lures adversaries into controlled environment",
        "governance_insight": (
            "The Venus flytrap uses a two-trigger system: the trap only closes "
            "when two separate trigger hairs are touched within 20 seconds. "
            "This is a biological BFT consensus requirement — two independent "
            "confirmations before irreversible action. The plant also counts "
            "triggers: 5 touches starts enzyme production. This graduated "
            "response mirrors SCBE governance escalation levels."
        ),
    },
    {
        "species": "Octopus (Octopoda)",
        "kingdom": "Animalia",
        "trophic_level": 3,
        "role": "Distributed intelligence, camouflage master, tool user",
        "tongue_primary": "CA",
        "tongue_secondary": "UM",
        "domain_scores": {"KO": 0.4, "AV": 0.3, "RU": 0.2, "CA": 0.9, "UM": 0.8, "DR": 0.5},
        "scbe_analog": "Edge compute — 2/3 of neurons in arms, distributed processing",
        "governance_insight": (
            "An octopus has 500M neurons, 2/3 of which are in its arms. "
            "Each arm can taste, touch, and make decisions independently. "
            "This is distributed CA compute with local autonomy — the brain "
            "sends high-level intent (KO), but arms execute locally. "
            "Chromatophore camouflage is UM concealment at biological scale."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════
# Ecological Topology Concepts
# ═══════════════════════════════════════════════════════════════

TOPOLOGY_MAPPINGS: List[Dict[str, str]] = [
    {
        "ecology_concept": "Food Web",
        "topology_analog": "Directed Acyclic Graph (DAG)",
        "cddm_mapping": "DomainGraph with energy-flow morphisms",
        "explanation": (
            "A food web is a directed graph where edges represent energy transfer "
            "between trophic levels. In CDDM, this maps to DomainGraph.find_path() — "
            "computing the morphism chain from producer (autotroph) to apex predator. "
            "Energy loss at each trophic level (~90%) maps to the morphism's "
            "transformation function (lossy conversion)."
        ),
    },
    {
        "ecology_concept": "Trophic Cascade",
        "topology_analog": "Chain Complex / Composition Chain",
        "cddm_mapping": "CompositionChain.apply_traced() with cascading effects",
        "explanation": (
            "When wolves were removed from Yellowstone, elk overgrazed willows, "
            "streams eroded, songbirds disappeared — a cascade through connected "
            "morphisms. In CDDM, this is a CompositionChain where removing one "
            "morphism (wolf -> elk) breaks the entire chain, causing the composition "
            "to produce invalid results downstream."
        ),
    },
    {
        "ecology_concept": "Ecological Niche",
        "topology_analog": "Manifold Region / Domain with Bounds",
        "cddm_mapping": "Domain(name, units, bounds=(min, max))",
        "explanation": (
            "An ecological niche is a bounded region in N-dimensional resource space "
            "(temperature, humidity, food size, activity time, etc.). This maps "
            "directly to CDDM Domain objects with bounds — each species occupies "
            "a region, and two species cannot occupy the same niche (competitive "
            "exclusion = domain uniqueness constraint)."
        ),
    },
    {
        "ecology_concept": "Keystone Species",
        "topology_analog": "Hub Node / High Betweenness Centrality",
        "cddm_mapping": "Critical morphism in DomainGraph — removal disconnects subgraphs",
        "explanation": (
            "A keystone species has disproportionate impact relative to its abundance. "
            "In graph theory, this is a node with high betweenness centrality — "
            "removing it disconnects the graph. In CDDM, a keystone morphism is one "
            "whose removal breaks all composition chains passing through it."
        ),
    },
    {
        "ecology_concept": "Invasive Species",
        "topology_analog": "Adversarial Node Injection",
        "cddm_mapping": "Rogue agent that bypasses Domain.validate() bounds checking",
        "explanation": (
            "An invasive species enters an ecosystem without co-evolved checks "
            "(predators, diseases, competitors). In SCBE, this maps to a rogue "
            "agent that bypasses governance bounds — it operates outside the "
            "expected Domain.bounds and disrupts the existing morphism network. "
            "The semantic antivirus is the immune system that should detect "
            "and quarantine invasive inputs."
        ),
    },
    {
        "ecology_concept": "Carrying Capacity (K)",
        "topology_analog": "Domain Upper Bound",
        "cddm_mapping": "Domain.bounds upper limit — resource ceiling",
        "explanation": (
            "Carrying capacity K is the maximum population an environment can "
            "sustain indefinitely. This is the Domain.bounds upper limit — "
            "exceeding it triggers density-dependent feedback (the system "
            "clamps values back to bounds). In governance, this is rate limiting "
            "and resource quota enforcement."
        ),
    },
    {
        "ecology_concept": "Ecological Succession",
        "topology_analog": "State Machine / Directed Path in Phase Space",
        "cddm_mapping": "Ordered sequence of Domain transitions via morphisms",
        "explanation": (
            "Succession follows a predictable path: bare rock -> lichen -> moss -> "
            "grass -> shrubs -> forest. Each stage creates conditions for the next. "
            "In CDDM, this is a composition chain where each morphism's output "
            "falls within the next morphism's input domain — a directed path "
            "through phase space that the ecosystem follows deterministically."
        ),
    },
    {
        "ecology_concept": "Biodiversity Index (Shannon-Wiener)",
        "topology_analog": "Information Entropy over Domain Distribution",
        "cddm_mapping": "Shannon entropy H = -sum(p_i * log(p_i)) over tongue distribution",
        "explanation": (
            "The Shannon-Wiener diversity index is literally information entropy "
            "applied to species abundances. In SCBE, the same formula measures "
            "tongue diversity across a system — a healthy system has high entropy "
            "(balanced tongue activation), while a compromised system concentrates "
            "on one tongue (low entropy = monoculture = vulnerability)."
        ),
    },
    {
        "ecology_concept": "Edge Effects / Ecotone",
        "topology_analog": "Domain Boundary / Morphism Transition Zone",
        "cddm_mapping": "The region where two Domain bounds overlap — cross-tongue territory",
        "explanation": (
            "Ecotones (forest edge, shoreline, treeline) have highest biodiversity "
            "because species from both adjacent ecosystems overlap. In CDDM, the "
            "most interesting computation happens at domain boundaries — where "
            "cross-tongue morphisms operate. The authority_to_danger morphism "
            "(KO -> UM) is an ecotone between control and security domains."
        ),
    },
    {
        "ecology_concept": "Resilience vs. Resistance",
        "topology_analog": "Manifold Curvature vs. Metric Stiffness",
        "cddm_mapping": "H_eff(d,R,x) response to perturbation — bounce-back vs. rigidity",
        "explanation": (
            "Ecological resilience is how quickly a system returns to equilibrium "
            "after disturbance. Resistance is how much disturbance it can absorb "
            "without changing state. In the Harmonic Wall: resistance maps to "
            "the wall height H_eff at a given depth d, while resilience maps "
            "to the curvature of the wall — steep walls resist but shatter, "
            "gentle curves absorb and restore."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════
# Real Ecosystem Case Studies
# ═══════════════════════════════════════════════════════════════

ECOSYSTEM_CASES: List[Dict[str, Any]] = [
    {
        "name": "Yellowstone Wolf Reintroduction (1995)",
        "type": "trophic_cascade",
        "chain": ["Wolf (KO)", "Elk (CA)", "Willow (DR)", "Beaver (AV)", "Stream (RU)"],
        "lesson": (
            "Removing wolves from Yellowstone (1926) caused a 70-year trophic cascade: "
            "elk populations exploded, overgrazing willows and aspens. Without trees, "
            "beavers disappeared, streams eroded, songbirds declined. Reintroducing "
            "wolves in 1995 reversed this: elk behavior changed (they avoided open "
            "areas), vegetation recovered, beavers returned, streams stabilized. "
            "The governance lesson: the KO apex controller doesn't just kill prey — "
            "it shapes behavior through the 'landscape of fear.' The mere presence "
            "of governance changes how agents behave, even without enforcement."
        ),
        "scbe_parallel": (
            "The SCBE governance gate doesn't need to DENY every request. "
            "Its presence creates a 'landscape of fear' that makes agents "
            "self-regulate. The H_eff harmonic wall is the landscape of fear — "
            "agents near the boundary behave differently because they sense the wall."
        ),
    },
    {
        "name": "Coral Reef Bleaching (Climate Stress)",
        "type": "threshold_collapse",
        "chain": ["Temperature (RU)", "Zooxanthellae (AV)", "Coral (DR)", "Fish (CA)", "Reef (KO)"],
        "lesson": (
            "Coral reefs host 25% of marine species on 0.1% of ocean floor. "
            "When water temperature exceeds 1C above summer max for 4+ weeks, "
            "coral expels its symbiotic algae (zooxanthellae) — bleaching. "
            "If stress continues, the coral dies, and the entire reef ecosystem "
            "collapses. The AV mutualism (algae <-> coral nutrient exchange) is "
            "the critical morphism — when it breaks, everything downstream fails."
        ),
        "scbe_parallel": (
            "In SCBE, if the AV transport layer fails (network partition, data "
            "corruption), the entire system loses coordination — governance "
            "decisions can't propagate, telemetry goes dark, and agents lose "
            "coherence. The coral bleaching threshold (1C for 4 weeks) maps to "
            "SCBE's rate limit and timeout thresholds."
        ),
    },
    {
        "name": "Amazon Rainforest as Earth's Lungs",
        "type": "global_regulation",
        "chain": ["Trees (DR)", "Transpiration (AV)", "Clouds (RU)", "Rain (KO)", "Rivers (CA)"],
        "lesson": (
            "The Amazon generates 50% of its own rainfall through transpiration: "
            "trees pump water from roots to leaves, releasing it as vapor that "
            "forms clouds that rain back down. This is a self-sustaining AV "
            "feedback loop. Deforestation breaks this loop — below ~20-25% "
            "loss, the forest tips into savanna irreversibly. The DR structure "
            "(tree cover) maintains the AV transport (water cycle)."
        ),
        "scbe_parallel": (
            "SCBE systems that maintain their own infrastructure (self-hosted "
            "governance, self-healing consensus) are like the Amazon's rain cycle. "
            "If you remove enough governance layers (deforestation), the system "
            "passes a tipping point where self-regulation collapses. The 20-25% "
            "Amazon threshold maps to the SCBE minimum viable governance level."
        ),
    },
    {
        "name": "Chernobyl Exclusion Zone Recovery",
        "type": "succession_after_catastrophe",
        "chain": ["Radiation (UM)", "Pioneer Species (DR)", "Herbivores (KO)", "Predators (CA)", "Forest (AV)"],
        "lesson": (
            "After the 1986 disaster, the 2,600 km2 exclusion zone became an "
            "accidental nature reserve. Without humans, wildlife returned: "
            "Przewalski's horses, wolves, lynx, bison, 200+ bird species. "
            "Radiation is still present (UM threat), but succession (DR pattern) "
            "proved more powerful than the threat. The ecosystem adapted rather "
            "than collapsed — a demonstration of resilience over resistance."
        ),
        "scbe_parallel": (
            "Even after a catastrophic security breach (UM threat), a system "
            "with strong DR structural patterns can recover through succession. "
            "The SCBE kernel manifest is the seed bank — as long as the core "
            "schema survives, the system can rebuild from any state."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════
# SFT Generation Functions
# ═══════════════════════════════════════════════════════════════

def generate_tongue_ecology_pairs() -> List[SFTPair]:
    """Generate SFT pairs mapping ecological relationships to Sacred Tongues."""
    pairs: List[SFTPair] = []

    for tongue, data in TONGUE_ECOLOGY_MAP.items():
        # Main relationship mapping
        pairs.append(SFTPair(
            instruction=(
                f"How does the Sacred Tongue {tongue} map to ecological "
                f"relationships in the SCBE ecology-topology framework?"
            ),
            response=data["description"],
            category="ecology-tongue-mapping",
            metadata={"origin": "ecology_topology", "tongue": tongue},
        ))

        # Example pairs for each tongue
        for species_a, species_b, desc in data["examples"]:
            pairs.append(SFTPair(
                instruction=(
                    f"In the ecology-topology mapping, how does the "
                    f"{species_a}-{species_b} relationship map to CDDM?"
                ),
                response=(
                    f"The {species_a}-{species_b} interaction ({desc}) maps to "
                    f"the {tongue} tongue domain. {data['relationship']} dynamics "
                    f"translate into {tongue} morphisms in the CDDM framework: "
                    f"{data['description'][:200]}"
                ),
                category="ecology-species-pair",
                metadata={
                    "origin": "ecology_topology",
                    "tongue": tongue,
                    "species": [species_a, species_b],
                },
            ))

    return pairs


def generate_species_signature_pairs() -> List[SFTPair]:
    """Generate SFT pairs from real species -> CDDM domain signatures."""
    pairs: List[SFTPair] = []

    for sp in SPECIES_SIGNATURES:
        name = sp["species"]
        scores = sp["domain_scores"]

        # Species description + tongue signature
        score_str = ", ".join(f"{t}={s:.1f}" for t, s in scores.items())
        pairs.append(SFTPair(
            instruction=f"What is the CDDM tongue signature of {name}?",
            response=(
                f"{name} ({sp['kingdom']}, trophic level {sp['trophic_level']}): "
                f"Role: {sp['role']}. "
                f"Primary tongue: {sp['tongue_primary']}, secondary: {sp['tongue_secondary']}. "
                f"Domain scores: [{score_str}]. "
                f"SCBE analog: {sp['scbe_analog']}."
            ),
            category="ecology-species-signature",
            metadata={
                "origin": "ecology_topology",
                "species": name,
                "tongue_primary": sp["tongue_primary"],
            },
        ))

        # Governance insight pair
        pairs.append(SFTPair(
            instruction=(
                f"What governance lesson does {name} teach about the "
                f"SCBE-AETHERMOORE system?"
            ),
            response=sp["governance_insight"],
            category="ecology-governance-insight",
            metadata={
                "origin": "ecology_topology",
                "species": name,
                "scbe_analog": sp["scbe_analog"],
            },
        ))

        # Cross-domain comparison (find species with complementary scores)
        dominant = max(scores, key=scores.get)
        weakest = min(scores, key=scores.get)
        pairs.append(SFTPair(
            instruction=(
                f"In the ecology-topology framework, why does {name} score "
                f"highest in {dominant} and lowest in {weakest}?"
            ),
            response=(
                f"{name}'s ecological role as '{sp['role']}' explains its "
                f"tongue distribution: highest in {dominant} ({scores[dominant]:.1f}) "
                f"because {sp['scbe_analog'].lower()}, and lowest in {weakest} "
                f"({scores[weakest]:.1f}) because {sp['role'].lower()} "
                f"does not primarily involve {weakest} domain functions."
            ),
            category="ecology-domain-analysis",
            metadata={
                "origin": "ecology_topology",
                "species": name,
                "dominant_tongue": dominant,
            },
        ))

    return pairs


def generate_topology_mapping_pairs() -> List[SFTPair]:
    """Generate SFT pairs from ecology -> topology -> CDDM concept mappings."""
    pairs: List[SFTPair] = []

    for mapping in TOPOLOGY_MAPPINGS:
        # Main concept mapping
        pairs.append(SFTPair(
            instruction=(
                f"How does the ecological concept of '{mapping['ecology_concept']}' "
                f"map to topology and CDDM in the SCBE framework?"
            ),
            response=(
                f"Ecology: {mapping['ecology_concept']} -> "
                f"Topology: {mapping['topology_analog']} -> "
                f"CDDM: {mapping['cddm_mapping']}. "
                f"{mapping['explanation']}"
            ),
            category="ecology-topology-mapping",
            metadata={
                "origin": "ecology_topology",
                "ecology_concept": mapping["ecology_concept"],
                "topology_analog": mapping["topology_analog"],
            },
        ))

        # Reverse direction (CDDM -> ecology)
        pairs.append(SFTPair(
            instruction=(
                f"What ecological analog explains the CDDM concept of "
                f"'{mapping['cddm_mapping']}'?"
            ),
            response=(
                f"The CDDM concept '{mapping['cddm_mapping']}' has a direct "
                f"ecological analog: {mapping['ecology_concept']}. "
                f"In topology, both map to {mapping['topology_analog']}. "
                f"{mapping['explanation']}"
            ),
            category="ecology-reverse-mapping",
            metadata={
                "origin": "ecology_topology",
                "cddm_concept": mapping["cddm_mapping"],
            },
        ))

    return pairs


def generate_ecosystem_case_pairs() -> List[SFTPair]:
    """Generate SFT pairs from real ecosystem case studies."""
    pairs: List[SFTPair] = []

    for case in ECOSYSTEM_CASES:
        chain_str = " -> ".join(case["chain"])

        # Case study lesson
        pairs.append(SFTPair(
            instruction=(
                f"Describe the {case['name']} as an ecology-topology case study "
                f"and its SCBE governance parallel."
            ),
            response=(
                f"Case: {case['name']} (type: {case['type']}). "
                f"Trophic chain: {chain_str}. "
                f"{case['lesson']} "
                f"SCBE parallel: {case['scbe_parallel']}"
            ),
            category="ecology-case-study",
            metadata={
                "origin": "ecology_topology",
                "case": case["name"],
                "type": case["type"],
            },
        ))

        # SCBE parallel only
        pairs.append(SFTPair(
            instruction=(
                f"What SCBE governance lesson does the {case['name']} teach?"
            ),
            response=case["scbe_parallel"],
            category="ecology-scbe-parallel",
            metadata={
                "origin": "ecology_topology",
                "case": case["name"],
            },
        ))

    return pairs


def generate_cross_species_morphism_pairs() -> List[SFTPair]:
    """Generate pairs that compute CDDM morphism chains between species."""
    pairs: List[SFTPair] = []

    # Pick interesting species pairs
    interesting_paths: List[Tuple[str, str, str]] = [
        ("Gray Wolf (Canis lupus)", "Mycorrhizal Network (Glomeromycota)",
         "KO apex predator to AV transport network: wolves shape elk behavior, "
         "which determines which trees survive, which determines which mycorrhizal "
         "networks thrive. The morphism chain: KO->CA (predation pressure) -> "
         "DR (vegetation structure) -> AV (fungal network topology)."),
        ("Cordyceps (Ophiocordyceps unilateralis)", "Honey Bee (Apis mellifera)",
         "UM parasitic hijack vs AV swarm consensus: Cordyceps overrides individual "
         "agency (prompt injection), while bees achieve collective intelligence "
         "through consensus (BFT). The defensive morphism: AV consensus resists "
         "UM manipulation because distributed decision-making has no single "
         "point of hijack."),
        ("Slime Mold (Physarum polycephalum)", "Leafcutter Ant (Atta cephalotes)",
         "CA distributed compute vs KO hierarchical organization: slime mold "
         "computes optimal networks without structure, while leafcutter ants "
         "achieve the same through rigid caste hierarchy. Both solve the same "
         "problem (resource optimization) through different morphism paths: "
         "CA->AV (flow-based) vs KO->CA (authority-directed)."),
        ("Tardigrade (Tardigrada)", "Coral Reef Bleaching (Climate Stress)",
         "UM hardened defense vs threshold collapse: tardigrades survive "
         "anything through cryptobiosis (hardened UM+DR state preservation), "
         "while coral bleaches at just 1C above threshold. The lesson: "
         "individual hardening (tardigrade) vs systemic fragility (reef). "
         "SCBE needs both: hardened components AND systemic resilience."),
    ]

    for sp_a, sp_b, analysis in interesting_paths:
        pairs.append(SFTPair(
            instruction=(
                f"In the ecology-topology framework, compute the CDDM morphism "
                f"chain between {sp_a} and {sp_b}."
            ),
            response=analysis,
            category="ecology-morphism-chain",
            metadata={
                "origin": "ecology_topology",
                "species_pair": [sp_a, sp_b],
            },
        ))

    return pairs


# ═══════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════

def run(output_path: Path | None = None) -> int:
    """Generate all ecology-topology SFT pairs."""
    if output_path is None:
        output_path = TRAINING_OUT / "sft_ecology_topology.jsonl"

    all_pairs: List[SFTPair] = []

    print("\n[ecology] Generating tongue-ecology mapping pairs...")
    tongue_pairs = generate_tongue_ecology_pairs()
    all_pairs.extend(tongue_pairs)
    print(f"  {len(tongue_pairs)} pairs")

    print("[ecology] Generating species signature pairs...")
    species_pairs = generate_species_signature_pairs()
    all_pairs.extend(species_pairs)
    print(f"  {len(species_pairs)} pairs")

    print("[ecology] Generating topology mapping pairs...")
    topo_pairs = generate_topology_mapping_pairs()
    all_pairs.extend(topo_pairs)
    print(f"  {len(topo_pairs)} pairs")

    print("[ecology] Generating ecosystem case study pairs...")
    case_pairs = generate_ecosystem_case_pairs()
    all_pairs.extend(case_pairs)
    print(f"  {len(case_pairs)} pairs")

    print("[ecology] Generating cross-species morphism chains...")
    morph_pairs = generate_cross_species_morphism_pairs()
    all_pairs.extend(morph_pairs)
    print(f"  {len(morph_pairs)} pairs")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in all_pairs:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    print(f"\n{'='*50}")
    print(f"  ECOLOGY-TOPOLOGY: {len(all_pairs)} SFT pairs -> {output_path.name}")
    print(f"    tongue-ecology: {len(tongue_pairs)}")
    print(f"    species-signatures: {len(species_pairs)}")
    print(f"    topology-mappings: {len(topo_pairs)}")
    print(f"    case-studies: {len(case_pairs)}")
    print(f"    morphism-chains: {len(morph_pairs)}")
    print(f"{'='*50}\n")

    return len(all_pairs)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ecology-Topology -> SFT converter")
    parser.add_argument("--output", type=Path, default=None, help="Output JSONL path")
    args = parser.parse_args()
    run(output_path=args.output)
