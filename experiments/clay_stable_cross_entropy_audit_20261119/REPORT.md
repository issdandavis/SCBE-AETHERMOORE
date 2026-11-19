# Clay stable cross-entropy audit

Date: 2026-11-19  
Branch: `experiment/clay-stable-ce-audit-v1`  
Authority: read-only model audit plus isolated, default-off code; no training,
promotion, checkpoint mutation, or job control.

## Outcome

Clay's active frozen-multiview training path is arithmetically susceptible to
the float32 hard-target softmax-collapse failure described in
[Barron, Gnanapragasam, and Tschannen, arXiv:2610.31642v3](https://arxiv.org/abs/2610.31642).
The active call path is:

`clay_byte_embedding_thaw_campaign.py` ->
`clay_frozen_multiview_adapter.train_steps` -> float32 hard-target cross entropy.

Across the three independently trained, pinned baseline seeds and both the
multiview-train and source-disjoint-holdout splits:

- 27,000 supervised tokens were audited.
- 16,423 tokens had a target margin above the paper's approximate fp32 cliff
  of 16.6.
- Standard PyTorch cross entropy returned zero loss on 16,437 tokens.
- The stable formula recovered a nonzero target gradient on 5,784 tokens where
  the standard target gradient was exactly zero.
- The largest observed target margin was 1,391.04.
- Maximum per-token gradient-sum error was `1.193e-6` for standard CE and
  `2.384e-7` for the stable formulation.

The paper control reproduced exactly in PyTorch 2.13 fp32 for logits
`[9, -9, -9]`, target 0:

| formulation | loss | gradient | gradient sum |
| --- | ---: | --- | ---: |
| standard | 0 | `[0, 1.523e-8, 1.523e-8]` | `3.046e-8` |
| stable | `3.046e-8` | `[-3.046e-8, 1.523e-8, 1.523e-8]` | 0 |

The stable method cannot recover values that have already crossed exponential
underflow. That is why 10,702 extremely confident token losses remain zero.

## Formula and implementation

For target `t`, define shifted non-target logits `d_j = z_j - z_t` and
`m = max(0, max(d_j))`. The implemented loss is:

`m + log1p(sum(j != t, exp(d_j - m)) + expm1(-m))`.

The target slot is inserted as a constant zero rather than an expression that
depends on the target logit. Autograd therefore forms the target derivative as
the negative sum of the non-target derivatives instead of subtracting two
rounded probabilities.

`python/scbe/clay_stable_cross_entropy.py` provides two explicit modes:

- `standard` (default): delegates unchanged to `torch.nn.functional.cross_entropy`.
- `stable_log1p` (opt-in): uses the paper's hard-target formulation.

`train_steps(..., loss_mode="stable_log1p")` is the only integration change.
Checkpoints record the mode and refuse a different-mode resume. Old checkpoints
without the field are interpreted as `standard`, preserving compatibility.

## Claim boundary

**Arithmetic exposure: PROVEN on three model seeds.** The audit uses exact
pinned model bytes and regenerates the dataset only after matching its manifest
hash.

**Training-quality improvement: UNDERPOWERED / NOT RUN.** The active byte-
embedding successor is `WAITING_FOR_STORAGE_GATE` (12.8 GB free versus a 25 GiB
minimum at audit time). Per profile policy, this audit did not lower the gate,
start or stop training, or substitute a smaller experiment. A valid efficacy
claim still requires the preregistered three-seed stable arm to beat both the
same-size standard-loss control and the no-intervention baseline by at least
twice pooled standard deviation.

The pinned active runner remains byte-identical at SHA-256
`41ae605fe8a72df2bc24c6a55a43eb30a7a93e324838dd3b731cf1f8b5a4d956`.

## Evidence

- `PREREGISTRATION.json`: question, seeds, controls, and stop conditions.
- `RESULT.json`: per-seed/split margins, loss collapse, gradient collapse, and
  model/dataset hashes.
- `TEST_RECEIPT.json`: exact commands, hashes, and pass results.
- Primary paper HTML: <https://arxiv.org/html/2610.31642v3>

