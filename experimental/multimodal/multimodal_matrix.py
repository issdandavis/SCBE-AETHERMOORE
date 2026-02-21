"""EXPERIMENTAL — Multimodality Matrix training scaffold.

This module provides a runnable PyTorch reference for a matrix-first
multimodal architecture:

1) modality encoders -> embeddings E [B, M, D]
2) multimodal alignment matrix A [B, M, M]
3) matrix-weighted fusion -> z_fused [B, D]
4) losses: contrastive + conflict penalty

Status: non-canonical research scaffold; not protocol authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset


class MultiModalMatrix(nn.Module):
    """Compute pairwise modality alignment matrix and reliability weights."""

    def __init__(self, d_model: int, use_reliability: bool = True) -> None:
        super().__init__()
        self.use_reliability = use_reliability
        if use_reliability:
            self.reliability = nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.GELU(),
                nn.Linear(d_model, 1),
            )

    def forward(self, e: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor | None]:
        # e: [B, M, D]
        en = F.normalize(e, dim=-1)
        a = torch.einsum("bmd,bnd->bmn", en, en)

        if not self.use_reliability:
            return a, None

        w = torch.sigmoid(self.reliability(e)).squeeze(-1)
        return a, w


class MatrixWeightedFusion(nn.Module):
    """Fuse modality embeddings via alignment-aware weighting."""

    def __init__(self, d_model: int) -> None:
        super().__init__()
        self.proj = nn.Linear(d_model, d_model)
        self.out = nn.Linear(d_model, d_model)

    def forward(self, e: torch.Tensor, a: torch.Tensor, w: torch.Tensor | None = None) -> torch.Tensor:
        b, m, d = e.shape
        s = a.sum(dim=-1) / max(m, 1)

        if w is not None:
            s = s * w

        alpha = F.softmax(s, dim=-1).unsqueeze(-1)
        z = (alpha * self.proj(e)).sum(dim=1)
        return self.out(z)


class SimpleTextEncoder(nn.Module):
    def __init__(self, vocab_size: int = 50_000, d_model: int = 256) -> None:
        super().__init__()
        self.emb = nn.Embedding(vocab_size, d_model)
        self.pool = nn.Linear(d_model, d_model)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        x = self.emb(token_ids)
        x = x.mean(dim=1)
        return self.pool(x)


class SimpleImageEncoder(nn.Module):
    def __init__(self, d_model: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.GELU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.proj = nn.Linear(64, d_model)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        x = self.net(image).squeeze(-1).squeeze(-1)
        return self.proj(x)


class SimpleStateEncoder(nn.Module):
    """Optional SCBE governance/state vector encoder."""

    def __init__(self, state_dim: int = 64, d_model: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

    def forward(self, state_vec: torch.Tensor) -> torch.Tensor:
        return self.net(state_vec)


class SCBEMultiModalModel(nn.Module):
    """Matrix-first multimodal model for text/image/state alignment."""

    def __init__(self, d_model: int = 256, state_dim: int = 64) -> None:
        super().__init__()
        self.text = SimpleTextEncoder(d_model=d_model)
        self.image = SimpleImageEncoder(d_model=d_model)
        self.state = SimpleStateEncoder(state_dim=state_dim, d_model=d_model)

        self.mm = MultiModalMatrix(d_model=d_model, use_reliability=True)
        self.fuse = MatrixWeightedFusion(d_model=d_model)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor | None]:
        z_text = self.text(batch["text_tokens"])   # [B, D]
        z_img = self.image(batch["image"])         # [B, D]
        z_state = self.state(batch["state"])       # [B, D]

        e = torch.stack([z_text, z_img, z_state], dim=1)  # [B, M=3, D]
        a, w = self.mm(e)
        z_fused = self.fuse(e, a, w)

        return {
            "e": e,
            "a": a,
            "w": w,
            "z_fused": z_fused,
            "z_text": z_text,
            "z_img": z_img,
            "z_state": z_state,
        }


def clip_contrastive_loss(z_a: torch.Tensor, z_b: torch.Tensor, temperature: float = 0.07) -> torch.Tensor:
    z_a = F.normalize(z_a, dim=-1)
    z_b = F.normalize(z_b, dim=-1)
    logits = (z_a @ z_b.T) / temperature
    labels = torch.arange(z_a.size(0), device=z_a.device)
    return 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.T, labels))


def conflict_penalty(a: torch.Tensor, margin: float = 0.0) -> torch.Tensor:
    b, m, _ = a.shape
    mask = (1 - torch.eye(m, device=a.device)).unsqueeze(0)
    off = a * mask
    return F.relu(margin - off).mean()


def governance_proxy(a: torch.Tensor) -> Dict[str, torch.Tensor]:
    """SCBE-style telemetry hooks from multimodal matrix.

    Returns:
      coherence: mean off-diagonal alignment
      drift: variance of off-diagonal alignment
      conflict: negative alignment mass
    """
    b, m, _ = a.shape
    mask = (1 - torch.eye(m, device=a.device)).unsqueeze(0)
    off = a * mask
    denom = mask.sum().clamp_min(1.0)

    coherence = off.sum(dim=(1, 2)) / denom
    drift = off.var(dim=(1, 2), unbiased=False)
    conflict = F.relu(-off).sum(dim=(1, 2)) / denom
    return {"coherence": coherence, "drift": drift, "conflict": conflict}


@dataclass
class TrainConfig:
    batch_size: int = 16
    steps: int = 50
    lr: float = 1e-3
    lambda_conflict: float = 0.05
    device: str = "cpu"


class DummyMultimodalDataset(Dataset):
    """Tiny synthetic dataset for pipeline verification."""

    def __init__(self, n: int = 256, seq_len: int = 32, image_size: int = 64, state_dim: int = 64) -> None:
        self.n = n
        self.seq_len = seq_len
        self.image_size = image_size
        self.state_dim = state_dim

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        g = torch.Generator().manual_seed(idx)
        text_tokens = torch.randint(0, 4096, (self.seq_len,), generator=g)
        image = torch.rand((3, self.image_size, self.image_size), generator=g)
        state = torch.rand((self.state_dim,), generator=g)
        return {"text_tokens": text_tokens, "image": image, "state": state}


def train_dummy(cfg: TrainConfig) -> Dict[str, float]:
    torch.manual_seed(42)

    ds = DummyMultimodalDataset()
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True)
    model = SCBEMultiModalModel().to(cfg.device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)

    it = iter(dl)
    last_total = 0.0
    last_contrastive = 0.0
    last_conflict = 0.0

    for step in range(cfg.steps):
        try:
            batch = next(it)
        except StopIteration:
            it = iter(dl)
            batch = next(it)

        batch = {k: v.to(cfg.device) for k, v in batch.items()}
        out = model(batch)

        contrastive = (
            clip_contrastive_loss(out["z_text"], out["z_img"]) +
            clip_contrastive_loss(out["z_text"], out["z_state"]) +
            clip_contrastive_loss(out["z_img"], out["z_state"])
        ) / 3.0
        conflict = conflict_penalty(out["a"], margin=0.0)
        total = contrastive + cfg.lambda_conflict * conflict

        opt.zero_grad(set_to_none=True)
        total.backward()
        opt.step()

        last_total = float(total.detach().cpu())
        last_contrastive = float(contrastive.detach().cpu())
        last_conflict = float(conflict.detach().cpu())

        if step % 10 == 0 or step == cfg.steps - 1:
            telemetry = governance_proxy(out["a"])
            print(
                f"step={step:03d} total={last_total:.4f} "
                f"contrastive={last_contrastive:.4f} conflict={last_conflict:.4f} "
                f"coherence={telemetry['coherence'].mean().item():.4f}"
            )

    return {
        "total": last_total,
        "contrastive": last_contrastive,
        "conflict": last_conflict,
    }


if __name__ == "__main__":
    result = train_dummy(TrainConfig())
    print("done", result)
