from __future__ import annotations

from dataclasses import dataclass
import torch
import torch.nn.functional as F

from .tie_kb import TIEKB, retrieve_tie


def activation_fn(name: str):
    """Map activation string to callable."""

    n = name.lower()
    if n == "relu":
        return F.relu
    if n == "silu":
        return F.silu
    if n == "identity":
        return lambda x: x
    raise ValueError(f"Unknown activation {name}")


@dataclass
class BlockLayout:
    D_C: int
    D_K: int
    D_T: int

    @property
    def D(self) -> int:
        return self.D_C + self.D_K + self.D_T


class CVLFuser(torch.nn.Module):
    """Deterministic CVL fusion in concat mode: [aC*C | aK*K | aT*T]."""

    def __init__(
        self,
        layout: BlockLayout,
        alpha_C: float,
        alpha_K: float,
        alpha_T: float,
        activation: str,
    ):
        super().__init__()
        self.layout = layout
        self.alpha_C = float(alpha_C)
        self.alpha_K = float(alpha_K)
        self.alpha_T = float(alpha_T)
        self.act = activation_fn(activation)

        # Fixed query map Q: R^{D_C} -> R^{D_T}
        self.Q = torch.nn.Linear(layout.D_C, layout.D_T, bias=False)
        with torch.no_grad():
            self.Q.weight.zero_()
            d = min(layout.D_C, layout.D_T)
            self.Q.weight[:d, :d] = torch.eye(d)
        for p in self.Q.parameters():
            p.requires_grad_(False)

    def forward(
        self,
        C: torch.Tensor,
        K: torch.Tensor,
        tie_kb: TIEKB | None,
        top_k: int,
        temperature: float,
    ) -> torch.Tensor:
        n = C.shape[0]
        device = C.device

        if tie_kb is None:
            T = torch.zeros((n, self.layout.D_T), device=device, dtype=C.dtype)
        else:
            t_list = []
            for i in range(n):
                q = self.Q(C[i])
                t_list.append(retrieve_tie(tie_kb, q, top_k=top_k, temperature=temperature))
            T = torch.stack(t_list, dim=0)

        fused = torch.cat(
            [
                self.alpha_C * C,
                self.alpha_K * K,
                self.alpha_T * T,
            ],
            dim=1,
        )
        return self.act(fused)
