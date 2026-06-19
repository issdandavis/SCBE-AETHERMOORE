# Ladder Baselines & Lift — reproducible record (2026-06-19)

The thesis is **lift**: not a smarter model, the *same* model with its choices routed through logic-gates + tools. This is the first real measurement of that with a live local model. Machine-readable data: [`python/helm/ladder_baselines.json`](../python/helm/ladder_baselines.json).

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

| 1.5B, reasoning ladder | total /20 |
|---|---|
| RAW (mental math) | 8–9 |
| **PAL (routed through code execution)** | **15** (stable ×3) |
| **lift** | **+6 to +7** |

`program_aided_climber`: the model **writes** a short Python program that computes the answer; it runs in a sandboxed subprocess; we read the printed number. Same weights — only the *routing* changed.

**Honest caveats:** program-aided reasoning (PAL/PoT) is an established technique, not novel here. It lifts *computation-heavy* reasoning specifically (plays to a coder model's strength: writing code), and is **not** universal — tool/rails routing gave no lift on some tasks elsewhere. The contiguous-tier metric *understates* it (PAL trips one trivial arithmetic item → reads tier 0); the **total** (8.3 → 15) is the signal.

## Reproduce

```bash
# raw baselines (both ladders, any installed model)
PYTHONPATH=. python -c "from python.helm.reasoning_ladder import run_reasoning, llm_climber; from python.helm.ladder import render_climb; print(render_climb(run_reasoning(llm_climber(model='qwen2.5-coder:1.5b')), 'RAW 1.5b'))"

# the lift: raw vs program-aided, SAME model both slots
PYTHONPATH=. python -c "from python.helm.reasoning_ladder import measure_lift, llm_climber, program_aided_climber; print(measure_lift(llm_climber(model='qwen2.5-coder:1.5b'), program_aided_climber(model='qwen2.5-coder:1.5b')))"
```
