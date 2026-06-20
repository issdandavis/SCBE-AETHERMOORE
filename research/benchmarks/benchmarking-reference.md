# Benchmarking reference — tools, scoring, proper operation, templates

**Why this file:** SCBE already makes performance claims (e.g. "109x Python," "67% cheaper
than round-robin," polyglot build-speed). A number nobody can reproduce is marketing, not
evidence. This is the standard for running benchmarks here so the claims survive scrutiny —
plus copy-paste score templates. Honest discipline: report the metric definition, the
environment, and the spread, or don't publish the number.

---

## 1. Goals — what a benchmark is *for*

| Goal | Question it answers | Consumer |
|---|---|---|
| Regression detection | "Did this commit make it slower?" | CI gate |
| A/B comparison | "Is X faster than Y, and by how much?" | design decisions, marketing |
| Capacity planning | "How much load can this take?" | ops / sizing |
| Competition / leaderboard | "How do we rank vs others?" | Kaggle, MLPerf |
| Quality-at-budget | "Best accuracy within N tokens/$/ms?" | ML / LLM eval |

Pick the goal *first* — it determines the metric, the rigor, and the template.

---

## 2. Types (know which one you're running)

- **Micro vs macro:** microbenchmark = one function/op in isolation (nanoseconds, easy to
  fool with dead-code elimination); macro/application = end-to-end realistic workload.
- **Latency vs throughput:** latency = time per op (report percentiles p50/p95/p99, not just
  mean); throughput = ops/sec or items/sec under load.
- **Cold vs warm:** cold = first run (caches empty, JIT cold); warm = steady state. Report
  which, and warm up before measuring warm.
- **Wall-clock vs CPU time:** wall includes waiting/IO; CPU is compute only. State which.
- **Build-time vs run-time:** SCBE's polyglot bench is build-time; keep it separate from
  encoder run-time numbers.
- **Fixed-budget quality (ML/LLM):** hold a budget (tokens, $, ms, epochs) and measure
  quality, or hold a quality target and measure cost (MLPerf's time-to-train-to-target).

---

## 3. Proper operation — the rules that make a number trustworthy

1. **Isolate the environment.** Dedicated machine or pinned CI runner. CPU governor =
   `performance`, disable turbo/boost variance where possible, close background apps, avoid
   thermal throttling, prefer pinning to specific cores. Never benchmark on a busy laptop and
   publish it as fact.
2. **Warm up.** Discard the first N runs (page cache, JIT, branch predictors). Disk/IO-bound
   work *especially* needs warmup. For cold-start numbers, measure cold deliberately and say so.
3. **Repeat enough.** ≥10 runs minimum; 30+ for stable estimates; 50+ if noisy. Let the tool
   decide when stable if it supports it (hyperfine `--min-runs`, Google Benchmark auto-iters).
4. **Report the spread, not just the center.** Always: **mean, median, stddev, min, max,
   CV%** (coefficient of variation = stddev/mean), and a **95% confidence interval**. A
   **CV below ~2%** is stable/trustworthy; high CV means the result is noise — fix the setup
   before reporting. Prefer **median + IQR** for skewed timing data (one GC pause skews mean).
5. **Fix randomness.** Pin seeds. Same input data across compared variants.
6. **Measure the right thing.** Exclude setup/teardown from the timed region. Guard against
   the compiler optimizing your work away — use `black_box`/`benchmark::DoNotOptimize`/
   `volatile` sinks.
7. **Record the environment** with every result: CPU model, core count, RAM, OS + version,
   compiler/runtime + version, dependency versions, **commit SHA**, date, and the exact
   command. Without this, the number is unreproducible.
8. **Don't compare across machines.** Only compare runs from the same environment, or
   normalize honestly and label it an estimate.
9. **Avoid overfitting the metric.** Keep a holdout (this is *why* Kaggle splits public/
   private). If you tune to the benchmark, you're optimizing the test, not the system.
10. **State the metric definition exactly.** "100x faster" is meaningless without: faster at
    *what*, vs *what baseline*, on *what input*, measuring *what time*, over *how many runs*,
    with *what spread*.

---

## 4. Tool matrix (open-source, by domain)

| Domain | Tool | What it gives you |
|---|---|---|
| CLI / whole-command | **hyperfine** | warmup, min/max runs, mean±σ, relative speedup, JSON/CSV/MD export, `--prepare` for cache reset |
| Python micro | **pytest-benchmark** | min/max/mean/median/stddev/IQR/OPS/rounds, JSON, autosave baselines, compare + regression fail |
| Rust micro | **criterion.rs** | bootstrap confidence intervals, saved baselines, auto regression/improvement detection, plots (`cargo bench`) |
| C/C++ micro | **google/benchmark** | auto iteration count, real/CPU time, items/bytes per sec, `--benchmark_repetitions` + mean/median/stddev/cv, JSON |
| Java | **JMH** | warmup iters, forks, modes (throughput/avgtime/sampletime), CIs |
| .NET | **BenchmarkDotNet** | warmup, multiple runtimes, memory diagnostics, MD/HTML/CSV exporters |
| ML training/inference | **MLPerf** (MLCommons) | standardized tasks, closed/open divisions, time-to-target / throughput at quality |
| LLM eval | **lm-evaluation-harness** (EleutherAI), **HELM** | many academic tasks, standardized prompting + scoring |
| LLM code | **HumanEval** (pass@k), **MBPP**, **SWE-bench** (% issues resolved), **LiveCodeBench** | functional-correctness via unit tests / real GitHub fixes |
| Systems / HW | **Phoronix Test Suite**, **sysbench**, **fio** (IO), **stress-ng**, **coremark** | CPU/mem/disk/system stress + scores |
| DB / web load | **TPC-C/TPC-H**, **wrk/wrk2**, **ab**, **k6** | transactions/sec, request latency percentiles |
| Continuous benchmarking | **Bencher**, **CodSpeed**, **github-action-benchmark** | track results over time, alert on regression in CI |

Rule of thumb: **use a language-native micro-framework** (criterion/pytest-benchmark/Google
Benchmark) for code, **hyperfine** for whole-program/CLI, and a **domain suite** (MLPerf,
lm-eval-harness) when there's an accepted standard — don't roll your own timer if a standard exists.

---

## 5. Kaggle CLI — operation & scoring

**Install / auth.** `pip install kaggle`. Create an API token at kaggle.com → Settings → API →
*Create New Token* → `kaggle.json`. Put it at `~/.kaggle/kaggle.json` (Windows
`%USERPROFILE%\.kaggle\kaggle.json`) and `chmod 600`, or set `KAGGLE_USERNAME` / `KAGGLE_KEY`
env vars.

**Core commands:**
```
kaggle competitions list                                  # discover
kaggle competitions files  -c <competition>               # data files
kaggle competitions download -c <competition>             # get data
kaggle competitions submit -c <competition> -f sub.csv -m "msg"   # submit predictions
kaggle competitions submissions -c <competition>          # your past scores
kaggle competitions leaderboard -c <competition> --show   # standings
kaggle kernels push   -p <dir>     # run a notebook on Kaggle compute (uses kernel-metadata.json)
kaggle kernels status <user/slug>  # check run state
kaggle kernels output <user/slug> -p <dir>   # pull results/artifacts
kaggle datasets create -p <dir>    # publish a dataset (uses dataset-metadata.json)
```

**How scoring works (competitions):**
- You submit predictions (or a kernel that produces them). Kaggle scores them with a fixed
  metric chosen per competition (e.g. AUC, RMSE, LogLoss, accuracy, mAP).
- **Public/Private split:** the test set is divided into a **public** subset (drives the live
  leaderboard during the competition) and a **private** subset (hidden, decides final rank).
  The split is the same for everyone and unknown to you. Final standings use the private score —
  this is the anti-overfitting mechanism. Tuning to the public LB and crashing on private is
  the classic failure ("LB shakeup").
- For SCBE's use (free GPU/CPU compute via kernels, not competing): use `kernels push` to run
  benchmarks on Kaggle's machines, `kernels status`/`output` to retrieve. Record Kaggle's
  hardware in the result's environment block — it is *not* your machine.

---

## 6. Score templates (copy-paste)

### 6a. Universal benchmark result (the "full score template")
See `research/benchmarks/score-template.json` for the machine-readable version. Every
published number should fill this out:

```json
{
  "benchmark": "ast-cube-encoder",
  "metric": { "name": "wall_time", "unit": "s", "lower_is_better": true,
              "definition": "end-to-end encode of fixture corpus, parse+walk included, excludes process startup" },
  "result": { "mean": 0.0, "median": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0,
              "cv_pct": 0.0, "ci95": [0.0, 0.0], "unit": "s", "runs": 30, "warmup_runs": 5 },
  "baseline": { "name": "python-reference", "median": 0.0, "speedup_x": 0.0 },
  "input": { "description": "fixture corpus", "size": "N files / M LOC", "seed": 0 },
  "environment": { "cpu": "", "cores": 0, "ram_gb": 0, "os": "", "runtime": "",
                   "toolchain_versions": {}, "commit": "", "date": "YYYY-MM-DD", "machine_class": "dedicated|ci|laptop|kaggle" },
  "command": "exact command line used",
  "notes": "anomalies, caveats, what was excluded"
}
```

### 6b. A/B comparison table (markdown, for PRs/README)
```
| Variant   | Median | CV%  | vs baseline | Runs | Notes        |
|-----------|--------|------|-------------|------|--------------|
| baseline  | 1.000s | 1.2  | 1.00x       | 30   | python ref   |
| candidate | 0.012s | 1.8  | 83x faster  | 30   | rust encoder |
```
Rule: speedup = baseline_median / candidate_median; only quote it if both CV% < ~5%.

### 6c. Leaderboard template
```
| Rank | Entry        | Score (metric↓/↑) | Runs | Env hash | Date       |
|------|--------------|-------------------|------|----------|------------|
| 1    | rust+ruff    | 0.0118 s          | 30   | a1b2c3   | 2026-06-15 |
| 2    | rust         | 0.0240 s          | 30   | a1b2c3   | 2026-06-15 |
```

### 6d. Kaggle `kernel-metadata.json` (for `kaggle kernels push`)
```json
{
  "id": "<username>/scbe-rubix-bench",
  "title": "SCBE Rubix Bench",
  "code_file": "rubix_bench.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": false,
  "enable_internet": false,
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": []
}
```

### 6e. Regression gate (CI pass/fail)
```
FAIL the build if: candidate_median > baseline_median * (1 + tolerance)   # e.g. tolerance 0.10
ALSO FAIL if: cv_pct > max_cv   # e.g. 5.0 — noisy run is not a valid measurement, re-run
Tools that do this for you: pytest-benchmark --benchmark-compare-fail, criterion baselines,
github-action-benchmark alert-threshold.
```

---

## 7. Applying this to SCBE's existing claims

For each published number ("109x," "67% cheaper," polyglot build-speed), attach a **claim
card** = section 6a filled out. Specifically:

- **"109x Python" (Rust AST encoder):** state it's *parse+walk wall-time, median of ≥30 runs,
  same fixture corpus, CV% reported, on <env>, commit <sha>*. Note parsing was 93% of time —
  so the metric is parse-dominated; say that.
- **"67% cheaper than round-robin" (geometric router):** define cost (tokens? simulated $?),
  the workload, the baseline router config, runs, and that it's a *simulation*, not measured
  production spend. Mark it modeled.
- **Polyglot build-speed:** build-time only, per-language, cold vs warm stated, toolchain
  versions pinned.

A claim with a filled card is sellable. A claim without one is a liability — the first
skeptic who can't reproduce it discredits the rest.

---

## Sources
- Kaggle CLI / API: [kaggle-cli docs](https://github.com/Kaggle/kaggle-cli/blob/main/docs/competitions.md), [competition commands](https://deepwiki.com/Kaggle/kaggle-api/4.1-competition-commands), [CLI cheat sheet](https://www.kdnuggets.com/kaggle-cli-cheat-sheet), [public vs private LB](https://www.kaggle.com/general/380742)
- MLPerf: [Inference datacenter](https://mlcommons.org/benchmarks/inference-datacenter/), [Training](https://mlcommons.org/benchmarks/training/), [inference rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc)
- Micro-benchmark tools: [pytest-benchmark](https://pytest-benchmark.readthedocs.io/en/latest/usage.html), [hyperfine guide](https://how2.sh/posts/how-to-benchmark-commands-with-hyperfine/), [Bencher pytest-benchmark guide](https://bencher.dev/learn/benchmarking/python/pytest-benchmark/)
- Methodology / stats: [coefficient of variation](https://en.wikipedia.org/wiki/Coefficient_of_variation)
- LLM/code eval: [HumanEval to SWE-bench](https://runloop.ai/blog/understanding-llm-code-benchmarks-from-humaneval-to-swe-bench), [evaluation harness](https://arize.com/blog/what-is-an-evaluation-harness/)
