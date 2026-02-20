# Full System Review: Deterministic Load Order

Generated: `2026-02-20T00:49:45.744563+00:00`

## Scope

- Total tracked files: `4741`
- Runtime source files ordered by dependency graph: `1599`
- Python sources: `700`
- TS/JS sources: `899`
- Dependency edges: `1293`
- SCC components: `1599`
- Cycle components: `0`

## Entrypoints Considered

- `src/index.ts`
- `src/api/server.ts`
- `src/api/index.ts`
- `src/api/main.py`
- `api/main.py`
- `six-tongues-cli.py`
- `scbe-cli.py`
- `scripts/linux_kernel_antivirus_monitor.py`
- `scripts/spiral_engine_game_sim.py`
- `aethermoore.py`
- `agents/aetherbrowse_cli.py`
- `agents/browser/main.py`
- `agents/browser_agent.py`
- `agents/browsers/cdp_backend.py`
- `agents/browsers/chrome_mcp.py`
- `agents/browsers/playwright_backend.py`
- `agents/browsers/selenium_backend.py`
- `agents/swarm_browser.py`
- `build_package.py`
- `cleanup_imports.py`
- `demo-cli.py`
- `demo.py`
- `demo_full_system.py`
- `demo_memory_shard.py`
- `gumroad_image_uploader.py`
- `harmonic_scaling_law.py`
- `run_tests.py`
- `scbe-agent.py`
- `scripts/aetherbrowse_swarm_runner.py`
- `scripts/asana_aetherbrowse_orchestrator.py`
- `scripts/check_layer_status_transition.py`
- `scripts/coherence-check.py`
- `scripts/export_monthly_billable_usage.py`
- `scripts/journal.py`
- `scripts/launch_aws_sagemaker_training.py`
- `scripts/layer9_spectral_coherence.py`
- `scripts/long_run_training_bootstrap.py`
- `scripts/n8n_aetherbrowse_bridge.py`
- `scripts/notion_access_check.py`
- `scripts/notion_to_dataset.py`
- `scripts/prepare_gumroad_automation_dataset.py`
- `scripts/push_to_hf.py`
- `scripts/remote_gumroad_upload.py`
- `scripts/train_hf_longrun_placeholder.py`
- `scripts/training_auditor.py`
- `scripts/update_ai_hub.py`
- `scripts/validate_layer_manifest.py`
- `scripts/voxel_governance_sim.py`
- `setup-providers.py`
- `spiralverse_sdk.py`
- `src/aethermoore.py`
- `src/ai_orchestration/setup_assistant.py`
- `src/crypto/dual_lattice.py`
- `src/crypto/dual_lattice_integration.py`
- `src/crypto/geo_seal.py`
- `src/crypto/hyperbolic_viz.py`
- `src/crypto/hyperpath_finder.py`
- `src/crypto/octree.py`
- `src/crypto/pqc_liboqs.py`
- `src/crypto/signed_lattice_bridge.py`
- `src/crypto/symphonic_cipher.py`
- `src/crypto/symphonic_waveform.py`
- `src/gateway/COMPUTATIONAL_IMMUNE_SYSTEM.py`
- `src/gateway/DNA_MULTI_LAYER_ENCODING_TEST.py`
- `src/gateway/complex_math_core.py`
- `src/h_lwe.py`
- `src/lambda_tests/test_pqc.py`
- `src/minimal/scbe_core.py`
- `src/physics_sim/test_physics.py`
- `src/physics_sim/test_physics_comprehensive.py`
- `src/scbe_14layer_reference.py`
- `src/scbe_aethermoore_kyber_v2.1.py`
- `src/scbe_cpse_unified.py`
- `src/science_packs/__init__.py`
- `src/spiralverse/aethercode.py`
- `src/spiralverse/hive_memory.py`
- `src/spiralverse/polyglot_alphabet.py`
- `src/spiralverse/proximity_optimizer.py`
- `src/spiralverse/rwp2_envelope.py`
- `src/spiralverse/temporal_intent.py`
- `src/spiralverse/vector_6d.py`
- `src/symphonic_cipher/audio/stellar_octave_mapping.py`
- `src/symphonic_cipher/core/cymatic_voxel_storage.py`
- `src/symphonic_cipher/core/harmonic_scaling_law.py`
- `src/symphonic_cipher/dual_lattice_consensus.py`
- `src/symphonic_cipher/dynamics/flux_interaction.py`
- `src/symphonic_cipher/qasi_core.py`
- `src/symphonic_cipher/scbe_aethermoore/aetherlex_extract.py`
- `src/symphonic_cipher/scbe_aethermoore/attack_simulation.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/audio_axis.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/benchmark_comparison.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/demo_for_elon.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/dual_mode_core.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/hamiltonian_cfi.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py`
- `src/symphonic_cipher/scbe_aethermoore/cli_toolkit.py`
- `src/symphonic_cipher/scbe_aethermoore/cpse.py`
- `src/symphonic_cipher/scbe_aethermoore/cpse_integrator.py`
- `src/symphonic_cipher/scbe_aethermoore/dual_lattice.py`
- `src/symphonic_cipher/scbe_aethermoore/fractional_flux.py`
- `src/symphonic_cipher/scbe_aethermoore/full_system.py`
- `src/symphonic_cipher/scbe_aethermoore/kyber_orchestrator.py`
- `src/symphonic_cipher/scbe_aethermoore/layer_13.py`
- `src/symphonic_cipher/scbe_aethermoore/layer_tests.py`
- `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py`
- `src/symphonic_cipher/scbe_aethermoore/layers_9_12.py`
- `src/symphonic_cipher/scbe_aethermoore/living_metric.py`
- `src/symphonic_cipher/scbe_aethermoore/mass_system_grok.py`
- `src/symphonic_cipher/scbe_aethermoore/organic_hyperbolic.py`
- `src/symphonic_cipher/scbe_aethermoore/patent_validation_tests.py`
- `src/symphonic_cipher/scbe_aethermoore/phdm_module.py`
- `src/symphonic_cipher/scbe_aethermoore/pqc_module.py`
- `src/symphonic_cipher/scbe_aethermoore/production_v2_1.py`
- `src/symphonic_cipher/scbe_aethermoore/proofs_verification.py`
- `src/symphonic_cipher/scbe_aethermoore/qasi_core.py`
- `src/symphonic_cipher/scbe_aethermoore/sacred_eggs.py`
- `src/symphonic_cipher/scbe_aethermoore/scbe_aethermoore_core.py`
- `src/symphonic_cipher/scbe_aethermoore/test_scbe_system.py`
- `src/symphonic_cipher/scbe_aethermoore/tri_mechanism_detector.py`
- `src/symphonic_cipher/scbe_aethermoore/unified.py`
- `src/symphonic_cipher/scbe_aethermoore_core.py`
- `src/symphonic_cipher/scbe_aethermoore_kyber_v2.1.py`
- `src/symphonic_cipher/scbe_aethermoore_v2.1_production.py`
- `src/symphonic_cipher/topological_cfi.py`
- `stress_test.py`
- `symphonic_cipher_geoseal_manifold.py`
- `symphonic_cipher_spiralverse_sdk.py`
- `test_aethermoore_validation.py`
- `test_combined_protocol.py`
- `test_flat_slope.py`
- `test_harmonic_scaling_integration.py`
- `test_physics.py`

## Cycle Highlights (Top 20)

- none

## Source Load Order Preview (First 40)

1. `.kiro/specs/rwp-v2-integration/SCBE_LAYER9_CORRECTED_PROOF.py` (python)
2. `.kiro/specs/rwp-v2-integration/rwp_v3_hybrid_pqc.py` (python)
3. `SCBE-AETHERMOORE-v3.0.0/harmonic_scaling_law.py` (python)
4. `SCBE-AETHERMOORE-v3.0.0/scbe-cli.py` (python)
5. `SCBE-AETHERMOORE-v3.0.0/scbe_demo.py` (python)
6. `SCBE-AETHERMOORE-v3.0.0/spiralverse_sdk.py` (python)
7. `SCBE-AETHERMOORE-v3.0.0/src/aethermoore.py` (python)
8. `SCBE-AETHERMOORE-v3.0.0/src/crypto/bloom.ts` (tsjs)
9. `SCBE-AETHERMOORE-v3.0.0/src/crypto/envelope.ts` (tsjs)
10. `SCBE-AETHERMOORE-v3.0.0/src/crypto/hkdf.ts` (tsjs)
11. `SCBE-AETHERMOORE-v3.0.0/src/crypto/index.ts` (tsjs)
12. `SCBE-AETHERMOORE-v3.0.0/src/crypto/jcs.ts` (tsjs)
13. `SCBE-AETHERMOORE-v3.0.0/src/crypto/kms.ts` (tsjs)
14. `SCBE-AETHERMOORE-v3.0.0/src/crypto/nonceManager.ts` (tsjs)
15. `SCBE-AETHERMOORE-v3.0.0/src/crypto/replayGuard.ts` (tsjs)
16. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/assertions.ts` (tsjs)
17. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/audioAxis.ts` (tsjs)
18. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/constants.ts` (tsjs)
19. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/halAttention.ts` (tsjs)
20. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/hamiltonianCFI.ts` (tsjs)
21. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/harmonicScaling.ts` (tsjs)
22. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/hyperbolic.ts` (tsjs)
23. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/index.ts` (tsjs)
24. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/languesMetric.ts` (tsjs)
25. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/pqc.ts` (tsjs)
26. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/qcLattice.ts` (tsjs)
27. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/sacredTongues.ts` (tsjs)
28. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/spiralSeal.ts` (tsjs)
29. `SCBE-AETHERMOORE-v3.0.0/src/harmonic/vacuumAcoustics.ts` (tsjs)
30. `SCBE-AETHERMOORE-v3.0.0/src/index.ts` (tsjs)
31. `SCBE-AETHERMOORE-v3.0.0/src/lambda/index.js` (tsjs)
32. `SCBE-AETHERMOORE-v3.0.0/src/lambda_tests/__init__.py` (python)
33. `SCBE-AETHERMOORE-v3.0.0/src/metrics/telemetry.ts` (tsjs)
34. `SCBE-AETHERMOORE-v3.0.0/src/physics_sim/__init__.py` (python)
35. `SCBE-AETHERMOORE-v3.0.0/src/physics_sim/core.py` (python)
36. `SCBE-AETHERMOORE-v3.0.0/src/physics_sim/test_physics.py` (python)
37. `SCBE-AETHERMOORE-v3.0.0/src/rollout/canary.ts` (tsjs)
38. `SCBE-AETHERMOORE-v3.0.0/src/rollout/circuitBreaker.ts` (tsjs)
39. `SCBE-AETHERMOORE-v3.0.0/src/scbe_14layer_reference.py` (python)
40. `SCBE-AETHERMOORE-v3.0.0/src/scbe_cpse_unified.py` (python)

## Full Ordered Manifest

See `docs/SYSTEM_LOAD_ORDER_FULL.json` for the complete ordered list of every tracked file:

- `source_load_order`: dependency-first runtime order for all source files.
- `full_file_order`: every tracked file, with source first then non-source lexical order.
