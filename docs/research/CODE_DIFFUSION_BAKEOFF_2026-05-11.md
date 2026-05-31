# Code-Diffusion Bake-Off — coding_diffusion_bakeoff_v1

## Generator Pass-Rates

| Generator | Model | Pass | Rate | Artifact |
|---|---|---:|---:|---|
| ar | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | 4/12 | 0.333 | `artifacts/eval/diffusion_bakeoff_local/diffusion_bakeoff_coding_diffusion_bakeoff_v1_20260511T034624Z.json` |
| schrodinger | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | 0/12 | 0.000 | `artifacts/eval/diffusion_bakeoff_local/diffusion_bakeoff_coding_diffusion_bakeoff_v1_20260511T041708Z.json` |

## Per-Prompt Verdict

| Prompt | Shape | AR | Schrodinger | Winner |
|---|---|---:|---:|---|
| code_eval_inventory_unique_python | simple_implementation | pass | fail | ar |
| code_eval_count_vowels_translate | cross_tongue_translation | fail | fail | none |
| code_eval_zero_guard_safe_subtract | body_fidelity_with_guards | pass | fail | ar |
| code_eval_clamp_value_rust | body_fidelity_with_guards | pass | fail | ar |
| code_eval_avali_javascript_lens | simple_implementation | fail | fail | none |
| code_eval_identify_algorithm_haskell | meta_identification | fail | fail | none |
| code_eval_multi_lens_consistency | multi_lens_parallel | fail | fail | none |
| code_eval_approval_card_verdict | structured_card | fail | fail | none |
| code_eval_geoseal_pair_route | route_decision_with_body | fail | fail | none |
| code_eval_lane_boundary_no_chem | negative_constraint | fail | fail | none |
| code_eval_executable_dict_merge | body_fidelity_with_guards | fail | fail | none |
| code_eval_runethic_option_chain | body_fidelity_with_guards | pass | fail | ar |

## Findings

1. The AR baseline is the current winner on this strict substring-gated contract: 4/12 versus Schrödinger 0/12.
2. The Schrödinger code-wave primitive did not amplify the missing-token cases in this configuration. It degraded even the AR-easy prompts, including `inventory_unique`, `safe_subtract`, `clamp_value_rust`, and `runethic_option_chain`.
3. The diagnostic `code_eval_avali_javascript_lens` did not flip. AR missed only `export function firstWord`; Schrödinger missed the core body tokens too. That points to over-perturbation or prompt/body drift rather than a small required-token correction.
4. This is still a useful negative result. The current wave post-processor should not be promoted as a coding lift. Next experiments should reduce intervention strength further, constrain the wave step to required phrase prefixes only, or use the Schrödinger layer as a verifier/repair suggester instead of a next-token generator.

## Reproduction

```powershell
python scripts\eval\diffusion_codegen_bakeoff.py --baseline-only --baseline-model Qwen/Qwen2.5-Coder-0.5B-Instruct --max-new-tokens 192 --out-dir artifacts\eval\diffusion_bakeoff_local --emit-report
python scripts\eval\diffusion_codegen_bakeoff.py --schrodinger-only --schrodinger-model Qwen/Qwen2.5-Coder-0.5B-Instruct --max-new-tokens 192 --out-dir artifacts\eval\diffusion_bakeoff_local
```

## Implementation Note

After a PC restart, the direct script entrypoint failed because `scripts.eval` was not importable when running `scripts/eval/diffusion_codegen_bakeoff.py` as a file. The entrypoint now inserts `REPO_ROOT` into `sys.path`, and `tests/eval/test_schrodinger_codewave_generator.py` includes a direct-script dry-run regression.
