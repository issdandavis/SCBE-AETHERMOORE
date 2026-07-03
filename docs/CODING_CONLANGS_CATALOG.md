# SCBE Coding Conlangs Catalog

Compiled from all searches (latest: call-5d5b2cd3-8072-4f7c-8663-c480ea17b576-145 and priors).

## Core Dev Source
- C:\dev\train-orchestrator\training\conlang_macros.py
- C:\dev\train-orchestrator\training\shorthand.py

## SFT Generators & Tests (duplicated across checkouts/forks)
- instrument-wt/scripts/generate_conlang_first_sft.py
- instrument-wt/tests/test_conlang_first.py
- SCBE-AETHERMOORE/scripts/generate_conlang_first_sft.py
- SCBE-AETHERMOORE/tests/test_conlang_first.py (and __pycache__)
- SCBE-AETHERMOORE-fix-bandit/scripts/generate_conlang_first_sft.py
- SCBE-AETHERMOORE-fix-bandit/tests/test_conlang_first.py
- SCBE-AETHERMOORE-main-audit/scripts/generate_conlang_first_sft.py
- SCBE-AETHERMOORE-main-audit/tests/test_conlang_first.py
- SCBE-AETHERMOORE-security-fix/scripts/generate_conlang_first_sft.py
- SCBE-AETHERMOORE-security-fix/tests/test_conlang_first.py
- scbe-mcp-config-hygiene/scripts/generate_conlang_first_sft.py
- scbe-mcp-config-hygiene/tests/test_conlang_first.py
- scbe-pr2544-fix/scripts/generate_conlang_first_sft.py
- scbe-pr2544-fix/tests/test_conlang_first.py
- scbe-uport-wt/scripts/generate_conlang_first_sft.py
- scbe-uport-wt/tests/test_conlang_first.py
- helm-operator-land-wt/scripts/generate_conlang_first_sft.py
- helm-operator-land-wt/tests/test_conlang_first.py
- mountain-v8-wt/scripts/generate_conlang_first_sft.py
- mountain-v8-wt/tests/test_conlang_first.py
- slice-wt/scripts/generate_conlang_first_sft.py
- slice-wt/tests/test_conlang_first.py (and __pycache__)

## Research Docs (SCBE-AETHERMOORE/docs/research/)
- CODE_CONLANGS_RESEARCH_2026-06-27.md
- CODE_CONLANGS_OPEN_QUESTIONS_2026-06-27.md
- CODE_CONLANGS_EVIDENCE_2026-06-27.csv
- SCBE_CONLANG_AGENTIC_TASK_LIST_2026-06-27.md
- SCBE_CONLANG_TOKENIZER_COMPILER_MUSIC_NOTES_2026-06-27.md

## Artifacts & Integration
- SCBE-AETHERMOORE/artifacts/ai_brain/conlang_macros_claim_manifest.json
- SCBE-AETHERMOORE/artifacts/ai_brain/gate_reports/conlang_macros/...
- instrument-wt/artifacts/ai_brain/conlang_macros_claim_manifest.json
- SCBE-AETHERMOORE/scripts/system/claim_gate_adapter.py
- SCBE-AETHERMOORE/python/scbe/language_library_registry.py (conlang_macros as level=6 verified face with emitted-to-8 NOT executed-on-8 caveat)

## Memory & Workflows (.claude/projects/)
- memory/conlang-macro-binding.md
- memory/conlang-completeness-goal.md
- memory/shorthand-steering-wheel.md
- df679d16-faf2-43d8-986a-b930cd441d0a/workflows/scripts/conlang-macro-...

## OneDrive Backups
- OneDrive/SCBE-Archives/training_artifacts_2026-04/...
- OneDrive/scbe-session-backup/memory/...

## Core SCBE Support (instrument-wt/python/scbe/ and SCBE-AETHERMOORE equivalents)
- rosetta.py (CA conlang mode, verified faces, firewalls)
- tongue_code_lanes.py, tongue_isa.py, etc.
- instrument.py (ca_word_for_opcode), ca_opcode_table.py
- six-tongues-cli.py
- tests/conlang/test_tongue_turing.py

## Notes
- Duplicates across ~8-10 checkouts/forks (SCBE-AETHERMOORE-*, instrument-wt, helm-*, mountain-*, slice-*, scbe-*-hygiene/pr/fix etc.) for safety/parallel dev.
- Canonical dev source: train-orchestrator/training/
- Research + artifacts + registration: SCBE-AETHERMOORE/
- SFT copies: everywhere
- Support: instrument-wt/python/scbe/

**Saved state from searches + integration work (scbe_manaan_docking.py, rosetta.py updates, catalog, manifests, etc.).**
**Honesty firewalls applied throughout (emitted-to-8 NOT executed-on-8, etc.).**

(Full lists from all tasks incorporated; no more searches needed.)