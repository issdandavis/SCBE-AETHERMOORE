# Literature Context for SCBE Peer Review

## Relevant Academic Work (2023-2026)

### Adversarial Attacks on Hyperbolic Networks (Dec 2024)
- arXiv: 2412.01495
- Key finding: Conventional adversarial attacks assume Euclidean geometry. Poincare and Euclidean ResNets have **significantly different weaknesses**. The choice of geometry leads to different adversarial behavior.
- **Implication for SCBE**: The Poincare ball choice is theoretically defensible — different geometry = different attack surface. But attacks need to be reformulated in hyperbolic space, which SCBE hasn't done.

### Understanding and Improving Hyperbolic Deep RL (Dec 2025)
- arXiv: 2512.14202
- Key finding: Large-norm embeddings in Poincare Ball **destabilize gradient-based training**. RMSNorm + learned scaling bounds norms. Switching to Hyperboloid model removes instabilities inherent to Poincare ball.
- **Implication for SCBE**: The Poincare ball has known numerical stability issues near the boundary (exactly where SCBE puts high-risk actors). The current clamping to [-0.95, 0.95] is a band-aid. Academic recommendation is to use Hyperboloid model instead.

### Poincare Embeddings (Nickel & Kiela, 2017 — foundational)
- arXiv: 1705.08039
- Established that Poincare ball naturally represents hierarchical structures with exponential capacity.
- **Implication for SCBE**: The trust/threat hierarchy is a legitimate use case for hyperbolic embeddings. But SCBE uses 1D projections, not learned embeddings — missing the point.

### HarmBench (Mazeika et al., 2024)
- 510 behaviors, 18 attack modules
- SOTA defenses: 5-15% ASR against automated attacks
- Human red-teaming: up to 75% ASR
- **Implication for SCBE**: 57% ASR is in the "undefended" range. Need to benchmark against HarmBench dataset.

### TensorTrust (Toyer et al., 2023)
- 563K+ prompt injection attacks from adversarial game
- Models show significant vulnerability to extraction and hijacking
- **Implication for SCBE**: Direct comparison needed. SCBE's 0% detection on prompt_extraction is concerning given TensorTrust's findings.

## Summary Assessment

The theoretical foundation (Poincare ball for safety) has academic precedent and merit. The implementation gap is:
1. Using 1D linear projections instead of learned embeddings
2. Known Poincare ball stability issues near boundary (where SCBE puts threats)
3. No comparison against standardized attack suites
4. The geometry contributes ~8.5% of the risk score — not load-bearing

## Sources
- [Adversarial Attacks on Hyperbolic Networks](https://arxiv.org/html/2412.01495v1)
- [Understanding and Improving Hyperbolic Deep RL](https://arxiv.org/html/2512.14202)
- [Poincare Embeddings for Hierarchical Representations](https://arxiv.org/pdf/1705.08039)
- [HarmBench](https://www.harmbench.org/)
- [TensorTrust](https://tensortrust.ai/)
- [AI Safety Index 2025](https://futureoflife.org/ai-safety-index-summer-2025/)
