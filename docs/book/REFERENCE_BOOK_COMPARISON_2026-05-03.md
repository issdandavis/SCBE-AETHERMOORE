# Reference Book Comparison

Date: 2026-05-03

## Scope

This pass benchmarks the current reader-edition manuscript against one complete public-domain reference book:

- manuscript: `content/book/reader-edition/`
- reference: `Frankenstein; or, the Modern Prometheus` by Mary Wollstonecraft Shelley
- reference source: `https://www.gutenberg.org/ebooks/84.txt.utf-8`

The benchmark samples opening, middle, and closing windows from each chapter-like file. It is a local editing heuristic, not a literary authority claim. AI-likelihood is reported as a separate stylometric signal and does not feed the prose-quality score.

## Results

| Book | Sections | Samples | Average quality | HOLD count | HOLD rate | Average AI-likelihood |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| The Six Tongues Protocol | 41 | 123 | 69.172 | 105 | 85.4% | 16.813 |
| Frankenstein | 28 | 84 | 68.260 | 75 | 89.3% | 21.306 |

Delta:

- The Six Tongues Protocol scores `+0.912` above the reference on this heuristic.
- The Six Tongues Protocol has `-4.493` lower average AI-likelihood than the reference.
- Both books produce many HOLD decisions because the scorer is intentionally strict at short-window scale.

## Interpretation

This is a useful reality check. A famous public-domain novel does not score near 100 on the current benchmark. That means the gate is functioning more like an editing pressure map than a pass/fail verdict on whether a book is "good."

The AI-likelihood lane is even more important as a calibration check. If a human public-domain reference like Frankenstein receives non-zero AI-likelihood, the detector is showing stylistic pressure, not proving authorship. That makes it useful for "why did this passage get flagged?" review, but not useful as a standalone truth source.

## AI Detector Verification Pass

Quality and AI detection are separate metrics. They are not two flavors of the same score. Quality asks whether the passage works as prose. AI detection asks whether the passage carries detectable generated-text artifacts. In practice, they behave like oil and water in a recipe: both matter, but they have different weights and should not be blended into one verdict.

Command:

```powershell
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs detect --json
```

Result:

| Detector | Book | Samples | Average AI-likelihood | Max AI-likelihood | Labels |
| --- | --- | ---: | ---: | ---: | --- |
| local transparent stylometric | The Six Tongues Protocol | 123 | 16.813 | 49.357 | 123 likely human/human-edited |
| local transparent stylometric | Frankenstein | 84 | 21.306 | 42.200 | 84 likely human/human-edited |

Interpretation:

- The detector did not classify either book as generated.
- Frankenstein still scored higher on average AI-likelihood than the manuscript.
- The manuscript is known to be AI-written, so this is a detector false negative at book scale.
- Therefore the AI-likelihood score is a false-positive/calibration pressure map, not an authorship verdict.
- This supports using famous public-domain books as negative controls before trusting any detector threshold.

Calibration gate:

- Current status: `UNDER_SENSITIVE`
- Known AI control false negatives in the blind round: `1`
- Meaning: the detector catches generic AI writing but misses grounded, edited, or human-like AI writing.
- Best interpretation: either the manuscript is better than generic AI-book slop, or the detector is too weak to identify high-quality AI authorship. The evidence supports both, but the detector weakness is the stronger conclusion.

Open-source external adapter status:

```powershell
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs detect --detector superannotate-http --timeout 2 --max-external-samples 1 --json
```

Result: the local SuperAnnotate HTTP service was not running on `127.0.0.1:8080`, so the adapter emitted `detector_status.ok=false` and did not send the manuscript to any third-party service.

The strongest current use is comparative:

- find weak windows inside one manuscript
- compare those weak windows against public-domain references
- revise for concrete scene grounding, emotional motion, and thought-track composition
- keep AI-likelihood separate so the system does not optimize toward detector-gaming

## Current Manuscript Targets

Lowest The Six Tongues Protocol windows:

1. `interlude-09-tovak-hides:closing` - score `62.518`, AI-likelihood `23.264`
2. `interlude-08-the-pipe:middle` - score `62.676`, AI-likelihood `20.469`
3. `ch26:opening` - score `62.909`, AI-likelihood `23.000`
4. `interlude-07-nadia-runs:closing` - score `63.015`, AI-likelihood `26.182`
5. `ch20:middle` - score `63.154`, AI-likelihood `23.097`

Highest manuscript AI-likelihood windows:

1. `ch21:middle` - quality `66.124`, AI-likelihood `49.357`
2. `interlude-06-jorren-records:opening` - quality `64.941`, AI-likelihood `28.096`
3. `ch13:closing` - quality `63.716`, AI-likelihood `28.009`
4. `ch04:middle` - quality `64.035`, AI-likelihood `28.000`
5. `ch15:middle` - quality `65.748`, AI-likelihood `28.000`

## Reference Targets

Lowest Frankenstein windows:

1. `028-chapter-24:closing` - score `61.843`, AI-likelihood `28.000`
2. `006-chapter-2:opening` - score `62.161`, AI-likelihood `28.000`
3. `005-chapter-1:middle` - score `62.571`, AI-likelihood `24.727`
4. `007-chapter-3:closing` - score `62.965`, AI-likelihood `28.000`
5. `026-chapter-22:closing` - score `63.188`, AI-likelihood `22.000`

This matters because the manuscript's weakest windows are in the same rough band as weak windows from a canon reference. The next goal is not "make every sample 100." The next goal is to push the manuscript's weak floor upward while preserving voice.

## Commands

```powershell
python scripts/benchmark/book_quality_sweep.py --json
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs reference-book --json --refresh
node packages/scbe-fiction-quality/bin/scbe-fiction-quality.cjs detect --json
python -m pytest tests/benchmark/test_fiction_quality_benchmark.py -q
```

Artifacts:

- `artifacts/benchmarks/fiction_quality/book_quality_sweep_latest.json`
- `artifacts/benchmarks/fiction_quality/book_quality_sweep_latest.md`
- `artifacts/benchmarks/fiction_quality/reference_book_quality_sweep_latest.json`
- `artifacts/benchmarks/fiction_quality/reference_book_quality_sweep_latest.md`
- `artifacts/benchmarks/fiction_quality/ai_detection_comparison_local_latest.json`
- `artifacts/benchmarks/fiction_quality/ai_detection_comparison_local_latest.md`
- `artifacts/benchmarks/fiction_quality/reference_books/frankenstein/source_manifest.json`
