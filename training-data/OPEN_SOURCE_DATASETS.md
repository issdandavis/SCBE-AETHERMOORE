# Open Source Datasets for SCBE-AETHERMOORE Training

## Priority Integration Map

### Phase 1: Safety Alignment (HIGH priority)
| Dataset | Records | License | Why |
|---------|---------|---------|-----|
| [NVIDIA Aegis 2.0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0) | 33,416 | CC-BY-4.0 | 12-category hazard taxonomy maps to SCBE governance layers |
| [Anthropic HH-RLHF](https://huggingface.co/datasets/Anthropic/hh-rlhf) | 161,000 | MIT | Preference pairs for DPO training (ALLOW/DENY decisions) |
| [Hendrycks ETHICS](https://huggingface.co/datasets/hendrycks/ethics) | 111,602 | MIT | 5-framework ethical reasoning |

### Phase 2: Math Reasoning (HIGH priority)
| Dataset | Records | License | Why |
|---------|---------|---------|-----|
| [NVIDIA OpenMathReasoning](https://huggingface.co/datasets/nvidia/OpenMathReasoning) | 540K problems | CC-BY-4.0 | Geometry proofs, CoT reasoning for hyperbolic computations |
| [OpenR1-Math-220k](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k) | 220K | Apache 2.0 | Multi-trace verification, DPO-ready |

### Phase 3: Crypto + PQC Knowledge (MEDIUM-HIGH)
| Dataset | Records | License | Why |
|---------|---------|---------|-----|
| [NIST Cybersecurity Training](https://huggingface.co/datasets/ethanolivertroy/nist-cybersecurity-training) | 530,912 | Public Domain | FIPS 203/204 context for ML-KEM/ML-DSA |
| [Trendyol Cybersecurity](https://huggingface.co/datasets/Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset) | 53,202 | Check | 200+ security domains, SFT format |

### Phase 4: Hyperbolic Geometry Libraries
| Resource | Type | Why |
|----------|------|-----|
| [Geoopt](https://github.com/geoopt/geoopt) | Library | Poincare ball computations in PyTorch |
| [HNN++](https://github.com/mil-tokyo/hyperbolic_nn_plusplus) | Library | Hyperbolic attention layers (ICLR 2021) |

## All Licenses Are Commercial-Compatible
CC-BY-4.0, MIT, Apache 2.0, Public Domain — all OK for SCBE training + deployment.
