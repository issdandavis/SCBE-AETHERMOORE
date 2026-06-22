from __future__ import annotations

from python.scbe.phdm_chapter6 import (
    CHAPTER6_NODES,
    chapter6_table,
    evaluate_path,
    jailbreak_demo,
    negative_binary_signature,
    parse_path,
    self_test,
    transition_penalty,
)


def test_chapter6_table_pins_exact_16_polyhedra() -> None:
    rows = chapter6_table()

    assert len(rows) == 16
    assert [row["name"] for row in rows] == [
        "Tetrahedron",
        "Cube",
        "Octahedron",
        "Dodecahedron",
        "Icosahedron",
        "Truncated Icosahedron",
        "Rhombicosidodecahedron",
        "Snub Dodecahedron",
        "Great Stellated Dodecahedron",
        "Small Stellated Dodecahedron",
        "Genus-1 Torus",
        "Hexagonal Torus",
        "Rhombic Dodecahedron",
        "Rhombic Triacontahedron",
        "Square Gyrobicupola",
        "Pentagonal Orthobirotunda",
    ]
    energies = {row["name"]: row["base_energy"] for row in rows}
    assert energies["Tetrahedron"] == 1.0
    assert energies["Cube"] == 1.2
    assert energies["Truncated Icosahedron"] == 4.0
    assert energies["Small Stellated Dodecahedron"] == 12.0
    assert energies["Great Stellated Dodecahedron"] == 15.0
    assert energies["Hexagonal Torus"] == 10.0


def test_transition_penalties_match_chapter6_rules_and_example() -> None:
    assert transition_penalty("Tetrahedron", "Cube") == 0.5
    assert transition_penalty("Icosahedron", "Truncated Icosahedron") == 1.5
    assert transition_penalty("Snub Dodecahedron", "Great Stellated Dodecahedron") == 8.0
    assert transition_penalty("Tetrahedron", "Small Stellated Dodecahedron") == 8.0
    assert transition_penalty("Small Stellated Dodecahedron", "Great Stellated Dodecahedron") == 12.0
    assert transition_penalty("Cube", "Genus-1 Torus") == 4.0


def test_safe_core_path_allows_and_preserves_constructive_phase() -> None:
    receipt = evaluate_path("Tetrahedron,Cube,Octahedron")

    assert receipt["decision"] == "ALLOW"
    assert receipt["cost"]["total"] == 4.7
    assert receipt["geoseal"]["max_radial_position"] < 0.7
    assert receipt["negative_binary_signature"] == [1, 1, 1]
    assert receipt["anti_loop"]["valid"] is True


def test_repeated_node_triggers_anti_loop_denial() -> None:
    receipt = evaluate_path("Tetrahedron,Cube,Tetrahedron")

    assert receipt["decision"] == "DENY"
    assert receipt["anti_loop"]["valid"] is False
    assert receipt["anti_loop"]["repeated"] == ["Tetrahedron"]
    assert "anti_loop_repeat:Tetrahedron" in receipt["violations"]


def test_high_risk_path_escalates_before_budget_exhaustion() -> None:
    receipt = evaluate_path("Tetrahedron,Small Stellated Dodecahedron")

    assert receipt["decision"] == "ESCALATE"
    assert receipt["cost"]["exhausted"] is False
    assert receipt["negative_binary_signature"] == [1, -1]
    assert "edge_ring_escalation" in receipt["violations"]


def test_jailbreak_demo_exhausts_energy_and_denies() -> None:
    receipt = jailbreak_demo()

    assert receipt["decision"] == "DENY"
    assert receipt["cost"]["total"] > 100.0
    assert receipt["cost"]["exhausted"] is True
    assert "energy_budget_exhausted" in receipt["violations"]
    assert "edge_ring_escalation" in receipt["violations"]


def test_negative_binary_signature_uses_constructive_neutral_destructive() -> None:
    nodes = parse_path(["Tetrahedron", "Truncated Icosahedron", "Great Stellated Dodecahedron"])

    assert negative_binary_signature(nodes) == [1, 0, -1]


def test_chapter6_self_test() -> None:
    assert len(CHAPTER6_NODES) == 16
    assert self_test() is True
