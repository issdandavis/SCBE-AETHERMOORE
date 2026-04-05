---
title: M5 Mesh Foundry
emoji: 🔧
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.12.0
app_file: app.py
pinned: true
license: mit
datasets:
  - issdandavis/scbe-aethermoore-training-data
tags:
  - ai-safety
  - governance
  - security
  - training-data
---

# M5 Mesh Foundry

Interactive demo of the SCBE-AETHERMOORE 14-layer AI governance pipeline.

## Features

- **Governance Gate** — Test any prompt against 14 security layers
- **Tongue Explorer** — Visualize Sacred Tongue (6D phi-weighted) activations
- **Harmonic Wall** — Compute exponential adversarial cost H(d,R) = R^(d^2)
- **Training Data** — Browse 394K+ governed records across 8 views
- **Feedback** — Disagree with a decision? Your correction trains the next model

## Training Flywheel

Every interaction is logged as potential training data. User feedback creates
gold-standard correction pairs for DPO/RLHF training.

## Links

- [GitHub](https://github.com/issdandavis/SCBE-AETHERMOORE)
- [Dataset](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data)
- [Patent](https://aethermoorgames.com) — USPTO #63/961,403
- ORCID: 0009-0002-3936-9369
