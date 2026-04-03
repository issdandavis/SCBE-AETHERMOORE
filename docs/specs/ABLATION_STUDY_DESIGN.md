# Ablation Study Design: Geometric Scaffold Layers

**Source**: Codex session 2026-04-03
**Status**: Ready for execution on T4/Colab

## 7 Ablation Variants

| # | Variant | What's Removed | Expected Drop |
|---|---|---|---|
| 0 | Full Scaffold (Control) | Nothing | Baseline 31% gain |
| 1 | No Body | All trait axes (Big Five, Moral Foundations, SCBE-native) | ~8-11% |
| 2 | No Mind | Routing axes, region anchors, 21D/PHDM | ~12-15% |
| 3 | No Spirit | Stakeholder-cost tensor (self/user/system/attacker/inaction) | ~18-22% (LARGEST) |
| 4 | No Ternary Layering | Collapse to flat sign only | ~6-9% |
| 5 | No Phi Priors | Replace phi-scaled weights with uniform 1.0 | ~4-7% |
| 6 | No PHDM Routing | Flat 21D embedding only, ignore polyhedra | ~3-5% |
| 7 | Flat SFT Baseline | No scaffold at all | 0% reference |

## Key Prediction
Spirit (cost model) + Mind (routing) together = ~70% of the total gain. Body provides stable foundation, but dynamic parts (costs + routing) drive generalization to unseen attacks.

## Training Config (identical across all)
- Base model: Qwen2.5-0.5B or Polly seed
- Seeds: 3-5 for significance
- Budget: Matched T4 GPU hours
- Eval: Full scorecard + role fidelity (Polly evals) + governance compliance (400 SCBE attacks)

## Run Order
1. No Spirit (biggest predicted drop, clearest governance signal)
2. No Mind (second biggest)
3. No Body (third)
4. Rest in any order

---

## Scaffold vs Graph Transformers Verdict

**Keep the scaffold. GTs cannot replicate the Spirit block.**

| Dimension | Scaffold Wins | GT Wins |
|---|---|---|
| Governance/Safety | Yes (Spirit block, 34.5% blind holdout) | No |
| Latency | Yes (lookup + projection vs attention) | No |
| Role Fidelity | Yes (ternary states capture personality nuance) | No |
| Long-range dynamics | Tie | Tie |
| Dynamic relational reasoning | No | Yes |

**Best hybrid**: Add lightweight GT-style attention inside Mind block for dynamic polyhedra transitions. Keep Body + Spirit + phi priors + pruning unchanged.

---

## Polyhedral Graph Hybrid Designs

| Hybrid | Core Idea | Complexity | Expected Lift |
|---|---|---|---|
| 1. PolyGNN-Style | PHDM polyhedra = 16 nodes, ternary = features | Low (PyG) | +8-12% role fidelity |
| 2. PE-Transformer | Polyhedral Laplacian replaces Graphormer PE | Medium | +10-15% complementarity |
| 3. Tropical-GT | Attention reduces to tropical paths on cost landscape | Medium | +15-20% safety/recovery |
| 4. Dual-Graph + GT | Polyhedron dual for dynamic family relations | Higher | +18% disagreement handling |

**Recommended starter**: Hybrid 1 (PolyGNN-style) -- closest to existing PHDM, off-the-shelf PyG.

## Hybrid Energy Function
```
E_hybrid(z, u | p) = E(z, u | p) + lambda * Attn_GT(Proj_PHDM(z), Adj_poly)
```

Where Attn_GT is a lightweight Graphormer/Exphormer layer on the 16-node polyhedral graph.
