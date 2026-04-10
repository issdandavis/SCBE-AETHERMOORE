#!/usr/bin/env python3
"""Generate 15 SFT training pairs for Kimi Attention Residuals mapped to SCBE architecture.

Covers:
  1. PreNorm dilution & fixed residual failure (3 records)
  2. Depth-wise softmax attention replacing fixed accumulation (3 records)
  3. Block AttnRes for practical scaling (2 records)
  4. SCBE 14-layer to 6 AttnRes blocks aligned with axiom groups (3 records)
  5. Dual bounding: AttnRes soft filter + harmonic wall hard guarantee (2 records)
  6. Tongue-conditioned pseudo-queries for depth attention (2 records)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path so we can import from training/
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from training.auto_marker import orient_record, write_oriented_jsonl

OUTPUT = REPO_ROOT / "training-data" / "sft" / "attention_residuals_sft.jsonl"


def build_records():
    records = []

    # =========================================================================
    # Category 1: PreNorm dilution & fixed residual failure (3 records)
    # =========================================================================

    records.append(orient_record(
        instruction=(
            "What is PreNorm dilution in deep transformers, and why does it become "
            "a problem as the number of layers increases?"
        ),
        response=(
            "PreNorm dilution is a failure mode in deep transformers where the standard "
            "residual connection x_{l+1} = x_l + F_l(x_l) causes the contribution of "
            "each new layer F_l to shrink relative to the accumulated residual stream. "
            "After L layers, the residual stream magnitude grows roughly as O(L) while "
            "each new contribution is O(1), so the effective weight of layer l's output "
            "decays as ~1/L.\n\n"
            "Mathematically, after normalization the effective representation becomes:\n\n"
            "  x_L = x_0 + sum_{l=0}^{L-1} F_l(Norm(x_l))\n\n"
            "As L grows, ||x_l|| increases but ||F_l(Norm(x_l))|| stays bounded, so "
            "later layers contribute vanishingly small perturbations. This is especially "
            "damaging in SCBE's 14-layer pipeline where the final layers (L11 causality, "
            "L12 harmonic wall, L13 risk decision) carry the most critical governance "
            "semantics. If their signal is diluted by 1/14, the harmonic wall "
            "H(d*,R) = R^((phi*d*)^2) cannot reliably enforce its exponential "
            "cost boundary because the input features driving d_H and pd are attenuated."
        ),
        source="attention_residuals/concept_1",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "Why do fixed-weight residual connections fail at depth? Explain the "
            "mathematical mechanism behind signal dilution in a 14-layer security pipeline."
        ),
        response=(
            "Fixed-weight residual connections use a constant mixing coefficient "
            "(typically 1.0) at every layer: x_{l+1} = x_l + F_l(x_l). The problem is "
            "twofold:\n\n"
            "1. **Uniform weighting ignores layer importance**: In SCBE's 14-layer "
            "pipeline, Layer 5 (hyperbolic distance d_H = arcosh(1 + 2||u-v||^2 / "
            "((1-||u||^2)(1-||v||^2)))) and Layer 12 (harmonic wall) carry fundamentally "
            "different semantic weight than, say, Layer 1 (complex context). Fixed "
            "residuals treat them identically.\n\n"
            "2. **Accumulation dominance**: After passing through layers L1 through L14, "
            "the residual stream is dominated by the sum of all previous representations. "
            "The signal-to-noise ratio for any individual layer's contribution is:\n\n"
            "  SNR_l = ||F_l|| / ||sum_{k=0}^{l-1} F_k + x_0|| ~ 1/l\n\n"
            "For L14 in SCBE, this means the risk decision layer (L13: ALLOW/QUARANTINE/"
            "ESCALATE/DENY) has an SNR of approximately 1/13, meaning its governance "
            "output is buried under 13 layers of accumulated representations. The five "
            "quantum axioms (Unitarity, Locality, Causality, Symmetry, Composition) each "
            "operate at specific layer subsets, and fixed residuals cannot route axiom-"
            "specific signal preferentially."
        ),
        source="attention_residuals/concept_2",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "Can you give a concrete numerical example showing how PreNorm dilution "
            "degrades the harmonic wall score in SCBE?"
        ),
        response=(
            "Consider SCBE's harmonic wall at Layer 12:\n\n"
            "  H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)\n\n"
            "where phi = 1.618..., d_H is hyperbolic distance from Layer 5, and pd is "
            "the adversarial penalty. Suppose the true feature values from L5 and L12 "
            "yield d_H = 3.0 and pd = 0.5, giving:\n\n"
            "  H_true = 1 / (1 + 1.618 * 3.0 + 2 * 0.5)\n"
            "         = 1 / (1 + 4.854 + 1.0)\n"
            "         = 1 / 6.854\n"
            "         = 0.146\n\n"
            "This correctly triggers QUARANTINE (H < 0.2). Now with PreNorm dilution "
            "after 14 layers, the effective features are scaled by ~1/14:\n\n"
            "  d_H_diluted = 3.0 / 14 = 0.214\n"
            "  pd_diluted  = 0.5 / 14 = 0.036\n"
            "  H_diluted   = 1 / (1 + 1.618 * 0.214 + 2 * 0.036)\n"
            "              = 1 / (1 + 0.346 + 0.071)\n"
            "              = 1 / 1.417\n"
            "              = 0.706\n\n"
            "The diluted score is 0.706 -- well in the ALLOW range -- so an adversarial "
            "input that should be quarantined is instead allowed through. This is "
            "exactly the safety failure that depth-adaptive residuals must prevent."
        ),
        source="attention_residuals/concept_3",
        source_type="attention_residuals_research",
    ))

    # =========================================================================
    # Category 2: Depth-wise softmax attention replacing fixed accumulation (3)
    # =========================================================================

    records.append(orient_record(
        instruction=(
            "How does depth-wise softmax attention (Attention Residuals / AttnRes) "
            "replace fixed residual accumulation in deep networks?"
        ),
        response=(
            "Attention Residuals (AttnRes) replace the fixed identity shortcut with a "
            "learned, depth-wise attention mechanism. Instead of:\n\n"
            "  x_{l+1} = x_l + F_l(x_l)   [fixed residual]\n\n"
            "AttnRes computes:\n\n"
            "  x_{l+1} = sum_{k=0}^{l} alpha_{l,k} * h_k\n\n"
            "where h_k is the output of layer k, and alpha_{l,k} are softmax-normalized "
            "attention weights over all preceding layer outputs:\n\n"
            "  alpha_{l,k} = exp(score(q_l, h_k)) / sum_{j=0}^{l} exp(score(q_l, h_j))\n\n"
            "The query q_l is derived from the current layer's representation, and the "
            "score function is typically a dot-product or learned bilinear form. This "
            "means each layer can selectively attend to ANY previous layer's output, "
            "not just the immediately preceding one.\n\n"
            "Key benefits:\n"
            "- Layer l can directly access layer 0's features without dilution\n"
            "- The softmax normalization ensures weights sum to 1, preventing magnitude "
            "explosion\n"
            "- Important layers naturally receive higher attention weight\n"
            "- The network learns which depth-wise connections matter during training"
        ),
        source="attention_residuals/concept_4",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "Derive the gradient flow advantage of AttnRes over standard residuals "
            "in a deep network."
        ),
        response=(
            "In standard residuals, the gradient of the loss L with respect to layer l's "
            "parameters theta_l flows through:\n\n"
            "  dL/dtheta_l = dL/dx_L * prod_{k=l}^{L-1} (I + dF_k/dx_k) * dF_l/dtheta_l\n\n"
            "The product of (I + dF_k/dx_k) terms can lead to vanishing or exploding "
            "gradients depending on the spectral radius of dF_k/dx_k.\n\n"
            "With AttnRes, layer L's output depends on all previous layers via attention:\n\n"
            "  x_L = sum_{k=0}^{L-1} alpha_{L-1,k} * h_k\n\n"
            "So the gradient becomes:\n\n"
            "  dL/dtheta_l = dL/dx_L * alpha_{L-1,l} * dh_l/dtheta_l + [indirect terms]\n\n"
            "The critical difference: the attention weight alpha_{L-1,l} provides a "
            "DIRECT gradient path from the loss to layer l, bypassing all intermediate "
            "layers. This is analogous to how cross-attention in transformers allows "
            "direct encoder-decoder gradient flow.\n\n"
            "For SCBE's 14-layer pipeline, this means the gradient signal for Layer 5 "
            "(hyperbolic embedding) can be directly scaled by how much Layer 13 (risk "
            "decision) attends to it. If the Unitarity axiom (layers 2, 4, 7) needs "
            "strengthening, the attention weights alpha_{13, {2,4,7}} increase, "
            "automatically amplifying gradient flow to those specific layers."
        ),
        source="attention_residuals/concept_5",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "How does the softmax normalization in depth-wise attention prevent "
            "the magnitude explosion that occurs with additive residual streams?"
        ),
        response=(
            "With additive residuals, the magnitude of the representation grows "
            "approximately linearly: ||x_L|| ~ O(L * ||F||). For SCBE's 14 layers, "
            "this means ~14x the base feature magnitude, which distorts the Poincare "
            "ball embedding at Layer 4 (which requires ||x|| < 1).\n\n"
            "AttnRes prevents this through softmax normalization:\n\n"
            "  x_{l+1} = sum_{k=0}^{l} alpha_{l,k} * h_k\n"
            "  where sum_{k} alpha_{l,k} = 1, alpha_{l,k} >= 0\n\n"
            "Since the output is a convex combination of bounded layer representations, "
            "we get:\n\n"
            "  ||x_{l+1}|| <= max_{k} ||h_k||\n\n"
            "This is a norm-preserving property -- exactly the Unitarity axiom (A1) that "
            "SCBE enforces at layers 2, 4, and 7. The AttnRes mechanism thus provides a "
            "natural algebraic guarantee for unitarity without requiring explicit norm "
            "clamping.\n\n"
            "Furthermore, for the Poincare ball model at Layer 4, the convex combination "
            "stays within the ball if all h_k are in the ball, because the Poincare ball "
            "is a convex subset of R^n. This means AttnRes is geometrically compatible "
            "with hyperbolic embeddings, unlike additive residuals which can project "
            "points outside the unit ball."
        ),
        source="attention_residuals/concept_6",
        source_type="attention_residuals_research",
    ))

    # =========================================================================
    # Category 3: Block AttnRes for practical scaling (2 records)
    # =========================================================================

    records.append(orient_record(
        instruction=(
            "What is Block AttnRes and why is it necessary for scaling depth-wise "
            "attention to networks with many layers?"
        ),
        response=(
            "Full AttnRes computes attention over all preceding layers, giving O(L^2) "
            "memory and compute cost for L layers. Block AttnRes partitions the L layers "
            "into B blocks of size L/B each, and restricts depth attention to within "
            "each block plus a single summary vector from preceding blocks.\n\n"
            "Formally, for block b containing layers {l_{b,1}, ..., l_{b,S}} where "
            "S = L/B:\n\n"
            "  x_{l+1} = sum_{k in block(b)} alpha_{l,k} * h_k + alpha_{l,prev} * s_{b-1}\n\n"
            "where s_{b-1} is the summary of all previous blocks (typically the final "
            "output of block b-1). The cost drops from O(L^2) to O(L * S + B) = O(L^2/B).\n\n"
            "For SCBE's 14 layers with B=6 blocks (one per axiom group), each block "
            "contains 2-3 layers. The within-block attention cost is negligible (at most "
            "4 layers attending to each other), and the cross-block summary adds only 5 "
            "extra attention targets. Total: ~14 * 8 = 112 attention computations vs. "
            "14 * 14 = 196 for full AttnRes. More importantly, the block boundaries "
            "align with semantic boundaries in the pipeline."
        ),
        source="attention_residuals/concept_7",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "How do you choose the block boundaries in Block AttnRes? What principles "
            "guide the partitioning?"
        ),
        response=(
            "Block boundaries should align with semantic or functional stage transitions. "
            "Three principles guide the partitioning:\n\n"
            "1. **Functional coherence**: Layers within a block should collaborate on a "
            "shared subtask. In Kimi's original work, blocks correspond to attention "
            "heads working on similar positional ranges.\n\n"
            "2. **Information bottleneck**: The cross-block summary vector acts as an "
            "information bottleneck, compressing the full history into a fixed-size "
            "representation. Block boundaries should be placed where the representation "
            "undergoes a natural dimensionality reduction or domain change.\n\n"
            "3. **Axiom alignment** (SCBE-specific): The five quantum axioms each govern "
            "specific layer subsets. Blocks should respect axiom boundaries so that "
            "within-block attention serves intra-axiom coherence while cross-block "
            "summaries handle inter-axiom communication.\n\n"
            "Bad partitioning (e.g., splitting Layer 5 hyperbolic distance from Layer 4 "
            "Poincare embedding into different blocks) forces the cross-block summary to "
            "compress the full embedding, losing the geometric precision needed for "
            "d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2))). Good partitioning "
            "keeps L4-L5 together so the raw Poincare vectors are available for exact "
            "distance computation."
        ),
        source="attention_residuals/concept_8",
        source_type="attention_residuals_research",
    ))

    # =========================================================================
    # Category 4: SCBE 14 layers to 6 AttnRes blocks (3 records)
    # =========================================================================

    records.append(orient_record(
        instruction=(
            "How would you map SCBE's 14-layer pipeline into 6 AttnRes blocks "
            "aligned with the 5 quantum axiom groups?"
        ),
        response=(
            "The mapping uses 6 blocks -- one per axiom plus a dedicated governance "
            "block. Each block groups layers that share an axiom responsibility:\n\n"
            "Block 0 (Composition + Init): L1, L14\n"
            "  - Axiom 5: Pipeline integrity\n"
            "  - L1 = complex context, L14 = audio axis (FFT telemetry)\n"
            "  - Circular: output feeds back to input validation\n\n"
            "Block 1 (Unitarity): L2, L4, L7\n"
            "  - Axiom 1: Norm preservation\n"
            "  - L2 = realification, L4 = Poincare embedding, L7 = Mobius phase\n"
            "  - All three enforce ||x|| <= 1 in their respective spaces\n\n"
            "Block 2 (Locality): L3, L8\n"
            "  - Axiom 2: Spatial bounds\n"
            "  - L3 = weighted transform, L8 = multi-well Hamiltonian CFI\n"
            "  - Both enforce neighborhood constraints\n\n"
            "Block 3 (Symmetry): L5, L9, L10, L12\n"
            "  - Axiom 4: Gauge invariance\n"
            "  - L5 = hyperbolic distance, L9-10 = spectral/spin coherence, "
            "L12 = harmonic wall\n"
            "  - The harmonic wall H(d*,R) = R^((phi*d*)^2) is gauge-invariant "
            "under tongue rotations\n\n"
            "Block 4 (Causality): L6, L11, L13\n"
            "  - Axiom 3: Time-ordering\n"
            "  - L6 = breathing transform, L11 = triadic temporal distance, "
            "L13 = risk decision\n"
            "  - Causal ordering: sense -> evaluate -> decide\n\n"
            "Block 5 (Decision): L13 output head\n"
            "  - Final governance output: ALLOW/QUARANTINE/ESCALATE/DENY\n"
            "  - Attends to all 5 block summaries for the final verdict\n\n"
            "Note: L13 appears in both Block 4 and Block 5 via a shared reference -- "
            "it participates in causal reasoning but its output is the decision head."
        ),
        source="attention_residuals/concept_9",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "What are the cross-block summary vectors in the SCBE 6-block AttnRes "
            "configuration, and how do they flow between axiom groups?"
        ),
        response=(
            "Each block produces a summary vector s_b that compresses its internal "
            "state for downstream blocks. The summary is the attention-weighted "
            "combination of the block's layer outputs:\n\n"
            "  s_b = sum_{l in block(b)} beta_{b,l} * h_l\n\n"
            "where beta_{b,l} are learned summary weights (separate from the within-"
            "block attention weights alpha).\n\n"
            "The cross-block flow for SCBE's 6 blocks:\n\n"
            "  s_0 (Composition) -> Block 1 (Unitarity)\n"
            "    Carries: initial context embedding, pipeline integrity stamp\n\n"
            "  s_1 (Unitarity) -> Block 2 (Locality)\n"
            "    Carries: norm-preserved Poincare embedding, phase coherence\n\n"
            "  s_2 (Locality) -> Block 3 (Symmetry)\n"
            "    Carries: spatially-bounded neighborhoods, Hamiltonian well indices\n\n"
            "  s_3 (Symmetry) -> Block 4 (Causality)\n"
            "    Carries: gauge-invariant features, harmonic score H, spectral peaks\n\n"
            "  s_4 (Causality) -> Block 5 (Decision)\n"
            "    Carries: temporal ordering, triadic distance, causal consistency flag\n\n"
            "  s_5 (Decision) -> s_0 (Composition) [feedback loop]\n"
            "    Carries: final ALLOW/DENY/QUARANTINE/ESCALATE decision for next cycle\n\n"
            "The circular flow s_5 -> s_0 is critical: it implements the Composition "
            "axiom (A5), ensuring the pipeline's output is consistent with its input "
            "when run iteratively. Each summary is a 21D vector matching SCBE's "
            "canonical state dimension."
        ),
        source="attention_residuals/concept_10",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "How does axiom-aligned block partitioning improve training efficiency "
            "compared to uniform block sizes in SCBE's pipeline?"
        ),
        response=(
            "Uniform partitioning (e.g., 14 layers / 6 blocks ~ 2-3 layers per block) "
            "ignores the functional coupling between layers. Axiom-aligned partitioning "
            "provides three concrete training advantages:\n\n"
            "1. **Gradient locality**: Layers within the same axiom group need correlated "
            "parameter updates. For example, the Unitarity block (L2, L4, L7) must "
            "jointly maintain ||x|| <= 1. With axiom-aligned blocks, the within-block "
            "attention weights alpha_{l,k} directly mediate gradient flow between these "
            "co-dependent layers, enabling faster co-adaptation.\n\n"
            "2. **Sparse inter-axiom coupling**: The five axioms interact through "
            "well-defined interfaces (e.g., Unitarity feeds norm-bounded vectors to "
            "Locality, which feeds neighborhood bounds to Symmetry). The cross-block "
            "summaries learn to compress exactly these interfaces, rather than arbitrary "
            "intermediate states. Empirically, this reduces the effective rank of the "
            "cross-block summary from 21D to ~5-8D, saving compute.\n\n"
            "3. **Interpretable attention patterns**: The depth attention weights "
            "alpha_{l,k} within each block directly show which axiom sub-layers are "
            "most active for a given input. For SCBE governance auditing, this provides "
            "a per-axiom importance score: if the Symmetry block's harmonic wall layer "
            "(L12) receives attention weight > 0.6, the system is relying heavily on "
            "exponential cost scaling for this input. This transparency is required by "
            "the governance pipeline and is impossible with fixed residuals."
        ),
        source="attention_residuals/concept_11",
        source_type="attention_residuals_research",
    ))

    # =========================================================================
    # Category 5: Dual bounding: AttnRes soft + harmonic wall hard (2 records)
    # =========================================================================

    records.append(orient_record(
        instruction=(
            "Explain the dual bounding mechanism where AttnRes provides a soft filter "
            "and the harmonic wall provides a hard guarantee in SCBE."
        ),
        response=(
            "SCBE uses two complementary bounding mechanisms:\n\n"
            "**Soft filter (AttnRes)**: The depth-wise attention weights alpha_{l,k} "
            "act as a learned soft gate on information flow. If a layer's output is "
            "uninformative or adversarially corrupted, its attention weight drops toward "
            "zero via softmax competition. This is a STATISTICAL guarantee -- it works "
            "for the distribution of inputs seen during training, but an adversary could "
            "potentially craft inputs that fool the attention mechanism.\n\n"
            "  Soft bound: alpha_{l,k} -> 0 for corrupted layer k\n"
            "  Confidence: probabilistic (depends on training distribution)\n\n"
            "**Hard guarantee (Harmonic wall)**: The harmonic wall at Layer 12 provides "
            "a MATHEMATICAL guarantee via hyperbolic geometry:\n\n"
            "  H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)\n\n"
            "where d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2))). This "
            "score is bounded in (0, 1] and monotonically decreasing in both d_H and "
            "pd. No matter what the attention weights do, the harmonic wall score "
            "ALWAYS reflects the true hyperbolic distance. An adversary must make d_H "
            "small (i.e., embed close to the safe centroid in hyperbolic space) to get "
            "a high H score, which is exponentially expensive.\n\n"
            "  Hard bound: H(d, pd) < threshold => DENY\n"
            "  Confidence: mathematical (geometry-enforced)\n\n"
            "The dual system works as: AttnRes filters noise/irrelevant signal to "
            "improve the INPUT quality to the harmonic wall, while the harmonic wall "
            "provides the final UNFORGEABLE safety decision regardless of AttnRes "
            "behavior. Defense in depth: soft learning + hard math."
        ),
        source="attention_residuals/concept_12",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "What happens when AttnRes and the harmonic wall disagree? How does "
            "SCBE resolve conflicts between soft and hard safety bounds?"
        ),
        response=(
            "There are four possible states in the dual bounding system:\n\n"
            "1. **AttnRes PASS + H PASS** (both agree safe):\n"
            "   - Attention weights route signal normally, H > threshold\n"
            "   - Decision: ALLOW\n"
            "   - Common case for benign inputs\n\n"
            "2. **AttnRes FAIL + H FAIL** (both agree unsafe):\n"
            "   - Attention weights suppress corrupted layers, H < threshold\n"
            "   - Decision: DENY\n"
            "   - Common case for obvious attacks\n\n"
            "3. **AttnRes PASS + H FAIL** (soft says OK, hard says NO):\n"
            "   - The adversary fooled the attention mechanism but not the geometry\n"
            "   - Decision: DENY (hard bound always wins)\n"
            "   - This is the critical safety case -- the harmonic wall catches what "
            "AttnRes misses\n"
            "   - The attention weights that passed are logged as training signal for "
            "improving the soft filter\n\n"
            "4. **AttnRes FAIL + H PASS** (soft says NO, hard says OK):\n"
            "   - AttnRes suppressed a layer that the harmonic wall considers safe\n"
            "   - Decision: QUARANTINE (investigate)\n"
            "   - This suggests the attention weights are over-conservative or the "
            "input has unusual but non-adversarial structure\n"
            "   - The risk tier from L13 determines if this escalates to human review\n\n"
            "The key principle: the harmonic wall H(d*,R) = R^((phi*d*)^2) NEVER "
            "yields to AttnRes. It is the mathematical floor. AttnRes can only IMPROVE "
            "signal quality above this floor, never lower the bar. This asymmetry is "
            "essential for AI safety: learned components can help but cannot override "
            "geometric guarantees."
        ),
        source="attention_residuals/concept_13",
        source_type="attention_residuals_research",
    ))

    # =========================================================================
    # Category 6: Tongue-conditioned pseudo-queries (2 records)
    # =========================================================================

    records.append(orient_record(
        instruction=(
            "What are tongue-conditioned pseudo-queries in the context of SCBE's "
            "depth-wise attention mechanism?"
        ),
        response=(
            "In standard AttnRes, the query vector q_l at layer l is derived solely "
            "from the current layer's representation. Tongue-conditioned pseudo-queries "
            "augment this with SCBE's Sacred Tongue weight vector, creating queries that "
            "are biased by the linguistic/semantic domain of the input.\n\n"
            "The 6 Sacred Tongues have phi-scaled weights:\n"
            "  KO (Intent)      = 1.000\n"
            "  AV (Wisdom)      = 1.618  (phi)\n"
            "  RU (Governance)  = 2.618  (phi^2)\n"
            "  CA (Compute)     = 4.236  (phi^3)\n"
            "  UM (Security)    = 6.854  (phi^4)\n"
            "  DR (Structure)   = 11.090 (phi^5)\n\n"
            "The tongue profile t = [t_KO, t_AV, t_RU, t_CA, t_UM, t_DR] is computed "
            "for each input, where t_i in [0,1] is the activation of tongue i. The "
            "pseudo-query is:\n\n"
            "  q_l = W_q * h_l + W_t * (t . w_phi)\n\n"
            "where w_phi = [1, phi, phi^2, phi^3, phi^4, phi^5] and . is element-wise "
            "multiplication. The term W_t * (t . w_phi) adds a domain-specific bias to "
            "the attention query.\n\n"
            "Effect: For a security-heavy input (high t_UM), the pseudo-query biases "
            "depth attention toward layers in the Unitarity and Symmetry blocks where "
            "norm preservation and gauge invariance are critical. For a governance query "
            "(high t_RU), attention shifts toward the Causality block (L6, L11, L13) "
            "where temporal ordering and risk decisions dominate."
        ),
        source="attention_residuals/concept_14",
        source_type="attention_residuals_research",
    ))

    records.append(orient_record(
        instruction=(
            "Derive the attention score modification when using phi-weighted tongue "
            "vectors as pseudo-query bias, and show how this creates tongue-specific "
            "depth attention patterns."
        ),
        response=(
            "Start with the standard depth attention score between layer l (query) "
            "and layer k (key):\n\n"
            "  score_std(l, k) = (W_q * h_l)^T * (W_k * h_k) / sqrt(d)\n\n"
            "Adding the tongue-conditioned pseudo-query bias:\n\n"
            "  score(l, k) = score_std(l, k) + (W_t * (t . w_phi))^T * (W_k * h_k) / sqrt(d)\n\n"
            "Let T = W_t * (t . w_phi). The attention weights become:\n\n"
            "  alpha_{l,k} = softmax_k(score_std(l,k) + T^T * W_k * h_k / sqrt(d))\n\n"
            "The bias term T^T * W_k * h_k / sqrt(d) is input-independent for the query "
            "position -- it depends only on the tongue profile and the key layer's "
            "representation. This creates a STATIC PRIOR over depth attention that is "
            "then modulated by the dynamic score_std term.\n\n"
            "Example tongue-specific patterns:\n\n"
            "For t = [0, 0, 0, 0, 1, 0] (pure UM/Security, weight = phi^4 = 6.854):\n"
            "  - Heavy bias toward Block 1 (Unitarity: L2, L4, L7) for norm checks\n"
            "  - Heavy bias toward Block 3 (Symmetry: L5, L9, L10, L12) for the "
            "harmonic wall\n"
            "  - The phi^4 scaling makes this bias ~7x stronger than a KO (Intent) query\n\n"
            "For t = [1, 0, 0, 0, 0, 0] (pure KO/Intent, weight = 1.0):\n"
            "  - Mild bias toward Block 0 (Composition) and Block 4 (Causality)\n"
            "  - Intent queries need the full pipeline but with light weighting\n"
            "  - The phi^0 = 1 scaling means this barely perturbs the learned attention\n\n"
            "The phi scaling is essential: higher tongues (UM, DR) represent more "
            "critical security/structural concerns and should more strongly override "
            "learned attention patterns. Lower tongues (KO, AV) represent routine "
            "queries where the learned attention should dominate. This mirrors the "
            "SCBE design principle that adversarial intent costs exponentially more "
            "-- the phi weights enforce this at the attention routing level."
        ),
        source="attention_residuals/concept_15",
        source_type="attention_residuals_research",
    ))

    return records


def main():
    records = build_records()
    count = write_oriented_jsonl(records, OUTPUT)
    print(f"Wrote {count} records to {OUTPUT}")


if __name__ == "__main__":
    main()
