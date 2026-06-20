# Agentic OS CLI Benchmark

Generated: 2026-05-29T22:56:56.652Z
Benchmark id: 328dd1aeaf5839e2

## Summary

- Cases: 16
- Passed: 16
- Failed: 0
- Pass rate: 1
- Median ms: 12.409
- P95 ms: 3822.292
- Internal hardening candidates: 11
- Hardening passed: 10
- Hardening failed: 1
- Next-round flags: 1

## Lanes

- agent_harness: tools audit + governed state CLI
- cross_language_compiler: geoseal cross-build Tier 1 lexicon-bounded IR
- binary_hexa_interpolation: agent-bus semantic bridge 6D -> 48-bit binary -> 12-char hex -> recomposition
- compass_front_door: SCBE formation classifier + adapter slots + local/free-tier/paid model lane planner + writing/YouTube route examples
- board_mechanics: Pazaak bitboard planner + coding-board legality probe + octree/chessboard source anchors
- internal_hardening_candidates: Vault-surfaced higher-security probes are benchmarked here but are not published as public CLI tools
- governance: durable trajectory start set observe/read/verify

## Cases

| Case                                                    | OK   |       ms | Evidence                                 |
| ------------------------------------------------------- | ---- | -------: | ---------------------------------------- |
| tool_registry_audit_full_surface                        | PASS |    2.739 | 37                                       |
| semantic_hex_roundtrip:compile add operation across lan | PASS |   12.409 | 80d1c7eb268c                             |
| semantic_hex_roundtrip:block denied command but preserv | PASS |    5.055 | e27d82bfd249                             |
| semantic_hex_roundtrip:transform water flow into a comp | PASS |    0.593 | a4e7856163af                             |
| semantic_hex_roundtrip:convert prompt to tokens then re | PASS |    0.442 | 80d1c7eb268c                             |
| compass_plan_forge_cross_domain                         | PASS |    1.417 | compiler                                 |
| compass_plan_broadcast_youtube_pipeline                 | PASS |    0.175 | youtube                                  |
| compass_plan_council_model_lanes_free_limits            | PASS |     0.35 | model                                    |
| compass_board_rules_source_anchored                     | PASS |    0.253 |                                          |
| agentic_pazaak_board_default_moves                      | PASS |  371.573 |                                          |
| cross_build_ko_to_ru_add                                | PASS | 2871.213 | add                                      |
| cross_build_av_to_dr_xor                                | PASS | 3030.093 | xor                                      |
| cross_build_broadcast_add_all_tongues                   | PASS | 3822.292 | add                                      |
| cross_build_list_ops_64                                 | PASS |  1536.12 |                                          |
| cross_build_quarantine_arbitrary_code                   | PASS | 1313.773 |                                          |
| pipeline_state_init_governed_lane                       | PASS |  245.705 | scbe.agent_bus.governed_state_summary.v1 |

## Internal Hardening Candidates

| Candidate                            | Status | Surface                      | Maturity                 | Next Round                                                                                                         |
| ------------------------------------ | ------ | ---------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| geoseal_binary_tokenizer_roundtrip   | PASS   | internal-tokenizer           | hold-internal            | Keep out of published CLI; promote only after threat model, input bounds, and redaction policy are documented.     |
| lightning_indexer_octree_context     | PASS   | internal-context-retrieval   | hold-internal            | Keep as internal sparse-context benchmark until candidate redaction and prompt-injection isolation are added.      |
| op_binary_inverse_complexity_demo    | PASS   | internal-adaptive-tokenizer  | hold-internal            | Needs structured JSON output and deterministic bounds before any public tool exposure.                             |
| attention_fft_synthetic_control      | PASS   | internal-attention-telemetry | hold-internal            | Synthetic control is safe; model-backed probing stays internal until model/download and secret gates are explicit. |
| storage_compaction_lab_candidate     | PASS   | internal-storage-geometry    | candidate-ready-internal | Add generated-artifact cleanup, fixed output schema, and wider fixture set before CLI exposure.                    |
| storage_interaction_mesh_candidate   | PASS   | internal-storage-mesh        | candidate-ready-internal | Keep internal until note-ingest privacy labels and artifact retention rules are wired.                             |
| core_python_checks_dry_run_candidate | PASS   | internal-test-lane           | candidate-ready-internal | Can be used as internal merge-readiness evidence; public CLI should expose only summarized pass/fail receipts.     |
| system_card_deck_candidate           | FLAG   | internal-system-map          | flag-for-hardening       | Fails without artifacts/repo-ordering/latest.json; add a dry-run/sample fallback before promotion.                 |
| spiralverse_space_commerce_lineage   | PASS   | internal-origin-lineage      | candidate-ready-internal | Keep as lineage/evidence. Promote only as a read-only provenance report, not an execution tool.                    |
| spiralverse_polly_tier_lineage       | PASS   | internal-fleet-lineage       | candidate-ready-internal | Use as provenance for SCBE fleet tiers; do not expose raw pad/workspace controls in the public CLI.                |
| spiralverse_patent_sync_candidate    | PASS   | internal-ip-lineage          | flag-for-sync-review     | Reconcile with SCBE patent workbench before copying any claim language; keep separate evidence layer.              |

## Best-In-Class Gaps

- atomic-tokenizer bus surface is now registered but still only smoke-tests byte bijection: patent-ready atomic tokenizer needs a stronger task corpus covering semantic atoms, code slots, and transport packets
- cross-build is Tier 1 lexicon-bounded, not arbitrary AST translation: 64 ops close cleanly, but best-in-class cross-domain compiler needs Tier 2 parser-backed lift into same LatticeOp schema
- semantic hex recomposition is nearest-atom, not lossless semantic identity: good for routing/interpolation, but benchmark should not claim perfect natural-language bijection
- YouTube upload lane is registered but intentionally unlisted-first: public publish remains a human approval gate; benchmark validates route availability, not live upload success
