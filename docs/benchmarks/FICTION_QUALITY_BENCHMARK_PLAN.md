# AI Fiction Quality Benchmark Plan

This benchmark is for grading AI-generated fiction so better writing courses and training rows can be built from evidence instead of vibes.

It does not ask whether the work was AI-generated. It asks whether the passage is good enough, coherent enough, and useful enough to train from or publish after review.

## Local Gate

Run:

```powershell
python scripts/benchmark/fiction_quality_benchmark.py --json
```

Equivalent npm script:

```powershell
npm run benchmark:fiction-quality -- --json
```

Inputs:

- `config/eval/fiction_quality_benchmark.v1.json`
- `training-data/evals/fiction_quality_seed.jsonl`

Outputs:

- `artifacts/benchmarks/fiction_quality/fiction_quality_benchmark_latest.json`
- `artifacts/benchmarks/fiction_quality/fiction_quality_benchmark_latest.md`

## Rubric

The bootstrap judge scores:

- prompt adherence
- story coherence
- character continuity
- scene grounding
- prose naturalness
- rhythm and sound control
- thought-track composition
- specificity versus AI weirdness
- null-space structure
- emotional progression
- ending or transition

The alliteration rule is deliberately balanced. Alliteration is useful when it modulates pressure, rhythm, and atmosphere. It becomes a penalty only when it turns into ornamental noise.

The thought-track composition rule treats prose like sheet music. Emotional, sensory, action, memory, and decision tracks become instruments. Each sentence is a phrase with word-duration, active instruments, and a compressed chord. Strong passages vary tracks, create transitions, and land with resolution rather than staying as one flat tonal block.

The null-space structure rule is adapted from the local Bible/null-space notes as an absence detector, not as a religious-content requirement. It checks whether a scene has any durable structural anchors: commitment, witness, boundary, pause/audit, or invitation/choice. AI fiction often sounds fluent while missing those load-bearing anchors.

## AI-Likelihood Lane

The benchmark now keeps authorship detection separate from quality.

Quality and AI detection are separate metrics. They should be treated like oil
and water in a cooking recipe: both can sit in the same workflow, but they have
different weights, different behavior, and different jobs. Do not blend them
into one score.

- `score` is the writing-quality score.
- `ai_detection.ai_likelihood_score` is a local heuristic signal for whether the passage looks machine-generated.
- `ai_detection.label` is one of `likely_human_or_human_edited`, `mixed_or_uncertain`, or `likely_ai_generated`.

This local detector is transparent and GLTR-inspired: it records generic-generation markers, vague filler, sentence-length variance, lexical diversity, missing anchors, thought-track coverage, and over-smoothness. It is not proof of authorship.

Open-source detector lanes to integrate next:

- GLTR style: interpretable statistical visualization for humans reviewing token probability artifacts.
- Binoculars style: zero-shot LLM detector based on contrasting two language models.
- RAID/Beemo style: benchmark datasets for measuring false positives, adversarial robustness, and human-edited machine text.

The important gate is false positives. Famous human writing can still get flagged by shallow detectors, especially when the passage is short or stylistically unusual. The blind round therefore reports public-domain false-positive or uncertain counts separately from the quality score.

The second important gate is false negatives. A passage can be 100 percent
AI-written and still read as human-edited if it is grounded, specific, and
revised. That means a low AI-likelihood score is not proof of human authorship.
It only means the current detector did not find enough detectable machine-like
pressure in the passage.

## Kaggle Shape

Public version:

- input: prompt, response, constraints, optional genre/course stage
- target: human or committee quality score from 0 to 100
- public metric: mean absolute error
- local bootstrap metric: deterministic SCBE score until enough human labels exist
- submission columns: `id`, `score`

## Training Rule

Do not train blindly on generated fiction.

Train on judged revision pairs:

1. prompt
2. weak response
3. dimension report
4. revision instruction
5. improved response
6. frozen holdout prompt result

Longer courses should be built by stacking these units from small scene skills to chapter-scale continuity.

## Package Surface

Package-ready wrapper:

- `packages/scbe-fiction-quality/package.json`
- `packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs`
- `packages/scbe-fiction-quality/README.md`

Local commands:

```powershell
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs score --json
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs blind-round --json
```

The npm wrapper is deliberately thin for now. Python remains the canonical
scoring implementation while the public CLI name, command verbs, reports, and
dataset shape stabilize.
