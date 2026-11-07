# Prime Token Catalog Benchmark Result — 2026-11-07

Status: `UNDERPOWERED`; full six-view ranking did not beat the required baselines.

## Evaluator

The evaluator uses 11 unique query records that are not ingested into the
catalog. Each query has a unique `benchmark://` source identity. Expected source
labels are resolved after retrieval and never enter query features. The catalog
contains 11 target sources and 364 sections.

This is a source-record-disjoint mechanics check, not an independent semantic
benchmark. The queries are curated paraphrases of the target material, and 11 is
below the preregistered 30-query capability floor.

Controls:

- lexical-only baseline;
- no-intervention baseline, removing 5W, prime and source views;
- one-to-one shuffled non-lexical bindings with seeds 11, 29 and 47;
- individual 5W, prime, source, atomic and speech ablations;
- topology disabled.

## Results

| Arm | MRR | Recall@1 | Recall@5 |
|---|---:|---:|---:|
| lexical only | 0.6617 | 0.5455 | 0.8182 |
| no intervention | 0.5872 | 0.5455 | 0.5455 |
| no prime | 0.5812 | 0.5455 | 0.6364 |
| no atomic | 0.5682 | 0.5455 | 0.6364 |
| full six-view | 0.5329 | 0.4545 | 0.6364 |
| no source | 0.5326 | 0.4545 | 0.6364 |
| no topology | 0.5321 | 0.4545 | 0.6364 |
| no 5W | 0.5307 | 0.4545 | 0.5455 |
| no speech | 0.4773 | 0.3636 | 0.6364 |
| shuffled binding, three-seed mean | 0.2040 | 0.0606 | 0.3636 |

Full minus lexical-only MRR was `-0.1289`; full minus no-intervention was
`-0.0544`. Full exceeded shuffled controls by `0.3288`, below the required
two-pooled-SD threshold of `0.7402`. No gate passed.

## Interpretation

- The full field regressed against lexical retrieval on this sample.
- Prime query features dilute ranking here: removing prime improved MRR by
  0.0484, but still did not beat lexical-only.
- Atomic features also dilute ranking on average. Removing them improved MRR by
  0.0353 while increasing misses within the top-20 from two to four.
- Speech features are useful in aggregate: removing speech reduced MRR by
  0.0556.
- Source features are absent unless explicitly requested, so their ablation is
  effectively inert in this benchmark.
- Two topology steps barely changed rank order. The observed gain is not coming
  from propagation.
- 5W is mixed: removing it barely changed MRR and reduced Recall@5.
- Shuffling bindings causes a large regression, showing that binding identity
  matters structurally. It does not show that the complete field improves over
  a simpler lexical system.

This result blocks promotion. It does not refute every possible gated use of the
derived views because the query set is small and authored after reading the
targets. The correct status remains `UNDERPOWERED`, not `REFUTED`.

## Next Research Gate

Do not tune view weights on these 11 seen queries. Freeze this result and collect
at least 30 independently written local requests with reviewer-assigned source
labels and source-group-disjoint splits. Pre-register a zero-parameter
lexical-first cascade as a new candidate: lexical retrieval remains authoritative;
auxiliary views may break ties or recover a no-match case but may not displace a
confident lexical result. Test that candidate on the unseen set against the same
baselines and shuffled controls.

## Receipts

- Benchmark manifest SHA-256:
  `6ce32a8a7506e7c949eea20f633d5174429e10427f40a9518b9a2fe3d2822e09`
- Result SHA-256:
  `191d300d2f7a14a0d18f9154eda5d733c3f95452b1c0695001dba9a8d89aeeda`
- Runtime result:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/benchmark-v3-20261107/RESULT.json`
- Algorithm revision: `six-view-topology-v3`
- No model weight, tokenizer, probability sidecar or serving pointer changed.
