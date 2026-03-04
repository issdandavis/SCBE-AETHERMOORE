"""Gacha Isekai — Stuck-in-a-Gacha-Game integration for SCBE-AETHERMOORE.

Modules:
    squad                      — 6-Tongue squad with gravitational alignment
    evolution                  — Digimon-style evolution & life-sim careers
    training                   — HF training loop with SCBE governance gating
    nodal                      — Poly-AI cultural nodal network
    combat                     — Squad combat as code correction / math-monster debugging
    personality_manifold       — Dual-manifold personality (positive/negative space pairs)
    personality_cluster_lattice — Full cluster lattice with brackets, drift, portals
    personality_tri_manifold    — Tri-manifold personality (M+/M0/M-, 27-state ternary)
"""

from src.gacha_isekai.squad import GachaSquad, SquadMember, TernaryAlignment
from src.gacha_isekai.evolution import EvolutionSimulator
from src.gacha_isekai.combat import GachaSquadCombat
from src.gacha_isekai.training import HFTrainingLoop
from src.gacha_isekai.nodal import PolyAINodalNetwork
from src.gacha_isekai.personality_manifold import PersonalityManifold
from src.gacha_isekai.personality_cluster_lattice import PersonalityClusterLattice
from src.gacha_isekai.personality_tri_manifold import TriManifoldPersonality

__all__ = [
    "GachaSquad",
    "SquadMember",
    "TernaryAlignment",
    "EvolutionSimulator",
    "GachaSquadCombat",
    "HFTrainingLoop",
    "PolyAINodalNetwork",
    "PersonalityManifold",
    "PersonalityClusterLattice",
    "TriManifoldPersonality",
]
