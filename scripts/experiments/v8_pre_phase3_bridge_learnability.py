"""v8-pre Phase 3 falsifiable learnability test.

Sets up a synthetic role-conditioned token-prediction task that is
designed to be UNSOLVABLE without access to the MAHSS memory.

  Task: given hidden state h that encodes 'query role r_q' and a memory
  bundle M containing K (role, filler) bindings, predict which filler
  is bound under r_q in M. The hidden state h identifies which role to
  query but contains zero information about which fillers are in M --
  the model can only succeed by attending over M.

Two arms:

  Arm A (no bridge): a parameter-matched MLP that sees only h.
    -> Best achievable accuracy is 1/V (uniform random over V fillers).

  Arm B (bridge): the same MLP plus the MAHSSAttentionBridge layer.
    -> Hypothesis: with training, accuracy approaches 100%.

If Arm B >> Arm A, the bridge primitive works as designed and Phase 3
at scale (7B-LoRA or from-zero) is a real direction. If Arm B <= Arm A,
the bridge has a fundamental design flaw and Phase 3 is dead.

Runs entirely on CPU; no GPU required. Falsifiable in seconds."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from python.scbe.mahss_attention_bridge import (  # noqa: E402
    MAHSSAttentionBridge,
    MAHSSBridgeConfig,
    build_role_pinned_memory_tensor,
)


# ----------------------------------------------------------------------
# Synthetic task generator
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class TaskConfig:
    n_roles: int = 6  # tongue / lang / slot / metric / keyword / ident
    n_fillers_per_role: int = 8  # candidates per role
    bindings_per_example: int = 3  # how many (role, filler) pairs in M
    dim: int = 256
    seed: int = 0


def make_task_vectors(cfg: TaskConfig) -> tuple[torch.Tensor, torch.Tensor]:
    """Build the canonical role and filler vectors for the synthetic task.

    Roles: shape (n_roles, dim)
    Fillers: shape (n_roles, n_fillers_per_role, dim)

    All deterministic from cfg.seed."""

    g = torch.Generator().manual_seed(cfg.seed)
    roles = torch.randn(cfg.n_roles, cfg.dim, generator=g)
    roles = roles / roles.norm(dim=-1, keepdim=True)
    fillers = torch.randn(cfg.n_roles, cfg.n_fillers_per_role, cfg.dim, generator=g)
    fillers = fillers / fillers.norm(dim=-1, keepdim=True)
    return roles, fillers


def sample_batch(
    cfg: TaskConfig,
    roles: torch.Tensor,
    fillers: torch.Tensor,
    *,
    batch_size: int,
    seed: int | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Sample one batch.

    Returns:
        h: (B, dim) -- hidden state (= role vector for query role + small noise)
        memory: (B, dim) -- HRR bundle of `bindings_per_example` (role, filler) pairs
        vocab: (B, n_fillers_per_role, dim) -- candidate fillers for the query role
        labels: (B,) -- index of the bound filler in vocab
    """

    g = torch.Generator()
    if seed is not None:
        g.manual_seed(seed)
    B = batch_size
    H = []
    M_list = []
    V_list = []
    Y = []
    for b in range(B):
        # Pick which role this example queries
        q_role_idx = torch.randint(0, cfg.n_roles, (1,), generator=g).item()
        # Pick the filler bound under q_role for this context
        q_filler_idx = torch.randint(0, cfg.n_fillers_per_role, (1,), generator=g).item()
        # Build memory bundle: q_role -> q_filler PLUS some other (role, filler) pairs
        bindings = [(roles[q_role_idx], fillers[q_role_idx, q_filler_idx])]
        # Add distractor bindings for other roles
        other_roles = [r for r in range(cfg.n_roles) if r != q_role_idx]
        torch.manual_seed(int(g.initial_seed()) + b)
        # Sample distractor count - 1 (we already have the query binding)
        n_distract = min(cfg.bindings_per_example - 1, len(other_roles))
        if n_distract > 0:
            perm = torch.randperm(len(other_roles), generator=g)[:n_distract]
            for d_idx in perm:
                d_role_idx = other_roles[d_idx.item()]
                d_filler_idx = torch.randint(0, cfg.n_fillers_per_role, (1,), generator=g).item()
                bindings.append((roles[d_role_idx], fillers[d_role_idx, d_filler_idx]))
        memory = build_role_pinned_memory_tensor(bindings)
        # Hidden state = role vector + small noise (model knows WHICH role to query
        # but has no information about which filler is bound)
        noise = 0.05 * torch.randn(cfg.dim, generator=g)
        h = roles[q_role_idx] + noise
        # Vocab for this example: the n_fillers_per_role candidates under q_role
        vocab = fillers[q_role_idx]  # (n_fillers_per_role, dim)
        H.append(h)
        M_list.append(memory)
        V_list.append(vocab)
        Y.append(q_filler_idx)
    return (
        torch.stack(H),
        torch.stack(M_list),
        torch.stack(V_list),
        torch.tensor(Y, dtype=torch.long),
    )


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------


class NoBridgeMLP(nn.Module):
    """Baseline: an MLP head that maps h -> logits over fillers.

    It cannot solve the task because h carries only the query role and
    none of the per-context filler binding information. Best accuracy
    is 1/V (uniform random)."""

    def __init__(self, dim: int, n_fillers: int, hidden: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, n_fillers),
        )

    def forward(self, h: torch.Tensor, memory: torch.Tensor, vocab: torch.Tensor) -> torch.Tensor:
        return self.net(h)


class BridgedMLP(nn.Module):
    """Bridged: same head as NoBridgeMLP but preceded by the
    MAHSSAttentionBridge that lets h attend to memory."""

    def __init__(self, dim: int, n_fillers: int, hidden: int = 256) -> None:
        super().__init__()
        self.bridge = MAHSSAttentionBridge(MAHSSBridgeConfig(hidden_dim=dim, memory_dim=dim, rank=16))
        self.net = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, n_fillers),
        )

    def forward(self, h: torch.Tensor, memory: torch.Tensor, vocab: torch.Tensor) -> torch.Tensor:
        h_aug, _attn = self.bridge(h, memory, vocab)
        return self.net(h_aug)


def n_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ----------------------------------------------------------------------
# Training loop
# ----------------------------------------------------------------------


def train_one_arm(
    arm_label: str,
    model: nn.Module,
    cfg: TaskConfig,
    *,
    n_steps: int = 600,
    batch_size: int = 64,
    lr: float = 3e-3,
    eval_seed: int = 9999,
    eval_size: int = 512,
) -> dict:
    print(f"\n[{arm_label}] params={n_params(model):,}, steps={n_steps}, lr={lr}")
    roles, fillers = make_task_vectors(cfg)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    # Pre-train eval
    h_e, M_e, V_e, y_e = sample_batch(cfg, roles, fillers, batch_size=eval_size, seed=eval_seed)
    with torch.no_grad():
        logits_e = model(h_e, M_e, V_e)
        pre_acc = (logits_e.argmax(dim=-1) == y_e).float().mean().item()
    print(f"  pre-train eval acc: {pre_acc:.4f} (chance = {1/cfg.n_fillers_per_role:.4f})")

    losses = []
    accs_train = []
    for step in range(n_steps):
        h, M, V, y = sample_batch(cfg, roles, fillers, batch_size=batch_size, seed=step)
        opt.zero_grad()
        logits = model(h, M, V)
        loss = F.cross_entropy(logits, y)
        loss.backward()
        opt.step()
        if step % 50 == 0 or step == n_steps - 1:
            with torch.no_grad():
                acc = (logits.argmax(dim=-1) == y).float().mean().item()
            losses.append((step, loss.item()))
            accs_train.append((step, acc))
            print(f"  step {step:>4}  loss={loss.item():.4f}  train_acc={acc:.4f}")

    # Final eval on a fresh seed
    with torch.no_grad():
        logits_e = model(h_e, M_e, V_e)
        post_acc = (logits_e.argmax(dim=-1) == y_e).float().mean().item()
    print(f"  post-train eval acc: {post_acc:.4f}")

    return {
        "arm": arm_label,
        "n_params": n_params(model),
        "pre_train_acc": pre_acc,
        "post_train_acc": post_acc,
        "chance": 1 / cfg.n_fillers_per_role,
        "loss_curve": losses,
        "train_acc_curve": accs_train,
    }


def main() -> int:
    torch.manual_seed(0)

    cfg = TaskConfig()
    print("=" * 72)
    print("v8-pre Phase 3 bridge learnability test")
    print(f"  task: predict which filler is bound under query role in HRR memory")
    print(f"  roles per task: {cfg.n_roles}, fillers per role: {cfg.n_fillers_per_role}")
    print(f"  bindings per example: {cfg.bindings_per_example}, dim: {cfg.dim}")
    print(f"  chance baseline: {1/cfg.n_fillers_per_role:.4f}")
    print("=" * 72)

    no_bridge = NoBridgeMLP(dim=cfg.dim, n_fillers=cfg.n_fillers_per_role)
    bridged = BridgedMLP(dim=cfg.dim, n_fillers=cfg.n_fillers_per_role)

    arm_a = train_one_arm("no_bridge", no_bridge, cfg, n_steps=600)
    arm_b = train_one_arm("bridged",   bridged,   cfg, n_steps=600)

    delta = arm_b["post_train_acc"] - arm_a["post_train_acc"]
    bridge_lift_over_chance = arm_b["post_train_acc"] - arm_b["chance"]
    no_bridge_lift_over_chance = arm_a["post_train_acc"] - arm_a["chance"]

    print()
    print("=" * 72)
    print(f"== RESULT ==")
    print(f"  Arm A (no bridge):  acc {arm_a['post_train_acc']:.4f}  vs chance {arm_a['chance']:.4f}  (lift {no_bridge_lift_over_chance:+.4f})")
    print(f"  Arm B (bridged):    acc {arm_b['post_train_acc']:.4f}  vs chance {arm_b['chance']:.4f}  (lift {bridge_lift_over_chance:+.4f})")
    print(f"  Bridge advantage (B - A): {delta:+.4f}")
    print()

    if arm_b["post_train_acc"] >= 0.80 and arm_a["post_train_acc"] <= 0.30:
        verdict = "STRONG: bridge learns the task; no-bridge baseline at chance. Phase 3 substrate works."
    elif arm_b["post_train_acc"] >= 0.50 and delta >= 0.30:
        verdict = "POSITIVE: bridge significantly above no-bridge baseline. Substrate works but learning is partial."
    elif delta >= 0.10:
        verdict = "MARGINAL: bridge slightly above no-bridge baseline. Worth investigating but not a clear win."
    else:
        verdict = "NEGATIVE: bridge does not lift above no-bridge baseline. Substrate has a design flaw."
    print(f"  VERDICT: {verdict}")
    print("=" * 72)

    receipt = {
        "schema": "scbe_mahss_v8_pre_phase3_bridge_learnability_v1",
        "task_config": {
            "n_roles": cfg.n_roles,
            "n_fillers_per_role": cfg.n_fillers_per_role,
            "bindings_per_example": cfg.bindings_per_example,
            "dim": cfg.dim,
        },
        "arm_no_bridge": arm_a,
        "arm_bridged": arm_b,
        "bridge_advantage": delta,
        "verdict": verdict,
    }

    out_dir = _REPO_ROOT / "artifacts" / "mahss_v8_pre"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase3_bridge_learnability.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(f"  receipt: {out_dir / 'phase3_bridge_learnability.json'}")

    if arm_b["post_train_acc"] >= 0.50 and delta >= 0.30:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
