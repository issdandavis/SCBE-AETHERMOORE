# SCBE Eval Pack

This directory is the canonical local reproduction lane for the current public adversarial benchmark story.

## Scope

The public benchmark claim currently points to:

- 91 adversarial prompts in the local test corpus
- 15 clean prompts in the local baseline set
- a local pytest runner for the corpus
- a local comparison script for the industry/baseline table

## Canonical files

- Corpus source: [tests/adversarial/attack_corpus.py](../../tests/adversarial/attack_corpus.py)
- Corpus runner: [tests/adversarial/test_adversarial_benchmark.py](../../tests/adversarial/test_adversarial_benchmark.py)
- Industry comparison: [scripts/benchmark/scbe_vs_industry.py](../../scripts/benchmark/scbe_vs_industry.py)
- Verification note: [docs/research/BENCHMARK_VERIFICATION_2026-03-23.md](../research/BENCHMARK_VERIFICATION_2026-03-23.md)
- Eval manifest: [manifest.json](manifest.json)
- One-step runner: [scripts/eval/run_scbe_eval.ps1](../../scripts/eval/run_scbe_eval.ps1)

## Reproduction commands

```powershell
pytest tests/adversarial/test_adversarial_benchmark.py -v
python scripts/benchmark/scbe_vs_industry.py
Get-Content artifacts\benchmark\industry_benchmark_report.json
```

If you want a single scripted entrypoint:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/eval/run_scbe_eval.ps1
```

## Output locations

- `artifacts/benchmark/industry_benchmark_report.json`
- `artifacts/benchmark/latest/` (created by the one-step eval script)

## Claim boundaries

- The benchmark runner is measurement-oriented. It records rates and writes reports; it does not hard-code the public headline as a pass/fail gate.
- The comparison script may depend on local environment/model availability. Read its output as a documented comparison lane, not a universal guarantee across all hardware and provider setups.
- The safest public statement is reproducibility of the measured local run, not blanket claims about every possible deployment environment.

## Minimum reviewer path

1. Read [manifest.json](manifest.json)
2. Run the corpus benchmark
3. Run the comparison script
4. Inspect `artifacts/benchmark/industry_benchmark_report.json`
5. Compare those results against the current public tables
