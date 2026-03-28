from __future__ import annotations

from dataclasses import dataclass
import torch


def tanh_ball_projection(
    x: torch.Tensor, c: float = 1.0, eps: float = 1e-12
) -> torch.Tensor:
    """Project rows of x into open ball using tanh radial map."""

    sc = float(c) ** 0.5
    n = x.norm(dim=1, keepdim=True)
    scale = torch.tanh(sc * n) / (sc * n + eps)
    return x * scale


def blockwise_tanh_ball_projection(
    x: torch.Tensor,
    D_C: int,
    D_K: int,
    D_T: int,
    c: float = 1.0,
) -> torch.Tensor:
    """Project each C|K|T block independently to avoid cross-block leakage."""

    c_blk = tanh_ball_projection(x[:, :D_C], c=c)
    k_blk = tanh_ball_projection(x[:, D_C : D_C + D_K], c=c)
    t_blk = tanh_ball_projection(x[:, D_C + D_K : D_C + D_K + D_T], c=c)
    return torch.cat([c_blk, k_blk, t_blk], dim=1)


@dataclass(frozen=True)
class BlockGate:
    D_C: int
    D_K: int
    D_T: int
    keep_C: bool = True
    keep_K: bool = True
    keep_T: bool = False

    def mask(self, device=None, dtype=torch.float32) -> torch.Tensor:
        parts = [
            (
                torch.ones(self.D_C, device=device, dtype=dtype)
                if self.keep_C
                else torch.zeros(self.D_C, device=device, dtype=dtype)
            ),
            (
                torch.ones(self.D_K, device=device, dtype=dtype)
                if self.keep_K
                else torch.zeros(self.D_K, device=device, dtype=dtype)
            ),
            (
                torch.ones(self.D_T, device=device, dtype=dtype)
                if self.keep_T
                else torch.zeros(self.D_T, device=device, dtype=dtype)
            ),
        ]
        return torch.cat(parts, dim=0)

    def apply(self, z: torch.Tensor) -> torch.Tensor:
        m = self.mask(device=z.device, dtype=z.dtype)
        return z * m.unsqueeze(0)
