# SCBE Conlang / Tokenizer / Compiler / Music Agentic Task List

Date: 2026-06-27
Owner: rolling agent backlog
Rule: add evidence and artifacts here as work progresses. Do not launch paid/non-local jobs without explicit approval.

## Status legend

```text
todo       not started
doing      active work
blocked    needs user, license, credential, or design decision
done       artifact exists
```

## Backlog

| ID | Status | Task | Output |
|---|---|---|---|
| CL-001 | done | Research code conlangs/esolangs and how they run. | `CODE_CONLANGS_RESEARCH_2026-06-27.md` |
| CL-002 | done | Save evidence table for conlang claims. | `CODE_CONLANGS_EVIDENCE_2026-06-27.csv` |
| CL-003 | done | Save open questions for conlang research. | `CODE_CONLANGS_OPEN_QUESTIONS_2026-06-27.md` |
| CL-004 | done | Frame SCBE six-lane tokenizer/compiler/music research direction. | `SCBE_CONLANG_TOKENIZER_COMPILER_MUSIC_NOTES_2026-06-27.md` |
| CL-005 | todo | Review open-source human-authored docs for license-compatible tokenizer/compiler/conlang training data. | Source manifest with license/provenance. |
| CL-006 | todo | Create `human_open_source_guides_browser_compiler_v1.jsonl` from license-compatible guides. | Separate human-authored training slice. |
| CL-007 | todo | Draft a tiny SCBE browser-action conlang spec. | `SCBE_BROWSER_ACTION_LANGUAGE_SPEC.md` |
| CL-008 | todo | Implement parser for the browser-action conlang. | Local parser script or module. |
| CL-009 | todo | Compile browser-action conlang to JSON action packets only. | JSON schema + compiler output examples. |
| CL-010 | todo | Add verifier for compiled action packets. | Rejects unsafe shell, token exposure, repeated polling. |
| CL-011 | todo | Create holdout eval for conlang-to-action compilation. | `browser_action_conlang_holdout.jsonl` |
| CL-012 | todo | Map six tongues to tokenizer profiles. | Table: tongue, syntax role, token class, host target. |
| CL-013 | todo | Build reversible text -> token -> hex proof for one tongue. | Script + receipt sample. |
| CL-014 | todo | Design binary-to-piano mapping v0. | Mapping table: nibble/byte/token class to pitch/rhythm. |
| CL-015 | todo | Generate piano-roll receipt for a sample SCBE packet. | MIDI/JSON/text receipt, no runtime claims. |
| CL-016 | todo | Compare SCBE mapping to Brainfuck/Befunge/Piet/Whitespace runtime models. | Research note with useful borrowable patterns. |
| CL-017 | todo | Add browser-use dataset to next local mixed training proof. | Local training config only after approval. |
| CL-018 | todo | Evaluate base vs current `scbe-coder` on browser-action conlang holdout. | Pass/fail table. |
| CL-019 | todo | If eval is strong, wire browser-action mode into AetherDesk AI Desk. | UI mode + backend validation route. |
| CL-020 | todo | Prepare non-local 7B training config but do not launch. | HF/OpenWeights job script staged, not run. |
| CL-021 | done | Inspect local systems and Issac-authored notes for research inspiration. | `ISSAC_SYSTEMS_INSPIRATION_INDEX_2026-06-27.md` |
| CL-022 | todo | Draft `SCBE_BROWSER_ACTION_LANGUAGE_SPEC.md` using six-tongue web routing and haptic click geometry. | Browser-action conlang spec. |
| CL-023 | todo | Define route-cache metric tensor schema for Aether Browser. | JSON schema for `edge_cost`, `tongue_profile`, `membrane_density`, `flow_rate`. |
| CL-024 | todo | Add semantic-atom compiler pass for browser-action source. | Source -> semantic atoms -> action packet. |
| CL-025 | todo | Design positive/negative training pairs using bonding/antibonding pattern. | SFT/DPO-style browser-use slice. |
| CL-026 | todo | Create piano-roll receipt mapping for one browser-action packet. | Token/tongue/byte-to-music annotation. |
| CL-027 | todo | Build haptic event receipt model for browser automation. | 2D sweep, 3D press, 4D membrane, 2.5D transit fields. |

## Next agent instructions

When picking up this lane:

1. Read `SCBE_CONLANG_TOKENIZER_COMPILER_MUSIC_NOTES_2026-06-27.md`.
2. Read `ISSAC_SYSTEMS_INSPIRATION_INDEX_2026-06-27.md`.
3. Pick the lowest-numbered `todo` task that does not require paid compute.
4. If ingesting external docs, verify license first and write provenance metadata.
5. Keep synthetic SCBE examples separate from human open-source guide-derived examples.
6. Do not run training unless the user explicitly approves that run.
7. Add the artifact path and status update back into this task list.

## Good first task tomorrow

Start with `CL-005`: make a source manifest of human-authored open-source docs for:

- Brainfuck interpreter/compiler guides
- Befunge-93 reference docs
- Shakespeare language docs
- LOLCODE spec/interpreter docs
- browser automation docs
- OAuth/token-handling docs
- compiler construction/tokenizer tutorials with permissive licenses

Do not ingest text until license and provenance are clear.
