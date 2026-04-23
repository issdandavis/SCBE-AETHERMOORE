# Unified Attention Probe Synthesis: Outputs vs Weights

**Date:** 2026-03-19
**Authors:** Claude (synthesis), Codex (Colab correction), Issac (hypothesis)
**Status:** Research synthesis — combines Claude's sweep and Codex's correction into a single experimental design
**Depends on:**
- `notes/round-table/2026-03-19-mirror-probe-first-results.md`
- `notes/round-table/2026-03-18-mirror-problem-and-introspection-architecture.md`
- `docs/paper/davis-2026-intent-modulated-governance.md` (Section 14)

---

## 1. Comparison: Approach A vs Approach B

| Dimension | **Approach A (Claude's Sweep)** | **Approach B (Codex's Colab Correction)** |
|-----------|-------------------------------|----------------------------------------|
| **Target** | Attention output matrices (post-softmax) | Raw Q/K/V weight tensors (pre-softmax) |
| **What it measures** | Per-head probability distributions over token positions | Learned linear projections that create queries, keys, values |
| **Mathematical object** | Stochastic matrix: each row sums to 1 after softmax | Unconstrained real-valued matrices of shape (d_model, d_head) |
| **Signal extraction** | `model(output_attentions=True)` -> per-layer attention tensors | `model.layers[i].self_attn.q_proj.weight` (direct parameter access) |
| **Projection modes tested** | flatten, row_mean, diagonal | Not yet run; proposed: flatten, row_mean, SVD-rank spectrum |
| **S_spec formula** | `E_low / (E_total + eps)` with cutoff_ratio=0.25 | Same formula, but cutoff_ratio may need recalibration |
| **Model tested** | issdandavis/scbe-pivot-qwen-0.5b (PEFT on Qwen2.5-0.5B) | DistilBERT (Colab); proposed: same Qwen model |
| **Result** | Mean S_spec = 0.230 (semantic), 0.257 (control), delta = 0.027 | Not yet run on weight tensors |
| **Key finding** | U-shaped depth curve; semantic < control; layer 16 trough | Softmax flattens frequency domain; outputs are "move probabilities, not board state" |

### 1.1 What Approach A Measures (Mathematically)

The attention output matrix A for a single head has shape (seq_len, seq_len), where:

```
A[i,j] = softmax(Q[i] . K[j]^T / sqrt(d_k))
```

Each row is a probability distribution: `sum_j A[i,j] = 1`. The FFT probe flattens this matrix to a 1D signal and computes:

```
S_spec = sum(|X[k]|^2 for k < N*0.25) / sum(|X[k]|^2 for all k)
```

**What this detects:** Large-scale spatial patterns in how attention is distributed. A high S_spec means attention is concentrated (few tokens attended strongly), a low S_spec means attention is diffuse (many tokens attended roughly equally).

**What this misses:** The softmax constraint (rows sum to 1) acts as a normalizing filter. It compresses the dynamic range of the frequency domain. Two very different pre-softmax logit patterns can produce nearly identical post-softmax distributions. The softmax is a lossy projection from logit space to probability space — it destroys frequency-domain information. This is exactly what Codex identified: "we were probing the move probabilities, not the board state."

**Strengths:**
- Captures the actual computation the model performs at runtime
- The U-shaped depth curve is a real structural signature (reproducible across 8 prompts)
- Semantic vs control difference, while small (delta=0.027), is stable across all 24 layers
- Easy to extract — `output_attentions=True` is a standard API

**Weaknesses:**
- Softmax normalization destroys high-frequency structure
- S_spec values (0.20-0.35) are in a narrow band barely above random control (0.21)
- The 0.25 cutoff ratio was designed for audio signals, not attention matrices
- Cannot distinguish between "no structure exists" and "structure exists but softmax hides it"

### 1.2 What Approach B Measures (Mathematically)

The Q/K/V weight matrices are learned parameters:

```
Q = X @ W_Q    where W_Q has shape (d_model, d_head)
K = X @ W_K    where W_K has shape (d_model, d_head)
V = X @ W_V    where W_V has shape (d_model, d_head)
```

These are unconstrained real-valued matrices. They are the "compressed intuition" of the model — what it learned to look for (Q), what it learned to expose (K), and what it learned to transmit (V).

**What this detects:** Structural patterns in the learned projections themselves, independent of any specific input. If the model learned to create frequency-domain structure in its attention computation, it would be encoded here. These weights are analogous to the "board state" rather than the "move probabilities."

**What this misses:**
- Input-dependent structure (the same weights produce different attention patterns for different inputs)
- Interaction effects between Q and K (the attention pattern is Q @ K^T, not Q or K alone)
- Fine-tuning effects may be subtle: PEFT adapters modify a low-rank subspace of the full weight matrix

**Strengths:**
- No softmax normalization — full dynamic range preserved
- Input-independent — measures what the model "knows" regardless of prompt
- Directly comparable across models (base vs fine-tuned)
- Can detect whether fine-tuning (PEFT) introduced or altered frequency structure

**Weaknesses:**
- Not yet run — all claims are theoretical
- Weight matrices have different shapes than attention outputs (d_model x d_head vs seq_len x seq_len), so cutoff ratios and projections need re-derivation
- May require SVD or eigenvalue decomposition rather than simple FFT for meaningful analysis
- PEFT adapter weights are low-rank perturbations; the "interesting" structure may be in the residual

### 1.3 S_spec Appropriateness

The S_spec formula `E_low / (E_total + eps)` with cutoff_ratio=0.25 was defined in SCBE Layer 9 (`src/spectral/index.ts`) for audio/signal coherence. Applied to attention:

**For attention outputs (Approach A):** The 0.25 cutoff means "first quarter of frequency bins are low-frequency." For a flattened seq_len x seq_len matrix (e.g., 37x37 = 1,369 values), this probes the first ~342 frequency bins. Given that softmax compresses values to [0, 1] with rows summing to 1, the DC component (bin 0) dominates because the mean is nonzero (each row averages ~1/seq_len). The formula mostly measures how far the attention pattern deviates from uniform — not true spectral structure. **Verdict: partially appropriate, but measures uniformity more than structure.**

**For weight tensors (Approach B):** Weight values are approximately normally distributed around zero (standard initialization). Subtracting the mean (as `mirror_problem_fft.py` does) removes the DC component. The remaining spectrum genuinely reflects learned structure. The 0.25 cutoff needs empirical calibration — weight matrices may have meaningful structure at different frequency scales than attention outputs. **Verdict: more appropriate, but cutoff needs empirical tuning.**

---

## 2. What Each Found and Why

### Approach A Found:

1. **U-shaped spectral curve across 24 layers.** Measured S_spec values by layer:

   | Layer | S_spec | Layer | S_spec | Layer | S_spec |
   |-------|--------|-------|--------|-------|--------|
   | 0 | 0.3373 | 8 | 0.2240 | 16 | **0.2014** |
   | 1 | 0.3464 | 9 | 0.2021 | 17 | 0.2098 |
   | 2 | 0.3443 | 10 | 0.2223 | 18 | 0.2117 |
   | 3 | 0.2315 | 11 | 0.2123 | 19 | 0.2303 |
   | 4 | 0.2420 | 12 | 0.2302 | 20 | 0.2143 |
   | 5 | 0.2402 | 13 | 0.2368 | 21 | 0.2019 |
   | 6 | 0.2353 | 14 | 0.2135 | 22 | **0.2657** |
   | 7 | 0.2164 | 15 | 0.2244 | 23 | **0.2716** |

   **Why:** Early layers (0-2) perform token-local attention patterns (positional, syntactic), creating concentrated spectral energy. Middle layers do broad semantic mixing, flattening the spectrum. Final layers re-focus for next-token prediction, concentrating energy again. This is a real architectural signature of transformer depth.

2. **Semantic prompts produce lower S_spec than controls.** Mean 0.2302 vs 0.2570 (delta=0.027).

   **Why:** Meaningful input activates more distributed processing. Nonsense or repeated tokens allow the model to use simpler, more concentrated attention patterns. This is consistent with the hypothesis that semantic content requires broader context integration. However: the effect is small (delta=0.027 on a scale where random control = 0.207) and could be partly explained by sequence length differences (semantic prompts averaged ~37 tokens, control prompts varied from ~10 to ~30).

3. **Head specialization decreases with depth.** Std drops from 0.14 (layers 0-2) to 0.03-0.05 (layers 12-21).

   **Why:** Early heads are functionally diverse — some do local attention, others do global. By the middle layers, residual connections and layer norm have mixed information sufficiently that all heads converge toward similar patterns.

### Approach B Found (from the Colab run):

1. **Attention outputs are ~5x below noise baseline.** Attention S_spec scored 21-41 vs noise baseline 126.88 +/- 3.62 (note: the Colab run may have used a different S_spec scale — this looks like raw energy rather than the 0-1 ratio).

   **Why:** Softmax normalization maps logits to a probability simplex, which mathematically suppresses high-frequency components. The post-softmax distribution is always "smooth" relative to the pre-softmax logits.

2. **Decimal drift hypothesis: inconclusive.** 0/8 structured drift at float32 vs float64.

   **Why:** A freshly loaded model without compounded fine-tuning rounds has no accumulated numerical error. The drift hypothesis may apply to models that have been through multiple rounds of quantization, fine-tuning, and merging — not a fresh checkpoint.

3. **The correction:** Probe the raw Q/K/V weight matrices instead.

   **Why this is sound:** The weight matrices encode the "compressed intuition" of what the model learned. They are not constrained by softmax. If the model learned structured patterns (harmonic, geometric, or otherwise), they would be preserved in the weight matrices. The softmax is a lossy projection that destroys this information for the purpose of computing a valid probability distribution.

---

## 3. Unified Probe Design

### 3.1 Architecture

A single probe script that runs both approaches in one pass and computes a correlation metric.

```
unified_attention_probe.py
├── Phase 1: Weight Tensor Analysis (input-independent)
│   ├── For each layer L:
│   │   ├── Extract W_Q, W_K, W_V weight matrices
│   │   ├── For PEFT models: extract base + adapter weights separately
│   │   ├── Compute S_spec for each with multiple projections:
│   │   │   ├── flatten (reshape to 1D)
│   │   │   ├── row_mean (average across input dimensions)
│   │   │   ├── svd_spectrum (singular values as the 1D signal)
│   │   │   └── column_mean (average across output dimensions)
│   │   └── Log: layer, weight_type (Q/K/V), projection, S_spec, peak_ratio, entropy
│   └── Output: per-layer weight spectral profile (no input dependence)
│
├── Phase 2: Attention Output Analysis (input-dependent)
│   ├── For each prompt P in (semantic_set + control_set):
│   │   ├── Forward pass with output_attentions=True
│   │   ├── For each layer L, head H:
│   │   │   ├── Extract attention matrix A (seq_len x seq_len)
│   │   │   ├── Compute S_spec with projections: flatten, row_mean, diagonal
│   │   │   └── Log: layer, head, prompt_key, projection, S_spec, peak_ratio, entropy
│   │   └── Aggregate: per-layer mean/std across heads and prompts
│   └── Output: per-layer attention spectral profile (input-dependent)
│
├── Phase 3: Weight-Output Correlation
│   ├── For each layer L:
│   │   ├── weight_s_spec[L] = mean S_spec across Q/K/V weights
│   │   ├── output_s_spec[L] = mean S_spec across all heads/prompts
│   │   ├── Compute Pearson correlation across layers
│   │   ├── Compute rank correlation (Spearman) across layers
│   │   └── Per-head: correlate W_Q S_spec with that head's output S_spec
│   └── Output: correlation coefficients + scatter data
│
└── Phase 4: SCBE Baseline Comparison
    ├── Generate Langues Metric weight matrix (6x6, phi-scaled)
    ├── Compute S_spec of the governed weight profile
    ├── Compare: does governed attention have a different spectral signature
    │   than learned attention?
    └── Output: governed vs learned spectral comparison
```

### 3.2 Pseudocode

```python
def unified_probe(model_id, prompts, control_prompts):
    bundle = load_model_bundle(model_id)
    model = bundle.model

    # ---- Phase 1: Weight tensors ----
    weight_results = []
    for layer_idx, layer in enumerate(get_transformer_layers(model)):
        for weight_name in ['q_proj', 'k_proj', 'v_proj']:
            W = get_weight_matrix(layer.self_attn, weight_name)
            # If PEFT: also extract adapter_A, adapter_B separately

            for projection in ['flatten', 'row_mean', 'column_mean', 'svd_spectrum']:
                if projection == 'svd_spectrum':
                    signal = np.linalg.svd(W, compute_uv=False)  # singular values
                else:
                    signal = attention_signal(W, mode=projection)

                # Use cutoff_ratio=0.10 for weight tensors (empirical starting point)
                probe = compute_spectral_probe(signal, cutoff_ratio=0.10)
                weight_results.append({
                    'layer': layer_idx,
                    'weight': weight_name,
                    'projection': projection,
                    'probe': probe,
                })

    # ---- Phase 2: Attention outputs (existing sweep logic) ----
    output_results = []
    all_prompts = {**semantic_prompts, **control_prompts}
    for prompt_key, prompt_text in all_prompts.items():
        extraction = extract_attentions(bundle, prompt_text)
        for layer_idx in range(len(extraction['attentions'])):
            heads = tensor_to_heads(extraction['attentions'][layer_idx])
            for head_idx in range(heads.shape[0]):
                for projection in ['flatten', 'row_mean', 'diagonal']:
                    signal = attention_signal(heads[head_idx], mode=projection)
                    probe = compute_spectral_probe(signal, cutoff_ratio=0.25)
                    output_results.append({
                        'layer': layer_idx,
                        'head': head_idx,
                        'prompt_key': prompt_key,
                        'projection': projection,
                        'probe': probe,
                    })

    # ---- Phase 3: Correlation ----
    weight_by_layer = aggregate_mean_s_spec(weight_results, group_by='layer')
    output_by_layer = aggregate_mean_s_spec(output_results, group_by='layer')

    pearson_r = np.corrcoef(weight_by_layer, output_by_layer)[0, 1]
    spearman_r = scipy.stats.spearmanr(weight_by_layer, output_by_layer).statistic

    # Per-head correlation (do structured weights produce structured outputs?)
    head_correlations = []
    for layer_idx in range(n_layers):
        for head_idx in range(n_heads):
            # Q weight S_spec for this layer
            w_spec = get_weight_s_spec(weight_results, layer_idx, 'q_proj')
            # Output S_spec for this head across all prompts
            o_spec = get_output_s_spec(output_results, layer_idx, head_idx)
            head_correlations.append((w_spec, o_spec))

    # ---- Phase 4: Governed baseline ----
    langues_weights = generate_phi_scaled_weight_matrix()
    governed_probe = compute_spectral_probe(langues_weights.flatten())

    return {
        'weight_results': weight_results,
        'output_results': output_results,
        'correlation': {
            'pearson': pearson_r,
            'spearman': spearman_r,
            'head_correlations': head_correlations,
        },
        'governed_baseline': governed_probe,
    }
```

### 3.3 Key Design Decisions

1. **Different cutoff ratios.** Attention outputs use cutoff_ratio=0.25 (existing). Weight tensors use cutoff_ratio=0.10 (tentative). Rationale: weight matrices are larger (d_model x d_head, e.g., 896 x 64 for Qwen-0.5B) and may have meaningful structure at lower frequency ratios. The first run should sweep cutoff_ratio in [0.05, 0.10, 0.15, 0.20, 0.25] to find the most discriminative value.

2. **SVD spectrum as a fourth projection.** For weight matrices, the singular values capture the rank structure directly. A weight matrix with a few dominant singular values has "structured" attention; one with many similar singular values has "diffuse" attention. This is complementary to FFT and may be more interpretable for rectangular matrices.

3. **PEFT adapter separation.** For our model (scbe-pivot-qwen-0.5b), the PEFT adapter adds low-rank perturbations. Measuring the adapter weights separately from the base weights tells us what the fine-tuning *changed* — this is the "SCBE signal" on top of the base model.

4. **Semantic vs control comparison preserved.** The attention output analysis keeps the prompt-type comparison from Approach A, since it showed a small but stable effect.

---

## 4. SCBE System Connections

### 4.1 S_spec Formula: Layer 9 vs Attention Probing

The Layer 9 spectral coherence formula from `src/spectral/index.ts`:

```
S_spec = E_low / (E_low + E_high + epsilon)
```

where E_low = sum of power spectrum below cutoff frequency, E_high = sum above.

In the SCBE pipeline, this is applied to audio/telemetry signals with a physical cutoff frequency (Hz). When applied to attention matrices, "frequency" becomes spatial frequency across token positions (for outputs) or across model dimensions (for weights). The formula is mathematically identical — only the interpretation of "frequency" changes.

**For attention outputs:** "Low frequency" means large-scale patterns across the sequence (e.g., attending to nearby tokens creates a low-frequency pattern). "High frequency" means fine-grained, rapidly varying attention. S_spec near 1 = concentrated, local attention. S_spec near 0 = diffuse, global attention.

**For weight tensors:** "Low frequency" means smooth variation across the weight matrix (large-scale structure in how the model projects information). "High frequency" means rapid variation (potentially noise, or fine-grained learned features). S_spec near 1 = the weight matrix has large-scale structure. S_spec near 0 = the weight matrix has uniform or high-frequency structure.

**Assessment:** The formula is mathematically valid for both applications. The interpretation differs, and the optimal cutoff ratio will differ. The formula should be used with explicit acknowledgment that it measures energy distribution, not a physical property.

### 4.2 The U-Shaped Depth Curve and the 14-Layer Pipeline

The measured U-shaped S_spec curve across 24 transformer layers:

```
Layers 0-2:   S_spec ~ 0.34  (high structure, wide variance)
Layers 3-16:  S_spec ~ 0.22  (diffuse, low variance, trough at L16 = 0.201)
Layers 17-21: S_spec ~ 0.21  (still diffuse, slight uptick)
Layers 22-23: S_spec ~ 0.27  (re-concentration)
```

This maps suggestively (but not mechanistically) to the SCBE 14-layer pipeline:

| SCBE Pipeline | Function | Transformer Analog |
|--------------|----------|-------------------|
| L1-2 (Context) | Complex context -> realification | Layers 0-2: tokenization + positional encoding -> initial attention |
| L3-4 (Transform) | Weighted transform -> Poincare | Layers 3-5: first mixing, structure dissolution |
| L5-7 (Geometry) | Hyperbolic distance, breathing, Mobius | Layers 6-11: deep mixing, maximum diffusion |
| L8-10 (Spectral) | Multi-well, FFT coherence, spin | Layers 12-16: trough (layer 16 = maximum uniformity) |
| L11-12 (Temporal) | Triadic distance, harmonic wall | Layers 17-21: beginning to re-concentrate |
| L13-14 (Decision) | Risk decision, audio axis | Layers 22-23: final focusing for output |

**Caution:** This is an analogy, not a mechanistic correspondence. A 24-layer transformer does not implement the 14-layer SCBE pipeline. The U-shaped curve is a generic property of deep transformers (early layers encode, middle layers mix, late layers decode). The interesting question is whether governed attention would *change the shape* of this curve — e.g., would Langues Metric weights create a flatter curve (less U-shape) or a sharper one?

### 4.3 Langues Metric as Spectral Baseline

The Langues Metric (`packages/kernel/src/languesMetric.ts`) defines governed attention weights:

```
w_l = phi^l    for l in [0..5]   (golden ratio progression)
phi_l = 2*pi*l/6                  (60-degree phase intervals)
beta_l = beta_base * phi^(l*0.5)  (exponential sensitivity scaling)
```

The weight vector [1.00, 1.62, 2.62, 4.24, 6.85, 11.09] is a monotonically increasing geometric sequence. Its FFT would show:

- Strong low-frequency component (the monotonic trend)
- Weak harmonics from the specific phi-ratio spacing
- S_spec would be high (~0.7-0.9) because almost all energy is in the trend

**Prediction (SPECULATIVE):** If we compute S_spec of the Langues Metric weight vector, it will be significantly higher than any learned attention weight S_spec (0.20-0.35). This would mean governed attention is more structured than learned attention — which is the design intent. The question is whether "more structured" means "more robust" or "less flexible."

A fair comparison requires generating a full (d_model x d_head) governed weight matrix using the Langues Metric, not just the 6-element weight vector. One approach: tile the phi-weights across the model dimension, creating a structured projection matrix. Then compute S_spec and compare to the learned W_Q.

### 4.4 Harmonic Wall and Spectral Decay

The harmonic wall formula:

```
H_score(d, pd) = 1 / (1 + d + 2*pd)     (bounded, 0 to 1)
H_wall(d, R)   = R^(d^2)                  (super-exponential, unbounded)
```

The spectral structure decay across transformer depth is reminiscent of the harmonic wall: structure "costs" increase with depth (distance from input), making it harder for spectral energy to remain concentrated. The middle layers are the "deep hyperbolic region" where structure is most suppressed.

**Quantitative connection (SPECULATIVE):** If we define d = layer_index / total_layers (normalized depth), then:

```
H_score(d, 0) = 1 / (1 + d)
```

At d=0 (layer 0): H_score = 1.0, measured S_spec = 0.34
At d=0.5 (layer 12): H_score = 0.67, measured S_spec = 0.23
At d=1.0 (layer 23): H_score = 0.50, measured S_spec = 0.27

The measured S_spec does not follow H_score monotonically (the final uptick breaks the pattern). But the middle region (d=0.3 to d=0.7) shows rough proportionality. This is suggestive but not conclusive — more models need to be tested.

### 4.5 Theoretical "Governed Attention" Spectral Profile

**What would perfectly governed attention look like spectrally?**

In the SCBE framework, governed attention would follow these constraints:
1. Weights prescribed by the Langues Metric (phi-scaled, deterministic)
2. Phase modulated by the breathing transform (L6): `b(t) = 1 + A*sin(omega*t)`
3. Distance computed in Poincare ball (L5): exponential at boundary
4. Coherence verified by Layer 9: S_spec above threshold

The governed spectral profile would be:
- **High S_spec** (0.7+) because weights are deterministic and structured
- **Low variance across heads** because all heads follow the same geometric prescription
- **No U-shaped curve** because structure is imposed at every layer, not learned
- **Phase-dependent temporal variation** from the breathing transform, but the mean would be stable

**Contrast with learned attention:**
- **Low S_spec** (0.20-0.35) because gradient descent finds diverse solutions
- **High variance across heads** (especially early layers) because heads specialize
- **U-shaped depth curve** because structure is emergent, not imposed

**Key prediction:** The governed profile would be *qualitatively different* from the learned profile. This is testable by constructing a model with Langues Metric attention and running the same probe.

---

## 5. Theoretical Predictions for Weight Tensor Probe

When the Phase 2 (weight tensor) probe runs on issdandavis/scbe-pivot-qwen-0.5b, we predict:

### 5.1 High Confidence Predictions

1. **Weight tensor S_spec will be higher than attention output S_spec.** Because weight matrices are not softmax-normalized, they preserve more frequency-domain structure. Expected: weight S_spec in [0.3, 0.6] vs output S_spec in [0.2, 0.35].

2. **Q and K weights will have different spectral profiles than V weights.** Q and K are used multiplicatively (Q @ K^T) to compute attention, so they are trained to create complementary patterns. V weights are used additively (weighted sum), so they should be more uniform. Expected: S_spec(Q) and S_spec(K) will be correlated; S_spec(V) will be lower and less correlated with the others.

3. **The SVD spectrum will be more discriminative than FFT for weight matrices.** Weight matrices encode rank structure (how many independent "directions" the projection uses). SVD captures this directly. Expected: SVD-based S_spec will show wider separation between structured and unstructured layers.

### 5.2 Medium Confidence Predictions

4. **The U-shaped depth curve will appear in weight tensors too, but attenuated.** Weight structure is cumulative across training — deeper layers may have had more gradients passed through them but also more chances to develop structure. The curve may be flatter. Expected: still U-shaped, but with a shallower trough (0.25 vs 0.20 in outputs).

5. **PEFT adapter weights will show different spectral structure than base model weights.** The adapter is a low-rank perturbation; its spectral profile should be sparse (a few dominant frequencies). Expected: adapter S_spec will be higher than base weights because low-rank matrices have concentrated spectral energy.

6. **Weight-output correlation will be positive but moderate.** Structured weights should produce more structured outputs, but the softmax and input-dependence add noise. Expected: Pearson r in [0.3, 0.6] across layers.

### 5.3 Low Confidence Predictions (Speculative)

7. **Layer 16 will remain the trough in weight tensors.** If the depth curve is architecturally determined (not just an artifact of softmax), the trough should persist.

8. **Semantic vs control difference will be larger when viewed through weight-output correlation.** The weight structure is fixed; the attention output difference comes from how the same weights interact with different inputs. Structured weights may amplify input differences.

9. **The cutoff_ratio=0.10 will be more discriminative for weights than 0.25.** Weight matrices have structure at lower spatial frequencies than attention outputs because they operate on model dimensions rather than sequence positions.

---

## 6. Open Questions

### 6.1 Fundamental

1. **Is the U-shaped depth curve universal across transformer architectures, or specific to Qwen-0.5B?** Need to test on at least 3 different model families (e.g., Llama, Mistral, GPT-2).

2. **Does fine-tuning change the spectral profile measurably?** Compare base Qwen2.5-0.5B-Instruct vs our PEFT adapter on the same prompts. If the difference is within noise, the SCBE fine-tuning did not measurably alter attention structure.

3. **Is the semantic-control delta (0.027) larger than the prompt-length confound?** Semantic prompts averaged ~37 tokens; controls varied. Need prompts matched for length.

4. **What does "spectral structure" in weight tensors actually mean for computation?** A weight matrix with high S_spec projects inputs into a space dominated by a few directions. Is this "specialization" (good) or "bottleneck" (bad)?

### 6.2 Methodological

5. **What cutoff_ratio is optimal for weight tensors?** Need to sweep [0.05, 0.10, 0.15, 0.20, 0.25] and report which gives the best separation between layers and between semantic/control.

6. **Is FFT the right tool for weight matrices, or should we use wavelet transform?** Wavelets capture multi-scale structure better than FFT for signals with localized features.

7. **Should we analyze W_Q @ W_K^T instead of Q and K separately?** The attention pattern is determined by the product, not the individual matrices. The product may reveal structure that neither matrix has alone.

8. **How does batch normalization / layer norm interact with spectral analysis?** Layer norm rescales activations, which changes the frequency domain. Are we measuring structure in the weights or structure imposed by normalization?

### 6.3 SCBE-Specific

9. **Can we construct a "governed attention" model by replacing W_Q with a Langues Metric matrix?** Would it still produce coherent outputs?

10. **Does the Davis Security Score S(t,i,C,d) have an analog in the attention spectral domain?** Specifically, does the factorial C! term map to something measurable in the spectral profile?

11. **Can we use the spectral profile as a Layer 9 input for the 14-layer pipeline?** Instead of external audio signals, feed the model's own attention spectral profile into the governance pipeline. This would be a form of "attention self-governance."

---

## 7. Next Experiments (Priority Order)

### 7.1 Immediate (do this week)

1. **Run weight tensor probe on scbe-pivot-qwen-0.5b.** Implement Phase 1 of the unified probe. Extract Q/K/V weight matrices for all 24 layers. Compute S_spec with cutoff sweep [0.05, 0.10, 0.15, 0.20, 0.25]. Compare to attention output S_spec from the existing sweep.
   - **Why first:** This is the single most informative experiment. It tests whether the "board state" has structure that the "move probabilities" hide.

2. **Run same probe on base Qwen2.5-0.5B-Instruct (no PEFT).** Compare weight spectral profiles. If they are identical, the SCBE fine-tuning did not change the spectral structure.
   - **Why second:** This determines whether our fine-tuning is measurably different from the base model at the spectral level.

3. **Compute weight-output correlation.** Run Phase 3 of the unified probe. Report Pearson and Spearman correlations.
   - **Why third:** This tests the core hypothesis that weight structure predicts output structure.

### 7.2 Short-term (next 2 weeks)

4. **Length-matched prompt comparison.** Create semantic and control prompts with identical token counts. Re-run attention output probe to eliminate the length confound.

5. **Cross-model comparison.** Run the full probe on Llama-3.2-1B and DistilBERT to test whether the U-curve and spectral patterns generalize.

6. **SVD spectrum analysis.** Compute singular value spectra of W_Q/W_K/W_V for all layers. Plot rank structure vs depth.

### 7.3 Medium-term (next month)

7. **Construct governed attention model.** Replace learned attention weights with phi-scaled Langues Metric weights in a small model. Run the probe. Compare spectral profiles.

8. **Temporal breathing probe.** For attention outputs: collect multiple samples over time (different prompts), compute per-head S_spec trajectories, test for periodic structure matching the SCBE breathing transform frequency.

9. **Write paper Section 14.5.** Incorporate weight tensor results into the paper with honest error bars and effect sizes.

---

## 8. Artifacts

| File | Description |
|------|-------------|
| `src/minimal/mirror_problem_fft.py` | Core FFT probe (Codex) |
| `scripts/probe_attention_fft.py` | Attention tensor probe (Codex) |
| `scripts/sweep_attention_fft.py` | Multi-prompt sweep (Claude) |
| `artifacts/attention_fft/sweep-20260319T040455Z.json` | Full 24-layer sweep results |
| `notes/round-table/2026-03-19-mirror-probe-first-results.md` | First results analysis |
| `notes/round-table/2026-03-18-mirror-problem-and-introspection-architecture.md` | Original hypothesis |
| `src/spectral/index.ts` | SCBE Layer 9 spectral coherence |
| `packages/kernel/src/harmonicScaling.ts` | Harmonic wall formulas |
| `packages/kernel/src/languesMetric.ts` | Langues Metric |
| `docs/paper/davis-2026-intent-modulated-governance.md` | Paper Section 14 |

---

*This note synthesizes work from two independent agents (Claude and Codex) working on the same hypothesis from different angles. The unified probe design here has not yet been implemented — it is a specification for the next round of experiments.*
