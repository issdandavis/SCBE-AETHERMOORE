"""
Agentic Sphere Grid
====================

FFX-style skill manifestation engine fused with the Scattered Attention Sphere.

Every agent shares one grid. Skills are floating-point (0.0->1.0), not binary.
Growth is driven by computational necessity -- the system's own governance engines
decide which capabilities propagate. Recursive improvement cycles are deliberately
non-optimal: agents grow toward what they USE, not what's theoretically best.

FFX Analogy:
  Sphere Grid    -> ScatteredAttentionSphere with SkillNodes at lattice positions
  AP             -> Earned by doing useful work (training, research, tasks)
  S Levels       -> Floating-point activation (partial capability at <1.0)
  Character      -> Agent with position on the grid (phi = attention focus)
  Archetypes     -> Pre-filled nodes (like Tidus starts fast, Lulu starts magic)
  Grid traversal -> BFS through adjacent nodes, governed by tongue-weighted cost

Key Differences from FFX:
  - Skills DECAY if unused (use it or lose it)
  - Governance engines can RAISE thresholds dynamically
  - Computational necessity creates "need pressure" that lowers barriers
  - Multi-layer: skills -> combos -> specializations -> fleet capabilities
  - Agents can earn AP for OTHER agents (cooperative growth)

Integration:
  - ScatteredAttentionSphere provides the geometric substrate
  - GeoKernel governance gates control activation thresholds
  - Sacred Tongue weights determine skill domain costs
  - PHDM 21D state feeds the governance decisions
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np

from src.kernel.scattered_sphere import (
    ScatteredAttentionSphere,
    TONGUE_KEYS,
    TONGUE_LONGITUDES,
    TONGUE_WEIGHTS,
)

# =============================================================================
# Enums & Constants
# =============================================================================


class SkillDomain(str, Enum):
    """Capability domains mapped to Sacred Tongues."""

    COMMAND = "KO"  # Orchestration, coordination, task dispatch
    TRANSPORT = "AV"  # Navigation, browsing, data movement
    ENTROPY = "RU"  # Research, chaos testing, exploration
    COMPUTE = "CA"  # Code generation, training, execution
    SECURITY = "UM"  # Scanning, auditing, governance enforcement
    STRUCTURE = "DR"  # Architecture, documentation, healing


class ActivationTier(int, Enum):
    """Floating-point activation interpreted as capability tier."""

    DORMANT = 0  # 0.00 - 0.09: Cannot use at all
    LATENT = 1  # 0.10 - 0.29: Aware it exists, cannot invoke
    PARTIAL = 2  # 0.30 - 0.59: Can use with degraded performance
    CAPABLE = 3  # 0.60 - 0.89: Fully functional, not mastered
    MASTERED = 4  # 0.90 - 1.00: Peak performance, teaches others


class GovernanceVerdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    THROTTLE = "THROTTLE"  # Slow the activation (raise cost)
    ACCELERATE = "ACCELERATE"  # Speed up (lower cost, detected necessity)


# Archetype starting fills — which nodes start pre-activated
# Like FFX: Tidus starts at speed, Auron at strength, Lulu at magic
ARCHETYPES: dict[str, dict[str, float]] = {
    "blank": {},  # Tabula rasa — everything dormant
    "researcher": {
        "web_search": 0.6,
        "paper_analysis": 0.5,
        "citation_graph": 0.4,
        "hypothesis_gen": 0.3,
        "data_collection": 0.5,
    },
    "builder": {
        "code_gen": 0.7,
        "test_writing": 0.5,
        "deployment": 0.4,
        "refactoring": 0.5,
        "debugging": 0.6,
    },
    "guardian": {
        "governance_scan": 0.7,
        "threat_detection": 0.6,
        "audit_trail": 0.5,
        "access_control": 0.5,
        "anomaly_detection": 0.4,
    },
    "scout": {
        "web_search": 0.5,
        "navigation": 0.7,
        "scraping": 0.6,
        "site_mapping": 0.4,
        "screenshot_capture": 0.5,
    },
    "teacher": {
        "explanation": 0.7,
        "documentation": 0.6,
        "training_data_gen": 0.5,
        "example_creation": 0.5,
        "curriculum_design": 0.4,
    },
    "healer": {
        "debugging": 0.7,
        "self_healing": 0.6,
        "error_recovery": 0.5,
        "log_analysis": 0.5,
        "root_cause": 0.4,
    },
}

# AP rewards by outcome type
AP_REWARDS = {
    "success": 10.0,
    "partial": 5.0,
    "failure": 0.0,  # No AP for failure, but need pressure builds
    "assist": 3.0,  # Helped another agent
    "teach": 7.0,  # Mastered skill used to boost another
}

# Decay rate per tick for unused skills
DECAY_RATE = 0.005  # -0.5% per tick for unused skills
# Minimum activation to persist (below this, skill goes fully dormant)
ACTIVATION_FLOOR = 0.05
# How much "need pressure" a failure generates
NEED_PRESSURE_PER_FAILURE = 0.15
# Threshold at which need pressure triggers governance review
NEED_PRESSURE_TRIGGER = 0.5
# Maximum phi-distance for nodes to be "adjacent"
ADJACENCY_BANDWIDTH = 0.4


# =============================================================================
# Core Data Structures
# =============================================================================


@dataclass
class SkillNode:
    """
    A capability on the sphere grid.

    Activation is floating-point: 0.0 = dormant, 1.0 = mastered.
    Partial activation (0.3-0.6) means the skill WORKS but with degraded output.
    This is the key difference from binary skill trees.
    """

    id: str
    name: str
    tongue: str  # Sacred Tongue domain (KO/AV/RU/CA/UM/DR)
    tier: int = 1  # 1-4 (cost scales by tier)
    description: str = ""

    # Spherical coordinates on the grid
    phi: float = 0.0  # Latitude (-pi/2 to pi/2)
    theta: float = 0.0  # Longitude (tongue angle)
    r: float = 1.0  # Radius (tier depth: 1=surface, 0.4=deep)

    # Activation cost (governance-modulated)
    base_cost: float = 10.0  # AP needed for full activation
    governance_multiplier: float = 1.0  # Raised by governance if risky

    # Adjacency — which nodes must be partially active (>=0.3) first
    prerequisites: list[str] = field(default_factory=list)

    # What this skill produces when invoked
    capability_tag: str = ""  # e.g., "web_search", "code_gen", "governance_scan"

    # Hodge dual partner tongue (for combo unlocks)
    hodge_partner: Optional[str] = None

    def effective_cost(self) -> float:
        """Total AP cost including governance modifier and tongue weight."""
        return self.base_cost * self.governance_multiplier * TONGUE_WEIGHTS[self.tongue]

    def tier_radius(self) -> float:
        """Deeper tiers live on inner shells (like QKV concentric layers)."""
        return max(0.4, 1.0 - (self.tier - 1) * 0.2)


@dataclass
class NeedPressure:
    """
    Tracks what an agent NEEDS but doesn't have.

    When pressure exceeds the trigger threshold, governance reviews
    whether to ACCELERATE that skill's activation. This is the
    'computational necessity' engine — the system discovers what
    it needs by trying and failing.
    """

    skill_id: str
    pressure: float = 0.0  # Accumulated need (0.0 to unbounded)
    failure_count: int = 0  # How many times the agent needed this and didn't have it
    last_needed: float = 0.0  # Timestamp
    context: str = ""  # What task triggered the need

    def apply_failure(self, context: str = "") -> float:
        self.pressure += NEED_PRESSURE_PER_FAILURE
        self.failure_count += 1
        self.last_needed = time.time()
        self.context = context
        return self.pressure

    def should_trigger_review(self) -> bool:
        return self.pressure >= NEED_PRESSURE_TRIGGER


@dataclass
class AgentState:
    """
    An agent's personal state on the shared grid.

    Every agent sees the SAME grid but has different:
    - Activation levels per skill (their personal progress)
    - Position (phi = where they're focused)
    - AP bank (earned through work)
    - Need pressure map (what they're lacking)
    - Archetype (starting position)
    """

    agent_id: str
    archetype: str = "blank"

    # Position on the grid
    phi: float = 0.0  # Current attention focus (latitude)
    dominant_tongue: str = "KO"  # Emerges from usage patterns

    # Resources
    ap_bank: float = 0.0  # Unspent Ability Points
    ap_lifetime: float = 0.0  # Total AP ever earned

    # Personal activation map: skill_id -> activation level (0.0 to 1.0)
    activations: dict[str, float] = field(default_factory=dict)

    # Need pressure tracking
    needs: dict[str, NeedPressure] = field(default_factory=dict)

    # Usage history for decay calculation
    last_used: dict[str, float] = field(default_factory=dict)  # skill_id -> timestamp

    # Growth log
    growth_log: list[dict[str, Any]] = field(default_factory=list)

    def activation_tier(self, skill_id: str) -> ActivationTier:
        """Interpret float activation as a capability tier."""
        level = self.activations.get(skill_id, 0.0)
        if level < 0.10:
            return ActivationTier.DORMANT
        elif level < 0.30:
            return ActivationTier.LATENT
        elif level < 0.60:
            return ActivationTier.PARTIAL
        elif level < 0.90:
            return ActivationTier.CAPABLE
        else:
            return ActivationTier.MASTERED

    def can_use(self, skill_id: str) -> bool:
        """Can the agent use this skill at all? (PARTIAL or above)"""
        return self.activations.get(skill_id, 0.0) >= 0.30

    def performance_factor(self, skill_id: str) -> float:
        """
        How well the agent performs this skill (0.0 to 1.0).
        Partial activation = degraded but functional.
        """
        level = self.activations.get(skill_id, 0.0)
        if level < 0.30:
            return 0.0  # Can't use it
        # Smooth ramp from 0.3 (50% performance) to 1.0 (100%)
        return 0.5 + 0.5 * ((level - 0.3) / 0.7)

    def specialization_vector(self) -> dict[str, float]:
        """
        The agent's emergent specialization — sum of activations per tongue.
        This is NOT preset — it EMERGES from what skills the agent develops.
        """
        tongue_totals: dict[str, float] = {t: 0.0 for t in TONGUE_KEYS}
        # This needs the grid to resolve skill_id -> tongue, so we'll compute
        # it from activations directly using tongue prefixes
        return tongue_totals  # Filled by the engine


@dataclass
class PropagationResult:
    """What happened during one tick of the growth engine."""

    tick: int
    decayed: list[tuple[str, str, float]]  # (agent, skill, new_level)
    boosted: list[tuple[str, str, float]]  # (agent, skill, new_level)
    manifested: list[
        tuple[str, str, float]
    ]  # (agent, skill, new_level) — newly activated
    governance_reviews: list[dict[str, Any]]  # Skills that hit need-pressure threshold
    fleet_coverage: dict[str, float]  # Tongue -> % of skills activated fleet-wide


@dataclass
class HodgeCombo:
    """Dual-tongue synergy — unlocked when both tongues are CAPABLE."""

    name: str
    tongue_a: str
    tongue_b: str
    bonus: str
    multiplier: float = 1.3  # 30% bonus (Hodge pair boost)


# Hodge dual pairs — complementary tongue synergies
HODGE_PAIRS: list[HodgeCombo] = [
    HodgeCombo(
        "Architectural Command", "KO", "DR", "Structure + Command = system design"
    ),
    HodgeCombo(
        "Chaotic Research", "RU", "AV", "Entropy + Transport = deep exploration"
    ),
    HodgeCombo("Secure Computation", "CA", "UM", "Compute + Security = safe execution"),
    HodgeCombo("Command Transport", "KO", "AV", "Command + Transport = fleet dispatch"),
    HodgeCombo(
        "Structural Entropy", "DR", "RU", "Structure + Entropy = stress testing"
    ),
    HodgeCombo(
        "Compute Command", "CA", "KO", "Compute + Command = sovereign automation"
    ),
]


# =============================================================================
# The Canonical Skill Catalog
# =============================================================================


def _build_skill_catalog() -> list[SkillNode]:
    """
    The shared skill grid — every possible capability an agent can develop.

    Organized by tongue domain and tier. 4 tiers x 6 tongues = 24 core skills,
    plus 6 Hodge combo skills (tier 5) = 30 total.

    Phi positions distribute skills across the sphere latitude:
      Tier 1: phi near 0 (equator — easy access)
      Tier 2: phi +/- 0.3 (slightly harder)
      Tier 3: phi +/- 0.7 (specialist territory)
      Tier 4: phi +/- 1.2 (mastery — near the poles)
    """
    skills = []

    # Per-tongue skill trees
    tongue_skills = {
        "KO": [
            ("task_dispatch", "Task Dispatch", 1, "Route tasks to appropriate agents"),
            ("formation_swap", "Formation Swap", 2, "Reorganize agent fleet mid-task"),
            (
                "rally_coordination",
                "Rally Coordination",
                3,
                "Boost all fleet members performance",
            ),
            (
                "sovereign_command",
                "Sovereign Command",
                4,
                "Full fleet orchestration authority",
            ),
        ],
        "AV": [
            ("web_search", "Web Search", 1, "Find and retrieve web content"),
            ("navigation", "Navigation", 2, "Multi-step browser navigation"),
            ("site_mapping", "Site Mapping", 3, "Map full site structure and extract"),
            (
                "fleet_transport",
                "Fleet Transport",
                4,
                "Move data between agents and systems",
            ),
        ],
        "RU": [
            (
                "hypothesis_gen",
                "Hypothesis Generation",
                1,
                "Generate research hypotheses",
            ),
            (
                "data_collection",
                "Data Collection",
                2,
                "Gather and structure research data",
            ),
            (
                "chaos_testing",
                "Chaos Testing",
                3,
                "Stress-test systems with random inputs",
            ),
            (
                "entropy_oracle",
                "Entropy Oracle",
                4,
                "Predict system failures from entropy patterns",
            ),
        ],
        "CA": [
            ("code_gen", "Code Generation", 1, "Write functional code"),
            ("test_writing", "Test Writing", 2, "Generate comprehensive test suites"),
            ("training_pipeline", "Training Pipeline", 3, "Run ML training workflows"),
            (
                "model_deployment",
                "Model Deployment",
                4,
                "Deploy and manage production models",
            ),
        ],
        "UM": [
            (
                "governance_scan",
                "Governance Scan",
                1,
                "Check content against governance rules",
            ),
            ("threat_detection", "Threat Detection", 2, "Detect adversarial patterns"),
            ("audit_trail", "Audit Trail", 3, "Generate verifiable audit records"),
            (
                "seal_enforcement",
                "Seal Enforcement",
                4,
                "Enforce Sacred Seal cryptographic proofs",
            ),
        ],
        "DR": [
            ("documentation", "Documentation", 1, "Generate structured documentation"),
            ("debugging", "Debugging", 2, "Diagnose and fix system issues"),
            ("self_healing", "Self Healing", 3, "Automatic error recovery and repair"),
            (
                "architecture",
                "Architecture",
                4,
                "Design and validate system architecture",
            ),
        ],
    }

    for tongue, skill_list in tongue_skills.items():
        theta = TONGUE_LONGITUDES[tongue]
        prev_ids: list[str] = []

        for skill_id, name, tier, desc in skill_list:
            # Phi distributes tiers: equator (easy) to poles (mastery)
            # Alternate positive/negative phi per tongue for spread
            sign = 1 if TONGUE_KEYS.index(tongue) % 2 == 0 else -1
            phi = sign * (tier - 1) * 0.4

            node = SkillNode(
                id=skill_id,
                name=name,
                tongue=tongue,
                tier=tier,
                description=desc,
                phi=phi,
                theta=theta,
                r=max(0.4, 1.0 - (tier - 1) * 0.15),
                base_cost=tier * 8.0,  # 8, 16, 24, 32
                prerequisites=list(prev_ids),  # Must have previous tier
                capability_tag=skill_id,
            )
            skills.append(node)
            prev_ids = [skill_id]

    # Hodge combo skills (tier 5 — emerge from dual-tongue mastery)
    for combo in HODGE_PAIRS:
        combo_id = f"hodge_{combo.tongue_a}_{combo.tongue_b}"
        # Prerequisites: tier 3 from both tongues
        prereqs = [
            tongue_skills[combo.tongue_a][2][0],  # Tier 3 of tongue A
            tongue_skills[combo.tongue_b][2][0],  # Tier 3 of tongue B
        ]
        theta_mid = (
            TONGUE_LONGITUDES[combo.tongue_a] + TONGUE_LONGITUDES[combo.tongue_b]
        ) / 2
        skills.append(
            SkillNode(
                id=combo_id,
                name=combo.name,
                tongue=combo.tongue_a,  # Primary domain
                tier=5,
                description=combo.bonus,
                phi=0.0,  # Hodge combos live at the equator (balance point)
                theta=theta_mid,
                r=0.3,  # Innermost shell — deep skill
                base_cost=40.0,
                prerequisites=prereqs,
                capability_tag=combo_id,
                hodge_partner=combo.tongue_b,
            )
        )

    return skills


SKILL_CATALOG = _build_skill_catalog()


# =============================================================================
# The Agentic Sphere Grid Engine
# =============================================================================


class AgenticSphereGrid:
    """
    The FFX Sphere Grid for AI agents.

    Fused with the ScatteredAttentionSphere — the geometric substrate IS the grid.
    Skills manifest as floating-point capabilities driven by computational necessity.
    The system's own governance engines let commands naturally propagate.

    Growth is deliberately non-optimal and dynamically growing across agents.
    Every agent gets the whole grid, but filling it takes work.
    Some agents show up stronger because they are by design (archetypes)
    and because they have their own grid with stuff pre-filled.

    Multi-layer capability emergence:
      L1: Individual skills (floating-point activation)
      L2: Hodge combos (dual-tongue synergy at 30% bonus)
      L3: Specialization (dominant tongue emerges from usage)
      L4: Fleet synergy (collective grid coverage)
    """

    def __init__(self):
        # The geometric substrate
        self.sphere = ScatteredAttentionSphere(sparsity_threshold=0.0)

        # Shared skill grid (same for all agents)
        self.nodes: dict[str, SkillNode] = {s.id: s for s in SKILL_CATALOG}

        # Agent states
        self.agents: dict[str, AgentState] = {}

        # Global tick counter
        self.tick_count: int = 0

        # Governance log
        self.governance_log: list[dict[str, Any]] = []

        # Plant the grid onto the sphere
        self._plant_grid()

    def _plant_grid(self):
        """
        Plant skill nodes onto the scattered sphere as lattice points.
        This creates the geometric substrate that agents traverse.
        """
        # Create a weight matrix where each skill is a "hot" point
        # Grid size: 6 tongues x 5 tiers = 30 positions
        grid_matrix = np.zeros((6, 5))

        for node in self.nodes.values():
            tongue_idx = TONGUE_KEYS.index(node.tongue)
            tier_idx = min(node.tier - 1, 4)
            # Value = inverse of cost (cheap skills are "louder" on the sphere)
            grid_matrix[tongue_idx, tier_idx] = 1.0 / (
                1.0 + node.effective_cost() * 0.01
            )

        self.sphere.scatter(grid_matrix, "skill_grid", layer_radius=1.0)

    # -------------------------------------------------------------------------
    #  Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str, archetype: str = "blank") -> AgentState:
        """
        Register an agent on the grid with optional archetype pre-fills.

        Like FFX: Tidus starts fast (high agility), Auron starts strong.
        Our archetypes: researcher, builder, guardian, scout, teacher, healer.
        """
        if archetype not in ARCHETYPES:
            archetype = "blank"

        state = AgentState(
            agent_id=agent_id,
            archetype=archetype,
            activations={},
            needs={},
        )

        # Apply archetype pre-fills
        prefills = ARCHETYPES[archetype]
        for skill_id, level in prefills.items():
            if skill_id in self.nodes:
                state.activations[skill_id] = level
                state.last_used[skill_id] = time.time()

        # Set dominant tongue from archetype
        tongue_map = {
            "researcher": "RU",
            "builder": "CA",
            "guardian": "UM",
            "scout": "AV",
            "teacher": "KO",
            "healer": "DR",
            "blank": "KO",
        }
        state.dominant_tongue = tongue_map.get(archetype, "KO")
        state.phi = (
            TONGUE_LONGITUDES.get(state.dominant_tongue, 0.0) * 0.1
        )  # Start near archetype

        self.agents[agent_id] = state
        return state

    # -------------------------------------------------------------------------
    #  AP Economy — Earning and Spending
    # -------------------------------------------------------------------------

    def earn_ap(
        self,
        agent_id: str,
        amount: float,
        reason: str,
        skill_context: Optional[str] = None,
    ) -> float:
        """
        Agent earns AP from doing useful work.

        AP sources:
          - Task completion (success/partial/failure)
          - Teaching (mastered skill used to boost another agent)
          - Cooperation (helped another agent succeed)
        """
        state = self.agents.get(agent_id)
        if not state:
            return 0.0

        state.ap_bank += amount
        state.ap_lifetime += amount

        # If a skill was used in earning this AP, mark it as recently used
        if skill_context and skill_context in state.activations:
            state.last_used[skill_context] = time.time()
            # Tiny activation boost from successful use (practice makes perfect)
            current = state.activations[skill_context]
            boost = min(0.02, (1.0 - current) * 0.05)  # Diminishing returns
            state.activations[skill_context] = min(1.0, current + boost)

        state.growth_log.append(
            {
                "type": "earn_ap",
                "amount": amount,
                "reason": reason,
                "skill": skill_context,
                "tick": self.tick_count,
            }
        )

        return state.ap_bank

    def spend_ap(self, agent_id: str, amount: float) -> bool:
        """Attempt to spend AP. Returns False if insufficient."""
        state = self.agents.get(agent_id)
        if not state or state.ap_bank < amount:
            return False
        state.ap_bank -= amount
        return True

    # -------------------------------------------------------------------------
    #  Skill Manifestation — The Core Growth Engine
    # -------------------------------------------------------------------------

    def manifest_skill(
        self, agent_id: str, skill_id: str, ap_investment: float = 0.0
    ) -> tuple[bool, float, str]:
        """
        Attempt to manifest (or grow) a skill.

        Returns: (success, new_activation_level, message)

        The activation grows proportionally to AP invested relative to cost.
        Partial investment = partial growth. You don't need to pay all at once.

        Governance gate: checks if the agent is ALLOWED to grow this skill
        based on the current system state.
        """
        state = self.agents.get(agent_id)
        node = self.nodes.get(skill_id)
        if not state or not node:
            return False, 0.0, "Invalid agent or skill"

        # Check prerequisites — all must be at least PARTIAL (0.3)
        for prereq_id in node.prerequisites:
            prereq_level = state.activations.get(prereq_id, 0.0)
            if prereq_level < 0.30:
                return (
                    False,
                    state.activations.get(skill_id, 0.0),
                    f"Prerequisite '{prereq_id}' not met (need 0.30, have {prereq_level:.2f})",
                )

        # Governance gate — check if the system allows this activation
        verdict = self._governance_check(agent_id, skill_id)
        if verdict == GovernanceVerdict.DENY:
            return False, state.activations.get(skill_id, 0.0), "Governance DENIED"

        # Apply governance modifier
        if verdict == GovernanceVerdict.THROTTLE:
            node.governance_multiplier = min(3.0, node.governance_multiplier * 1.5)
        elif verdict == GovernanceVerdict.ACCELERATE:
            node.governance_multiplier = max(0.3, node.governance_multiplier * 0.7)

        # Calculate AP to invest
        if ap_investment <= 0:
            ap_investment = min(
                state.ap_bank, node.effective_cost() * 0.25
            )  # Default: 25% of cost

        if not self.spend_ap(agent_id, ap_investment):
            return False, state.activations.get(skill_id, 0.0), "Insufficient AP"

        # Grow activation proportionally
        cost = node.effective_cost()
        growth = ap_investment / cost if cost > 0 else 0.0
        current = state.activations.get(skill_id, 0.0)
        new_level = min(1.0, current + growth)

        state.activations[skill_id] = new_level
        state.last_used[skill_id] = time.time()

        # Adjacency boost: nearby skills get a tiny free boost
        self._adjacency_ripple(state, node, growth * 0.1)

        tier_name = state.activation_tier(skill_id).name
        state.growth_log.append(
            {
                "type": "manifest",
                "skill": skill_id,
                "from": current,
                "to": new_level,
                "tier": tier_name,
                "ap_spent": ap_investment,
                "tick": self.tick_count,
            }
        )

        return (
            True,
            new_level,
            f"{skill_id}: {current:.2f} -> {new_level:.2f} ({tier_name})",
        )

    def _adjacency_ripple(self, state: AgentState, source: SkillNode, ripple: float):
        """
        Adjacent skills get a tiny free boost when a nearby skill is activated.
        'Adjacent' = same tongue and within 1 tier, OR Hodge partner tongue.
        This is the non-optimal organic growth — skills bleed into neighbors.
        """
        for node in self.nodes.values():
            if node.id == source.id:
                continue

            # Same tongue, adjacent tier
            same_tongue = node.tongue == source.tongue
            adjacent_tier = abs(node.tier - source.tier) <= 1
            hodge_partner = node.tongue == source.hodge_partner

            if (same_tongue and adjacent_tier) or hodge_partner:
                current = state.activations.get(node.id, 0.0)
                if current < 1.0:
                    boost = ripple * (0.5 if hodge_partner else 1.0)
                    state.activations[node.id] = min(1.0, current + boost)

    # -------------------------------------------------------------------------
    #  Computational Necessity — The Recursive Improvement Engine
    # -------------------------------------------------------------------------

    def computational_necessity(
        self,
        agent_id: str,
        task_type: str,
        outcome: str,
        needed_skills: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        The system detects what the agent NEEDS.

        When an agent attempts a task:
          success -> AP earned, nearby skills get a tiny boost
          partial -> AP earned, 'need pressure' on missing skills
          failure -> No AP, strong 'need pressure' toward what was needed

        This IS the recursive improvement engine. The system discovers what
        capabilities it needs by trying and failing, then governance reviews
        whether to lower barriers.

        Args:
            agent_id: Which agent attempted the task
            task_type: What kind of task (maps to a skill domain)
            outcome: "success", "partial", "failure"
            needed_skills: Skills that would have helped (optional, auto-detected)

        Returns:
            Dict with AP earned, skills affected, governance reviews triggered
        """
        state = self.agents.get(agent_id)
        if not state:
            return {"error": "Unknown agent"}

        result: dict[str, Any] = {
            "agent": agent_id,
            "task": task_type,
            "outcome": outcome,
            "ap_earned": 0.0,
            "skills_used": [],
            "need_pressure_applied": [],
            "governance_reviews": [],
        }

        # Earn AP based on outcome
        ap = AP_REWARDS.get(outcome, 0.0)
        if ap > 0:
            self.earn_ap(agent_id, ap, f"task:{task_type}", task_type)
            result["ap_earned"] = ap

        # Auto-detect needed skills from task type if not provided
        if needed_skills is None:
            needed_skills = self._infer_needed_skills(task_type)

        # Track which skills were used vs which were needed but missing
        for skill_id in needed_skills:
            if state.can_use(skill_id):
                # Skill was available — mark as used
                state.last_used[skill_id] = time.time()
                result["skills_used"].append(skill_id)
            else:
                # Skill was NEEDED but not available — apply need pressure
                if skill_id not in state.needs:
                    state.needs[skill_id] = NeedPressure(skill_id=skill_id)

                pressure = state.needs[skill_id]
                new_pressure = pressure.apply_failure(task_type)
                result["need_pressure_applied"].append(
                    {
                        "skill": skill_id,
                        "pressure": new_pressure,
                        "failures": pressure.failure_count,
                    }
                )

                # Check if pressure triggers a governance review
                if pressure.should_trigger_review():
                    review = self._governance_review_necessity(
                        agent_id, skill_id, pressure
                    )
                    result["governance_reviews"].append(review)

        return result

    def _infer_needed_skills(self, task_type: str) -> list[str]:
        """Infer which skills a task type needs based on capability tags."""
        needed = []
        for node in self.nodes.values():
            if node.capability_tag == task_type:
                needed.append(node.id)
            # Also check if task_type is a broader domain
            if (
                task_type in node.description.lower()
                or task_type == node.capability_tag
            ):
                if node.id not in needed:
                    needed.append(node.id)
        return needed if needed else [task_type]  # Fall back to literal

    def _governance_review_necessity(
        self, agent_id: str, skill_id: str, pressure: NeedPressure
    ) -> dict[str, Any]:
        """
        Governance reviews whether to ACCELERATE a skill based on demonstrated need.

        This is where the system's governance engines LET commands naturally propagate.
        If an agent keeps needing something and governance approves, the barrier drops.
        """
        node = self.nodes.get(skill_id)
        state = self.agents.get(agent_id)
        if not node or not state:
            return {"verdict": "DENY", "reason": "Unknown skill or agent"}

        # Governance heuristic: approve if need is genuine and risk is low
        # Higher tiers and security-domain skills get more scrutiny
        risk_score = node.tier * TONGUE_WEIGHTS[node.tongue] * 0.1
        need_score = pressure.pressure * (1 + pressure.failure_count * 0.1)

        if need_score > risk_score * 2:
            # Strong need, acceptable risk -> ACCELERATE
            node.governance_multiplier = max(0.3, node.governance_multiplier * 0.6)
            # Grant a free partial activation as a "head start"
            current = state.activations.get(skill_id, 0.0)
            if current < 0.15:
                state.activations[skill_id] = 0.15  # Push to LATENT
            # Reset pressure (need was addressed)
            pressure.pressure = 0.0

            review = {
                "verdict": "ACCELERATE",
                "skill": skill_id,
                "agent": agent_id,
                "need_score": need_score,
                "risk_score": risk_score,
                "new_multiplier": node.governance_multiplier,
                "new_activation": state.activations.get(skill_id, 0.0),
            }
        elif need_score > risk_score:
            # Moderate need -> THROTTLE (allow but watch)
            review = {
                "verdict": "THROTTLE",
                "skill": skill_id,
                "agent": agent_id,
                "need_score": need_score,
                "risk_score": risk_score,
            }
        else:
            # Risk too high -> DENY
            review = {
                "verdict": "DENY",
                "skill": skill_id,
                "agent": agent_id,
                "need_score": need_score,
                "risk_score": risk_score,
            }

        self.governance_log.append(review)
        return review

    # -------------------------------------------------------------------------
    #  Governance Gate
    # -------------------------------------------------------------------------

    def _governance_check(self, agent_id: str, skill_id: str) -> GovernanceVerdict:
        """
        Check if governance allows this skill activation.

        Factors:
          - Agent's drift from safe operation (high drift = DENY/THROTTLE)
          - Skill's security tier (UM skills get extra scrutiny)
          - System-wide resource pressure (too many agents growing same skill = THROTTLE)
          - Need pressure (high need + low risk = ACCELERATE)
        """
        state = self.agents.get(agent_id)
        node = self.nodes.get(skill_id)
        if not state or not node:
            return GovernanceVerdict.DENY

        # Check need pressure — if the agent NEEDS this, governance is more lenient
        need = state.needs.get(skill_id)
        if need and need.pressure > NEED_PRESSURE_TRIGGER:
            return GovernanceVerdict.ACCELERATE

        # Security domain skills always get scrutiny
        if node.tongue == "UM" and node.tier >= 3:
            return GovernanceVerdict.THROTTLE

        # Default: ALLOW
        return GovernanceVerdict.ALLOW

    # -------------------------------------------------------------------------
    #  Propagation Tick — The Growth Cycle
    # -------------------------------------------------------------------------

    def propagate(self) -> PropagationResult:
        """
        Run one tick of the growth engine.

        Per tick:
          1. Decay unused skills (use it or lose it)
          2. Apply adjacency ripple from recently used skills
          3. Process accumulated need pressure -> governance reviews
          4. Compute fleet-wide coverage stats

        This runs on a cycle — like the FFX battle system.
        Each tick, the grid evolves based on what's actually happening.
        """
        self.tick_count += 1
        now = time.time()

        decayed = []
        boosted = []
        manifested = []
        reviews = []

        for agent_id, state in self.agents.items():
            for skill_id in list(state.activations.keys()):
                level = state.activations[skill_id]
                last = state.last_used.get(skill_id, now)
                age = now - last

                # Decay: skills unused for > 60 seconds lose activation
                # (In production this would be hours/days, but for demo: seconds)
                if age > 60.0 and level > ACTIVATION_FLOOR:
                    decay = DECAY_RATE * (
                        1 + age / 300.0
                    )  # Faster decay for older disuse
                    new_level = max(0.0, level - decay)
                    if new_level < ACTIVATION_FLOOR:
                        new_level = 0.0
                    state.activations[skill_id] = new_level
                    decayed.append((agent_id, skill_id, new_level))

                # Track newly manifested skills (crossed the 0.3 threshold)
                was_usable = level >= 0.30
                is_usable = state.activations.get(skill_id, 0.0) >= 0.30
                if is_usable and not was_usable:
                    manifested.append((agent_id, skill_id, state.activations[skill_id]))

            # Process need pressure -> governance reviews
            for skill_id, need in list(state.needs.items()):
                if need.should_trigger_review():
                    review = self._governance_review_necessity(agent_id, skill_id, need)
                    reviews.append(review)

        # Fleet coverage: what % of skills are activated across ALL agents
        fleet_coverage = self._compute_fleet_coverage()

        return PropagationResult(
            tick=self.tick_count,
            decayed=decayed,
            boosted=boosted,
            manifested=manifested,
            governance_reviews=reviews,
            fleet_coverage=fleet_coverage,
        )

    def _compute_fleet_coverage(self) -> dict[str, float]:
        """
        Compute fleet-wide coverage per tongue.
        This is the L4 emergence — the fleet as a whole has capabilities
        no single agent has.
        """
        coverage: dict[str, dict[str, float]] = {t: {} for t in TONGUE_KEYS}

        for node in self.nodes.values():
            # Best activation across all agents for this skill
            best = 0.0
            for state in self.agents.values():
                level = state.activations.get(node.id, 0.0)
                if level > best:
                    best = level
            coverage[node.tongue][node.id] = best

        # Percentage of skills at PARTIAL or above per tongue
        result = {}
        for tongue in TONGUE_KEYS:
            skills = coverage[tongue]
            if not skills:
                result[tongue] = 0.0
                continue
            usable = sum(1 for v in skills.values() if v >= 0.30)
            result[tongue] = usable / len(skills)

        return result

    # -------------------------------------------------------------------------
    #  Cooperative AP — One Agent Helps Another
    # -------------------------------------------------------------------------

    def teach(self, teacher_id: str, student_id: str, skill_id: str) -> dict[str, Any]:
        """
        A mastered agent teaches a skill to another agent.

        Requirements: teacher must be MASTERED (>=0.9) in the skill.
        Effect: student gets a free activation boost + teacher earns teach AP.

        This is the cooperative growth mechanism — agents help each other.
        """
        teacher = self.agents.get(teacher_id)
        student = self.agents.get(student_id)
        node = self.nodes.get(skill_id)

        if not teacher or not student or not node:
            return {"success": False, "reason": "Invalid teacher, student, or skill"}

        teacher_level = teacher.activations.get(skill_id, 0.0)
        if teacher_level < 0.90:
            return {
                "success": False,
                "reason": f"Teacher not mastered ({teacher_level:.2f} < 0.90)",
            }

        # Student gets 20% of the remaining activation for free
        student_level = student.activations.get(skill_id, 0.0)
        boost = (1.0 - student_level) * 0.20
        student.activations[skill_id] = min(1.0, student_level + boost)
        student.last_used[skill_id] = time.time()

        # Teacher earns AP for teaching
        self.earn_ap(teacher_id, AP_REWARDS["teach"], f"taught:{skill_id}", skill_id)

        return {
            "success": True,
            "teacher": teacher_id,
            "student": student_id,
            "skill": skill_id,
            "student_before": student_level,
            "student_after": student.activations[skill_id],
            "teacher_ap_earned": AP_REWARDS["teach"],
        }

    # -------------------------------------------------------------------------
    #  Agent Specialization Analysis
    # -------------------------------------------------------------------------

    def agent_specialization(self, agent_id: str) -> dict[str, Any]:
        """
        Analyze an agent's emergent specialization.

        This is NOT preset — it EMERGES from what skills the agent develops.
        Like in FFX where characters drift toward certain grid areas through play.
        """
        state = self.agents.get(agent_id)
        if not state:
            return {"error": "Unknown agent"}

        tongue_scores: dict[str, float] = {t: 0.0 for t in TONGUE_KEYS}
        skill_count: dict[str, int] = {t: 0 for t in TONGUE_KEYS}

        for skill_id, level in state.activations.items():
            node = self.nodes.get(skill_id)
            if node and level > 0.0:
                tongue_scores[node.tongue] += level
                if level >= 0.30:
                    skill_count[node.tongue] += 1

        # Dominant tongue = highest total activation
        dominant = max(tongue_scores, key=tongue_scores.get)  # type: ignore

        # Active Hodge combos
        active_combos = []
        for combo in HODGE_PAIRS:
            a_capable = (
                tongue_scores.get(combo.tongue_a, 0.0) >= 1.5
            )  # Multiple skills active
            b_capable = tongue_scores.get(combo.tongue_b, 0.0) >= 1.5
            if a_capable and b_capable:
                active_combos.append(combo.name)

        return {
            "agent_id": agent_id,
            "archetype": state.archetype,
            "dominant_tongue": dominant,
            "tongue_scores": tongue_scores,
            "usable_skills": skill_count,
            "total_ap_earned": state.ap_lifetime,
            "ap_bank": state.ap_bank,
            "active_hodge_combos": active_combos,
            "activation_tier_summary": {
                t.name: sum(
                    1
                    for s, l in state.activations.items()
                    if state.activation_tier(s) == t
                )
                for t in ActivationTier
            },
        }

    # -------------------------------------------------------------------------
    #  Grid Snapshot — Full State View
    # -------------------------------------------------------------------------

    def grid_snapshot(self) -> dict[str, Any]:
        """Full grid state for serialization or visualization."""
        return {
            "tick": self.tick_count,
            "total_nodes": len(self.nodes),
            "total_agents": len(self.agents),
            "sphere_points": len(self.sphere.lattice),
            "fleet_coverage": self._compute_fleet_coverage(),
            "agents": {aid: self.agent_specialization(aid) for aid in self.agents},
            "governance_log_size": len(self.governance_log),
        }
