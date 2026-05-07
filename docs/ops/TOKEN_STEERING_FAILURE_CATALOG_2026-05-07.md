# Token Steering Failure Catalog

Generated: 2026-05-07T13:56:32.895319+00:00

## Bottom Line

Primary next action: `logit_mask_or_verifier_rejection`.

structure is present but continuation drifts into forbidden tokens

Do not launch a new fine-tune solely to solve schema or required-token failures; those are steering/gating problems first.

## Current Evidence Summary

- Checked trials/results: 1225/1321 passed (0.9273).
- Missing-required incidents: 0
- Forbidden-token incidents: 96
- Syntax/runtime incidents: 0
- Semantic assertion incidents: 0

## Steering Routing Rules

- If `missing required markers or fixed schema fields` -> use `constrained decoding / forced prefix`.
- If `forbidden token appears after a valid prefix` -> use `logit mask, rejection sampling, or verifier retry`.
- If `syntax error or runtime/import error` -> use `compiler/interpreter verifier repair loop`.
- If `code runs but assertions fail consistently` -> use `targeted SFT, DPO, or activation control vector`.
- If `large seed-to-seed variance` -> use `best-of-N verifier search before changing weights`.

## Artifact Table

| Artifact | Schema | Passed | Missing | Forbidden | Syntax/Exec | Assertions | Note |
|---|---|---:|---:|---:|---:|---:|---|
| `artifacts\bijective_tongue\local_constrained_1778133356.json` | `scbe_bijective_tongue_gate_v3_constrained_decoding` | 25/25 (1.0000) | 0 | 0 | 0 | 0 | bijective round-trip code execution audit |
| `artifacts\eval\constrained_decoding_audit.json` | `scbe_multi_seed_gate_eval_v1` | 180/180 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\constrained_decoding_audit_noise10.json` | `scbe_multi_seed_gate_eval_v1` | 160/180 (0.8889) | 0 | 20 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\constrained_decoding_audit_noise30.json` | `scbe_multi_seed_gate_eval_v1` | 119/180 (0.6611) | 0 | 61 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\constrained_decoding_audit_noise_sleep_smoke.json` | `scbe_multi_seed_gate_eval_v1` | 33/48 (0.6875) | 0 | 15 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\constrained_decoding_audit_sleep_smoke.json` | `scbe_multi_seed_gate_eval_v1` | 48/48 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\constrained_decoding_audit_smoke.json` | `scbe_multi_seed_gate_eval_v1` | 180/180 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\multi_seed_gate_eval_sleep_smoke.json` | `scbe_multi_seed_gate_eval_v1` | 48/48 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\eval\multi_seed_gate_eval_smoke.json` | `scbe_multi_seed_gate_eval_v1` | 180/180 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\hf_eval_results\constrained_decoding_audit_real_model_20260506T074659Z.json` | `scbe_constrained_decoding_real_model_audit_v1` | 180/180 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |
| `artifacts\hf_eval_results\constrained_decoding_audit_real_model_20260506T085546Z.json` | `scbe_constrained_decoding_real_model_audit_v1` | 72/72 (1.0000) | 0 | 0 | 0 | 0 | multi-seed required/forbidden contract audit |

## Production Hooks Already Available

- `src/governance/coding_eval_constrained_decoding.py::build_bad_words_ids` converts forbidden strings into decode-time masks.
- `coding_eval_constrained_response(..., suppress_forbidden=True)` applies those masks during generation.
- `coding_eval_best_of_n_response(...)` retries deterministic decode contexts and returns the first verified pass.
- Focused guard test: `python -m pytest tests/governance/test_coding_eval_constrained_decoding.py -q`.

## Operational Decision

The checked constrained-decoding and bijective artifacts do not justify a new training run by themselves.
The next zero-cost work is to wire this catalog into CI, keep forbidden-token suppression enabled for drift-prone gates, and expand the contract coverage until a real semantic failure shape appears.
Activation vectors are worth scoping only for repeated semantic assertion failures, not for schema compliance.
