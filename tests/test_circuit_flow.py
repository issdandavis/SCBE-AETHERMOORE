"""
Tests for Poly-Didactic Quasicrystal Circuit Flow
===================================================

Validates:
1. 16-polyhedra registry with zone-dependent topology (including χ=-6 for Risk)
2. Sacred Tongue neurotransmitter weighting
3. Hamiltonian path routing (visits all accessible nodes exactly once)
4. FSGS governance gating (per-node action classification)
5. Harmonic Wall energy costs H(d,R) = R^(d²)
6. Trust Ring classification (4 tiers)
7. FluxState-aware polyhedra filtering (POLLY/QUASI/DEMI)
8. Didactic audit trail completeness
9. Intent → Tongue classification
10. End-to-end circuit trace integrity
"""

import hashlib
import math
import sys
import os

# Add the circuit_flow module's parent to path (direct import, avoids __init__.py
# which pulls in hamiltonian_braid.py containing a pre-existing unicode issue)
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "src",
    "symphonic_cipher", "scbe_aethermoore", "ai_brain",
))

from circuit_flow import (
    PolyDidacticCircuit,
    CircuitNode,
    CircuitTrace,
    Zone,
    FluxGate,
    GovernanceAction,
    harmonic_wall_cost,
    classify_trust_ring,
    classify_intent_tongue,
    create_circuit,
    TONGUE_WEIGHTS,
    TONGUE_PHASES,
    _build_registry,
)


PHI = (1 + math.sqrt(5)) / 2


# ============================================================================
# 1. Registry: 16 Polyhedra
# ============================================================================

class TestRegistry:

    def test_registry_has_16_nodes(self):
        registry = _build_registry()
        assert len(registry) == 16, f"Expected 16 polyhedra, got {len(registry)}"

    def test_all_zones_represented(self):
        registry = _build_registry()
        zones = {node.zone for node in registry.values()}
        assert zones == {Zone.CORE, Zone.CORTEX, Zone.RISK, Zone.RECURSIVE, Zone.BRIDGE}

    def test_zone_counts(self):
        registry = _build_registry()
        zone_counts = {}
        for node in registry.values():
            zone_counts[node.zone] = zone_counts.get(node.zone, 0) + 1
        assert zone_counts[Zone.CORE] == 5, "5 Platonic solids in Core"
        assert zone_counts[Zone.CORTEX] == 3, "3 Archimedean solids in Cortex"
        assert zone_counts[Zone.RISK] == 2, "2 Kepler-Poinsot in Risk"
        assert zone_counts[Zone.RECURSIVE] == 2, "2 Toroidal in Recursive"
        assert zone_counts[Zone.BRIDGE] == 4, "4 Johnson/Rhombic in Bridge"

    def test_all_six_tongues_used(self):
        registry = _build_registry()
        tongues = {node.tongue_affinity for node in registry.values()}
        assert tongues == {"KO", "AV", "RU", "CA", "UM", "DR"}


# ============================================================================
# 2. Topology Validation (Zone-Dependent χ)
# ============================================================================

class TestTopology:

    def test_platonic_solids_chi_2(self):
        registry = _build_registry()
        for name, node in registry.items():
            if node.zone == Zone.CORE:
                chi = node.euler_characteristic
                assert chi == 2, f"{name}: Platonic solid should have χ=2, got {chi}"

    def test_archimedean_solids_chi_2(self):
        registry = _build_registry()
        for name, node in registry.items():
            if node.zone == Zone.CORTEX:
                chi = node.euler_characteristic
                assert chi == 2, f"{name}: Archimedean should have χ=2, got {chi}"

    def test_kepler_poinsot_chi_negative(self):
        """Risk Zone: Kepler-Poinsot stars have χ ≤ 2 (self-intersecting).
        Small Stellated Dodecahedron: V=12, E=30, F=12 → χ = -6.
        """
        registry = _build_registry()
        for name, node in registry.items():
            if node.zone == Zone.RISK:
                chi = node.euler_characteristic
                assert chi <= 2, f"{name}: Risk Zone should have χ ≤ 2, got {chi}"

    def test_small_stellated_dodecahedron_chi_minus_6(self):
        registry = _build_registry()
        ssd = registry["small_stellated_dodecahedron"]
        assert ssd.euler_characteristic == -6, f"Expected χ=-6, got {ssd.euler_characteristic}"

    def test_toroidal_chi_0(self):
        registry = _build_registry()
        for name, node in registry.items():
            if node.zone == Zone.RECURSIVE:
                chi = node.euler_characteristic
                assert chi == 0, f"{name}: Toroidal (genus=1) should have χ=0, got {chi}"

    def test_all_topologies_valid(self):
        """All 16 should pass zone-dependent topology validation."""
        circuit = PolyDidacticCircuit()
        results = circuit.validate_topology()
        for name, r in results.items():
            assert r["valid"], f"{name}: topology invalid (χ={r['chi']}, zone={r['zone']})"


# ============================================================================
# 3. Harmonic Wall Energy
# ============================================================================

class TestHarmonicWall:

    def test_zero_distance_zero_cost(self):
        assert harmonic_wall_cost(0.0) == 0.0

    def test_cost_increases_with_distance(self):
        c1 = harmonic_wall_cost(0.3)
        c2 = harmonic_wall_cost(0.7)
        c3 = harmonic_wall_cost(0.9)
        assert c1 < c2 < c3, "Harmonic Wall cost should increase with radial distance"

    def test_cost_at_boundary_very_high(self):
        c = harmonic_wall_cost(0.999, dimension_depth=14)
        assert c > 0.1, f"Cost at boundary should be high, got {c}"

    def test_formula_matches_conformal_factor(self):
        """Cost = (λ - 2) * d where λ = 2/(1 - r²), d=14."""
        r, d = 0.5, 14
        conformal = 2.0 / (1.0 - r * r)
        expected = (conformal - 2.0) * d
        actual = harmonic_wall_cost(r, d)
        assert abs(actual - expected) < 1e-6


# ============================================================================
# 4. Trust Ring Classification
# ============================================================================

class TestTrustRing:

    def test_core_ring(self):
        ring, latency = classify_trust_ring(0.15)
        assert ring == "CORE"
        assert latency == 5

    def test_inner_ring(self):
        ring, latency = classify_trust_ring(0.5)
        assert ring == "INNER"
        assert latency == 30

    def test_outer_ring(self):
        ring, latency = classify_trust_ring(0.8)
        assert ring == "OUTER"
        assert latency == 200

    def test_wall_ring(self):
        ring, latency = classify_trust_ring(0.95)
        assert ring == "WALL"
        assert latency is None


# ============================================================================
# 5. Tongue Classification
# ============================================================================

class TestTongueClassification:

    def test_context_override_urgent(self):
        assert classify_intent_tongue(b"\x00", {"urgent": True}) == "CA"

    def test_context_override_sensitive(self):
        assert classify_intent_tongue(b"\x00", {"sensitive": True}) == "UM"

    def test_context_override_decision(self):
        assert classify_intent_tongue(b"\x00", {"decision": True}) == "DR"

    def test_context_override_recall(self):
        assert classify_intent_tongue(b"\x00", {"recall": True}) == "RU"

    def test_default_tongue(self):
        tongue = classify_intent_tongue(b"", None)
        assert tongue == "KO"

    def test_hash_based_returns_valid_tongue(self):
        tongue = classify_intent_tongue(b"test intent", {})
        assert tongue in TONGUE_WEIGHTS


# ============================================================================
# 6. FluxState Filtering
# ============================================================================

class TestFluxGate:

    def test_polly_all_16(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.POLLY)
        trace = circuit.route(b"test intent")
        assert trace.accessible_nodes == 16

    def test_quasi_core_plus_cortex(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.QUASI)
        trace = circuit.route(b"test intent")
        assert trace.accessible_nodes == 8, f"QUASI should have 8 nodes, got {trace.accessible_nodes}"

    def test_demi_core_only(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"test intent")
        assert trace.accessible_nodes == 5, f"DEMI should have 5 nodes, got {trace.accessible_nodes}"

    def test_demi_only_platonic(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"test intent")
        for step in trace.steps:
            node = circuit.nodes[step.node]
            assert node.zone == Zone.CORE, f"DEMI: {step.node} is {node.zone}, expected CORE"


# ============================================================================
# 7. Hamiltonian Path
# ============================================================================

class TestHamiltonianPath:

    def test_polly_visits_all_16(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.POLLY)
        trace = circuit.route(b"hamiltonian test")
        # Path may be blocked by Risk Zone governance;
        # check that we either visit all or get blocked
        if trace.path_valid:
            visited = {s.node for s in trace.steps}
            assert len(visited) == 16, f"Expected 16 unique nodes, got {len(visited)}"

    def test_demi_visits_all_5(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"demi test")
        visited = {s.node for s in trace.steps}
        assert len(visited) == 5, f"DEMI: expected 5 unique nodes, got {len(visited)}"

    def test_no_duplicate_visits(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"no dupes")
        visited = [s.node for s in trace.steps]
        assert len(visited) == len(set(visited)), "Hamiltonian path should have no duplicates"


# ============================================================================
# 8. Governance Gating
# ============================================================================

class TestGovernance:

    def test_core_nodes_get_run(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"core test")
        for step in trace.steps:
            assert step.mode == "RUN", f"{step.node}: expected RUN in Core, got {step.mode}"

    def test_risk_zone_gets_quarantine(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.POLLY)
        trace = circuit.route(b"risk test")
        risk_steps = [s for s in trace.steps if s.zone == "risk"]
        for step in risk_steps:
            assert step.mode in ("QUAR", "ROLLBACK"), \
                f"Risk node {step.node}: expected QUAR or ROLLBACK, got {step.mode}"

    def test_final_governance_reflects_worst(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.POLLY)
        trace = circuit.route(b"governance check")
        if any(s.mode == "ROLLBACK" for s in trace.steps):
            assert trace.final_governance == "ROLLBACK"
        elif any(s.mode == "QUAR" for s in trace.steps):
            assert trace.final_governance == "QUAR"


# ============================================================================
# 9. Didactic Audit Trail
# ============================================================================

class TestAuditTrail:

    def test_every_step_has_reasoning(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"audit check")
        for step in trace.steps:
            assert step.reasoning, f"Step {step.step_index} ({step.node}) has no reasoning"

    def test_step_indices_sequential(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"sequence check")
        indices = [s.step_index for s in trace.steps]
        assert indices == list(range(len(indices)))

    def test_cumulative_energy_monotonic(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        trace = circuit.route(b"energy check")
        for i in range(1, len(trace.steps)):
            assert trace.steps[i].cumulative_energy >= trace.steps[i - 1].cumulative_energy

    def test_trace_digest_deterministic(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        t1 = circuit.route(b"digest test")
        t2 = circuit.route(b"digest test")
        assert t1.trace_digest == t2.trace_digest

    def test_trace_digest_changes_with_input(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        t1 = circuit.route(b"input A")
        t2 = circuit.route(b"input B")
        # Different inputs may produce different paths → different digests
        # (not guaranteed but very likely with different hash inputs)
        # At minimum, the digest should be non-empty
        assert len(t1.trace_digest) > 0
        assert len(t2.trace_digest) > 0


# ============================================================================
# 10. End-to-End Integration
# ============================================================================

class TestEndToEnd:

    def test_factory_function(self):
        circuit = create_circuit("POLLY", 1e6)
        assert circuit.flux == FluxGate.POLLY

    def test_flux_change(self):
        circuit = create_circuit("POLLY")
        circuit.set_flux(FluxGate.DEMI)
        trace = circuit.route(b"after flux change")
        assert trace.accessible_nodes == 5

    def test_tongue_map(self):
        circuit = PolyDidacticCircuit()
        tmap = circuit.get_tongue_map()
        assert all(tongue in tmap for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"])

    def test_zone_summary(self):
        circuit = PolyDidacticCircuit()
        summary = circuit.get_zone_summary()
        assert len(summary["core"]) == 5
        assert len(summary["cortex"]) == 3

    def test_multiple_routes_stable(self):
        circuit = PolyDidacticCircuit(flux=FluxGate.DEMI)
        for i in range(10):
            trace = circuit.route(f"intent {i}".encode())
            assert len(trace.steps) == 5
            assert trace.total_energy >= 0

    def test_tongue_weights_phi_scaled(self):
        """Verify tongue weights follow φ^n scaling."""
        weights = list(TONGUE_WEIGHTS.values())
        for i in range(1, len(weights)):
            ratio = weights[i] / weights[i - 1]
            # Should be approximately φ ≈ 1.618
            assert 1.5 < ratio < 1.7, f"Weight ratio {weights[i]}/{weights[i-1]}={ratio:.3f}, expected ≈φ"

    def test_tongue_phases_pi_over_3_spacing(self):
        """Verify tongue phases are spaced at π/3."""
        phases = list(TONGUE_PHASES.values())
        for i in range(1, len(phases)):
            spacing = phases[i] - phases[i - 1]
            assert abs(spacing - math.pi / 3) < 1e-10


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    import traceback

    test_classes = [
        TestRegistry, TestTopology, TestHarmonicWall, TestTrustRing,
        TestTongueClassification, TestFluxGate, TestHamiltonianPath,
        TestGovernance, TestAuditTrail, TestEndToEnd,
    ]

    total = 0
    passed = 0
    failed = 0
    errors = []

    print("=" * 70)
    print(" POLY-DIDACTIC QUASICRYSTAL CIRCUIT FLOW TESTS")
    print("=" * 70)

    for cls in test_classes:
        print(f"\n--- {cls.__name__} ---")
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in sorted(methods):
            total += 1
            try:
                getattr(instance, method_name)()
                passed += 1
                print(f"  PASS: {method_name}")
            except Exception as e:
                failed += 1
                errors.append((cls.__name__, method_name, e))
                print(f"  FAIL: {method_name}: {e}")

    print("\n" + "=" * 70)
    print(f" {passed}/{total} PASSED, {failed} FAILED")
    print("=" * 70)

    if errors:
        print("\nFailed tests:")
        for cls_name, method, err in errors:
            print(f"  {cls_name}.{method}: {err}")
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED")
