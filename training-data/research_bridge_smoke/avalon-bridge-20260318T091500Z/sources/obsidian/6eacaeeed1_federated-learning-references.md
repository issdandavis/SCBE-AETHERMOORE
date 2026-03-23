# Federated Learning References

> Academic foundations for privacy-preserving training in SCBE's multi-model architecture.

## Core Papers

1. **McMahan, B. et al. (2017)** "Communication-Efficient Learning of Deep Networks from Decentralized Data" — AISTATS
   - FedAvg algorithm — the foundation of federated learning
   - Relevant to: `training/federated_orchestrator.py`

2. **Kairouz, P. et al. (2021)** "Advances and Open Problems in Federated Learning" — Foundations and Trends in ML
   - Comprehensive survey (100+ pages) of FL challenges
   - Relevant to: Understanding aggregation strategies for multi-cloud training

3. **Bonawitz, K. et al. (2019)** "Towards Federated Learning at Scale: A System Design" — MLSys
   - Production FL system design at Google
   - Relevant to: Scaling SCBE's federated orchestrator

## Differential Privacy + FL

4. **Abadi, M. et al. (2016)** "Deep Learning with Differential Privacy" — CCS
   - DP-SGD for training with privacy guarantees
   - Relevant to: Future work on DP integration with SCBE governance

## SCBE's Approach

SCBE uses federated learning with additional governance layers:
- **Layer 12**: Entropy monitoring during training (rho_e bounds)
- **Layer 13**: BFT consensus for model update approval
- **Layer 14**: PQC-signed model artifacts

The `flock_shepherd.py` module implements multi-AI fleet coordination with BFT voting — each "sheep" agent trains locally and submits updates to the "shepherd" for governance-checked aggregation.

## Cross-References
- [[14-Layer Architecture]] — FL spans Layers 12-14
- [[Grand Unified Statement]] — Model updates pass through G(xi, i, poly)
- [[CDDM Framework]] — Future: domain mappings for training data quality metrics
