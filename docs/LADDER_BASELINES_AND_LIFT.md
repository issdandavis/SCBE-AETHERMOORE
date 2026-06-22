# Ladder Baselines & Lift — reproducible record (2026-06-19)

The thesis is **lift**: not a smarter model, the *same* model with its choices routed through logic-gates + tools. This is the first real measurement of that with a live local model. Machine-readable data: [`python/helm/ladder_baselines.json`](../python/helm/ladder_baselines.json).
Current `measure_lift(...)` output also includes `baseline_misses` and `tooled_misses` item IDs, so a reported lift can be audited by the exact questions each arm missed rather than only by aggregate totals.

## System setup (to reproduce)

- **OS:** Windows 11. Run from repo root with `PYTHONPATH=.`.
- **Model server:** [Ollama](https://ollama.com) local, default endpoint `http://127.0.0.1:11434` (OpenAI-compatible at `/v1`).
- **Model:** `qwen2.5-coder:1.5b` (≈1 GB). `qwen2.5-coder:3b` was removed during a disk cleanup — `ollama pull qwen2.5-coder:3b` to restore it, then re-run for its numbers.
- **Env overrides (optional):** `SCBE_LLM_BASE`, `SCBE_LLM_MODEL`, `SCBE_LLM_KEY` (default `ollama`). The climbers read these; defaults already point at local Ollama.
- **Modules:** `python/helm/reasoning_ladder.py` (math, exact-match), `python/helm/curriculum.py` (code, hidden-test via `public_bench`), `python/helm/ladder.py` (the shared kernel).

## Results

| | reasoning (math, /20) | code (/15) |
|---|---|---|
| **1.5B raw** | 8–9 (mean 8.3) | 13 |
| **3B raw** *(pre-removal)* | 10 | 13 |

- **Stable, not noise** (temp 0): code deterministic across runs; reasoning ±1.
- **Size isn't the lever:** 1.5B ≈ 3B on both ladders.
- **Domain matters:** these are *coder* models — strong on code (~87%), weak on math reasoning (~45%).
- **Walls** (consistent misses): code — `fizzbuzz` (drops the stated `%15` rule; public passes, hidden fails); reasoning — hard tier 3–5 plus `p4` (perimeter 5×8, a real miss, not extraction).

### LIFT — the headline (PR #2456)

| reasoning ladder, /20 | RAW (mental math) | PAL (routed through code execution) | lift |
|---|---|---|---|
| **1.5B** | 8–9 | **15** (stable ×3) | **+6 to +7** |
| **3B** | 10 | **17–18** (stable) | **+7 to +8** |

`program_aided_climber`: the model **writes** a short Python program that computes the answer; it runs in a sandboxed subprocess; we read the printed number. Same weights — only the *routing* changed. The lift holds across both models and scales slightly with the base.

**Honest caveats:** program-aided reasoning (PAL/PoT) is an established technique, not novel here. It lifts *computation-heavy* reasoning specifically (plays to a coder model's strength: writing code), and is **not** universal — tool/rails routing gave no lift on some tasks elsewhere. The contiguous-tier metric *understates* it (PAL trips one trivial arithmetic item → reads tier 0); the **total** (8.3 → 15) is the signal.

### Same routing on the CODE ladder — and the contrast that matters

`make_repair_generator`: write code → run the **public** test → on failure, feed the error back and retry (hidden held out, no leakage).

| code ladder, /15 | RAW (single shot) | repair (2 rounds) | lift |
|---|---|---|---|
| **1.5B** | 13 | **13** | **+0** |
| **3B** | 13 | **13** | **+0** |

The +0 is the finding, not a dud. The loop **fires** on the remaining misses (public fails for `fizzbuzz` + `regex`; a unit test proves it retries with the failure in the prompt) — but the model regenerates code that *still fails*. It can't act on the signal: `fizzbuzz` is a **prior-override** (it keeps writing the reflexive Fizz/Buzz despite the failing test), `regex` is a real **capability ceiling**.

**The lesson:** tool-routing lifts when it **supplies a missing capability** (compute the math the model can't do in its head → reasoning **+6–7**); it does **nothing** when the failure is a prior or capability ceiling (code **+0**). This is "harness rescues interface/computation gaps, not capability" in two contrasting measurements.

## Reproduce

```bash
# raw baselines (both ladders, any installed model)
PYTHONPATH=. python -c "from python.helm.reasoning_ladder import run_reasoning, llm_climber; from python.helm.ladder import render_climb; print(render_climb(run_reasoning(llm_climber(model='qwen2.5-coder:1.5b')), 'RAW 1.5b'))"

# the lift: raw vs program-aided, SAME model both slots
PYTHONPATH=. python -c "from python.helm.reasoning_ladder import measure_lift, llm_climber, program_aided_climber; print(measure_lift(llm_climber(model='qwen2.5-coder:1.5b'), program_aided_climber(model='qwen2.5-coder:1.5b')))"
```
