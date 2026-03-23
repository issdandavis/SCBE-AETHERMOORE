# HallPass Guidance Integration Review - 2026-03-09

## Summary
HallPass fits SCBE-AETHERMOORE as a guidance-token corridor overlay, not a permission token. The best seams are in fleet routing, PHDM monitoring, roundabout lane docs, and HyperLane zone scoring.

## Integration Joints
- Fleet selection and ordering: `src/fleet/skill_deck_engine.py` at `classify_permissions()` line 112, `ContextBudget` line 277, `WorkflowCompiler` line 351, `DeckOptimizer` line 486, `SkillRouter` line 648.
- PHDM geometry and drift: `src/ai_brain/phdm-core.ts` at `TONGUE_LABELS` line 66, `brainStateToLangues()` line 92, `PHDMCore` line 230, `monitor()` line 308.
- Lane semantics: `docs/AETHERMORE_ROUNDABOUT_CITY_ARCH.md` lines 10-11 and 38-44 define roads, rail, and roundabouts R0-R3.
- Zone-aware route evaluation: `src/aetherbrowser/hyperlane_py.py` lines 68-100.
- Trust tube behavior: `tests/ai_brain/hamiltonian-braid.test.ts` line 311 (`zero cost inside tube`).

## Build Evidence
- PASS: `npm test -- tests/ai_brain/phdm-core.test.ts tests/ai_brain/hamiltonian-braid.test.ts` -> 143 tests passed.
- PARTIAL: `python -m pytest tests/test_skill_card_forge.py tests/test_skill_deck_engine.py -q` -> 113 passed, 6 errors.
- Python failure mode is environment/file hygiene around `artifacts/pytest_tmp`, not deck logic failures.

## Risks
- `SkillRouter` routes tasks to skills but has no time-slot reservation, lane occupancy, or collision model.
- `WorkflowCompiler` orders by role/IO, not by corridor timing.
- `PHDMCore.monitor()` assumes normalized path parameter `t`; multi-agent guidance will need time-window mapping.
- `scripts/system/terminal_crosstalk_emit.ps1` is stale and fails because `src.aethercode.gateway` is missing.
- `scripts/system/ops_control.py` is the live cross-talk bus.

## Recommendation
Build a `HallPassGuidanceCompiler` between `DeckOptimizer` and `WorkflowCompiler`. It should add route biasing, tongue-phase/facet projection, timed lane reservations, drift budgets, and fallback branches, while leaving permissions to the existing antivirus/quorum/cost layers.

## Repo Packet
- JSON packet: `artifacts/agent_comm/20260309/cross-talk-codex-sync-20260309T204943Z-43e8e8.json`
- JSONL lane: `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
