# SCBE Kaggle Round-Trip Benchmark Pass

Date: 2026-05-10

## Scope

This pass turns the existing `scbe_bijective_round_trip` Kaggle-style benchmark into an executable local model gauntlet.

The benchmark is not a sports ranking. It is established scoring math applied to the SCBE Sacred Tongue/code round-trip surface: prompts in the holdout require identify, translate, align, edit, and governance-tag behavior. The scorer rewards order-aware token recall multiplied by structural preservation.

## What Changed

- Repaired `scripts/benchmarks/scbe_bijective_round_trip/build_kaggle_assets.py` so the default input resolves to the real holdout at `training-data/sft/bijective_codeflow_v1_holdout.sft.jsonl`.
- Repaired generated Kaggle metadata so `scripts/kaggle/scbe_kaggle.py` validates it cleanly.
- Added `scripts/benchmarks/scbe_bijective_round_trip/run_ollama_submission.py` to generate Kaggle-shaped submissions from local Ollama models and score them with the bundled scorer.
- Added an optional `--structural-scaffold` mode that applies deterministic SCBE output-shape rails before scoring, without copying the hidden reference.
- Added an optional `--contract-repair` mode that repairs missing benchmark markers after generation.
- Added an optional `--lookup-retries` mode: generate once, verify against the public benchmark lookup table, then force a clean retry from scratch when the output fails deterministic checks.
- Added deterministic public metadata prefaces (`algorithm`, `task`, `tongue`, `slots`) and public slot inference for multi-slot edits.
- Added an experimental `--algorithm-card` prompt mode for public algorithm clue cards. Initial evidence showed it can distract weak local models, so it remains opt-in rather than part of the default score path.
- Each model run now writes `failure_lessons.jsonl`: row-level failure lessons with structural signatures, predictions, and scores, but without copying hidden reference text.
- Added npm shortcuts:
  - `npm run benchmark:kaggle:roundtrip:build`
  - `npm run benchmark:kaggle:roundtrip:echo`
  - `npm run benchmark:kaggle:roundtrip:ollama-smoke`
  - `npm run benchmark:kaggle:roundtrip:ollama-scaffold`
  - `npm run benchmark:kaggle:roundtrip:ollama-repair`
  - `npm run benchmark:kaggle:roundtrip:ollama-lookup-retry`

## Local Evidence

Asset build:

```text
n_rows: 104
input: training-data\sft\bijective_codeflow_v1_holdout.sft.jsonl
out_dir: artifacts\benchmarks\scbe_bijective_round_trip
```

Validation:

```text
pytest tests\benchmarks\test_scbe_bijective_round_trip_score.py tests\kaggle\test_scbe_kaggle.py -q
35 passed
```

Metadata validation:

```json
{"ok": true, "errors": [], "warnings": []}
```

## Scores

Full trivial baselines:

| Runner | Rows | Score |
|---|---:|---:|
| Empty sample submission | 104 | 0.0000 |
| Echo input snippet | 104 | 0.2633 |

Eight-row local Ollama smoke on the corrected holdout:

| Runner | Rows | Score |
|---|---:|---:|
| Echo input snippet, same first 8 rows | 8 | 0.1274 |
| `openclaw:latest` | 8 | 0.2481 |
| `openclaw:latest` + structural scaffold | 8 | 0.4880 |
| `openclaw:latest` + scaffold + contract repair | 8 | 0.4999 |
| `openclaw:latest` + scaffold + contract repair + lookup retry | 8 | 0.5168 |
| `qwen2.5-coder:1.5b` | 8 | 0.2272 |
| `qwen2.5-coder:1.5b` + structural scaffold | 8 | 0.4711 |

The scaffold result is the useful system result from this pass. Same local models, same benchmark rows, but the SCBE control layer nearly doubled the score:

| Model | Plain | Scaffold | Delta |
|---|---:|---:|---:|
| `openclaw:latest` | 0.2481 | 0.4880 | +0.2399 |
| `qwen2.5-coder:1.5b` | 0.2272 | 0.4711 | +0.2440 |

OpenClaw with scaffold plus the first repair pass reached 0.4999. Adding the lookup-table verification and clean retry loop reached 0.5168 on the latest reproducible 8-row smoke, with one earlier peak run at 0.5464. The useful change was not just "try again"; the runner now forces every answer through a public manual lookup surface before scoring:

- benchmark tongue map: KO/Python, AV/JavaScript, RU/Rust, CA/Mathematica, UM/Haskell, DR/Markdown,
- exact public algorithm identity,
- task-family contract,
- target fence language,
- tongue order,
- slot coverage.

The model still generates the answer. The harness now verifies whether the generated answer remembered the public tables and, when it does not, restarts the generation with the failed checks as correction data.

Task-family effect on the first eight rows:

| Task | OpenClaw plain | OpenClaw scaffold |
|---|---:|---:|
| identify | 0.2927 | 0.3659 |
| multiline_edit | 0.0000 | 0.2383 |
| translate_all | 0.0000 | 0.5581 |
| translate_one | 0.7500 | 0.6964 |
| align | 0.1919 | 0.2323 |

Latest lookup-retry task-family effect:

| Task | OpenClaw scaffold + repair + lookup retry |
|---|---:|
| identify | 0.4146 |
| multiline_edit | 0.5872 |
| translate_all | 0.4890 |
| translate_one | 0.6964 |
| align | 0.2727 |

Every row in the latest run reached structural preservation 1.0. That means the current remaining bottleneck is token/content quality inside valid structures, not missing headers, slots, or target fences.

## Failure Lessons

The models are not failing because they cannot code simple functions. They are failing the benchmark contract.

Observed failure classes:

- `translate_all` collapses to one language instead of emitting all six tongue sections. This drives structural preservation to zero.
- `multiline_edit` emits normal code or a diff instead of the expected multi-tongue, slot-marked edited surface.
- `align` tends to summarize the source rather than produce the required slot-alignment format.
- Both models often answer as generic coding assistants instead of obeying the benchmark output grammar.

This is exactly the useful lesson: the next improvement is not "bigger model first." It is a benchmark-aware contract adapter that forces:

1. exact `### TONGUE:<CODE>` headers for multi-tongue tasks,
2. exact `#slot:<name>` preservation when references require slots,
3. no diff format unless the prompt explicitly asks for a diff,
4. task-family-specific output skeletons before model generation,
5. row-level repair data from low-scoring predictions.

## Next Patch

Build a deterministic pre/post adapter for this benchmark:

- Pre-classify task family from `meta.task`.
- Inject a task-specific output skeleton. First scaffold pass is implemented in `run_ollama_submission.py`.
- Reject or repair outputs missing required structural markers before scoring.
- Export failed predictions plus expected structural signature as SFT repair rows.

That will test whether SCBE's edge is the control system around the model: same local weak models, better geometry/contract routing, higher benchmark score.

## Output-Improvement Research Notes

Current structured-output practice points toward four upgrades:

1. Schema-constrained generation where the runtime supports it. Ollama supports JSON-schema structured outputs through the `format` field; OpenAI Structured Outputs and tools like Guidance, LLGuidance, and Outlines follow the same general principle: make invalid structure impossible or unlikely at decoding time.
2. Validate then repair. A deterministic validator should check required headers, slot markers, code fences, tongue order, and task-family fields before scoring or delivery.
3. Deterministic rendering. Ask the model for a structured intermediate representation, then render markdown/code sections ourselves. This is better than asking weak models to manually format six long sections.
4. Separate structure score from content score. This pass fixed much of the structure gap; content recall now needs examples, task-specific repair rows, or a stronger model only for the content-bearing fields.

Next implementation target: add `--structured-json` so Ollama returns a schema-shaped intermediate object, then render the final Kaggle submission deterministically from that object. The lookup-retry loop showed the control layer is working; the remaining gap is content-level code quality inside the verified slots.
