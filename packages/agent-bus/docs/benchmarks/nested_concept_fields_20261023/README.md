# Nested concept fields — 23 October 2026

This packet binds Issac's 84-sentence **Hoard of Thoughts** sentence-function lattice to the public reasoning-artifact graph. It implements overlapping concept bubbles, nested topic fields, typed directed relations, deterministic goal-conditioned routing, and hash-chained route receipts.

It does **not** expose private chain of thought. The recorded steps are source sentences, public summaries, declared relations, and deterministic state transitions.

## Result

- Source sentences: **84**
- Reasoning artifacts: **84**
- Concept bubbles: **202**
- Nested topic fields: **10**
- Typed edges: **186**
- Mechanism tasks: **120**
- Typed route accuracy: **100.0%**
- Flat lexical baseline: **52.5%**
- Untyped equal-cost baseline: **42.5%**
- Shuffled-label mean: **44.3% ± 4.0%** across 8 seeds
- Preregistered claim rule: **PASS**

The passed claim is narrow: **typed relation labels control deterministic public routing on this source-derived mechanism test**. This packet does not show improved language-model reasoning, generalization, or training gains.

## Route demonstrations

- `evidence-to-explanation`: reached; P2.03 → P2.04 → P2.05 → P2.06
- `return-to-thesis`: reached; P4.15 → P1.19
- `strict-theme-refusal`: no-route (E_NO_ROUTE); no admitted path
- `exploratory-theme-route`: reached; P1.01 → P1.02 → P1.03 → P1.04
- `paragraph-hyperedge`: reached; P4.03 → P4.14

Open [concept_fields.html](concept_fields.html) for the offline interactive view. Select fields, bubbles, routes, and sentence nodes. Theme bubbles are amber hypotheses; source annotations are green.

## Reproduce

From `packages/agent-bus`:

```powershell
npm run build
node scripts/build_nested_concept_fields.mjs --source "C:\dev\tongue-compiler\artifacts\essay_sentence_lattice_20261023"
node scripts/build_nested_concept_fields.mjs --verify
```
