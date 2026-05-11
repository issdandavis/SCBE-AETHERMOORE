# Code-Diffusion Bake-Off — coding_diffusion_bakeoff_v1

## Generator pass-rates

| Generator | Model | Pass | Rate |
|---|---|---|---|
| ar | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | 4/12 | 0.333 |

## Per-prompt verdict-class

| Prompt | Shape | Class | Winners |
|---|---|---|---|
| code_eval_inventory_unique_python | simple_implementation | all_pass | ar |
| code_eval_count_vowels_translate | cross_tongue_translation | all_fail | — |
| code_eval_zero_guard_safe_subtract | body_fidelity_with_guards | all_pass | ar |
| code_eval_clamp_value_rust | body_fidelity_with_guards | all_pass | ar |
| code_eval_avali_javascript_lens | simple_implementation | all_fail | — |
| code_eval_identify_algorithm_haskell | meta_identification | all_fail | — |
| code_eval_multi_lens_consistency | multi_lens_parallel | all_fail | — |
| code_eval_approval_card_verdict | structured_card | all_fail | — |
| code_eval_geoseal_pair_route | route_decision_with_body | all_fail | — |
| code_eval_lane_boundary_no_chem | negative_constraint | all_fail | — |
| code_eval_executable_dict_merge | body_fidelity_with_guards | all_fail | — |
| code_eval_runethic_option_chain | body_fidelity_with_guards | all_pass | ar |
