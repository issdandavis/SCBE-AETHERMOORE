# Agentic OS CLI Benchmark

Generated: 2026-05-29T13:52:03.500Z
Benchmark id: 2d8ab25cc36de274

## Summary

- Cases: 14
- Passed: 14
- Failed: 0
- Pass rate: 1
- Median ms: 5.509
- P95 ms: 905.552

## Lanes

- agent_harness: tools audit + governed state CLI
- cross_language_compiler: geoseal cross-build Tier 1 lexicon-bounded IR
- binary_hexa_interpolation: agent-bus semantic bridge 6D -> 48-bit binary -> 12-char hex -> recomposition
- hermes_front_door: task classifier + local/free-tier/paid model lane planner + writing/YouTube route examples
- governance: durable trajectory start set observe/read/verify

## Cases

| Case                                                    | OK   |      ms | Evidence                                 |
| ------------------------------------------------------- | ---- | ------: | ---------------------------------------- |
| tool_registry_audit_full_surface                        | PASS |   1.383 | 34                                       |
| semantic_hex_roundtrip:compile add operation across lan | PASS |   5.509 | 80d1c7eb268c                             |
| semantic_hex_roundtrip:block denied command but preserv | PASS |   2.345 | e27d82bfd249                             |
| semantic_hex_roundtrip:transform water flow into a comp | PASS |   0.276 | a4e7856163af                             |
| semantic_hex_roundtrip:convert prompt to tokens then re | PASS |   0.209 | 80d1c7eb268c                             |
| hermes_plan_compiler_cross_domain                       | PASS |   0.614 | compiler                                 |
| hermes_plan_youtube_writing_pipeline                    | PASS |    0.08 | youtube                                  |
| hermes_plan_model_lanes_free_limits                     | PASS |   0.173 | model                                    |
| cross_build_ko_to_ru_add                                | PASS | 905.552 | add                                      |
| cross_build_av_to_dr_xor                                | PASS | 787.962 | xor                                      |
| cross_build_broadcast_add_all_tongues                   | PASS |  795.69 | add                                      |
| cross_build_list_ops_64                                 | PASS | 783.139 |                                          |
| cross_build_quarantine_arbitrary_code                   | PASS | 796.111 |                                          |
| pipeline_state_init_governed_lane                       | PASS | 175.996 | scbe.agent_bus.governed_state_summary.v1 |

## Best-In-Class Gaps

- atomic-tokenizer bus surface is now registered but still only smoke-tests byte bijection: patent-ready atomic tokenizer needs a stronger task corpus covering semantic atoms, code slots, and transport packets
- cross-build is Tier 1 lexicon-bounded, not arbitrary AST translation: 64 ops close cleanly, but best-in-class cross-domain compiler needs Tier 2 parser-backed lift into same LatticeOp schema
- semantic hex recomposition is nearest-atom, not lossless semantic identity: good for routing/interpolation, but benchmark should not claim perfect natural-language bijection
- YouTube upload lane is registered but intentionally unlisted-first: public publish remains a human approval gate; benchmark validates route availability, not live upload success
