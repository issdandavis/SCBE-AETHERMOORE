# Linux AI Workstation Hardware Cost Analysis

**Date**: 2026-05-31  
**Use**: Attachment E/F cost support  
**Recommended line item**: `$6,500`  
**Preferred OS**: Pop!_OS NVIDIA Edition or Ubuntu 24.04 LTS  

## Recommendation

Include one **Linux-based SCBE AI workstation** at **`$6,500`** as a prime-owned hardware / ODC line.

This supports local, auditable execution of:

- SCBE benchmark harnesses,
- small-model inference and latent-state extraction,
- local coding-agent and document-generation workflows,
- MAHSS / physical-compute topology generation,
- synthetic impulse clustering,
- kinematic mesh simulations,
- IV&V artifact preparation.

It does not replace cloud A100/H100 compute for large training. It reduces dependence on cloud for repeatable development and evidence generation.

## Recommended Build Band

| Tier | Estimated cost | Use |
| --- | ---: | --- |
| Lean | `$3,200-$4,500` | Used RTX 3090 24GB, 96-128GB RAM, enough for Phase 0/1. |
| Recommended | `$5,800-$6,800` | RTX 4090 24GB or sane RTX 5090 32GB, Ryzen 9, 128GB RAM, 8TB NVMe total. |
| Buffered proposal line | `$6,500` | Recommended build with normal price fluctuation, Linux OS, UPS/cooling/storage room. |
| High-end | `$8,000-$12,000` | 5090 or dual-GPU posture; not needed for current Phase I baseline. |
| Threadripper class | `$10,000-$18,000` | Only for future multi-GPU workstation/lab build. Not recommended now. |

## Component Budget

| Component | Planning range |
| --- | ---: |
| NVIDIA GPU, RTX 4090 24GB or RTX 5090 32GB if priced sanely | `$1,800-$3,500` |
| Ryzen 9 9950X / 7950X class CPU | `$450-$650` |
| 128GB DDR5 RAM | `$500-$1,500` |
| X670E / X870E motherboard | `$250-$450` |
| NVMe storage, 4TB primary + 4TB secondary | `$450-$750` |
| 1200W quality PSU | `$200-$350` |
| Cooling, case, fans | `$300-$600` |
| UPS | `$250-$500` |
| Linux OS | `$0` |
| Miscellaneous / warranty / cabling buffer | `$150-$300` |

## Linux Choice

Preferred operating system:

1. **Pop!_OS NVIDIA Edition**: lowest-friction NVIDIA install path because System76 provides a dedicated NVIDIA ISO.
2. **Ubuntu 24.04 LTS**: best official CUDA/PyTorch documentation path and strong long-term support.

Avoid Windows as the default proposal line. Linux saves the Windows Pro license cost, gives native Docker/NVIDIA container workflows, and better matches reproducible research and local audit-chain execution.

## Proposal Language

> A `$6,500` Linux-based SCBE AI workstation will support local execution of the seed-to-geometry-to-physical-fingerprint and agent-governance benchmark pipeline. The workstation enables repeatable CUDA/PyTorch workloads, local latent-state extraction, synthetic physical-response clustering, kinematic mesh simulation, and IV&V artifact preparation without persistent external compute dependency.

## Cost Placement

Use as a prime ODC / hardware line in Attachment F:

- Category: `Other Direct Costs` or `Equipment`, depending on official workbook categories.
- Amount: `$6,500`.
- Owner: Prime / SCBE.
- Not part of Hoags subcontract.
- Not cloud compute.

## Source Basis

- NVIDIA CUDA Linux installation guide confirms current CUDA support across Ubuntu LTS releases.
- NVIDIA Container Toolkit docs support Docker GPU workflows on Linux.
- System76 Pop!_OS download page provides NVIDIA-specific installer path.
- PyTorch official install flow supports Linux CUDA builds.
- Current GPU/workstation market checks support `$6,500` as a practical RTX 4090-class workstation line.

