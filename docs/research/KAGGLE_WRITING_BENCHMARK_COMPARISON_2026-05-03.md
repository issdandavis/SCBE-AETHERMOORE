# Kaggle Writing Benchmark Comparison - 2026-05-03

This note compares the new SCBE AI Fiction Quality Benchmark with real writing and text-generation benchmark patterns from Kaggle and adjacent public evaluation programs.

## Local Benchmark Built

Files:

- `scripts/benchmark/fiction_quality_benchmark.py`
- `config/eval/fiction_quality_benchmark.v1.json`
- `training-data/evals/fiction_quality_seed.jsonl`
- `tests/benchmark/test_fiction_quality_benchmark.py`
- `docs/benchmarks/FICTION_QUALITY_BENCHMARK_PLAN.md`

Current local result:

- rows: `3`
- average score: `72.281`
- pass count: `2`
- hold count: `1`
- test status: `4 passed`

The benchmark scores short fiction on:

- prompt adherence
- story coherence
- character continuity
- scene grounding
- prose naturalness
- rhythm and sound control
- specificity versus AI weirdness
- null-space structure
- emotional progression
- ending or transition

The null-space structure dimension is adapted from local Bible/null-space notes as absence detection, not as religious-content scoring. It checks whether a scene has durable anchors such as commitment, witness, boundary, pause/audit, or invitation/choice.

## Real Benchmark Shapes

### Automated Essay Scoring 2.0

Source: https://hippocampus-garden.com/kaggle_aes2/

Kaggle Automated Essay Scoring 2.0 graded essays on a 1-6 scale using quadratic weighted kappa. The major lesson for us is distribution shift. Strong solutions handled the mismatch between training sources and hidden test data instead of trusting public leaderboard fit.

How we match:

- We already separate local bootstrap scoring from public leaderboard claims.
- Our config names a future human-labeled target and keeps the heuristic judge as a bootstrap only.

Gap:

- We need human or committee labels before this can become a real Kaggle-grade competition.
- We need train/public/private split discipline, not random splits across similar prompt families.

### Feedback Prize / PERSUADE Style

Source: https://www.kaggle.com/datasets/julesking/tla-lab-persuade-dataset

The Feedback Prize ecosystem uses student writing, discourse/rhetorical labels, effectiveness labels, and holistic quality signals. This is closest to our "longer courses" idea because it can grade parts of writing, not just whole passages.

How we match:

- Our rubric is multi-dimensional and can create lesson units from dimension reports.
- Our training rule requires judged revision pairs rather than raw generated text.

Gap:

- We need explicit labels for fiction-specific discourse functions: setup, turn, anchor, pressure, reveal, choice, consequence, transition.
- We need a larger corpus of before/after revisions.

### LLM Detection And GenAI Text Evaluation

Sources:

- https://ai-challenges.nist.gov/t2t
- https://scale.stanford.edu/ai/repository/ai-write-essay-me-large-scale-comparison-human-written-versus-chatgpt-generated
- https://arxiv.org/abs/2410.17439

NIST GenAI Text-to-Text detection uses confidence scoring and metrics such as AUC, EER, TPR at fixed FPR, and Bayes risk. Stanford and arXiv work on AI-generated essays points to measurable differences between AI and human writing style, and newer scoring research warns that existing scoring features may need recalibration for AI-influenced text.

How we match:

- Our benchmark does not ask "is this AI?" as the main target.
- It instead scores the specific quality failures readers notice: generic phrase load, vague filler, weak grounding, and absent structure.

Gap:

- If we want a public detector lane, it should be separate from the quality lane.
- Quality score and AI-likeness score must not collapse into one moral label. Good AI-assisted prose can pass; bad human prose can fail.

### Kaggle Community Benchmarks

Source: https://blog.google/innovation-and-ai/technology/developers-tools/kaggle-community-benchmarks/

Kaggle Community Benchmarks are built for custom AI evaluations that can reflect real-world model behavior. This looks like the right future surface for our fiction benchmark because it can evaluate models directly rather than only accepting static CSV submissions.

How we match:

- We already have a task shape, local scorer, submission columns, and artifacts.
- The next step can be a community benchmark task where models receive prompts and output passages, then the scorer grades them.

Gap:

- We still need packaging against Kaggle's current benchmark SDK or notebook shape.
- We need a larger hidden test set and anti-overfit prompt families.

## Fit Score

Out of 100, current release readiness for a public Kaggle-style writing benchmark:

`54/100`

Why:

- `+20` local deterministic scorer exists.
- `+10` multi-dimensional rubric exists.
- `+8` seed JSONL and docs exist.
- `+8` tests pass.
- `+8` null-space structure gives a differentiating failure mode.
- `-18` no human-labeled train/public/private split yet.
- `-12` no Kaggle package or Community Benchmark SDK adapter yet.
- `-8` fiction-specific course taxonomy is still seed-level.
- `-10` no model-vs-model run evidence yet.

## Best Next Step

Build `fiction_quality_course_v1` with 50-100 hand-checked rows:

1. prompt
2. weak response
3. dimension scores
4. revision instruction
5. improved response
6. hidden holdout tag
7. genre/course stage

Then package a Kaggle-ready dry run with:

- `train.csv`
- `test.csv`
- `sample_submission.csv`
- `metric.py`
- `README.md`

The first public claim should be modest:

> "A deterministic bootstrap benchmark for grading and improving AI fiction quality, with multi-dimensional feedback and anti-generic-prose checks."
