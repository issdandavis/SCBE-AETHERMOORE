# Agentic OS CLI Benchmark

Generated: 2026-05-29T17:36:17.661Z
Benchmark id: 328dd1aeaf5839e2

## Summary

- Cases: 16
- Passed: 16
- Failed: 0
- Pass rate: 1
- Median ms: 5.596
- P95 ms: 872.414

## Lanes

- agent_harness: tools audit + governed state CLI
- cross_language_compiler: geoseal cross-build Tier 1 lexicon-bounded IR
- binary_hexa_interpolation: agent-bus semantic bridge 6D -> 48-bit binary -> 12-char hex -> recomposition
- compass_front_door: SCBE formation classifier + adapter slots + local/free-tier/paid model lane planner + writing/YouTube route examples
- board_mechanics: Pazaak bitboard planner + coding-board legality probe + octree/chessboard source anchors
- governance: durable trajectory start set observe/read/verify

## Cases

| Case                                                    | OK   |      ms | Evidence                                 |
| ------------------------------------------------------- | ---- | ------: | ---------------------------------------- |
| tool_registry_audit_full_surface                        | PASS |   1.328 | 37                                       |
| semantic_hex_roundtrip:compile add operation across lan | PASS |   5.596 | 80d1c7eb268c                             |
| semantic_hex_roundtrip:block denied command but preserv | PASS |   3.411 | e27d82bfd249                             |
| semantic_hex_roundtrip:transform water flow into a comp | PASS |   0.319 | a4e7856163af                             |
| semantic_hex_roundtrip:convert prompt to tokens then re | PASS |   0.202 | 80d1c7eb268c                             |
| compass_plan_forge_cross_domain                         | PASS |   0.894 | compiler                                 |
| compass_plan_broadcast_youtube_pipeline                 | PASS |   0.116 | youtube                                  |
| compass_plan_council_model_lanes_free_limits            | PASS |   0.223 | model                                    |
| compass_board_rules_source_anchored                     | PASS |   0.147 |                                          |
| agentic_pazaak_board_default_moves                      | PASS | 129.024 |                                          |
| cross_build_ko_to_ru_add                                | PASS | 778.806 | add                                      |
| cross_build_av_to_dr_xor                                | PASS | 872.414 | xor                                      |
| cross_build_broadcast_add_all_tongues                   | PASS | 832.906 | add                                      |
| cross_build_list_ops_64                                 | PASS | 777.213 |                                          |
| cross_build_quarantine_arbitrary_code                   | PASS |  764.41 |                                          |
| pipeline_state_init_governed_lane                       | PASS | 163.388 | scbe.agent_bus.governed_state_summary.v1 |

## Best-In-Class Gaps

- atomic-tokenizer bus surface is now registered but still only smoke-tests byte bijection: patent-ready atomic tokenizer needs a stronger task corpus covering semantic atoms, code slots, and transport packets
- cross-build is Tier 1 lexicon-bounded, not arbitrary AST translation: 64 ops close cleanly, but best-in-class cross-domain compiler needs Tier 2 parser-backed lift into same LatticeOp schema
- semantic hex recomposition is nearest-atom, not lossless semantic identity: good for routing/interpolation, but benchmark should not claim perfect natural-language bijection
- YouTube upload lane is registered but intentionally unlisted-first: public publish remains a human approval gate; benchmark validates route availability, not live upload success
