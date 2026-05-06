# Shallow vs Full-Depth Attention: A Synthesis

**Date**: 2026-05-06
**Trigger**: User asked while v6f training run (`69fb49a046974e2a21d27a1a`) is in flight: "research shallow and depth full attention mechanisms"
**Why this matters for SCBE**: The 14-layer pipeline routes attention through L7 Möbius phase, L9-10 spectral/spin coherence, and the harmonic wall at L12. The MAHSS spec (multi-attention holographic fold) explicitly composes K attention heads via HRR-bound role vectors. The choice between shallow and deep attention is not an engineering tradeoff — it determines what kind of computation the substrate supports.

---

## 1. The spectrum: from shallow-wide to every-layer-dense

### Shallow attention: feedforward proves it can imitate

- **Bozic 2023** (arXiv 2311.10642). Shallow non-linear feedforward networks **emulate attention head outputs** with minimal accuracy loss. The implication: attention is not architecturally privileged — it is a *function* the model can learn to approximate at any depth, including depth one.
- **Brown 2022** (arXiv 2210.00640). A **single wide attention layer** can outperform deeper transformer stacks on certain tasks. Width substitutes for depth when the receptive task has low compositional depth.

These two papers anchor the lower bound. Attention without depth is sufficient for many tasks — the question is which.

### Full-depth attention: the conventional default

Every layer attends. This is GPT, Llama, Qwen — the v6f base model. The implicit claim is that each layer needs a separate global view of the residual stream. That claim has been quietly eroding.

### The middle ground: dynamic depth

- **Mixture of Depths** family. Router-Tuning (arXiv 2410.13184) makes attention conditional per-token per-layer.
- **Lawson 2025** (arXiv 2506.21103) — "Learning to Skip Middle Layers" — shows middle layers contribute less than the residual norm suggests; the model can skip ~30% of them with measured-loss only.
- **Csordas 2025** (arXiv 2505.13898) — "Do LLMs Use Their Depth Efficiently?" — empirically, no. Depth utilization is uneven; a small fraction of layers carry most of the load.
- **I3D dynamic depth** (arXiv 2303.07624) — depth chosen at inference time per input.

Conclusion of the dynamic-depth literature: **the canonical "every layer attends globally" architecture is wasteful** for the majority of inputs. The cost-honest design is depth-conditional attention.

---

## 2. Attention sinks: a depth-specific phenomenon

Sinks (the first-token absorbing pattern) are **not uniform across depth** — they emerge at specific layers and serve as boundary conditions:

- **Survey 2604.10098** — taxonomy of sink patterns and their distribution across layer index.
- **Barbero 2025** (arXiv 2504.02732) — "Why does the first token attract so much attention?" — the sink is a **representational pressure valve** that concentrates at early layers, not late.
- **Wong 2025** (arXiv 2512.22213) — secondary sinks emerge at specific deeper layers, suggesting hierarchical sink structure.
- **Ruscio 2025** (arXiv 2508.02546) — sinks act as **geometric reference frames**, anchoring the attention manifold.

This is the most SCBE-relevant strand. Sinks are *depth-localized geometric anchors*. That maps directly onto the L7 Möbius phase boundary and the L8 Hamiltonian wells. SCBE's well structure already imposes the kind of layer-localized basin that the sink literature describes empirically.

---

## 3. Sparse vs full: a complementary axis (not a replacement)

Sparse attention is orthogonal to depth. You can sparsify a deep model or densify a shallow one.

- **Native Sparse Attention** (arXiv 2502.11089, DeepSeek). Hardware-native sparse pattern; trains end-to-end. Match-or-beats dense at long context.
- **Flash Sparse Attention** (arXiv 2508.18224) — the kernel makes NSA actually fast.
- **NOSA** (arXiv 2510.13602) — natively-organized sparse attention.
- **SSA** (arXiv 2511.20102, SubQuadratic). Subquadratic attention — the architecture behind the SubQuadratic company seed round noted in memory.
- **HISA** (arXiv 2603.28458) — hierarchical sparse attention.

### Hybrid local-global

- **Native Hybrid Attention** (arXiv 2510.07019). Local windows + global summary tokens; trained jointly.
- **"Learning When Not to Attend Globally"** (arXiv 2512.22562). Per-token global-attention gating. Most tokens don't need it.
- **Optimizing NSA with Local-Global Alternating** (arXiv 2511.00819).

The trend across 2025-2026: **alternating local and global attention**, with global gated per-token. Full global attention every layer is unjustified by the evidence.

---

## 4. Adjacent depth-modulating directions

- **DIFF Transformer family** (arXiv 2501.17900, 2505.16333, 2501.17486). Differential attention — two attention maps, subtract — denoises across depth.
- **MUDDFormer** (arXiv 2502.12170). Multi-way dense-to-dense — replaces residual stream with explicit cross-depth routing.
- **Transformers without Normalization** (arXiv 2503.10622). Removes LayerNorm; depth dynamics change qualitatively.
- **Neural Attention** (arXiv 2502.17206). Reframes attention as a learned neural operator rather than dot-product.

Survey: arXiv 2507.19595 "Efficient Attention Mechanisms for LLMs: A Survey" gives the canonical taxonomy — **linear attention** (kernel / recurrent / fastweight) vs **sparse attention** (fixed patterns / block routing / clustering). The survey treats depth as orthogonal — most efficiency work targets *width* of attention, not *depth* of stack.

---

## 5. SCBE cross-references

| SCBE component | Attention-depth literature it touches |
|---|---|
| **L5 hyperbolic distance** | Distance metric in the residual stream; analogous to attention kernel. Hyperbolic kernel work has not been integrated into mainstream attention papers — opportunity. |
| **L7 Möbius phase** | Möbius transforms are *isometries* — they preserve hyperbolic distance. This is the SCBE-native answer to "how does attention compose across depth without losing geometric structure." Mainstream models lose it (hence the empirical sink phenomenon as a band-aid). |
| **L8 Hamiltonian wells** | The well structure *is* the depth-localized basin that sink literature describes empirically. SCBE has the substrate to formalize what sink papers report. |
| **L9-10 spectral/spin coherence** | Coherence across depth is the FFT-based diagnostic. Csordas 2505.13898 (depth efficiency) measures the same thing without the spectral framing. |
| **L12 harmonic wall** `H = 1/(1+φ·d_H + 2·pd)` | The wall is a *single-pass scoring*. By design it is shallow — the depth lives in d_H computation upstream. This is a deliberate shallow-attention-at-the-decision-boundary choice. |
| **MAHSS spec** | HRR-bound role vectors composed via Möbius fold = attention without per-layer redundancy. The MAHSS framing is closer to *one wide attention layer over composed roles* (Brown 2210.00640) than to per-layer dense attention. The depth lives in the role hierarchy, not the layer stack. |

---

## 6. What this means for the v6f-class direction

v6f is fine-tuning Qwen2.5-7B — fully-dense, full-depth attention. The constrained-decoding shim sits *outside* the model: prefix injected at decode time, model continues. This is a **shallow-at-the-boundary** choice — the discipline is enforced at one point, not at every layer.

That maps onto the literature: the most cost-effective place to enforce structure is at the depth boundary (decode), not via per-layer fine-tuning (which v6c through v6e-bumped showed produces marker habits, not internalized discipline).

The MAHSS direction takes this further — **compose K attention views via HRR + Möbius into one geometric query**, replacing per-layer redundant attention with a single geometrically-correct fold. The literature trend (Native Hybrid Attention, Learning When Not to Attend Globally) is converging on the same answer empirically; SCBE has the geometric substrate to do it principled.

---

## 7. Open questions

1. **Is the harmonic wall layer-conditional?** Currently `H(d, pd)` is a single scalar. Could a per-layer `H_l(d_l, pd_l)` give a depth-resolved safety profile, identifying which layer the adversarial drift occurs at?
2. **Möbius isometry depth budget**. Each L7 transform is a single isometric step. How many can compose before numerical drift dominates? This bounds SCBE's effective "attention depth."
3. **Sink-as-well duality**. If sinks are empirically what the L8 well structure imposes by construction, can we read attention sinks in a base model as evidence of which layers the model has discovered well-like behavior at? Diagnostic, pre-fine-tune.
4. **Sparse attention + hyperbolic kernel**. NSA-class sparse attention has not been combined with hyperbolic distance kernels. Open patent surface.

---

## 8. Citation index (HF papers + arXiv IDs)

**Shallow / single-layer**: 2311.10642 (Bozic), 2210.00640 (Brown).
**Dynamic depth / layer skipping**: 2410.13184 (Router-Tuning), 2506.21103 (Lawson), 2505.13898 (Csordas), 2303.07624 (I3D).
**Attention sinks**: 2604.10098 (survey), 2504.02732 (Barbero), 2512.22213 (Wong), 2508.02546 (Ruscio).
**Native sparse**: 2502.11089 (NSA, DeepSeek), 2508.18224 (Flash NSA), 2510.13602 (NOSA), 2511.20102 (SSA, SubQuadratic), 2603.28458 (HISA).
**Hybrid local-global**: 2510.07019 (Native Hybrid), 2512.22562 (Learning When Not to Attend Globally), 2511.00819 (NSA Local-Global Alternating).
**Adjacent**: 2501.17900 + 2505.16333 + 2501.17486 (DIFF Transformer), 2502.12170 (MUDDFormer), 2503.10622 (Transformers w/o Normalization), 2502.17206 (Neural Attention).
**Survey**: 2507.19595 (Efficient Attention Mechanisms for LLMs).
