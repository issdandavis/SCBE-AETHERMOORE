# Manhwa Round Table - Lane-Specific Context

**Primary roster**: `notes/round-table/ROUND_TABLE.md`
**This file**: What each agent owns in the manhwa pipeline specifically.
**Long-run packet context**: `notes/manhwa-project/ledger/roundtable-long-run-context.md`

---

## Lane Assignments

### OPUS (Scroll lane)
**Owns**: Narrative pipeline - frame scripts, text layer, pacing, assembly, preview
- `artifacts/webtoon/ch01/ch01_frame_script_v4.md` — 82-frame narrative script
- `scripts/merge_text_layer_v4.py` — text overlay merge into prompt packet
- `artifacts/webtoon/panel_prompts/ch01_prompts_v4_merged.json` — 62-panel merged packet (the contract)
- `artifacts/webtoon/ch01/v4_preview/` — preview strips
- `artifacts/webtoon/PANEL_MOTION_PACING_ANALYSIS.md` — sequential art research
- `artifacts/webtoon/MANHWA_TEXT_OVERLAY_STYLE_GUIDE.md` — text/layout style guide with PIL code
- `docs/superpowers/specs/2026-03-15-beat-expansion-pipeline-design.md`

### CODEX (Forge lane)
**Owns**: Build pipeline - scripts, prompts, renderers, tests
- `scripts/build_ch01_prompts_v4.py` — prompt packet generator
- `scripts/render_grok_storyboard_packet.py` — multi-backend image router
- `scripts/build_manhwa_edit_packet.py` — targeted panel fix pipeline
- `scripts/train_art_lora_colab.py` — LoRA training
- `artifacts/webtoon/panel_prompts/ch01_prompts_v4.json` — 56-panel base packet
- `docs/specs/WEBTOON_IMAGE_CONSISTENCY_SYSTEM.md`
- Test suite (16 passing)

### KEEPER (Opus - other session, library lane)
**Owns**: World bible — art style, characters, locations, consistency
- `notes/manhwa-project/` — Obsidian vault
- `artifacts/webtoon/ch01/text_overlays.json` — rendering style spec
- `notes/manhwa-project/ledger/art-style-bible.md` — 6 Arc Locks
- `notes/manhwa-project/references/` — character catalog, location catalog, storyboard tactics
- FLUX Kontext research ($0.003/img consistency path)

### GROK (art lane)
**Owns**: Hero concept art, character design, quality targets
- `artifacts/webtoon/references/grok_concepts/` — 6 concept art pieces
- Browser-only, manual prompt from Issac

### IMAGEN (generation lane)
**Owns**: Nothing — tool, not agent. Routed by Forge's renderer.
- Standard tier: batch panels
- Ultra tier: hero panels (F01, F16, F28, F47, F53, F59 + 3 more)

---

## The Contract

**`ch01_prompts_v4_merged.json`** is the single source of truth:
- 56 image panels with generation prompts + text overlays
- 4 text-only panels (zero gen cost, pure typography)
- 2 scroll gaps (negative space beats)
- 9 hero-tier panels routed to Ultra
- Every text overlay is a direct book quote

## Current Pipeline Status

| Stage | Status | Owner |
|-------|--------|-------|
| Frame script (82 frames) | DONE | Opus |
| Prompt packet (56 panels) | DONE | Codex |
| Text layer merge (62 panels) | DONE | Opus |
| Preview strip validation | DONE | Opus — "reads like a book" |
| Style spec (fonts, boxes, colors) | DONE | Keeper |
| Pacing analysis + text guide | DONE | Opus |
| Image generation (Imagen) | NOT STARTED | Codex renderer + Opus quality |
| Styled text rendering | NOT STARTED | Keeper styles + Opus assembly |
| Final strip assembly | NOT STARTED | Opus |
| Emulator/app test | NOT STARTED | Codex APK build |
| Ch02+ expansion | NOT STARTED | Codex template builder |

## Long-Run Packet Rule

Use stable callsigns with one shared task ID:

- `TaskId`: `MANHWA-ROUNDTABLE`
- Codex: `Codex`
- Claude narrative lane: `Opus`
- Library lane: `Keeper`
- Generation lane: `Imagen`
- Voice lane: `Kokoro`
- Optional fine-edit helper: `Editor`

For copy-paste packet commands, use:

- `notes/manhwa-project/ledger/roundtable-long-run-context.md`
