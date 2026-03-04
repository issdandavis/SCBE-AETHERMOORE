from __future__ import annotations

from dataclasses import dataclass

import torch

from .cvl import BlockLayout, CVLFuser
from .geometry import BlockGate, blockwise_tanh_ball_projection
from .manifest import FluxManifest
from .mesh_graph import MeshOps
from .smear import smear
from .tie_kb import TIEKB
from .wave import damped_wave


@dataclass
class M4Subsystem:
    """End-to-end deterministic M4 pipeline.

    Flow: CVL -> projection -> wave(physics gate) -> SMEAR -> visibility gate
    """

    ops: MeshOps
    layout: BlockLayout
    manifest: FluxManifest
    cvl: CVLFuser
    vis_gate: BlockGate
    phys_gate: BlockGate

    @staticmethod
    def build(ops: MeshOps, layout: BlockLayout, manifest: FluxManifest) -> "M4Subsystem":
        cvl = CVLFuser(layout, manifest.alpha_C, manifest.alpha_K, manifest.alpha_T, manifest.activation)
        vis_gate = BlockGate(layout.D_C, layout.D_K, layout.D_T, keep_C=True, keep_K=True, keep_T=False)
        phys_gate = BlockGate(layout.D_C, layout.D_K, layout.D_T, keep_C=True, keep_K=True, keep_T=False)
        return M4Subsystem(
            ops=ops,
            layout=layout,
            manifest=manifest,
            cvl=cvl,
            vis_gate=vis_gate,
            phys_gate=phys_gate,
        )

    def run(self, C: torch.Tensor, K: torch.Tensor, tie_kb: TIEKB | None) -> dict:
        fused = self.cvl(
            C,
            K,
            tie_kb=tie_kb,
            top_k=self.manifest.top_k,
            temperature=self.manifest.temperature,
        )

        if self.manifest.projection != "tanh_ball_v1":
            raise ValueError(f"Unknown projection {self.manifest.projection}")

        z0 = blockwise_tanh_ball_projection(fused, self.layout.D_C, self.layout.D_K, self.layout.D_T, c=self.manifest.curvature_c)

        zT = damped_wave(
            z0=z0,
            L_norm=self.ops.L_norm,
            alpha=self.manifest.wave_alpha,
            gamma=self.manifest.wave_gamma,
            steps=self.manifest.wave_steps,
            physics_gate=self.phys_gate.apply if self.manifest.physics_gate.startswith("in_loop") else None,
            init=self.manifest.wave_init,
        )

        if self.manifest.smear_enabled:
            zT = smear(zT, self.ops.A_norm, betas=self.manifest.smear_betas, J=self.manifest.smear_J)

        y = self.vis_gate.apply(zT)

        return {
            "f": fused,
            "z0": z0,
            "zT": zT,
            "y": y,
            "manifest_hash": self.manifest.hash(),
        }
