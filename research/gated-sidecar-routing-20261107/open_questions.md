# Open questions — gated sidecar junctions

Date: 2026-11-07

## Must answer before implementation

1. Which exact output schema lets a specialist rejoin without changing frozen
   hidden state: logits, typed action candidates, retrieval evidence, or all
   three as separate lanes?
2. The first 30-case ordinary-prompt development contract is now frozen in
   `false_route_benchmark_v1.json`. What authentic, source-disjoint prompt set
   and commercial ceiling are acceptable before launch remains open.
3. Which zero-parameter fields are allowed in eligibility: source kind, prompt
   grammar, tool declaration, catalog provenance, and capability ID?
4. Can the gate abstain independently of both the core and specialist, or must
   abstention remain a product-level policy?
5. How are specialist latency, memory, and capacity budgets enforced when two
   routes are eligible simultaneously?

## Experimental unknowns

1. Does late-logit fusion preserve counting exactly as reliably as isolated
   specialist dispatch?
2. Does a learned sigmoid gate beat a deterministic gate after controlling for
   parameter count and route metadata?
3. Does Gumbel/hard routing improve deploy-time specificity enough to justify
   temperature tuning and train/deploy mismatch?
4. Are v6's six views useful to route identity after lexical evidence, or do
   they merely correlate with source labels? The prospective pool is currently
   `0/30`, so this remains untestable.
5. Does a shuffled-binding control eliminate any apparent six-view routing gain?
6. What is the maximum useful number of local specialists before dispatch and
   memory overhead outweigh modularity?

## Registry and product unknowns

1. Where should the canonical specialist registry live, and which existing
   Clay weight catalog can be extended instead of duplicated?
2. What statuses and evidence fields are required to retain failed runs without
   accidentally exposing them to production traffic?
3. Should customers buy one specialist, a governed bundle, or a deployment with
   a fixed route contract?
4. Which licensing and redistribution fields must accompany specialists trained
   from owner-authorized conversation data or internal research sources?
5. How should rollback prove that the core, tokenizer, and unrelated specialists
   are unchanged?

## Next checks

1. Wait for the current confirmatory three-seed run and independent verifier.
2. Inventory the existing weight catalog schema before adding a specialist
   registry field.
3. Keep the frozen false-route contract as a development regression suite; do
   not mistake its authored `0/42` false-route result for deployment evidence.
4. Do not attach v6 until at least 30 authentic post-freeze requests satisfy the
   existing source-disjoint gate.
