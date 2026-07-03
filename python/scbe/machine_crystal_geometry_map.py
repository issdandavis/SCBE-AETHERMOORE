"""Geometry relation map for the Machine Crystal.

The cube is not the whole system. It is the local 8-address hub.

This module records how that hub relates to the adjacent geometry already
present in the repo:

* octahedron: dual executable surface for the 8 Machine Crystal ops
* Fano plane: 7 nonzero GF(2)^3 incidence layer, not including zero
* cuboctahedron: PHDM bridge between cube and octahedron
* rhombic dodecahedron: PHDM space-filling/context bridge
* tesseract / Rubix-Cubit: 4D lift from 8 to 16 vertices
* torus / hypercube: wraparound and bit-flip locality
* Bhargava cube: arithmetic overlay on the same 8 entries
* Bhargava factorial: growth/factorial values that feed cube overlays
* p/n/e cube: chemistry and nuclear conservation surface
* particle chemistry: exact balancer and valence-rung companion

Honesty boundary:
    This is a relation map and validation receipt, not a universal geometry
    theorem. Each edge is either executable locally, grounded in an existing
    SCBE file/note, or explicitly marked as a design bridge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .machine_crystal_bhargava import bhargava_crystal_receipt
from .machine_crystal_bhargava_factorial import bhargava_factorial_receipt
from .machine_crystal_dual import duality_receipt
from .machine_crystal_particle_chem import particle_chem_receipt
from .machine_crystal_pne_cube import pne_cube_receipt


ROOT = Path(__file__).resolve().parents[2]


NODES: tuple[dict[str, Any], ...] = (
    {
        "id": "cube",
        "role": "local 3-bit address hub and token-face object",
        "evidence": [
            "python/scbe/board.py",
            "python/scbe/cube_faces.py",
            "python/scbe/ast_cube_encoder.py",
            "python/scbe/machine_crystal_dual.py",
        ],
    },
    {
        "id": "octahedron",
        "role": "dual 8-face executable surface for Machine Crystal ops",
        "evidence": ["python/scbe/machine_crystal.py", "python/scbe/machine_crystal_dual.py"],
    },
    {
        "id": "fano_plane",
        "role": "7 nonzero GF(2)^3 incidence layer",
        "evidence": ["python/scbe/machine_crystal_dual.py"],
        "boundary": "zero address is a Machine Crystal op but not a Fano point",
    },
    {
        "id": "cuboctahedron",
        "role": "PHDM cube-octahedron bridge",
        "evidence": ["python/scbe/phdm_router.py"],
    },
    {
        "id": "rhombic_dodecahedron",
        "role": "PHDM context bridge and space-filling connector",
        "evidence": ["python/scbe/phdm_router.py"],
    },
    {
        "id": "tesseract",
        "role": "4D state container with 16 vertices",
        "evidence": ["python/scbe/rubix_cubit.py"],
    },
    {
        "id": "torus_hypercube",
        "role": "wraparound surface plus bit-flip graph locality",
        "evidence": ["python/scbe/torus.py"],
    },
    {
        "id": "phdm_lattice",
        "role": "broader polyhedral governance route network",
        "evidence": ["python/scbe/phdm_router.py"],
    },
    {
        "id": "bhargava_cube",
        "role": "8-entry arithmetic overlay with equal discriminants",
        "evidence": ["python/scbe/machine_crystal_bhargava.py"],
        "boundary": "discriminant overlay only, not full class-group composition",
    },
    {
        "id": "bhargava_factorial",
        "role": "validated generalized-factorial surfaces feeding cube overlays",
        "evidence": ["python/scbe/machine_crystal_bhargava_factorial.py"],
        "boundary": "Z and arithmetic progressions only; arbitrary-set p-orderings are backlog",
    },
    {
        "id": "quasicrystal_sampling",
        "role": "golden-angle program generator and path-state stress surface",
        "evidence": ["python/scbe/machine_crystal_higher.py"],
        "boundary": "distinct hashes and golden-angle sampling do not prove crystallographic aperiodic order",
    },
    {
        "id": "pne_cube",
        "role": "proton/neutron/electron conservation surface for chemistry and nuclear processes",
        "evidence": ["python/scbe/machine_crystal_pne_cube.py"],
        "boundary": "small conservation-gate example set, not a full chemistry or nuclear database",
    },
    {
        "id": "particle_chem",
        "role": "exact stoichiometry balancer projected into p/n/e totals plus valence-rung annotations",
        "evidence": [
            "python/scbe/machine_crystal_particle_chem.py",
            "python/scbe/reaction_balance.py",
            "python/scbe/atomic_tokenization.py",
        ],
        "boundary": "exact balance is real; valence rung is a heuristic route annotation, not a stability proof",
    },
)


EDGES: tuple[dict[str, Any], ...] = (
    {
        "from": "cube",
        "to": "octahedron",
        "relation": "polyhedral_dual",
        "status": "executable",
        "load_bearing_check": "dual_fano_bridge_passes",
    },
    {
        "from": "cube",
        "to": "fano_plane",
        "relation": "nonzero_gf2_3_incidence",
        "status": "executable",
        "load_bearing_check": "dual_fano_bridge_passes",
    },
    {
        "from": "cube",
        "to": "cuboctahedron",
        "relation": "phdm_adjacency_bridge",
        "status": "grounded_in_repo",
        "load_bearing_check": "phdm_bridge_nodes_present",
    },
    {
        "from": "octahedron",
        "to": "cuboctahedron",
        "relation": "phdm_adjacency_bridge",
        "status": "grounded_in_repo",
        "load_bearing_check": "phdm_bridge_nodes_present",
    },
    {
        "from": "cube",
        "to": "rhombic_dodecahedron",
        "relation": "phdm_context_bridge",
        "status": "grounded_in_repo",
        "load_bearing_check": "phdm_bridge_nodes_present",
    },
    {
        "from": "cube",
        "to": "tesseract",
        "relation": "dimension_lift_3d_to_4d",
        "status": "grounded_in_repo",
        "load_bearing_check": "tesseract_surface_present",
    },
    {
        "from": "cube",
        "to": "torus_hypercube",
        "relation": "bit_flip_and_wraparound_embedding",
        "status": "grounded_in_repo",
        "load_bearing_check": "torus_hypercube_surface_present",
    },
    {
        "from": "phdm_lattice",
        "to": "cube",
        "relation": "polyhedral_governance_node",
        "status": "grounded_in_repo",
        "load_bearing_check": "phdm_bridge_nodes_present",
    },
    {
        "from": "cube",
        "to": "bhargava_cube",
        "relation": "8_entry_arithmetic_overlay",
        "status": "executable",
        "load_bearing_check": "bhargava_cube_passes",
    },
    {
        "from": "bhargava_cube",
        "to": "bhargava_factorial",
        "relation": "factorial_values_feed_cube_entries",
        "status": "executable",
        "load_bearing_check": "bhargava_factorial_passes",
    },
    {
        "from": "cube",
        "to": "quasicrystal_sampling",
        "relation": "golden_angle_path_state_generator",
        "status": "validated_as_stress_surface",
        "load_bearing_check": "quasicrystal_boundary_is_explicit",
    },
    {
        "from": "cube",
        "to": "pne_cube",
        "relation": "three_axis_particle_conservation_lattice",
        "status": "executable",
        "load_bearing_check": "pne_cube_passes",
    },
    {
        "from": "pne_cube",
        "to": "particle_chem",
        "relation": "stoichiometry_balancer_and_valence_rung",
        "status": "executable",
        "load_bearing_check": "particle_chem_passes",
    },
)


def _path_exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return (str(edge["from"]), str(edge["to"]), str(edge["relation"]))


def geometry_relation_receipt() -> dict[str, Any]:
    """Emit a validated map of cube-adjacent geometry surfaces."""

    dual = duality_receipt()
    bhargava = bhargava_crystal_receipt()
    factorial = bhargava_factorial_receipt()
    pne = pne_cube_receipt()
    particle_chem = particle_chem_receipt()

    evidence_paths = sorted({path for node in NODES for path in node.get("evidence", [])})
    evidence_status = [{"path": path, "exists": _path_exists(path)} for path in evidence_paths]
    edge_keys = {_edge_key(edge) for edge in EDGES}

    required_edges = {
        ("cube", "octahedron", "polyhedral_dual"),
        ("cube", "cuboctahedron", "phdm_adjacency_bridge"),
        ("cube", "rhombic_dodecahedron", "phdm_context_bridge"),
        ("cube", "tesseract", "dimension_lift_3d_to_4d"),
        ("cube", "torus_hypercube", "bit_flip_and_wraparound_embedding"),
        ("cube", "bhargava_cube", "8_entry_arithmetic_overlay"),
        ("bhargava_cube", "bhargava_factorial", "factorial_values_feed_cube_entries"),
        ("cube", "pne_cube", "three_axis_particle_conservation_lattice"),
        ("pne_cube", "particle_chem", "stoichiometry_balancer_and_valence_rung"),
    }

    node_ids = {node["id"] for node in NODES}
    checks = {
        "cube_is_not_only_node": len(node_ids) >= 10 and "cube" in node_ids,
        "required_edges_present": required_edges.issubset(edge_keys),
        "all_edge_nodes_exist": all(edge["from"] in node_ids and edge["to"] in node_ids for edge in EDGES),
        "evidence_paths_exist": all(item["exists"] for item in evidence_status),
        "dual_fano_bridge_passes": dual["verdict"] == "PASS" and all(dual["checks"].values()),
        "bhargava_cube_passes": bhargava["verdict"] == "PASS" and all(bhargava["checks"].values()),
        "bhargava_factorial_passes": factorial["verdict"] == "PASS" and all(factorial["checks"].values()),
        "pne_cube_passes": pne["verdict"] == "PASS" and all(pne["checks"].values()),
        "particle_chem_passes": particle_chem["verdict"] == "PASS" and all(particle_chem["checks"].values()),
        "phdm_bridge_nodes_present": _path_exists("python/scbe/phdm_router.py"),
        "tesseract_surface_present": _path_exists("python/scbe/rubix_cubit.py"),
        "torus_hypercube_surface_present": _path_exists("python/scbe/torus.py"),
        "quasicrystal_boundary_is_explicit": any(
            node["id"] == "quasicrystal_sampling" and "boundary" in node for node in NODES
        ),
    }

    return {
        "schema": "scbe_machine_crystal_geometry_relation_map_v1",
        "claim": "The cube is a local 8-address hub connected to adjacent geometric, arithmetic, and governance surfaces; it is not the whole geometry.",
        "nodes": list(NODES),
        "edges": list(EDGES),
        "evidence_status": evidence_status,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "honest_boundary": "Validated relation map over repo surfaces; not a universal theorem that all geometry reduces to cubes.",
    }


def main() -> int:
    receipt = geometry_relation_receipt()
    out_dir = ROOT / "artifacts/machine_crystal"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "geometry_relation_map.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


__all__ = [
    "EDGES",
    "NODES",
    "geometry_relation_receipt",
]


if __name__ == "__main__":
    raise SystemExit(main())
