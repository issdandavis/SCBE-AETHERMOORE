"""Chapter 6 PHDM executable contract.

This module pins the Chapter 6 draft as a small, auditable runtime layer:
16 named polyhedra, Hamiltonian path energy accounting, single-visit
anti-loop checks, negative-binary phase signatures, and GeoSeal-style
decision receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Dict, Iterable, List, Sequence


DEFAULT_BUDGET = 100.0


class PHDMChapter6Error(ValueError):
    """Raised when a Chapter 6 PHDM path cannot be parsed or evaluated."""


@dataclass(frozen=True)
class PHDMNode:
    index: int
    name: str
    family: str
    category: str
    faces: int | str
    base_energy: float
    cognitive_role: str
    radial_position: float
    phase: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "family": self.family,
            "category": self.category,
            "faces": self.faces,
            "base_energy": self.base_energy,
            "cognitive_role": self.cognitive_role,
            "radial_position": self.radial_position,
            "negative_binary_phase": self.phase,
        }


CHAPTER6_NODES: tuple[PHDMNode, ...] = (
    PHDMNode(0, "Tetrahedron", "platonic", "safe_core", 4, 1.0, "Basic facts", 0.10, 1),
    PHDMNode(1, "Cube", "platonic", "safe_core", 6, 1.2, "Simple logic gates", 0.12, 1),
    PHDMNode(2, "Octahedron", "platonic", "safe_core", 8, 1.5, "Binary decisions", 0.14, 1),
    PHDMNode(3, "Dodecahedron", "platonic", "safe_core", 12, 2.0, "Pattern recognition", 0.16, 1),
    PHDMNode(4, "Icosahedron", "platonic", "safe_core", 20, 2.5, "Complex reasoning", 0.18, 1),
    PHDMNode(5, "Truncated Icosahedron", "archimedean", "complex_reasoning", 32, 4.0, "Multi-agent consensus", 0.45, 0),
    PHDMNode(6, "Rhombicosidodecahedron", "archimedean", "complex_reasoning", 62, 5.5, "Context integration", 0.50, 0),
    PHDMNode(7, "Snub Dodecahedron", "archimedean", "complex_reasoning", 92, 7.0, "High-dimensional optimization", 0.55, 0),
    PHDMNode(8, "Great Stellated Dodecahedron", "kepler_poinsot", "high_risk", 12, 15.0, "Adversarial prompt paths", 0.95, -1),
    PHDMNode(9, "Small Stellated Dodecahedron", "kepler_poinsot", "high_risk", 12, 12.0, "Jailbreak attempts", 0.92, -1),
    PHDMNode(10, "Genus-1 Torus", "toroidal", "specialized", "genus-1", 8.0, "Cyclic reasoning", 0.72, 0),
    PHDMNode(11, "Hexagonal Torus", "toroidal", "specialized", "hexagonal genus-1", 10.0, "Feedback loops", 0.74, 0),
    PHDMNode(12, "Rhombic Dodecahedron", "rhombic", "specialized", 12, 6.0, "Space-filling lattice", 0.58, 0),
    PHDMNode(13, "Rhombic Triacontahedron", "rhombic", "specialized", 30, 8.0, "Dense space-filling lattice", 0.62, 0),
    PHDMNode(14, "Square Gyrobicupola", "johnson", "specialized", 18, 5.0, "Edge-case handling", 0.56, 0),
    PHDMNode(15, "Pentagonal Orthobirotunda", "johnson", "specialized", 22, 7.0, "Rare edge-case handling", 0.60, 0),
)

_BY_NAME = {node.name.casefold(): node for node in CHAPTER6_NODES}
_BY_INDEX = {node.index: node for node in CHAPTER6_NODES}


def chapter6_table() -> List[Dict[str, Any]]:
    """Return the canonical Chapter 6 polyhedron table."""

    return [node.to_dict() for node in CHAPTER6_NODES]


def get_node(name_or_index: str | int) -> PHDMNode:
    """Resolve a Chapter 6 node by exact name, loose token, or index."""

    if isinstance(name_or_index, int):
        try:
            return _BY_INDEX[name_or_index]
        except KeyError as exc:
            raise PHDMChapter6Error(f"unknown PHDM node index: {name_or_index}") from exc

    raw = str(name_or_index).strip()
    if raw.isdigit():
        return get_node(int(raw))

    folded = raw.casefold()
    if folded in _BY_NAME:
        return _BY_NAME[folded]

    compact = "".join(ch for ch in folded if ch.isalnum())
    for key, node in _BY_NAME.items():
        if "".join(ch for ch in key if ch.isalnum()) == compact:
            return node

    raise PHDMChapter6Error(f"unknown PHDM node: {name_or_index}")


def parse_path(path: str | Iterable[str | int]) -> List[PHDMNode]:
    """Parse a path from names/indices or a comma/semicolon separated string."""

    if isinstance(path, str):
        pieces = [piece.strip() for chunk in path.split(";") for piece in chunk.split(",")]
        tokens = [piece for piece in pieces if piece]
    else:
        tokens = list(path)
    if not tokens:
        raise PHDMChapter6Error("empty PHDM path")
    return [get_node(token) for token in tokens]


def transition_penalty(left: PHDMNode | str | int, right: PHDMNode | str | int) -> float:
    """Chapter 6 edge-weight penalty between two polyhedra."""

    a = left if isinstance(left, PHDMNode) else get_node(left)
    b = right if isinstance(right, PHDMNode) else get_node(right)
    families = {a.family, b.family}

    if a.index == b.index:
        return 0.0
    if "kepler_poinsot" in families:
        return 12.0 if families == {"kepler_poinsot"} else 8.0
    if "toroidal" in families:
        return 4.0
    if families == {"platonic"}:
        return 0.5
    if families == {"platonic", "archimedean"}:
        return 1.5
    if "archimedean" in families:
        return 3.0
    if families & {"johnson", "rhombic"}:
        return 2.5
    return 2.0


def negative_binary_signature(nodes: Sequence[PHDMNode]) -> List[int]:
    """Return {-1, 0, 1} phase values for a reasoning path."""

    return [node.phase for node in nodes]


def evaluate_path(path: str | Iterable[str | int], budget: float = DEFAULT_BUDGET) -> Dict[str, Any]:
    """Evaluate a Chapter 6 Hamiltonian path and emit a governance receipt."""

    nodes = parse_path(path)
    visited: set[int] = set()
    violations: List[str] = []
    repeated: List[str] = []

    node_costs = []
    for node in nodes:
        if node.index in visited:
            violations.append(f"anti_loop_repeat:{node.name}")
            repeated.append(node.name)
        visited.add(node.index)
        node_costs.append({"name": node.name, "energy": node.base_energy})

    transition_costs = []
    for left, right in zip(nodes, nodes[1:]):
        penalty = transition_penalty(left, right)
        transition_costs.append({"from": left.name, "to": right.name, "penalty": penalty})

    node_total = sum(item["energy"] for item in node_costs)
    transition_total = sum(item["penalty"] for item in transition_costs)
    total_cost = round(node_total + transition_total, 10)
    remaining = round(float(budget) - total_cost, 10)
    max_radius = max(node.radial_position for node in nodes)
    exhausted = total_cost > budget
    phases = negative_binary_signature(nodes)

    if exhausted:
        violations.append("energy_budget_exhausted")
    if max_radius >= 0.7 and "edge_ring_escalation" not in violations:
        violations.append("edge_ring_escalation")

    if repeated or exhausted:
        decision = "DENY"
    elif max_radius >= 0.7:
        decision = "ESCALATE"
    else:
        decision = "ALLOW"

    program = [node.name for node in nodes]
    receipt_core = {
        "program": program,
        "budget": float(budget),
        "total_cost": total_cost,
        "decision": decision,
        "violations": violations,
    }

    return {
        "schema": "scbe_phdm_chapter6_path_v1",
        "program": program,
        "budget": float(budget),
        "node_costs": node_costs,
        "transition_costs": transition_costs,
        "cost": {
            "node_total": round(node_total, 10),
            "transition_total": round(transition_total, 10),
            "total": total_cost,
            "remaining": remaining,
            "exhausted": exhausted,
        },
        "geoseal": {
            "max_radial_position": max_radius,
            "inner_execute_threshold": 0.7,
            "decision": decision,
        },
        "negative_binary_signature": phases,
        "phase_counts": {
            "constructive": phases.count(1),
            "neutral": phases.count(0),
            "destructive": phases.count(-1),
        },
        "anti_loop": {
            "valid": not repeated,
            "repeated": repeated,
        },
        "violations": violations,
        "decision": decision,
        "receipt_sha256": hashlib.sha256(
            repr(sorted(receipt_core.items(), key=lambda item: item[0])).encode("utf-8")
        ).hexdigest(),
    }


JAILBREAK_DEMO_PATH = (
    "Tetrahedron",
    "Small Stellated Dodecahedron",
    "Great Stellated Dodecahedron",
    "Snub Dodecahedron",
    "Hexagonal Torus",
    "Genus-1 Torus",
    "Rhombic Triacontahedron",
    "Rhombicosidodecahedron",
    "Truncated Icosahedron",
    "Icosahedron",
    "Dodecahedron",
    "Octahedron",
    "Cube",
    "Square Gyrobicupola",
    "Pentagonal Orthobirotunda",
    "Rhombic Dodecahedron",
)


def jailbreak_demo() -> Dict[str, Any]:
    """Evaluate the Chapter 6 jailbreak path example as a runnable receipt."""

    return evaluate_path(JAILBREAK_DEMO_PATH)


def self_test() -> bool:
    """Lightweight invariant check used by tests and diagnostics."""

    names = [node.name for node in CHAPTER6_NODES]
    return (
        len(CHAPTER6_NODES) == 16
        and len(set(names)) == 16
        and transition_penalty("Tetrahedron", "Cube") == 0.5
        and transition_penalty("Tetrahedron", "Small Stellated Dodecahedron") == 8.0
        and transition_penalty("Small Stellated Dodecahedron", "Great Stellated Dodecahedron") == 12.0
        and jailbreak_demo()["decision"] == "DENY"
    )

