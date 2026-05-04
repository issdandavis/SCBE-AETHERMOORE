# The Six Tongues Protocol Quality Sweep Review

Date: 2026-05-03

## Scope

Target manuscript:

- `content/book/reader-edition/`
- Title: The Six Tongues Protocol
- Author: Issac Daniel Davis

The sweep uses `scripts/benchmark/book_quality_sweep.py`, which samples opening, middle, and closing windows from each reader-edition chapter or interlude. It ignores AI authorship for the prose-quality score and reports AI-likelihood separately.

## Baseline After Punctuation Fix

The first useful sweep preserved sentence boundaries and punctuation.

- samples: 123
- chapters/interludes: 41
- average quality score: 69.077
- weakest chapter window: `ch20:closing`
- `ch20` average quality score: 62.855
- `ch20` average AI-likelihood: 29.766

The earlier lower sweep was discarded as diagnostic noise because it flattened punctuation before scoring.

## Revision Applied

Updated:

- `content/book/reader-edition/ch20.md`

Quality-only goal:

- add concrete object anchoring with the bone tablet
- add rain, touch, and storm detail
- turn abstract realization into a visible commitment
- remove repeated vague `thing` language from the sampled ending
- preserve the same plot beat: Marcus and Polly recognize the missing seventh silence and move toward Dremsreach

## Post-Revision Result

Latest sweep:

- average manuscript quality score: 69.172
- `ch20` average quality score: 66.725
- `ch20` minimum score: 63.154
- `ch20` average AI-likelihood: 18.025

Movement:

- manuscript average: +0.095
- `ch20` average quality: +3.870
- `ch20` minimum sample: +8.593
- `ch20` average AI-likelihood: -11.741

Interpretation:

The revision improved the weakest chapter without using AI-likelihood as the quality target. The AI-likelihood drop happened as a side effect of better prose: fewer vague placeholders, more concrete sensory anchors, and a clearer action/commitment beat.

## Current Weakest Quality Targets

Next prose-quality targets from the latest sweep:

1. `interlude-09-tovak-hides:closing` — score 62.518
2. `interlude-08-the-pipe:middle` — score 62.676
3. `ch26:opening` — score 62.909
4. `interlude-07-nadia-runs:closing` — score 63.015
5. `ch20:middle` — score 63.154

Common weaknesses:

- low thought-track composition
- low scene grounding
- low emotional progression
- flat or abstract explanatory density

## AI-Likelihood Subtraction Targets

The highest AI-likelihood sample is still:

- `ch21:middle`
- quality score: 66.124
- AI-likelihood: 49.357

Detected reasons:

- `synthetic_fiction_pressure`: `chosen`
- `over_smooth_signal`: 7.0
- `thought_track_coverage`: 0
- `null_space_family_count`: 0
- `vague_filler_count`: 1

This should be treated as the first "negative-space subtraction" pass later: preserve meaning, then add concrete anchors and a stronger action/emotion track without flattening the voice.

## Embodied Negative-Space Revision

Updated:

- `content/book/reader-edition/interlude-09-tovak-hides.md`
- `external/codex-skills-live/book-manuscript-edit/SKILL.md`

Revision principle:

- use sensory detail like an instrument panel, not the road
- give the reader enough edges, contrast, and missing signal to complete the image
- let darkness and absence do work instead of over-describing the scene
- improve quality without blending the AI-detection lane into the quality score

Movement:

- manuscript average quality score: `69.172` -> `69.271`; after spelling out the Sacred Tongue names and adding off-stage professional presence to exposition-heavy scenes, the current sweep is `69.208`
- manuscript HOLD count: `105` -> `104`
- `interlude-09-tovak-hides:closing`: `62.518` -> `73.199`
- `interlude-09-tovak-hides:closing` AI-likelihood: `23.264` -> `9.000`
- council promotion decision remains `PROMOTE_QUALITY_GATE_ONLY`
- embodied senses lane remains `HOLD`, which is correct: it is an instrument panel for revision, not a checklist command

## Commands

```powershell
python scripts/benchmark/book_quality_sweep.py --json
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs book-sweep --json
python -m pytest tests/benchmark/test_fiction_quality_benchmark.py -q
```

Latest artifacts:

- `artifacts/benchmarks/fiction_quality/book_quality_sweep_latest.json`
- `artifacts/benchmarks/fiction_quality/book_quality_sweep_latest.md`
