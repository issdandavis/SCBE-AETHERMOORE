---
title: "The 14-Layer Pipeline: How We Score Every AI Request in Under 8 Milliseconds"
slug: the-14-layer-pipeline-under-8-milliseconds
date: 2026-05-23
author: Issac Daniel Davis
tags: [pipeline, performance, ai-safety, scbe, architecture, hyperbolic-geometry]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# The 14-Layer Pipeline: How We Score Every AI Request in Under 8 Milliseconds

The number people ask about first is the latency. Under 8ms for the full governance pipeline, on commodity hardware. No GPU. No inference call. No model in the loop.

Here's why that's possible, and what the 14 layers are actually doing.

---

## The key design constraint

Most AI safety classifiers make a model call. You pass the input to a classifier model, it returns a score, you act on the score. The latency is bounded by inference time — typically 50–500ms depending on model size and hardware.

SCBE doesn't do that. Every layer of the pipeline is deterministic geometry. Same input, same output, every time. The computation is matrix operations, hash functions, and fixed-point arithmetic — not autoregressive generation.

The tradeoff: you lose the generalization power of a fine-tuned classifier. You gain: speed, auditability, reproducibility, and the ability to run the pipeline in CI as part of your test suite. You can diff outputs. You can set thresholds and know they'll hold. A change in the underlying LLM doesn't invalidate the governance layer because the governance layer doesn't depend on the LLM.

---

## What the 14 layers do

**Layers 1–2: Complex context ingestion and realification**

The raw input token sequence gets lifted into complex-valued representation and then realified — converted to real-valued vectors while preserving the information content. This is where the Sacred Tongue projection happens: each token maps to a position in the six-dimensional coordinate space (one dimension per tongue), and the imaginary components capture the phase relationships between tongue activations.

**Layers 3–4: Weighted transform and Poincaré embedding**

The real-valued vectors get multiplied by the golden-ratio tongue weights (KO×1.00, Avali×1.618, Runethic×2.618, Cassisivadan×4.236, Umbroth×6.854, Draumric×11.090) and then projected into the Poincaré ball via the exponential map. After this step, every input is a point inside the unit ball in six-dimensional hyperbolic space.

**Layer 5: Hyperbolic distance**

The core metric:

```
d_H(u, v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
```

The trusted semantic center is near the origin. Legitimate inputs cluster near the center. The denominator terms `(1-‖u‖²)` and `(1-‖v‖²)` approach zero as inputs approach the boundary, making distance grow exponentially with drift.

**Layers 6–7: Breathing transform and Möbius phase**

The breathing transform applies oscillatory modulation that adds temporal dynamics — a pulse that modulates security state over conversation history. The Möbius phase applies isometric transformations that preserve the hyperbolic metric while rotating the security perspective. These layers make the pipeline responsive to patterns that emerge across multiple turns, not just within a single input.

**Layer 8: Multi-well Hamiltonian (realms)**

The energy landscape. Four stable states — ALLOW, QUARANTINE, ESCALATE, DENY — modeled as potential wells. The Hamiltonian governs which well the current system state is attracted to based on the accumulated geometric signal from Layers 1–7.

**Layers 9–10: Spectral and spin coherence**

FFT-based frequency analysis of the security signal detects anomalous spectral patterns. Spin coherence measures alignment and decoherence of security state across the conversation. These are the temporal layers — they accumulate signal over history rather than scoring each input in isolation.

**Layer 11: Triadic temporal distance**

Temporal intent at three scales: immediate (last turn), medium (last 10 turns), long-term (full session). Inputs that behave consistently over time are different from inputs that are adversarial in isolated turns but blend in otherwise. The triadic distance feeds into Layer 12 as the `pd` (phase deviation) term.

**Layer 12: Harmonic wall**

```
H(d, pd) = 1 / (1 + d_H + 2·pd)
```

The canonical safety score. Hyperbolic distance plus twice the temporal phase deviation, inverted. Score in (0, 1]. The score feeds into Layer 13 as the governance decision input.

**Layer 13: Risk decision**

Score-to-tier mapping: ALLOW / QUARANTINE / ESCALATE / DENY. This is where the governance receipt gets stamped. The receipt is deterministic — same input, same score, same tier, same audit trail entry.

**Layer 14: Audio axis (FFT telemetry)**

The final layer encodes governance decisions and system state as phase-modulated audio waveforms for monitoring and audit signaling. This is the telemetry surface — it closes the pipeline loop and lets external systems observe the governance state without polling the decision layer directly.

---

## Why it's fast

The pipeline has no branch on a learned model's output. Every computation is fixed-point: hash, multiply, project, arcosh, compare. The Poincaré projection is O(n) in the input length. The FFT in Layers 9–10 is O(n log n). The rest is O(n) or constant.

On commodity hardware (x86_64, no GPU, single core), full pipeline latency for a 512-token input is under 8ms. For a 128-token input, under 3ms.

That's fast enough to run inline — not as a pre-filter, not as an async check, but as a synchronous gate on every request.

---

## The benchmark

Against 91 adversarial attacks across 10 attack classes: F1 of 0.813, detection rate 74.2%. The 25.8% that pass the geometry layer hit the temporal coherence layers — most of those are low-and-slow attacks that need multi-turn accumulation to detect.

The full pipeline is in `src/harmonic/pipeline14.ts`. The Python reference implementation is in `src/symphonic_cipher/`. Tests at `tests/harmonic/`. All MIT OR Apache-2.0.

[issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)
