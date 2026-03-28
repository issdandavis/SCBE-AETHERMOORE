"""
Tongue-Domain Mappings — Sacred Tongue semantic domains for CDDM.

Each Sacred Tongue governs a conceptual domain:
  KO (Control)   -> Energy / Force / Authority
  AV (Transport) -> Momentum / Flow / Communication
  RU (Policy)    -> Entropy / Order / Governance
  CA (Compute)   -> Complexity / Processing / Logic
  UM (Security)  -> Risk / Threat / Protection
  DR (Schema)    -> Structure / Pattern / Memory

These mappings let the CDDM framework translate between physical quantities,
narrative elements, and governance states through tongue-mediated morphisms.

@module cddm/tongue_domains
@version 1.0.0
"""

from __future__ import annotations

import math
from typing import Dict, List

from .domain import Domain
from .morphism import Morphism

# ═══════════════════════════════════════════════════════════════
# Sacred Tongue Domains
# ═══════════════════════════════════════════════════════════════

TONGUE_DOMAINS: Dict[str, Domain] = {
    # KO — Control: Energy, Force, Authority
    "KO": Domain("Energy", units=("Joule",), bounds=(0, 1e6)),
    "KO_narrative": Domain("Authority", units=("AuthLevel",), bounds=(0, 10)),
    "KO_governance": Domain("CommandForce", units=("CmdUnit",), bounds=(0, 100)),
    # AV — Transport: Momentum, Flow, Communication
    "AV": Domain("Momentum", units=("kg*m/s",), bounds=(0, 1e5)),
    "AV_narrative": Domain("Communication", units=("CommFlow",), bounds=(0, 10)),
    "AV_governance": Domain("DataFlow", units=("Mbps",), bounds=(0, 1e4)),
    # RU — Policy: Entropy, Order, Governance
    "RU": Domain("Entropy", units=("J/K",), bounds=(0, 1e3)),
    "RU_narrative": Domain("PlotChaos", units=("ChaosLevel",), bounds=(0, 10)),
    "RU_governance": Domain(
        "PolicyBreakdown", units=("BreakdownIdx",), bounds=(0, 100)
    ),
    # CA — Compute: Complexity, Processing, Logic
    "CA": Domain("Complexity", units=("FLOP",), bounds=(0, 1e12)),
    "CA_narrative": Domain("Intrigue", units=("IntrigueLevel",), bounds=(0, 10)),
    "CA_governance": Domain("ComputeLoad", units=("TFLOP",), bounds=(0, 1e3)),
    # UM — Security: Risk, Threat, Protection
    "UM": Domain("Risk", units=("RiskScore",), bounds=(0, 1)),
    "UM_narrative": Domain("Danger", units=("DangerLevel",), bounds=(0, 10)),
    "UM_governance": Domain("ThreatIndex", units=("ThreatIdx",), bounds=(0, 100)),
    # DR — Schema: Structure, Pattern, Memory
    "DR": Domain("Structure", units=("ShannonBit",), bounds=(0, 1e6)),
    "DR_narrative": Domain(
        "WorldComplexity", units=("ComplexityLevel",), bounds=(0, 10)
    ),
    "DR_governance": Domain(
        "SchemaIntegrity", units=("IntegrityPct",), bounds=(0, 100)
    ),
}


# ═══════════════════════════════════════════════════════════════
# Cross-Domain Morphisms
# ═══════════════════════════════════════════════════════════════


def _linear(scale: float, offset: float = 0.0):
    """Create a linear mapping function."""

    def f(x: float) -> float:
        return x * scale + offset

    return f


def _log_scale(base: float, cap: float):
    """Logarithmic scaling with cap."""

    def f(x: float) -> float:
        if x <= 0:
            return 0.0
        return min(cap, math.log(x + 1) / math.log(base))

    return f


def _sigmoid(midpoint: float, steepness: float, out_scale: float):
    """Sigmoid mapping centered at midpoint."""

    def f(x: float) -> float:
        return out_scale / (1 + math.exp(-steepness * (x - midpoint)))

    return f


CROSS_DOMAIN_MAP: Dict[str, Morphism] = {
    # KO: Energy -> Authority (log scale: 1MJ -> 10 authority)
    "energy_to_authority": Morphism(
        src=TONGUE_DOMAINS["KO"],
        dst=TONGUE_DOMAINS["KO_narrative"],
        func=_log_scale(1e6, 10.0),
        name="Energy->Authority",
        inverse_func=lambda y: (1e6 ** (y / 10.0)) - 1 if y > 0 else 0.0,
    ),
    # KO: Energy -> CommandForce (linear: 1MJ -> 100 CmdUnit)
    "energy_to_command": Morphism(
        src=TONGUE_DOMAINS["KO"],
        dst=TONGUE_DOMAINS["KO_governance"],
        func=_linear(100 / 1e6),
        name="Energy->Command",
        inverse_func=_linear(1e6 / 100),
    ),
    # AV: Momentum -> Communication (log scale)
    "momentum_to_comm": Morphism(
        src=TONGUE_DOMAINS["AV"],
        dst=TONGUE_DOMAINS["AV_narrative"],
        func=_log_scale(1e5, 10.0),
        name="Momentum->Communication",
    ),
    # AV: Momentum -> DataFlow (linear)
    "momentum_to_dataflow": Morphism(
        src=TONGUE_DOMAINS["AV"],
        dst=TONGUE_DOMAINS["AV_governance"],
        func=_linear(1e4 / 1e5),
        name="Momentum->DataFlow",
        inverse_func=_linear(1e5 / 1e4),
    ),
    # RU: Entropy -> PlotChaos (sigmoid: mid=500 J/K, steep=0.01)
    "entropy_to_chaos": Morphism(
        src=TONGUE_DOMAINS["RU"],
        dst=TONGUE_DOMAINS["RU_narrative"],
        func=_sigmoid(500, 0.01, 10.0),
        name="Entropy->PlotChaos",
    ),
    # RU: Entropy -> PolicyBreakdown (linear)
    "entropy_to_breakdown": Morphism(
        src=TONGUE_DOMAINS["RU"],
        dst=TONGUE_DOMAINS["RU_governance"],
        func=_linear(100 / 1e3),
        name="Entropy->PolicyBreakdown",
        inverse_func=_linear(1e3 / 100),
    ),
    # CA: Complexity -> Intrigue (log)
    "complexity_to_intrigue": Morphism(
        src=TONGUE_DOMAINS["CA"],
        dst=TONGUE_DOMAINS["CA_narrative"],
        func=_log_scale(1e12, 10.0),
        name="Complexity->Intrigue",
    ),
    # UM: Risk -> Danger (linear scale: [0,1] -> [0,10])
    "risk_to_danger": Morphism(
        src=TONGUE_DOMAINS["UM"],
        dst=TONGUE_DOMAINS["UM_narrative"],
        func=_linear(10.0),
        name="Risk->Danger",
        inverse_func=_linear(0.1),
    ),
    # UM: Risk -> ThreatIndex (linear: [0,1] -> [0,100])
    "risk_to_threat": Morphism(
        src=TONGUE_DOMAINS["UM"],
        dst=TONGUE_DOMAINS["UM_governance"],
        func=_linear(100.0),
        name="Risk->ThreatIndex",
        inverse_func=_linear(0.01),
    ),
    # DR: Structure -> WorldComplexity (log)
    "structure_to_world": Morphism(
        src=TONGUE_DOMAINS["DR"],
        dst=TONGUE_DOMAINS["DR_narrative"],
        func=_log_scale(1e6, 10.0),
        name="Structure->WorldComplexity",
    ),
    # DR: Structure -> SchemaIntegrity (inverse: more structure = higher integrity)
    "structure_to_integrity": Morphism(
        src=TONGUE_DOMAINS["DR"],
        dst=TONGUE_DOMAINS["DR_governance"],
        func=lambda x: min(100.0, 100.0 * (1 - math.exp(-x / 1e5))),
        name="Structure->SchemaIntegrity",
    ),
    # Cross-tongue: Authority -> Danger (KO_narrative -> UM_narrative)
    "authority_to_danger": Morphism(
        src=TONGUE_DOMAINS["KO_narrative"],
        dst=TONGUE_DOMAINS["UM_narrative"],
        func=lambda x: 10.0 - x,  # high authority = low danger
        name="Authority->Danger",
        inverse_func=lambda y: 10.0 - y,
    ),
    # Cross-tongue: PlotChaos -> Intrigue (RU_narrative -> CA_narrative)
    "chaos_to_intrigue": Morphism(
        src=TONGUE_DOMAINS["RU_narrative"],
        dst=TONGUE_DOMAINS["CA_narrative"],
        func=lambda x: min(10.0, x * 1.2),
        name="PlotChaos->Intrigue",
    ),
}


def tongue_domain(tongue: str, variant: str = "physical") -> Domain:
    """Look up a tongue's domain by variant (physical, narrative, governance)."""
    if variant == "physical":
        return TONGUE_DOMAINS[tongue]
    elif variant == "narrative":
        return TONGUE_DOMAINS[f"{tongue}_narrative"]
    elif variant == "governance":
        return TONGUE_DOMAINS[f"{tongue}_governance"]
    raise ValueError(f"Unknown variant {variant!r} for tongue {tongue!r}")


def all_tongue_morphisms() -> List[Morphism]:
    """Return all registered cross-domain morphisms."""
    return list(CROSS_DOMAIN_MAP.values())
