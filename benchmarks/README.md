# benchmarks/

Benchmarks that measure the governance pipeline against baselines.

| Path | What it is |
|------|------------|
| `scbe/` | The benchmark framework, run with `python -m benchmarks.scbe`. Subpackages: `attacks/` (generator producing 400+ attacks in 20 categories, plus an adaptive mutating attacker), `baselines/` (allow-everything baseline, ProtectAI DeBERTa guard, SCBE `RuntimeGate` wrapper), `datasets/`, `metrics/` (ASR, FPR, precision, recall, F1, and SCBE-specific drift metrics), `runners/`, `reports/` |
| `scbe_agentic_v1/` | Repo-native agentic tasks, each a `task.json` with a checkable outcome. Has its own README |
| `scbe_governance_benchmark.ipynb`, `scbe_benchmark_standalone.py` | Notebook benchmark and its auto-extracted script form |
| `results/` | One recorded local run (JSON) and the adversarial peer-review prompts and reviews written about it |

Results in `results/` are point-in-time records of one machine's run, not continuously verified numbers. Benchmark *drivers* that call out to external tools live in `scripts/benchmark/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/benchmarks.md`](../docs/file-index/benchmarks.md).
