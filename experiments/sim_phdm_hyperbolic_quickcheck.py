#!/usr/bin/env python3
"""
Quick SCBE simulation:
1) PHDM Hamiltonian path integrity checks
2) Hyperbolic embedding exploration checks

Usage:
  python experiments/sim_phdm_hyperbolic_quickcheck.py
"""

import json
import pathlib
import sys

import numpy as np


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.symphonic_cipher.scbe_aethermoore.qasi_core import (  # noqa: E402
    hyperbolic_distance,
    poincare_embed,
)
from src.symphonic_cipher.scbe_aethermoore.qc_lattice.phdm import (  # noqa: E402
    PHDMDeviationDetector,
    PHDMHamiltonianPath,
)


def run_phdm() -> dict:
    phdm = PHDMHamiltonianPath()
    path = phdm.compute_path()
    path_valid, first_invalid = phdm.verify_path()

    detector = PHDMDeviationDetector(phdm)
    topo_ok, topo_errors = detector.check_topological_integrity()

    orig_tag = path[7].hmac_tag
    path[7].hmac_tag = bytes([orig_tag[0] ^ 0xFF]) + orig_tag[1:]
    tamper_valid, tamper_pos = phdm.verify_path()
    path[7].hmac_tag = orig_tag

    removed = path.pop(5)
    skip_valid, skip_pos = phdm.verify_path()
    path.insert(5, removed)

    path = phdm.compute_path()
    first_name = path[0].polyhedron.name
    last_name = path[-1].polyhedron.name

    return {
        "node_count": len(path),
        "unique_polyhedra": len({n.polyhedron.name for n in path}),
        "path_valid": path_valid,
        "first_invalid": first_invalid,
        "topology_valid": topo_ok,
        "topology_error_count": len(topo_errors),
        "topology_errors_ascii": [e.encode("ascii", "ignore").decode("ascii") for e in topo_errors],
        "tamper_detected": (not tamper_valid),
        "tamper_position": tamper_pos,
        "skip_detected": (not skip_valid),
        "skip_position": skip_pos,
        "first_polyhedron": first_name,
        "last_polyhedron": last_name,
        "path_span_steps": phdm.get_geodesic_distance(first_name, last_name),
        "path_digest_prefix": phdm.get_path_digest().hex()[:16],
    }


def run_hyperbolic() -> dict:
    rng = np.random.default_rng(42)
    x = rng.normal(0.0, 1.0, size=(500, 6))
    u = np.array([poincare_embed(v) for v in x])

    norms = np.linalg.norm(u, axis=1)
    ball_ok = bool(np.all(norms < 1.0))

    pairs = rng.integers(0, len(u), size=(300, 2))
    sym_errs = []
    for i, j in pairs:
        d1 = hyperbolic_distance(u[i], u[j])
        d2 = hyperbolic_distance(u[j], u[i])
        sym_errs.append(abs(d1 - d2))

    triplets = rng.integers(0, len(u), size=(200, 3))
    tri_violations = 0
    max_violation = 0.0
    for i, j, k in triplets:
        d_ik = hyperbolic_distance(u[i], u[k])
        bound = hyperbolic_distance(u[i], u[j]) + hyperbolic_distance(u[j], u[k])
        margin = d_ik - bound
        if margin > 1e-9:
            tri_violations += 1
            max_violation = max(max_violation, float(margin))

    # Equal Euclidean step near center vs near boundary
    center_a = np.array([0.10, 0, 0, 0, 0, 0], dtype=np.float64)
    center_b = np.array([0.11, 0, 0, 0, 0, 0], dtype=np.float64)
    boundary_a = np.array([0.90, 0, 0, 0, 0, 0], dtype=np.float64)
    boundary_b = np.array([0.91, 0, 0, 0, 0, 0], dtype=np.float64)

    d_h_center = float(hyperbolic_distance(center_a, center_b))
    d_h_boundary = float(hyperbolic_distance(boundary_a, boundary_b))

    d_origin = np.array([hyperbolic_distance(v, np.zeros(6)) for v in u])
    orig_norm = np.linalg.norm(x, axis=1)

    return {
        "samples": int(len(u)),
        "inside_poincare_ball": ball_ok,
        "max_norm": float(norms.max()),
        "symmetry_max_abs_error": float(np.max(sym_errs)),
        "symmetry_mean_abs_error": float(np.mean(sym_errs)),
        "triangle_violations": int(tri_violations),
        "triangle_max_violation": float(max_violation),
        "equal_step_dH_center": d_h_center,
        "equal_step_dH_boundary": d_h_boundary,
        "equal_step_boundary_amplification": float(d_h_boundary / max(d_h_center, 1e-12)),
        "radius_distance_correlation": float(np.corrcoef(orig_norm, d_origin)[0, 1]),
    }


def main() -> None:
    out = {
        "phdm": run_phdm(),
        "hyperbolic": run_hyperbolic(),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
