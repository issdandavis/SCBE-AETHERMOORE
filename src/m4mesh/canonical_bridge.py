from __future__ import annotations

from typing import Any, Dict, Optional

import torch

from .canonical_state import harmonic_energy_from_radial, validate_canonical_state
from .cvl import BlockLayout
from .manifest import FluxManifest
from .mesh_graph import MeshOps
from .pipeline import M4Subsystem
from .scbe_graph import build_phdm_mesh_ops
from .tie_kb import TIEKB

LAYOUT = BlockLayout(D_C=6, D_K=6, D_T=6)


def _ensure_layout_inputs(c: torch.Tensor, k: torch.Tensor) -> None:
    if c.ndim != 2 or k.ndim != 2:
        raise ValueError("tongue_position and tongue_phase must be rank-2 tensors")
    if c.shape != k.shape:
        raise ValueError(f"Shape mismatch: C{tuple(c.shape)} vs K{tuple(k.shape)}")
    if c.shape[1] != 6:
        raise ValueError(f"Expected 6 features per node, got {c.shape[1]}")


def run_governance_pipeline(
    tongue_position: torch.Tensor,
    tongue_phase: torch.Tensor,
    manifest: FluxManifest,
    tie_kb: Optional[TIEKB] = None,
    mesh_ops: Optional[MeshOps] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    """Run M4 pipeline and emit canonical 21D telemetry vectors."""
    _ensure_layout_inputs(tongue_position, tongue_phase)
    ops = mesh_ops or build_phdm_mesh_ops(device=tongue_position.device)
    if ops.N != tongue_position.shape[0]:
        raise ValueError(f"Mesh node count mismatch: ops.N={ops.N}, input={tongue_position.shape[0]}")

    subsystem = M4Subsystem.build(ops, LAYOUT, manifest)
    result = subsystem.run(C=tongue_position, K=tongue_phase, tie_kb=tie_kb)

    z0 = result["z0"]
    zt = result["zT"]
    y = result["y"]

    u = y[:, 0:6]
    theta = y[:, 6:12]

    flux = torch.linalg.norm(zt - z0, dim=1)
    e_full = torch.sum(zt * zt, dim=1)
    e_vis = torch.sum(y * y, dim=1)
    coherence_spectral = e_vis / torch.clamp(e_full, min=1e-12)
    stabilization = 1.0 / (1.0 + flux)
    radial = torch.linalg.norm(u, dim=1)
    harmonic = harmonic_energy_from_radial(radial, d_hyp=6)

    zeros = torch.zeros_like(flux)
    canonical_states = torch.stack(
        [
            u[:, 0],
            u[:, 1],
            u[:, 2],
            u[:, 3],
            u[:, 4],
            u[:, 5],
            theta[:, 0],
            theta[:, 1],
            theta[:, 2],
            theta[:, 3],
            theta[:, 4],
            theta[:, 5],
            flux,
            coherence_spectral,
            zeros,  # coherence_spin (filled by Layer 10 runtime)
            zeros,  # coherence_triadic (filled by Layer 11 runtime)
            zeros,  # risk_aggregate (filled by Layer 13 runtime)
            zeros,  # entropy_density (filled by Layer 12/runtime policy)
            stabilization,
            radial,
            harmonic,
        ],
        dim=1,
    )

    out: Dict[str, Any] = {
        "canonical_states": canonical_states,
        "raw": result,
        "manifest_hash": result["manifest_hash"],
    }
    if validate:
        out["validation"] = validate_canonical_state(canonical_states)
    return out

