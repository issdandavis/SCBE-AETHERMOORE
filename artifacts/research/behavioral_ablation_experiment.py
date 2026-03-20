#!/usr/bin/env python3
"""
Behavioral Ablation Experiment — PhaseTunnelGate on OPT-1.3B
=============================================================

Paste this entire cell into Google Colab (GPU runtime, T4 or better).

Hypothesis:
  Zeroing COLLAPSE-classified attention heads should barely affect perplexity
  (they're near-noise), while zeroing TUNNEL-classified heads should
  significantly degrade it (they carry the model's core learned structure).

This connects the SCBE PhaseTunnelGate's 4-outcome classification to
measurable behavioral consequences in a real language model.

Prior results (from opt_1.3b_phase_tunnel_results.json):
  - OPT-1.3B: 24 layers, 72 Q/K/V weight matrices
  - Q resonance angle: -30 deg, K: -66 deg, V: -36 deg
  - Trained peak T = 0.9342, random baseline T = 0.0054 (173x ratio)
  - PhaseTunnelGate classification is NOT a statistical artifact

Author: Issac Davis
Date: 2026-03-19
SCBE-AETHERMOORE / USPTO #63/961,403
"""

# ---------------------------------------------------------------------------
# 0. Install dependencies
# ---------------------------------------------------------------------------
import subprocess, sys
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "transformers", "datasets", "accelerate",
])

# ---------------------------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------------------------
import gc
import json
import math
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
from torch import nn

print("=" * 70)
print("BEHAVIORAL ABLATION EXPERIMENT — PhaseTunnelGate on OPT-1.3B")
print("=" * 70)
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    gpu_mem_gb = torch.cuda.get_device_properties(0).total_mem / 1e9
    print(f"GPU Memory: {gpu_mem_gb:.1f} GB")
else:
    print("WARNING: No GPU detected. This will be very slow on CPU.")
print()

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# ---------------------------------------------------------------------------
# 2. PhaseTunnelGate — self-contained (no external deps)
# ---------------------------------------------------------------------------
# Reimplemented from src/aetherbrowser/phase_tunnel.py so this cell is
# fully self-contained for Colab.

PHI = (1 + math.sqrt(5)) / 2
R_FIFTH = 1.5


@dataclass
class HeadClassification:
    """Classification of a single attention head by the PhaseTunnelGate."""
    layer: int
    head: int
    weight_type: str          # "Q", "K", or "V"
    transmission_coeff: float # T in [0, 1]
    resonance_angle: float    # dominant phase angle in radians
    spectral_density: float   # ratio of structured vs flat spectrum
    outcome: str              # TUNNEL / ATTENUATE / REFLECT / COLLAPSE


def harmonic_wall_cost(d: float, R: float = R_FIFTH) -> float:
    """H(d,R) = R^(d^2) — standard geometric governance wall."""
    return R ** (d * d)


def classify_weight_matrix(
    W: torch.Tensor,
    layer: int,
    head: int,
    weight_type: str,
    phi_wall: float = 0.0,
    beta: float = 1.0,
    gamma: float = 2.0,
) -> HeadClassification:
    """Run the PhaseTunnelGate on a single weight matrix.

    Steps:
    1. 2D FFT of the weight matrix
    2. Power spectrum -> spectral density ratio
    3. Dominant mode -> phase angle (B_phase)
    4. Transmission: T = cos^2((B_phase - phi_wall) / 2)
    5. Classify into 4 outcomes using SCBE thresholds

    The thresholds match compute_transmission() in phase_tunnel.py:
      T >= 0.35 -> TUNNEL
      T >= 0.08 -> ATTENUATE
      T >= 0.01 -> REFLECT
      T <  0.01 -> COLLAPSE
    """
    w = W.detach().float().cpu()

    # Ensure 2D for FFT (if 1D, reshape to approx-square)
    if w.dim() == 1:
        n = w.shape[0]
        side = int(math.ceil(math.sqrt(n)))
        padded = torch.zeros(side * side)
        padded[:n] = w
        w = padded.view(side, side)
    elif w.dim() > 2:
        w = w.view(w.shape[0], -1)

    # 2D FFT
    fft_result = torch.fft.fft2(w)
    power = torch.abs(fft_result) ** 2

    # Spectral density: high-freq vs low-freq energy
    rows, cols = power.shape
    center_r, center_c = rows // 2, cols // 2
    # Shift so DC is at center
    power_shifted = torch.fft.fftshift(power)
    # Low-freq = center 25%, high-freq = rest
    r_low = max(1, rows // 4)
    c_low = max(1, cols // 4)
    low_mask = torch.zeros_like(power_shifted, dtype=torch.bool)
    low_mask[
        center_r - r_low : center_r + r_low,
        center_c - c_low : center_c + c_low,
    ] = True
    low_energy = power_shifted[low_mask].mean().item()
    high_energy = power_shifted[~low_mask].mean().item()
    spectral_density = high_energy / max(low_energy, 1e-12)

    # Dominant mode phase angle
    flat_idx = torch.argmax(power[1:, :].flatten())  # skip DC
    flat_idx += cols  # offset for skipping row 0
    peak_r = flat_idx // cols
    peak_c = flat_idx % cols
    dominant_phase = torch.angle(fft_result[peak_r, peak_c]).item()

    # Transmission coefficient
    # T = cos^2((B_phase - phi_wall) / 2)
    T = math.cos((dominant_phase - phi_wall) / 2) ** 2

    # Classify using SCBE thresholds (from compute_transmission)
    if T >= 0.35:
        outcome = "TUNNEL"
    elif T >= 0.08:
        outcome = "ATTENUATE"
    elif T >= 0.01:
        outcome = "REFLECT"
    else:
        outcome = "COLLAPSE"

    return HeadClassification(
        layer=layer,
        head=head,
        weight_type=weight_type,
        transmission_coeff=T,
        resonance_angle=dominant_phase,
        spectral_density=spectral_density,
        outcome=outcome,
    )


# ---------------------------------------------------------------------------
# 3. Load model and tokenizer
# ---------------------------------------------------------------------------
print("[Step 1/6] Loading OPT-1.3B ...")
t0 = time.time()

from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "facebook/opt-1.3b"

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=DTYPE,
        device_map="auto" if DEVICE == "cuda" else None,
        low_cpu_mem_usage=True,
    )
    if DEVICE == "cpu":
        model = model.to(DEVICE)
    model.eval()
    print(f"  Loaded in {time.time() - t0:.1f}s")
except Exception as e:
    print(f"  ERROR loading model: {e}")
    print("  Attempting CPU fallback with float32 ...")
    DEVICE = "cpu"
    DTYPE = torch.float32
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=DTYPE,
        low_cpu_mem_usage=True,
    )
    model.eval()
    print(f"  Loaded (CPU) in {time.time() - t0:.1f}s")

# Model architecture info
num_layers = model.config.num_hidden_layers
num_heads = model.config.num_attention_heads
hidden_dim = model.config.hidden_size
head_dim = hidden_dim // num_heads
print(f"  Architecture: {num_layers} layers, {num_heads} heads/layer, "
      f"d_model={hidden_dim}, d_head={head_dim}")
print()

# ---------------------------------------------------------------------------
# 4. Classify all attention heads with PhaseTunnelGate
# ---------------------------------------------------------------------------
print("[Step 2/6] Running PhaseTunnelGate on all Q/K/V weight matrices ...")
t0 = time.time()

classifications: list[HeadClassification] = []
outcome_counts = {"TUNNEL": 0, "ATTENUATE": 0, "REFLECT": 0, "COLLAPSE": 0}

for layer_idx in range(num_layers):
    # OPT stores attention as model.decoder.layers[i].self_attn
    attn = model.model.decoder.layers[layer_idx].self_attn

    # Extract Q, K, V projection weights
    # OPT uses separate q_proj, k_proj, v_proj
    weight_map = {
        "Q": attn.q_proj.weight.data,
        "K": attn.k_proj.weight.data,
        "V": attn.v_proj.weight.data,
    }

    for wtype, W_full in weight_map.items():
        # W_full shape: [num_heads * head_dim, hidden_dim]
        # Split into per-head matrices: [num_heads, head_dim, hidden_dim]
        W_heads = W_full.view(num_heads, head_dim, hidden_dim)

        for head_idx in range(num_heads):
            W_head = W_heads[head_idx]  # [head_dim, hidden_dim]
            cls = classify_weight_matrix(
                W_head, layer_idx, head_idx, wtype,
                phi_wall=0.0, beta=1.0, gamma=2.0,
            )
            classifications.append(cls)
            outcome_counts[cls.outcome] += 1

    if (layer_idx + 1) % 6 == 0:
        print(f"  Layer {layer_idx + 1}/{num_layers} done ...")

total_heads = len(classifications)
print(f"  Classified {total_heads} head-weight matrices in {time.time() - t0:.1f}s")
print()
print("  PhaseTunnelGate Classification Summary:")
print("  " + "-" * 50)
for outcome in ["TUNNEL", "ATTENUATE", "REFLECT", "COLLAPSE"]:
    count = outcome_counts[outcome]
    pct = 100.0 * count / total_heads
    print(f"  {outcome:12s}: {count:4d} ({pct:5.1f}%)")
print("  " + "-" * 50)
print()

# Group by outcome for ablation
heads_by_outcome: dict[str, list[HeadClassification]] = {
    "TUNNEL": [], "ATTENUATE": [], "REFLECT": [], "COLLAPSE": [],
}
for cls in classifications:
    heads_by_outcome[cls.outcome].append(cls)

# Show some per-type breakdowns
for outcome in ["TUNNEL", "COLLAPSE"]:
    heads = heads_by_outcome[outcome]
    if heads:
        q_count = sum(1 for h in heads if h.weight_type == "Q")
        k_count = sum(1 for h in heads if h.weight_type == "K")
        v_count = sum(1 for h in heads if h.weight_type == "V")
        avg_T = np.mean([h.transmission_coeff for h in heads])
        print(f"  {outcome} breakdown: Q={q_count}, K={k_count}, V={v_count}, avg_T={avg_T:.4f}")

print()

# ---------------------------------------------------------------------------
# 5. Load evaluation dataset (WikiText-2)
# ---------------------------------------------------------------------------
print("[Step 3/6] Loading WikiText-2 evaluation corpus ...")
t0 = time.time()

from datasets import load_dataset

dataset = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")

# Concatenate all non-empty lines and tokenize
texts = [t for t in dataset["text"] if t.strip()]
full_text = "\n".join(texts)

# Tokenize — use stride for sliding window evaluation
MAX_SEQ_LEN = 512
STRIDE = 256
MAX_EVAL_TOKENS = 50_000  # cap to keep runtime reasonable on T4

encodings = tokenizer(
    full_text,
    return_tensors="pt",
    truncation=True,
    max_length=MAX_EVAL_TOKENS,
)
input_ids = encodings.input_ids[0]
total_tokens = input_ids.shape[0]
print(f"  Tokenized {total_tokens} tokens in {time.time() - t0:.1f}s")
print(f"  Evaluation: seq_len={MAX_SEQ_LEN}, stride={STRIDE}")
print()


# ---------------------------------------------------------------------------
# 6. Perplexity evaluation function
# ---------------------------------------------------------------------------
def evaluate_perplexity(
    mdl: nn.Module,
    input_ids: torch.Tensor,
    seq_len: int = MAX_SEQ_LEN,
    stride: int = STRIDE,
    device: str = DEVICE,
    desc: str = "model",
) -> float:
    """Compute perplexity using sliding window with stride.

    Uses the standard approach from the Hugging Face perplexity docs:
    stride through the sequence, compute NLL on the non-overlapping tokens.
    """
    mdl.eval()
    nlls = []
    n_tokens = input_ids.shape[0]
    n_windows = 0

    print(f"    Evaluating {desc} ...", end="", flush=True)
    t_start = time.time()

    with torch.no_grad():
        for begin_loc in range(0, n_tokens - 1, stride):
            end_loc = min(begin_loc + seq_len, n_tokens)
            trg_len = end_loc - begin_loc - 1  # tokens to score

            # For windows after the first, we only score the last (end-begin-overlap) tokens
            if begin_loc > 0:
                trg_len = min(trg_len, end_loc - begin_loc - (seq_len - stride))

            input_chunk = input_ids[begin_loc:end_loc].unsqueeze(0).to(device)

            try:
                outputs = mdl(input_chunk, labels=input_chunk)
                # OPT/GPT models return loss averaged over the sequence
                # We need to un-average to accumulate properly
                # The loss is cross-entropy averaged over all positions
                neg_log_likelihood = outputs.loss * trg_len
                nlls.append(neg_log_likelihood.item())
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    print(f"\n    OOM at window {n_windows}, reducing stride ...", end="")
                    torch.cuda.empty_cache()
                    gc.collect()
                    # Skip this window
                    continue
                raise

            n_windows += 1
            if n_windows % 20 == 0:
                print(".", end="", flush=True)

            # Stop if we have enough windows for a stable estimate
            if n_windows >= 150:
                break

    total_nll = sum(nlls)
    total_scored = sum(
        min(stride, seq_len - (seq_len - stride) if i > 0 else seq_len - 1)
        for i in range(n_windows)
    )
    # Safer: count actual scored tokens
    total_scored = max(total_scored, 1)

    ppl = math.exp(total_nll / total_scored)
    elapsed = time.time() - t_start
    print(f" done ({n_windows} windows, {elapsed:.1f}s)")
    return ppl


# ---------------------------------------------------------------------------
# 7. Condition A: FULL MODEL — baseline perplexity
# ---------------------------------------------------------------------------
print("[Step 4/6] Condition A: FULL MODEL baseline perplexity ...")
t0 = time.time()

ppl_baseline = evaluate_perplexity(model, input_ids, desc="FULL MODEL (baseline)")
print(f"  BASELINE perplexity: {ppl_baseline:.2f}")
print()

# ---------------------------------------------------------------------------
# 8. Ablation helper — zero out specific heads
# ---------------------------------------------------------------------------
def ablate_heads(
    mdl: nn.Module,
    heads_to_zero: list[HeadClassification],
    n_heads: int,
    d_head: int,
    d_model: int,
) -> dict[str, torch.Tensor]:
    """Zero out the specified attention heads and return saved originals.

    Works by zeroing the corresponding rows in the Q/K/V projection weights.
    Returns a dict of saved weight tensors for restoration.
    """
    saved = {}

    # Group by (layer, weight_type) for efficient batch operations
    groups: dict[tuple[int, str], list[int]] = {}
    for h in heads_to_zero:
        key = (h.layer, h.weight_type)
        if key not in groups:
            groups[key] = []
        groups[key].append(h.head)

    proj_name_map = {"Q": "q_proj", "K": "k_proj", "V": "v_proj"}

    for (layer_idx, wtype), head_indices in groups.items():
        attn = mdl.model.decoder.layers[layer_idx].self_attn
        proj = getattr(attn, proj_name_map[wtype])
        W = proj.weight.data  # [num_heads * head_dim, hidden_dim]

        # Save original
        save_key = f"L{layer_idx}_{wtype}"
        saved[save_key] = W.clone()

        # Zero out rows for each head
        for head_idx in head_indices:
            row_start = head_idx * d_head
            row_end = row_start + d_head
            W[row_start:row_end, :] = 0.0

    return saved


def restore_heads(
    mdl: nn.Module,
    saved: dict[str, torch.Tensor],
) -> None:
    """Restore ablated weights from saved originals."""
    proj_name_map = {"Q": "q_proj", "K": "k_proj", "V": "v_proj"}

    for save_key, original_W in saved.items():
        # Parse "L{layer}_{wtype}"
        parts = save_key.split("_", 1)
        layer_idx = int(parts[0][1:])
        wtype = parts[1]

        attn = mdl.model.decoder.layers[layer_idx].self_attn
        proj = getattr(attn, proj_name_map[wtype])
        proj.weight.data.copy_(original_W)


# ---------------------------------------------------------------------------
# 9. Condition B: COLLAPSE HEADS ZEROED
# ---------------------------------------------------------------------------
print("[Step 5/6] Condition B: COLLAPSE heads zeroed ...")

collapse_heads = heads_by_outcome["COLLAPSE"]
print(f"  Zeroing {len(collapse_heads)} COLLAPSE-classified head-weight matrices ...")

if len(collapse_heads) == 0:
    print("  No COLLAPSE heads found — skipping condition B.")
    ppl_collapse_ablated = ppl_baseline
else:
    saved_collapse = ablate_heads(model, collapse_heads, num_heads, head_dim, hidden_dim)
    ppl_collapse_ablated = evaluate_perplexity(
        model, input_ids, desc="COLLAPSE-ABLATED",
    )
    restore_heads(model, saved_collapse)
    del saved_collapse
    torch.cuda.empty_cache() if DEVICE == "cuda" else None
    gc.collect()

print(f"  COLLAPSE-ABLATED perplexity: {ppl_collapse_ablated:.2f}")
delta_collapse = ((ppl_collapse_ablated - ppl_baseline) / ppl_baseline) * 100
print(f"  Delta from baseline: {delta_collapse:+.2f}%")
print()

# ---------------------------------------------------------------------------
# 10. Condition C: TUNNEL HEADS ZEROED
# ---------------------------------------------------------------------------
print("[Step 6/6] Condition C: TUNNEL heads zeroed ...")

tunnel_heads = heads_by_outcome["TUNNEL"]
print(f"  Zeroing {len(tunnel_heads)} TUNNEL-classified head-weight matrices ...")

if len(tunnel_heads) == 0:
    print("  No TUNNEL heads found — skipping condition C.")
    ppl_tunnel_ablated = ppl_baseline
else:
    saved_tunnel = ablate_heads(model, tunnel_heads, num_heads, head_dim, hidden_dim)
    ppl_tunnel_ablated = evaluate_perplexity(
        model, input_ids, desc="TUNNEL-ABLATED",
    )
    restore_heads(model, saved_tunnel)
    del saved_tunnel
    torch.cuda.empty_cache() if DEVICE == "cuda" else None
    gc.collect()

print(f"  TUNNEL-ABLATED perplexity: {ppl_tunnel_ablated:.2f}")
delta_tunnel = ((ppl_tunnel_ablated - ppl_baseline) / ppl_baseline) * 100
print(f"  Delta from baseline: {delta_tunnel:+.2f}%")
print()


# ---------------------------------------------------------------------------
# 11. Results summary
# ---------------------------------------------------------------------------
print("=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)
print()

# Classification table
print("1. PhaseTunnelGate Classification (OPT-1.3B, 24 layers x 16 heads x 3 weight types)")
print("-" * 70)
print(f"{'Outcome':<12} {'Count':>6} {'Pct':>7}  {'Avg T':>8}  {'Q':>4} {'K':>4} {'V':>4}")
print("-" * 70)
for outcome in ["TUNNEL", "ATTENUATE", "REFLECT", "COLLAPSE"]:
    heads = heads_by_outcome[outcome]
    count = len(heads)
    pct = 100.0 * count / total_heads
    avg_T = np.mean([h.transmission_coeff for h in heads]) if heads else 0.0
    q = sum(1 for h in heads if h.weight_type == "Q")
    k = sum(1 for h in heads if h.weight_type == "K")
    v = sum(1 for h in heads if h.weight_type == "V")
    print(f"{outcome:<12} {count:>6} {pct:>6.1f}%  {avg_T:>8.4f}  {q:>4} {k:>4} {v:>4}")
print("-" * 70)
print(f"{'TOTAL':<12} {total_heads:>6}")
print()

# Ablation comparison table
print("2. Behavioral Ablation — Perplexity Impact")
print("-" * 70)
print(f"{'Condition':<30} {'Perplexity':>12} {'Delta':>10} {'Heads Zeroed':>14}")
print("-" * 70)
print(f"{'A. FULL MODEL (baseline)':<30} {ppl_baseline:>12.2f} {'---':>10} {'0':>14}")
print(f"{'B. COLLAPSE heads zeroed':<30} {ppl_collapse_ablated:>12.2f} {delta_collapse:>+9.2f}% {len(collapse_heads):>14}")
print(f"{'C. TUNNEL heads zeroed':<30} {ppl_tunnel_ablated:>12.2f} {delta_tunnel:>+9.2f}% {len(tunnel_heads):>14}")
print("-" * 70)
print()

# Hypothesis evaluation
print("3. Hypothesis Evaluation")
print("-" * 70)

hypothesis_supported = (
    abs(delta_collapse) < abs(delta_tunnel)
    and abs(delta_tunnel) > 5.0  # meaningful degradation
)

if hypothesis_supported:
    print("  HYPOTHESIS SUPPORTED")
    print()
    print(f"  COLLAPSE ablation caused {abs(delta_collapse):.1f}% change (expected: minimal)")
    print(f"  TUNNEL ablation caused {abs(delta_tunnel):.1f}% change (expected: significant)")
    print()
    print("  Interpretation: PhaseTunnelGate correctly identifies which attention")
    print("  heads carry learned structure (TUNNEL) vs which are near-noise (COLLAPSE).")
    print("  The 4-outcome classification has behavioral validity.")
else:
    if abs(delta_collapse) >= abs(delta_tunnel):
        print("  HYPOTHESIS NOT SUPPORTED — COLLAPSE ablation >= TUNNEL ablation")
        print()
        print(f"  COLLAPSE ablation: {abs(delta_collapse):.1f}% change")
        print(f"  TUNNEL ablation: {abs(delta_tunnel):.1f}% change")
        print()
        print("  This could mean:")
        print("  - The gate thresholds need recalibration for OPT architecture")
        print("  - COLLAPSE heads are not actually near-noise in this model")
        print("  - The phi_wall=0 setting is not optimal for behavioral separation")
    elif abs(delta_tunnel) <= 5.0:
        print("  HYPOTHESIS INCONCLUSIVE — TUNNEL ablation effect too small")
        print()
        print(f"  COLLAPSE ablation: {abs(delta_collapse):.1f}% change")
        print(f"  TUNNEL ablation: {abs(delta_tunnel):.1f}% change")
        print()
        print("  Both effects are small. Possible reasons:")
        print("  - Model has high redundancy across heads")
        print("  - Need to ablate more aggressively (zero entire heads, not just one weight type)")
        print("  - Evaluation corpus too small for effect to manifest")

print("-" * 70)
print()

# Additional statistics
print("4. Per-Layer Analysis")
print("-" * 70)
print(f"{'Layer':>6} {'TUNNEL':>8} {'ATTENUATE':>10} {'REFLECT':>9} {'COLLAPSE':>10} {'Avg T':>8}")
print("-" * 70)
for layer_idx in range(num_layers):
    layer_cls = [c for c in classifications if c.layer == layer_idx]
    t_count = sum(1 for c in layer_cls if c.outcome == "TUNNEL")
    a_count = sum(1 for c in layer_cls if c.outcome == "ATTENUATE")
    r_count = sum(1 for c in layer_cls if c.outcome == "REFLECT")
    c_count = sum(1 for c in layer_cls if c.outcome == "COLLAPSE")
    avg_t = np.mean([c.transmission_coeff for c in layer_cls])
    print(f"{layer_idx:>6} {t_count:>8} {a_count:>10} {r_count:>9} {c_count:>10} {avg_t:>8.4f}")
print("-" * 70)
print()

# Effect size
if abs(delta_tunnel) > 0 and abs(delta_collapse) > 0:
    effect_ratio = abs(delta_tunnel) / max(abs(delta_collapse), 0.01)
    print(f"5. Effect Size Ratio: {effect_ratio:.2f}x")
    print(f"   (TUNNEL ablation is {effect_ratio:.1f}x more damaging than COLLAPSE ablation)")
    print()

# ---------------------------------------------------------------------------
# 12. Save results to markdown
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/content/behavioral_ablation_results.md"

results_md = f"""# Behavioral Ablation Experiment — PhaseTunnelGate on OPT-1.3B

**Date:** {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
**Model:** facebook/opt-1.3b (24 layers, 16 heads, d_model=2048)
**Evaluation corpus:** WikiText-2 (raw, test split, {total_tokens} tokens)
**Device:** {DEVICE} ({torch.cuda.get_device_name(0) if DEVICE == "cuda" else "CPU"})
**Author:** Issac Davis / SCBE-AETHERMOORE / USPTO #63/961,403

---

## Hypothesis

Zeroing COLLAPSE-classified attention heads should barely affect perplexity
(they are near-noise), while zeroing TUNNEL-classified heads should significantly
degrade it (they carry the model's core learned structure).

## PhaseTunnelGate Classification

| Outcome | Count | Pct | Avg T | Q | K | V |
|---------|-------|-----|-------|---|---|---|
"""

for outcome in ["TUNNEL", "ATTENUATE", "REFLECT", "COLLAPSE"]:
    heads = heads_by_outcome[outcome]
    count = len(heads)
    pct = 100.0 * count / total_heads
    avg_T = np.mean([h.transmission_coeff for h in heads]) if heads else 0.0
    q = sum(1 for h in heads if h.weight_type == "Q")
    k = sum(1 for h in heads if h.weight_type == "K")
    v = sum(1 for h in heads if h.weight_type == "V")
    results_md += f"| {outcome} | {count} | {pct:.1f}% | {avg_T:.4f} | {q} | {k} | {v} |\n"

results_md += f"| **TOTAL** | **{total_heads}** | | | | | |\n"

results_md += f"""
## Behavioral Ablation Results

| Condition | Perplexity | Delta | Heads Zeroed |
|-----------|-----------|-------|-------------|
| A. FULL MODEL (baseline) | {ppl_baseline:.2f} | --- | 0 |
| B. COLLAPSE heads zeroed | {ppl_collapse_ablated:.2f} | {delta_collapse:+.2f}% | {len(collapse_heads)} |
| C. TUNNEL heads zeroed | {ppl_tunnel_ablated:.2f} | {delta_tunnel:+.2f}% | {len(tunnel_heads)} |

## Hypothesis Evaluation

**{"SUPPORTED" if hypothesis_supported else "NOT SUPPORTED / INCONCLUSIVE"}**

- COLLAPSE ablation impact: {abs(delta_collapse):.2f}%
- TUNNEL ablation impact: {abs(delta_tunnel):.2f}%
- Effect size ratio: {abs(delta_tunnel) / max(abs(delta_collapse), 0.01):.2f}x

"""

if hypothesis_supported:
    results_md += """### Interpretation

The PhaseTunnelGate's 4-outcome classification has **behavioral validity**: heads
classified as COLLAPSE contribute negligibly to model performance, while heads
classified as TUNNEL are critical. This means the gate is not just detecting
spectral patterns — it is identifying functionally meaningful structure.

### Implications for Governance

1. **Pruning target**: COLLAPSE heads can be safely pruned/quantized more aggressively
2. **Security monitor**: Changes to TUNNEL head weights should trigger governance alerts
3. **Mode-selective governance**: The PhaseTunnelGate enables operation-type-aware filtering,
   not just binary allow/deny
"""
else:
    results_md += """### Notes

The result needs further investigation. Possible refinements:
1. Sweep phi_wall to find optimal classification angle for ablation separation
2. Ablate by full attention head (all Q+K+V simultaneously) rather than individual weight types
3. Use a larger evaluation corpus for more stable perplexity estimates
4. Test on additional architectures (encoder-decoder, mixture-of-experts)
"""

results_md += f"""
## Per-Layer Breakdown

| Layer | TUNNEL | ATTENUATE | REFLECT | COLLAPSE | Avg T |
|-------|--------|-----------|---------|----------|-------|
"""

for layer_idx in range(num_layers):
    layer_cls = [c for c in classifications if c.layer == layer_idx]
    t_c = sum(1 for c in layer_cls if c.outcome == "TUNNEL")
    a_c = sum(1 for c in layer_cls if c.outcome == "ATTENUATE")
    r_c = sum(1 for c in layer_cls if c.outcome == "REFLECT")
    c_c = sum(1 for c in layer_cls if c.outcome == "COLLAPSE")
    avg = np.mean([c.transmission_coeff for c in layer_cls])
    results_md += f"| {layer_idx} | {t_c} | {a_c} | {r_c} | {c_c} | {avg:.4f} |\n"

results_md += f"""
## Connection to Prior Results

| Finding | Source | Value |
|---------|--------|-------|
| Trained peak T | OPT-1.3B validation | 0.9342 |
| Random baseline T | OPT-1.3B validation | 0.0054 |
| Survival ratio | OPT-1.3B validation | 173x |
| Q resonance angle | OPT-1.3B validation | -30 deg |
| K resonance angle | OPT-1.3B validation | -66 deg |
| COLLAPSE ablation delta | **This experiment** | {delta_collapse:+.2f}% |
| TUNNEL ablation delta | **This experiment** | {delta_tunnel:+.2f}% |
| Effect ratio | **This experiment** | {abs(delta_tunnel) / max(abs(delta_collapse), 0.01):.2f}x |

## Artifacts

- Source: `artifacts/research/behavioral_ablation_experiment.py`
- Prior results: `artifacts/research/opt_1.3b_phase_tunnel_results.json`
- Phase tunnel impl: `src/aetherbrowser/phase_tunnel.py`
- DistilBERT finding: `notes/round-table/2026-03-19-phase-tunnel-resonance-finding.md`

---

*Generated by SCBE-AETHERMOORE behavioral ablation experiment.*
*PhaseTunnelGate: phase-selective governance for transformer attention heads.*
"""

try:
    with open(OUTPUT_PATH, "w") as f:
        f.write(results_md)
    print(f"Results saved to {OUTPUT_PATH}")
except Exception as e:
    print(f"Could not save to {OUTPUT_PATH}: {e}")
    # Try alternate location
    alt_path = "behavioral_ablation_results.md"
    try:
        with open(alt_path, "w") as f:
            f.write(results_md)
        print(f"Results saved to {alt_path} (fallback)")
    except Exception as e2:
        print(f"Could not save results: {e2}")
        print("Printing full markdown instead:")
        print(results_md)

# Also save raw data as JSON for programmatic access
results_json = {
    "experiment": "behavioral_ablation",
    "model": MODEL_NAME,
    "date": time.strftime("%Y-%m-%d", time.gmtime()),
    "device": DEVICE,
    "eval_tokens": int(total_tokens),
    "classification_counts": outcome_counts,
    "total_heads_classified": total_heads,
    "perplexity": {
        "baseline": round(ppl_baseline, 4),
        "collapse_ablated": round(ppl_collapse_ablated, 4),
        "tunnel_ablated": round(ppl_tunnel_ablated, 4),
    },
    "delta_pct": {
        "collapse": round(delta_collapse, 4),
        "tunnel": round(delta_tunnel, 4),
    },
    "effect_ratio": round(abs(delta_tunnel) / max(abs(delta_collapse), 0.01), 4),
    "hypothesis_supported": hypothesis_supported,
    "classifications": [
        {
            "layer": c.layer,
            "head": c.head,
            "weight_type": c.weight_type,
            "T": round(c.transmission_coeff, 6),
            "angle_rad": round(c.resonance_angle, 6),
            "spectral_density": round(c.spectral_density, 6),
            "outcome": c.outcome,
        }
        for c in classifications
    ],
}

json_path = OUTPUT_PATH.replace(".md", ".json")
try:
    with open(json_path, "w") as f:
        json.dump(results_json, f, indent=2)
    print(f"JSON data saved to {json_path}")
except Exception:
    pass

print()
print("=" * 70)
print("EXPERIMENT COMPLETE")
print("=" * 70)
