from __future__ import annotations

import torch


def sparse_mm(a: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """Sparse-dense matrix multiply helper."""

    return torch.sparse.mm(a, x)


def damped_wave(
    z0: torch.Tensor,
    L_norm: torch.Tensor,
    alpha: float,
    gamma: float,
    steps: int,
    physics_gate=None,
    init: str = "z_minus_1_equals_z0",
) -> torch.Tensor:
    """Second-order damped wave recurrence on graph laplacian."""

    if init == "z_minus_1_equals_z0":
        z_prev = z0.clone()
    elif init == "z_minus_1_zero":
        z_prev = torch.zeros_like(z0)
    else:
        raise ValueError(f"Unknown wave init: {init}")

    z = z0.clone()
    if physics_gate is not None:
        z_prev = physics_gate(z_prev)
        z = physics_gate(z)

    for _ in range(int(steps)):
        z_next = (2.0 - float(gamma)) * z - (1.0 - float(gamma)) * z_prev - float(alpha) * sparse_mm(L_norm, z)
        z_prev, z = z, z_next
        if physics_gate is not None:
            z = physics_gate(z)

    return z
