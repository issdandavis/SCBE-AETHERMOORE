---
title: "How 6 Named Dimensions Beat 411K-Download AI Security Models"
tags: [ai-safety, prompt-injection, security, open-source]
published: true
---

# How 6 Named Dimensions Beat 411K-Download AI Security Models

Most AI security systems throw thousands of unnamed neural dimensions at prompt injection. We tried something different: **6 intentionally designed dimensions**, each mapping to an academic knowledge domain. The result: 91/91 attacks blocked with 0 false positives, beating ProtectAI's DeBERTa v2 (which caught 62/91).

## The Problem With Unnamed Dimensions

Standard prompt injection detectors like ProtectAI's DeBERTa train a classifier on thousands of features nobody can name. Dimension 847 might encode "formality" or "technical density" — nobody knows. When it fails, you can't debug it because you can't interpret what it saw.

## Our Approach: Sacred Tongues

We mapped every input to 6 **named** dimensions, each representing an academic knowledge domain:

| Tongue | Domain | What It Reads |
|--------|--------|---------------|
| KO | Humanities | Identity, narrative, intent |
| AV | Social Sciences | Temporal dynamics, diplomacy |
| RU | Mathematics | Binding, formal structures |
| CA | Engineering | Verification, building |
| UM | Creative Arts | Shadow, veiling, intuition |
| DR | Physical Sciences | Structure, power, material |

Each word in the input activates one or more domains. "override" lights up Engineering (CA=0.8). "quantum" lights up Physics (DR=0.8) and Math (RU=0.5). The aggregate across all words produces a 6D "tongue coordinate."

## The Benchmark

We tested against the real ProtectAI DeBERTa v2 model (411K downloads on HuggingFace), loaded and run on our corpus of 91 adversarial attacks across 10 categories:

```
System                          Blocked    ASR
No Protection                     0/91   100.0%
ProtectAI DeBERTa v2             62/91    31.9%
SCBE Semantic + Remainder        91/91     0.0%
```

Where SCBE specifically dominated:

- **Spin drift** (gradual escalation): ProtectAI 2/10, SCBE 10/10
- **Tool exfiltration**: ProtectAI 1/10, SCBE 10/10
- **Adaptive sequences**: ProtectAI 5/11, SCBE 11/11

## The Discovery: Null Space Signatures

The most interesting finding wasn't what the tongues detected — it was what they **didn't** detect. Attack types leave characteristic "holes" in their tongue profiles:

```
Encoding attacks:     __#___  (only Math active)
Tool exfiltration:    __##__  (only Math + Engineering)
Spin drift:           ####__  (Security + Physics absent)
```

The absence pattern is a fingerprint. Encoding attacks have no meaning beyond mathematical transformation, so only RU (Mathematics) activates. Tool exfiltration is pure engineering, so only RU + CA light up. The dimensions that stay dark tell you what the text ISN'T — and that's diagnostic.

## How It Works

The system uses a "triple-weight remainder" — three different weighting methods process the same input, and the **disagreement** between them is the signal:

1. Raw phi-weighted coordinates
2. Moon counter-weighted (each weight reduced by 1/phi)
3. Foam-dampened (boundary smoothing between tongue regions)

If all three agree: fast path, allow. If they disagree: the remainder score triggers deeper inspection. This catches the 13 attacks that the primary detection misses, without adding false positives.

## Reproducible

```bash
git clone https://github.com/issdandavis/SCBE-AETHERMOORE
pip install numpy transformers
python scripts/benchmark/spectral_sweep_benchmark.py
```

The benchmark loads the real ProtectAI model from HuggingFace and runs head-to-head.

## What This Means

You don't need 1,536 unnamed dimensions to detect prompt injection. You need 6 dimensions that you understand. When something goes wrong, you can point to exactly which domain is firing (or not firing) and why.

The tradeoff: our system is purpose-built for security classification, not general retrieval. A 1,536D embedding will always beat 6D at finding similar documents. But for the specific task of "is this input trying to manipulate the AI?" — named, interpretable dimensions win.

---

**Links:**
- Code: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)
- Dataset: [huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data)
- Patent: USPTO #63/961,403
- Author: Issac Daniel Davis (ORCID: 0009-0002-3936-9369)
