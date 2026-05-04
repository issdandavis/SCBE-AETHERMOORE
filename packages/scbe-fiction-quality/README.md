# scbe-fiction-quality

`scbe-fiction-quality` is a package-ready command line interface for the SCBE
fiction-quality benchmark.

It grades prose for usable story quality rather than only detecting whether it
was written by AI. The current scorer is deterministic and checks prompt
adherence, coherence, character continuity, grounded scene detail, naturalness,
rhythm, thought-track composition, null-space structure, emotional progression,
and transition quality.

The report also includes a separate `ai_detection` lane. That lane estimates
AI-likelihood with transparent stylometric signals and should be treated as a
false-positive probe, not proof of authorship.

## Install

From npm after publication:

```bash
npm i -g scbe-fiction-quality
```

From this repository before publication:

```bash
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs --help
```

## Usage

Run the seed benchmark:

```bash
scbe-fiction-quality score --json
```

Run the blind comparison round:

```bash
scbe-fiction-quality blind-round --json
```

Run the reader-edition book sweep:

```bash
scbe-fiction-quality book-sweep --json
```

Run a public-domain reference book sweep:

```bash
scbe-fiction-quality reference-book --json
```

Compare AI-likelihood detector lanes across the current manuscript and
reference sweeps:

```bash
scbe-fiction-quality detect --json
```

Run the multi-lane rubric council:

```bash
scbe-fiction-quality council --json
```

Use a custom input file:

```bash
scbe-fiction-quality score --input training-data/evals/fiction_quality_seed.jsonl --json
```

## Commands

- `score` runs `scripts/benchmark/fiction_quality_benchmark.py`.
- `blind-round` runs `scripts/benchmark/fiction_quality_blind_round.py`.
- `book-sweep` runs `scripts/benchmark/book_quality_sweep.py`.
- `reference-book` runs `scripts/benchmark/reference_book_quality_sweep.py`.
- `detect` runs `scripts/benchmark/ai_detection_comparison.py`.
- `council` runs `scripts/benchmark/writing_rubric_council.py`.
- `version` prints the npm package version.

## Current Architecture

The npm command is intentionally a thin wrapper around the Python benchmark
scripts in SCBE-AETHERMOORE. That keeps the scoring logic in one canonical place
while the package interface stabilizes.

Later package work can move the scorer into a bundled library or publish the
benchmark assets as a dataset package without changing the command names.

## Output

The local benchmark writes:

- `artifacts/benchmarks/fiction_quality/fiction_quality_benchmark_latest.json`
- `artifacts/benchmarks/fiction_quality/fiction_quality_benchmark_latest.md`
- `artifacts/benchmarks/fiction_quality/fiction_quality_blind_round_latest.json`
- `artifacts/benchmarks/fiction_quality/fiction_quality_blind_round_latest.md`
- `artifacts/benchmarks/fiction_quality/book_quality_sweep_latest.json`
- `artifacts/benchmarks/fiction_quality/book_quality_sweep_latest.md`
- `artifacts/benchmarks/fiction_quality/reference_book_quality_sweep_latest.json`
- `artifacts/benchmarks/fiction_quality/reference_book_quality_sweep_latest.md`
- `artifacts/benchmarks/fiction_quality/ai_detection_comparison_local_latest.json`
- `artifacts/benchmarks/fiction_quality/ai_detection_comparison_local_latest.md`
- `artifacts/benchmarks/fiction_quality/writing_rubric_council_latest.json`
- `artifacts/benchmarks/fiction_quality/writing_rubric_council_latest.md`

## Metric Separation

Quality and AI detection are intentionally separate.

- Quality asks whether the prose works for readers.
- AI detection asks what generated-text artifacts a detector can observe.
- Mimicry checks observable patterns.
- Imagination and creative construction are judged by coherence, surprise,
  reader effect, continuity, and revision usefulness.

Do not blend these into one score. A passage can be AI-written and still pass
quality; a human passage can fail quality; a detector can miss grounded AI and
still be useful as a calibration signal.

## Publish

Maintainer dry run:

```bash
cd packages/scbe-fiction-quality
npm pack --dry-run --json
```

Public publish:

```bash
npm publish --access public
```
