from __future__ import annotations

import torch


def energy(x: torch.Tensor) -> torch.Tensor:
    """Total signal energy."""

    return (x * x).sum()


def energy_ratio(x: torch.Tensor, vis_gate) -> dict:
    """Energy split between visible and hidden channels."""

    full = energy(x)
    vis = energy(vis_gate.apply(x))
    hidden = full - vis
    return {
        "E_full": float(full.item()),
        "E_vis": float(vis.item()),
        "E_hid": float(hidden.item()),
        "r_g": float((vis / (full + 1e-12)).item()),
    }


def leakage_sensitivity(
    pipeline_fn, x0: torch.Tensor, tie_gate, delta: torch.Tensor
) -> float:
    """Numerical sensitivity of visible output to hidden/T perturbations."""

    d = tie_gate.apply(delta)
    y0 = pipeline_fn(x0)
    y1 = pipeline_fn(x0 + d)
    return float(((y1 - y0).norm() / (d.norm() + 1e-12)).item())


def block_coupling_corr(x: torch.Tensor, D_vis: int, D_hid: int) -> float:
    """Max abs correlation between visible and hidden blocks across nodes."""

    xv = x[:, :D_vis]
    xh = x[:, D_vis : D_vis + D_hid]

    xv = xv - xv.mean(dim=0, keepdim=True)
    xh = xh - xh.mean(dim=0, keepdim=True)

    xv = xv / xv.std(dim=0, unbiased=False).clamp_min(1e-12)
    xh = xh / xh.std(dim=0, unbiased=False).clamp_min(1e-12)

    corr = (xv.T @ xh) / max(1, xv.shape[0])
    return float(corr.abs().max().item())
