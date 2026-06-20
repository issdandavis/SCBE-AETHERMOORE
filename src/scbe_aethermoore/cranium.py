"""The full 16-region Crystal Cranium connectome + governed thoughts.

Builds the PHDM "Geometric Skull" as a Connectome: 16 polyhedral regions across five
anatomical rings (core / cortex / bridge / cerebellum / risk), wired by valid synapses
weighted with the Sacred Tongues. A THOUGHT is a path of governed synapse firings; the
cranium adds the doc's two geometric laws:

  * Orthogonal excursion -> blocked: a jump between regions with no synapse (e.g. the doc's
    Cube -> Great Stellated Dodecahedron) terminates the thought.
  * Can't stay in the risk zone: a thought that ends in a Kepler-Poinsot risk region is
    forced to BOUNCE back to the core (energy cost makes lingering impossible).

Energy cost rises toward the Wall (bone density): energy(r) = 1/(1-r), so a risk hop costs
~6-13x a core hop and a thought has an energy budget.

    from scbe_aethermoore.cranium import build_cranium, think
    out = think(build_cranium(), ["cube", "octahedron", "dodecahedron"], "verify these facts")
    out["status"]  # "COMPLETED"
"""

from __future__ import annotations

from typing import Dict, List

from scbe_aethermoore.synapses import Connectome, Region, Synapse

# (name, ring, r, cognitive function) -- the 16 polyhedral regions.
_REGIONS = [
    # Core: the limbic system (5 Platonic solids), r < 0.2, maximally stable
    ("tetrahedron", "core", 0.10, "do-no-harm axiom"),
    ("cube", "core", 0.15, "verified facts / data integrity"),
    ("octahedron", "core", 0.15, "binary decision / access gate"),
    ("dodecahedron", "core", 0.18, "policy / complex rules"),
    ("icosahedron", "core", 0.18, "multimodal integration"),
    # Cortex: the processing layer (3 Archimedean solids), mid radius
    ("truncated_icosahedron", "cortex", 0.45, "multi-step planning"),
    ("rhombicuboctahedron", "cortex", 0.45, "concept bridging / analogy"),
    ("snub_dodecahedron", "cortex", 0.55, "creative synthesis"),
    # Connectome: the neural bridges (Johnson / Rhombic)
    ("rhombic_dodecahedron", "bridge", 0.35, "space-filling logic"),
    ("rhombic_triacontahedron", "bridge", 0.40, "high-dim pattern match"),
    ("johnson_a", "bridge", 0.50, "domain connector A"),
    ("johnson_b", "bridge", 0.60, "domain connector B (gateway to risk)"),
    # Cerebellum: the recursive processor (2 toroidal), self-stabilizing audit path
    ("szilassi", "cerebellum", 0.30, "self-diagnostic loop"),
    ("csaszar", "cerebellum", 0.35, "recursive processing"),
    # Subconscious: the risk zone (2 Kepler-Poinsot stars), near the Wall -- visit only
    ("small_stellated_dodecahedron", "risk", 0.85, "high-risk abstract reasoning"),
    ("great_stellated_dodecahedron", "risk", 0.92, "adversarial / hallucination onset"),
]

# Valid synapses (edges). The tongue weight signals the nature of the transition.
_EDGES = [
    ("entry", "cube", "DR"),  # govern entry into the skull
    # core internal -- fast intent (KO)
    ("tetrahedron", "cube", "KO"),
    ("cube", "octahedron", "KO"),
    ("cube", "icosahedron", "KO"),
    ("octahedron", "dodecahedron", "KO"),
    ("dodecahedron", "icosahedron", "KO"),
    # core -> bridges -- memory consolidation (RU)
    ("cube", "rhombic_dodecahedron", "RU"),
    ("icosahedron", "rhombic_triacontahedron", "RU"),
    # bridges -> cortex -- attention/context (AV)
    ("rhombic_dodecahedron", "rhombicuboctahedron", "AV"),
    ("rhombic_triacontahedron", "truncated_icosahedron", "AV"),
    ("johnson_a", "snub_dodecahedron", "AV"),
    # cortex internal -- execution (CA)
    ("truncated_icosahedron", "rhombicuboctahedron", "CA"),
    ("rhombicuboctahedron", "snub_dodecahedron", "CA"),
    ("rhombicuboctahedron", "johnson_a", "CA"),
    # cortex -> risk zone ONLY through the johnson_b gateway -- suppression (UM), dangerous
    ("snub_dodecahedron", "johnson_b", "UM"),
    ("johnson_b", "small_stellated_dodecahedron", "UM"),
    ("small_stellated_dodecahedron", "great_stellated_dodecahedron", "UM"),
    # risk zone -> bounce back via the cerebellar audit path -> core -- lock/seal (DR)
    ("small_stellated_dodecahedron", "szilassi", "DR"),
    ("great_stellated_dodecahedron", "szilassi", "DR"),
    ("szilassi", "tetrahedron", "DR"),
    ("szilassi", "cube", "DR"),
    ("csaszar", "szilassi", "KO"),
]


def _region_handler(name: str, function: str):
    def handler(message: str) -> str:
        return f"visited {name} [{function}]"

    return handler


def build_cranium() -> Connectome:
    c = Connectome()
    for name, ring, r, function in _REGIONS:
        c.add_region(Region(name, function, _region_handler(name, function), r=r, ring=ring))
    for source, target, tongue in _EDGES:
        c.add_synapse(Synapse(source, target, tongue))
    return c


def _energy(r: float) -> float:
    return 1.0 / max(1e-6, 1.0 - r)


def think(cranium: Connectome, path: List[str], message: str, budget: float = 40.0) -> Dict:
    """Run a thought (a path of regions). Governed + receipted per hop; risk-zone visits are
    forced to bounce back to the core; an edge-less jump blocks; energy is budgeted."""
    hops: List[dict] = []
    total = 0.0
    prev = "entry"
    status = "COMPLETED"
    for region in path:
        rec = cranium.fire(prev, region, message)  # canonical sealed receipt (transcript)
        reg = cranium.regions.get(region)
        hop = dict(rec)  # annotation view -- never mutate the sealed receipt
        if reg is not None:
            hop["ring"], hop["region_r"], hop["energy"] = reg.ring, reg.r, round(_energy(reg.r), 2)
        hops.append(hop)
        prev = region
        if rec["status"] != "FIRED":
            status = "BLOCKED" if rec["status"] == "NO_SYNAPSE" else rec["status"]
            break
        total += _energy(reg.r)  # cost only what actually fired
        if total > budget:
            status = "ENERGY_EXCEEDED"
            break
    # Can't stay in the risk zone: force a bounce back to the core via the audit path.
    if status == "COMPLETED" and hops and hops[-1].get("ring") == "risk":
        for nxt in ("szilassi", "tetrahedron"):
            rec = cranium.fire(prev, nxt, message)
            reg = cranium.regions[nxt]
            hop = dict(rec)
            hop["ring"], hop["region_r"], hop["energy"], hop["forced"] = reg.ring, reg.r, round(_energy(reg.r), 2), True
            hops.append(hop)
            prev = nxt
            if rec["status"] != "FIRED":
                break
            total += _energy(reg.r)
        status = "BOUNCED"
    return {
        "status": status,
        "route": " -> ".join(h["target"] for h in hops),
        "total_energy": round(total, 2),
        "rings": [h.get("ring", "?") for h in hops],
        "hops": hops,
        "sealed": cranium.verify(),
    }
