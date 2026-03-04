# Nonlinear Model Routing Brief (2026-03-03)

## Objective

Move SCBE model routing from point labels to array/spectrum routing so each task
is matched across multiple intent axes (KO/AV/RU/CA/UM/DR), then combined with
cost and duty-cycle constraints.

## Primary Findings

1. Cost-quality routers can reduce spend significantly without large quality loss
   when model selection is done at request time.
2. Preference-trained routing transfers reasonably well across changing model
   pairs.
3. Sparse conditional routing (MoE) scales by selecting expert paths per input
   instead of using one fixed model path for all inputs.
4. Contextual bandit methods are practical for online exploration/exploitation
   tradeoffs and can improve click/utility outcomes under changing content pools.
5. Hyperbolic/Poincare embeddings are suitable when latent structure is
   hierarchical; this supports non-Euclidean routing semantics for intent trees.

## Applied to SCBE

Implemented in `src/fleet/switchboard.py`:

- task vector in 6-axis Sacred Tongue space:
  - `task_vector = f(task_type, prompt_keywords)`
- profile vector per specialist model:
  - `profile_vector = tongue_vector` in `model_duty_profiles.json`
- alignment:
  - `alignment = cosine(task_vector, profile_vector)`
- nonlinear boost:
  - `spectrum_boost = 1 + spectrum_bonus_pct * max(0, alignment)^2`
- full route score:
  - `final_score = base_value_cost_score * duty_boost * spectrum_boost`

This preserves existing value/cost and duty-cycle routing while adding a
continuous coherence signal.

## Why This Matters

- Better handling of mixed tasks (e.g., research+governance, code+architecture).
- Cleaner model specialization without hard class boundaries.
- Supports future online learning where axis weights are tuned from outcomes.

## Next Iteration Candidates

1. Online bandit adjustment of `spectrum_bonus_pct` per profile from observed
   outcome metrics.
2. Optional hyperbolic distance scorer for hierarchy-heavy tasks.
3. Multi-model quorum trigger when top-2 candidates are within a narrow margin.

## Sources

- FrugalGPT (arXiv): https://arxiv.org/abs/2305.05176
- RouteLLM (arXiv): https://arxiv.org/abs/2406.18665
- Switch Transformers (arXiv): https://arxiv.org/abs/2101.03961
- Contextual Bandits (arXiv/WWW): https://arxiv.org/abs/1003.0146
- UCB confidence bounds (JMLR): https://jmlr.org/papers/v3/auer02a.html
- Poincare Embeddings (arXiv): https://arxiv.org/abs/1705.08039
- LiteLLM Router docs: https://docs.litellm.ai/docs/routing

