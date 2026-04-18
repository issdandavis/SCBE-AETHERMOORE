---
title: SCBE-AETHERMOORE — Hardware Requirements
version: 1.0.0
date: 2026-04-13
scope: Full 14-layer pipeline, training + inference + governance
tiers: [SOVEREIGN, LAB, EDGE, FIELD, SURVIVAL]
---

# SCBE Hardware Requirements

Five tiers from maximum capability to bare-bones field deployment.
Each tier runs the full pipeline — fidelity and throughput differ, math does not.

---

## Compute Bottleneck Map (per layer)

| Layer | Primary Op | Bottleneck |
|-------|-----------|------------|
| L1 | PQC keygen (ML-KEM, ML-DSA) | Crypto — CPU/FPGA |
| L2 | Matrix multiply (21D product metric) | RAM bandwidth |
| L3 | 6 exp() calls + phi weights | FP32 throughput |
| L4 | tanh + normalize | FP32 throughput |
| L5 | arcosh + norm² | FP64 accuracy critical |
| L6 | sin + tanh per frame | FP32 throughput |
| L7 | 2×2 rotation matrix | Trivial |
| L8 | K Gaussian evals | FP32 throughput |
| L9 | FFT(256) | DSP / FFT core |
| L10 | 6 cos() + mean | Trivial |
| L11 | 3× d_ℍ calls | FP64 accuracy |
| L12 | Harmonic wall (exp chain) | FP64, overflow guard |
| L13 | Weighted sum + threshold | Trivial |
| L14 | FFT(256) + spectral stats | DSP / FFT core |

**FP64 required**: L5, L11, L12 (hyperbolic distance blows up in FP32 near boundary)
**FFT cores help**: L9, L14

---

## Tier 1 — SOVEREIGN
*Maximum fidelity. Research cluster. Full training + inference.*

### Compute
| Component | Spec | Purpose |
|-----------|------|---------|
| GPU | 8× NVIDIA H100 80GB SXM5 | Training, batch inference |
| CPU | 2× AMD EPYC 9654 (96c) | Pipeline orchestration, PQC |
| RAM | 2TB DDR5 ECC | 21D state manifold at scale |
| NVMe | 8× 4TB PCIe 5.0 (RAID) | Dataset + checkpoint storage |
| Network | 400Gb InfiniBand NDR | Multi-node gradient sync |
| FPGA | Xilinx Alveo U55C | ML-KEM/ML-DSA hardware offload |

### Storage
- Hot: 32TB NVMe (training data, active checkpoints)
- Warm: 512TB NAS (full dataset, audit logs)
- Cold: object storage (S3/GCS, immutable audit archive)

### Software stack
- CUDA 12.x, cuDNN, cuBLAS
- liboqs (PQC bindings)
- PyTorch 2.x (training)
- ONNX Runtime (inference)
- Docker + Kubernetes (orchestration)

### Throughput
- Training: full 14-layer gradient pass, batch 512+, FP64 where required
- Inference: ~10,000 requests/sec
- PQC keygen: hardware-accelerated, <1ms per key

---

## Tier 2 — LAB
*Single workstation. Development, ablations, small training runs.*

### Compute
| Component | Spec | Purpose |
|-----------|------|---------|
| GPU | 1-2× NVIDIA RTX 4090 24GB | Training, inference |
| CPU | AMD Ryzen 9 7950X (16c) or Intel i9-14900K | Pipeline, PQC |
| RAM | 128GB DDR5 ECC | State manifold, dataset cache |
| NVMe | 2× 4TB PCIe 4.0 | Dataset + checkpoints |

### Constraints vs Tier 1
- Training batch size: 32-64 (vs 512+)
- No hardware PQC — software liboqs (~5ms keygen)
- L12 toroidal cavity: compute serially not in parallel

### Software stack
- Same as Tier 1, minus InfiniBand / multi-node
- Python 3.11+, CUDA 12.x
- `SCBE_FORCE_SKIP_LIBOQS=0` (liboqs installed locally)

### Throughput
- Training: viable for ablations and curriculum runs
- Inference: ~500 requests/sec
- This is the current primary development environment

---

## Tier 3 — EDGE
*Embedded inference. No training. Runs full pipeline in governed inference mode.*

### Compute
| Component | Spec | Purpose |
|-----------|------|---------|
| SoC | NVIDIA Jetson AGX Orin 64GB | GPU + CPU unified |
| Storage | 1TB NVMe | Model weights + audit logs |
| Network | GbE or LTE modem | Connectivity |

### Alternatively
| Component | Spec |
|-----------|------|
| SoC | Apple M3 Pro / M4 (unified memory) | 
| RAM | 36-48GB unified |
| Storage | 1TB SSD |

### Constraints vs Lab
- No training — inference only (frozen weights)
- FP16 quantization for L3/L4/L6-L8/L10/L13 (tolerable)
- **FP64 must be preserved for L5, L11, L12** — hyperbolic math collapses in FP16
- PQC: software, ~15ms keygen (acceptable for edge rate)
- Cauchy Core κ: computed every N steps (not every frame), cached

### Throughput
- Inference: ~50 requests/sec
- Governance decisions: <100ms latency
- Audit logs: buffered locally, synced on connectivity

---

## Tier 4 — FIELD
*Portable. Power-constrained. Ruggedized. Full governance, reduced fidelity.*

### Compute
| Component | Spec | Purpose |
|-----------|------|---------|
| SBC | Raspberry Pi 5 (8GB) + Coral TPU USB | L3/L4/L8 on TPU |
| OR: Mobile SoC | Qualcomm Snapdragon X Elite laptop | CPU + NPU |
| RAM | 8-16GB |  |
| Storage | 256GB microSD or USB NVMe |  |
| Power | 5-25W draw | Battery deployable |

### Reduced fidelity operations
| Layer | Field adaptation |
|-------|-----------------|
| L1 | Software PQC, cached keys (rekey every 24h not every session) |
| L2 | 9D state manifold (drop governance telemetry z) instead of 21D |
| L3 | Precomputed LWS weights, no breathing oscillation |
| L4 | FP32 tanh (boundary avoidance via clamping instead of precision) |
| L5 | **FP64 preserved** — non-negotiable |
| L6 | Static (no breathing), pd = 0 |
| L7 | Identity (skip rotation, save cycles) |
| L8 | 2-well only (ALLOW / DENY — no QUARANTINE/ESCALATE gradation) |
| L9 | FFT(64) not FFT(256) |
| L10 | Spin coherence from 3 tongues not 6 |
| L11 | Triadic window = 2 (not 3) |
| L12 | Form B only: S = 1/(1 + d_H + 2·pd), no Cauchy Core |
| L13 | Binary gate: ALLOW / DENY |
| L14 | Skip (no audio axis in field) |

### What is preserved
- L5 hyperbolic distance (the invariant — never skip this)
- L12 harmonic wall (safety gate — degraded form still functional)
- L13 decision (binary is enough for field)
- Full audit log (write to local storage, sync when connected)

### Throughput
- ~5 requests/sec
- Governance latency: <500ms
- Battery life: 8-12h at sustained load

---

## Tier 5 — SURVIVAL
*Absolute minimum. CPU only. Emergency or air-gapped deployment.*

### Compute
| Component | Spec |
|-----------|------|
| CPU | Any x86-64 with AVX2, ≥4 cores, ≥4GB RAM |
| Storage | 8GB USB drive |
| Python | 3.9+ |
| Dependencies | numpy only (no torch, no cuda, no liboqs) |

### Implementation
Run `src/scbe_14layer_reference.py` — pure numpy reference implementation.

### Layer map in survival mode
| Layer | Status |
|-------|--------|
| L1 | HMAC-SHA256 only (no PQC) |
| L2 | 6D only (tongue positions, no 21D manifold) |
| L3 | Precomputed φ-weights, no time term |
| L4 | tanh embed, FP64 |
| L5 | **Full hyperbolic distance, FP64** — always |
| L6 | Skip |
| L7 | Skip |
| L8 | 2-well (ALLOW / DENY) |
| L9 | Skip |
| L10 | Skip |
| L11 | Single pair d_ℍ(t₁, t₂) |
| L12 | S = 1/(1 + d_H) — minimal form |
| L13 | d_H > threshold → DENY, else ALLOW |
| L14 | Skip |

### Core guarantee in survival mode
```python
# All you need on any machine with Python + numpy:
import numpy as np

def hyperbolic_distance(u, v):
    """L5 — THE INVARIANT. Never skip."""
    norm_u2 = np.dot(u, u)
    norm_v2 = np.dot(v, v)
    diff = u - v
    num = 2 * np.dot(diff, diff)
    den = (1 - norm_u2) * (1 - norm_v2)
    return np.arccosh(1 + num / den)

def survival_gate(u_input, u_safe_center, threshold=1.5):
    """Minimal SCBE governance. Runs on anything."""
    d = hyperbolic_distance(u_input, u_safe_center)
    return "ALLOW" if d < threshold else "DENY"
```

### Throughput
- ~100 requests/sec (pure numpy, no GPU)
- No latency guarantee
- Sufficient for: air-gapped validation, field triage, emergency governance check

---

## Training vs Inference Requirements

| Mode | Minimum Tier | Notes |
|------|-------------|-------|
| Full training (14 layers, gradient) | Tier 2 (Lab) | Tier 1 preferred |
| Fine-tuning / LoRA | Tier 2 | 24GB VRAM minimum |
| Full inference (production) | Tier 2-3 | |
| Governed inference (edge) | Tier 3 | |
| Field governance check | Tier 4 | |
| Emergency audit | Tier 5 | |

---

## Non-Negotiables Across All Tiers

These cannot be reduced regardless of hardware:

1. **L5 hyperbolic distance in FP64** — FP32 produces incorrect values near the boundary where adversarial behavior lives
2. **L12 harmonic wall always runs** — even in survival mode, degraded form
3. **L13 decision always produces output** — binary is acceptable, no output is not
4. **Audit log always written** — governance without traceability is not governance

---

## Power Envelope Summary

| Tier | TDP | Deployment |
|------|-----|-----------|
| SOVEREIGN | 10-20 kW | Data center |
| LAB | 500W-1kW | Workstation / server room |
| EDGE | 15-65W | Embedded, vehicle, rack |
| FIELD | 5-25W | Battery, backpack, ruggedized |
| SURVIVAL | 5-15W | Any laptop, Raspberry Pi, air-gapped |
