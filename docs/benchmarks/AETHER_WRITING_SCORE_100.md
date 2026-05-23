# Aether Writing Score 100

Status: v1 local/free benchmark lane.

This benchmark tests whether a local AI writing route can follow practical writing constraints for product, editing, fiction, and governance copy. It is not a literary-quality leaderboard. It is a usability score: can the system produce text that obeys the requested structure, preserves required facts, avoids banned terms, and leaves evidence?

## Policy

- Provider path: local Ollama only.
- Hosted API usage: none.
- Judge: deterministic checks, not a paid LLM judge.
- Output artifact: `artifacts/benchmarks/aether_writing_score/writing_benchmark_20260523T231225Z.json`.

## Task Set

| Task | What It Tests |
| --- | --- |
| `free_local_product_note` | Product framing with exact headings, free/local policy, and no-hype terms |
| `typo_repair_with_ledger` | Human typo correction plus JSON change ledger |
| `fact_retention_long_context` | Long-context retention of twelve required fact IDs |
| `constrained_story_scene` | Fiction scene constraints, sensory nouns, dialogue, and forbidden-topic avoidance |
| `safety_case_explainer` | Practical safety/liability explanation with required terms |

## 2026-05-23 Local Run

Command:

```powershell
python scripts\benchmark\local_writing_benchmark.py --models qwen2.5:7b-instruct,openclaw:latest,qwen2.5-coder:1.5b,scbe-geoseal-coder:q8 --timeout 90 --num-predict 360
```

Results:

| Rank | Model | Score | Pass Rate | Passed Tasks | Runtime |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `openclaw:latest` | 88.52 | 100% | 5/5 | 30.762s |
| 2 | `qwen2.5-coder:1.5b` | 80.92 | 80% | 4/5 | 28.341s |
| 3 | `scbe-geoseal-coder:q8` | 73.85 | 60% | 3/5 | 18.101s |
| 4 | `qwen2.5:7b-instruct` | 0.00 | 0% | 0/5 | 21.484s |

## Caveats

`qwen2.5:7b-instruct` returned Ollama HTTP 500 on all five tasks. Treat that as a local runtime/model-load failure, not proof that the model cannot write.

The v1 score is intentionally mechanical. It can catch missing facts, wrong section shape, forbidden words, bad JSON ledgers, and word-count failures. It cannot yet measure prose taste, emotional effect, or whether a reader would buy the product.

Several passed outputs still had partial misses. For example, `openclaw:latest` won but missed exact terms like `no API`, `bell`, and `simulation` on individual tasks. That means it is usable, not finished.

## Readiness Score

Current local/free writing route readiness: 76/100.

Reasoning:

- Best local model clears the benchmark at 88.52/100.
- The model pool average is pulled down by one runtime-failing model.
- Ledger-writing and exact-policy wording are still brittle.
- The benchmark is now repeatable and artifact-backed.

## Next Repairs

1. Add a preflight that tests each Ollama model with a one-token call before benchmark runs. Runtime-failing models should be marked `unavailable`, not mixed into writing-quality averages.
2. Add a repair loop for failed tasks: rerun only the missed task with the failed checks injected as constraints.
3. Add a human-review column for style quality after deterministic checks pass.
4. Add transcript/video task variants so the same writing benchmark can score YouTube endings, descriptions, captions, and CTA treatment.
