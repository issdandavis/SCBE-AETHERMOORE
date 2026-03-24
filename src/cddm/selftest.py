#!/usr/bin/env python3
"""
CDDM Framework Self-Test
=========================

Validates Domain, Morphism, CompositionChain, DomainGraph,
GraphIsomorphism, and tongue-domain mappings.

Run: python -m cddm.selftest  (from src/)
  or: python src/cddm/selftest.py
"""

import sys
import os

# Allow running from repo root or src/
_here = os.path.dirname(os.path.abspath(__file__))
_src = os.path.dirname(_here)
if _src not in sys.path:
    sys.path.insert(0, _src)

from cddm.domain import Domain, DomainError
from cddm.morphism import Morphism, MorphismError
from cddm.functor import (
    CompositionChain,
    DomainGraph,
    GraphIsomorphism,
    compose,
    identity_morphism,
)
from cddm.tongue_domains import (
    CROSS_DOMAIN_MAP,
    tongue_domain,
    all_tongue_morphisms,
)


def selftest() -> int:
    errors = 0

    def check(label: str, condition: bool) -> None:
        nonlocal errors
        if not condition:
            print(f"  FAIL: {label}")
            errors += 1

    print("=== CDDM Framework Self-Test ===\n")

    # [1] Domain
    print("[1] Domain")
    energy = Domain("Energy", units=("Joule",), bounds=(0, 1e6))
    check("domain creation", energy.name == "Energy")
    check("contains in-bounds", energy.contains(500_000))
    check("contains lower", energy.contains(0))
    check("contains upper", energy.contains(1e6))
    check("rejects out-of-bounds", not energy.contains(-1))
    check("rejects above", not energy.contains(1e6 + 1))
    check("clamp low", energy.clamp(-100) == 0)
    check("clamp high", energy.clamp(2e6) == 1e6)
    check("normalize 0", abs(energy.normalize(0) - 0.0) < 1e-9)
    check("normalize mid", abs(energy.normalize(500_000) - 0.5) < 1e-9)
    check("normalize 1", abs(energy.normalize(1e6) - 1.0) < 1e-9)
    check("denormalize", abs(energy.denormalize(0.5) - 500_000) < 1)
    check("span", abs(energy.span() - 1e6) < 1)
    check("midpoint", abs(energy.midpoint() - 500_000) < 1)
    check("equality", energy == Domain("Energy", units=("Joule",), bounds=(0, 1e6)))
    check("hash stable", hash(energy) == hash(Domain("Energy", units=("Joule",), bounds=(0, 1e6))))

    # Validation
    try:
        energy.validate(500_000)
        check("validate passes", True)
    except DomainError:
        check("validate passes", False)
    try:
        energy.validate(-1)
        check("validate rejects", False)
    except DomainError:
        check("validate rejects", True)

    # Bad construction
    try:
        Domain("bad", units=("x",), bounds=(10, 5))
        check("rejects inverted bounds", False)
    except DomainError:
        check("rejects inverted bounds", True)
    try:
        Domain("", units=("x",), bounds=(0, 1))
        check("rejects empty name", False)
    except DomainError:
        check("rejects empty name", True)

    # [2] Morphism
    print("[2] Morphism")
    motivation = Domain("Motivation", units=("MotUnit",), bounds=(0, 1))
    e_to_m = Morphism(
        src=energy,
        dst=motivation,
        func=lambda x: min(1.0, x / 1e6),
        name="Energy->Motivation",
        inverse_func=lambda y: y * 1e6,
    )
    check("morphism name", e_to_m.name == "Energy->Motivation")
    check("morphism call", abs(e_to_m(500_000) - 0.5) < 1e-9)
    check("morphism call 0", abs(e_to_m(0) - 0.0) < 1e-9)
    check("morphism call max", abs(e_to_m(1e6) - 1.0) < 1e-9)
    check("morphism invertible", e_to_m.invertible)

    # Safe call
    ok, val = e_to_m.safe_call(500_000)
    check("safe_call ok", ok and abs(val - 0.5) < 1e-9)
    ok2, _ = e_to_m.safe_call(-100)
    check("safe_call rejects", not ok2)

    # Inverse
    inv = e_to_m.invert()
    check("inverse src", inv.src.name == "Motivation")
    check("inverse dst", inv.dst.name == "Energy")
    check("inverse call", abs(inv(0.5) - 500_000) < 1)

    # Round-trip
    check("roundtrip 0", e_to_m.validate_roundtrip(0.0))
    check("roundtrip mid", e_to_m.validate_roundtrip(500_000))
    check("roundtrip max", e_to_m.validate_roundtrip(1e6))

    # Bounds violation
    try:
        e_to_m(-1)
        check("rejects negative input", False)
    except MorphismError:
        check("rejects negative input", True)

    # Constraints
    constrained = Morphism(
        src=energy,
        dst=motivation,
        func=lambda x: min(1.0, x / 1e6),
        constraints=[("monotonic", lambda x, y: y >= 0)],
    )
    check("constrained passes", abs(constrained(100) - 0.0001) < 1e-6)

    # [3] Composition
    print("[3] Composition")
    incentive = Domain("Incentive", units=("IncentiveUnit",), bounds=(0, 100))
    m_to_i = Morphism(
        src=motivation,
        dst=incentive,
        func=lambda x: x * 100,
        name="Motivation->Incentive",
        inverse_func=lambda y: y / 100,
    )
    composed = compose(e_to_m, m_to_i)
    check("compose name", "Motivation->Incentive" in composed.name and "Energy->Motivation" in composed.name)
    check("compose call", abs(composed(500_000) - 50.0) < 1e-6)
    check("compose invertible", composed.invertible)

    # CompositionChain
    chain = CompositionChain()
    chain.add(e_to_m)
    chain.add(m_to_i)
    check("chain length", len(chain) == 2)
    check("chain apply", abs(chain.apply(500_000) - 50.0) < 1e-6)

    trace = chain.apply_traced(500_000)
    check("chain trace len", len(trace) == 3)
    check("chain trace start", trace[0] == ("Energy", 500_000))
    check("chain trace mid", trace[1][0] == "Motivation")
    check("chain trace end", trace[2][0] == "Incentive")

    flat = chain.compose_all()
    check("chain compose_all", abs(flat(500_000) - 50.0) < 1e-6)

    # Invertible chain
    check("chain invertible", chain.invertible)
    inv_chain = chain.invert()
    check("inv chain len", len(inv_chain) == 2)
    check("inv chain apply", abs(inv_chain.apply(50.0) - 500_000) < 1)

    # Identity
    id_e = identity_morphism(energy)
    check("identity", abs(id_e(42.0) - 42.0) < 1e-9)
    check("identity invertible", id_e.invertible)

    # [4] DomainGraph
    print("[4] DomainGraph")
    g = DomainGraph()
    g.add_morphism(e_to_m)
    g.add_morphism(m_to_i)
    check("graph nodes", g.node_count == 3)
    check("graph edges", g.edge_count == 2)
    check("graph neighbors", len(g.neighbors("Energy")) == 1)

    # Path finding
    path = g.find_path("Energy", "Incentive")
    check("path found", path is not None and len(path) == 2)

    no_path = g.find_path("Incentive", "Energy")
    check("no reverse path", no_path is None)

    # Build chain from graph
    chain2 = g.build_chain("Energy", "Incentive")
    check("build_chain", chain2 is not None)
    check("build_chain apply", abs(chain2.apply(1e6) - 100.0) < 1e-6)

    # Self path
    self_path = g.find_path("Energy", "Energy")
    check("self path empty", self_path == [])

    # Adjacency matrix
    names, adj = g.adjacency_matrix()
    check("adj names sorted", names == sorted(names))
    check("adj is square", len(adj) == len(names))

    # [5] Graph Isomorphism
    print("[5] Graph Isomorphism")

    # Build two structurally identical graphs with different names
    g1 = DomainGraph()
    d_a = Domain("A", units=("u",), bounds=(0, 10))
    d_b = Domain("B", units=("u",), bounds=(0, 10))
    d_c = Domain("C", units=("u",), bounds=(0, 10))
    g1.add_morphism(Morphism(d_a, d_b, lambda x: x, name="A->B"))
    g1.add_morphism(Morphism(d_b, d_c, lambda x: x, name="B->C"))

    g2 = DomainGraph()
    d_x = Domain("X", units=("u",), bounds=(0, 10))
    d_y = Domain("Y", units=("u",), bounds=(0, 10))
    d_z = Domain("Z", units=("u",), bounds=(0, 10))
    g2.add_morphism(Morphism(d_x, d_y, lambda x: x, name="X->Y"))
    g2.add_morphism(Morphism(d_y, d_z, lambda x: x, name="Y->Z"))

    check("isomorphic graphs", GraphIsomorphism.is_isomorphic(g1, g2))

    mapping = GraphIsomorphism.find_mapping(g1, g2)
    check("mapping found", mapping is not None)
    check("mapping size", len(mapping) == 3)

    # Non-isomorphic: add extra edge to g2
    g3 = DomainGraph()
    g3.add_morphism(Morphism(d_x, d_y, lambda x: x))
    g3.add_morphism(Morphism(d_y, d_z, lambda x: x))
    g3.add_morphism(Morphism(d_x, d_z, lambda x: x))  # Extra shortcut
    check("non-isomorphic detected", not GraphIsomorphism.is_isomorphic(g1, g3))

    # Empty graphs are isomorphic
    check("empty isomorphic", GraphIsomorphism.is_isomorphic(DomainGraph(), DomainGraph()))

    # [6] Tongue Domains
    print("[6] Tongue Domains")
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
    for tg in tongues:
        phys = tongue_domain(tg, "physical")
        narr = tongue_domain(tg, "narrative")
        gov = tongue_domain(tg, "governance")
        check(f"{tg} physical exists", phys is not None)
        check(f"{tg} narrative exists", narr is not None)
        check(f"{tg} governance exists", gov is not None)

    all_morph = all_tongue_morphisms()
    check("tongue morphisms exist", len(all_morph) > 0)
    check("tongue morphisms count", len(all_morph) == len(CROSS_DOMAIN_MAP))

    # Test specific morphisms
    e2a = CROSS_DOMAIN_MAP["energy_to_authority"]
    auth = e2a(500_000)
    check("energy->authority in range", 0 <= auth <= 10)

    r2d = CROSS_DOMAIN_MAP["risk_to_danger"]
    danger = r2d(0.5)
    check("risk->danger value", abs(danger - 5.0) < 1e-9)
    check("risk->danger invertible", r2d.invertible)
    check("risk->danger roundtrip", r2d.validate_roundtrip(0.5))

    e2c = CROSS_DOMAIN_MAP["entropy_to_chaos"]
    chaos = e2c(500)
    check("entropy->chaos sigmoid midpoint", 4.0 < chaos < 6.0)

    # Cross-tongue
    a2d = CROSS_DOMAIN_MAP["authority_to_danger"]
    check("authority->danger inverse", abs(a2d(10.0) - 0.0) < 1e-9)
    check("authority->danger high auth = low danger", a2d(8.0) < 3.0)

    # Build a full tongue graph
    tg_graph = DomainGraph()
    for m in all_morph:
        tg_graph.add_morphism(m)
    check("tongue graph has nodes", tg_graph.node_count >= 6)
    check("tongue graph has edges", tg_graph.edge_count >= 6)

    # [7] Integration: Multi-Step Cross-Domain Pipeline
    print("[7] Multi-Step Pipeline")

    # Energy -> Authority -> Danger (cross-tongue chain: KO -> UM via narrative)
    chain3 = CompositionChain()
    chain3.add(CROSS_DOMAIN_MAP["energy_to_authority"])
    chain3.add(CROSS_DOMAIN_MAP["authority_to_danger"])
    danger_from_energy = chain3.apply(100_000)
    check("pipeline energy->authority->danger", 0 <= danger_from_energy <= 10)

    trace3 = chain3.apply_traced(100_000)
    check("pipeline trace", len(trace3) == 3)
    check("pipeline trace domains", trace3[0][0] == "Energy" and trace3[2][0] == "Danger")

    # Entropy -> PlotChaos -> Intrigue (RU -> CA narrative bridge)
    chain4 = CompositionChain()
    chain4.add(CROSS_DOMAIN_MAP["entropy_to_chaos"])
    chain4.add(CROSS_DOMAIN_MAP["chaos_to_intrigue"])
    intrigue = chain4.apply(800)
    check("pipeline entropy->chaos->intrigue", 0 <= intrigue <= 10)

    # --- Summary ---
    print(f"\n{'=' * 40}")
    if errors == 0:
        print("CDDM selftest ok -- all checks passed")
    else:
        print(f"CDDM selftest FAILED -- {errors} check(s) failed")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(selftest())
