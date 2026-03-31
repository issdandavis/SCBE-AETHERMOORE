---
objective: Convert local training data to 50K+ SFT pairs for Polly chatbot
status: in_progress
phase: 5 of 5
started: 2026-03-30T06:30:00-07:00
updated: 2026-03-31T00:15:00-07:00
---

## Source Re-anchor
- Root source map now lives at `docs/map-room/scbe_source_roots.md`.
- Use that file first when a future session starts drifting on canon, tokenizer, geometry, Sacred Eggs, embedding docs, or federated-training roots.
- Important correction from this session: the SCBE system is not speculative or "vapor"; the failure mode was partial context reconstruction instead of immediate re-anchoring on the Notion export, docs, and code roots already in the repo.
- `references/repo-map.md` and `references/runtime-entrypoints.md` are missing in this repo. `scbe_source_roots.md` is acting as the temporary orientation replacement.

## Completed
- Phase plan created
- Phase 1: 43,725 pairs from root JSONL (consolidated, deduped)
- Phase 2: 3,922 pairs from 1,190 Notion export files
- Phase 3: 6,281 pairs from Everweave RPG lore logs
- Phase 4: 5,000 enriched triplets with tongue + governance tags
- Phase 4b: 2,612 pairs from Claude conversation export (602 convos)
- Phase 4c: 4,107 pairs from subdirectory sessions
- Phase 4d: 796 content articles + 557 kindle + 811 training-data markdown
- Phase 4e: 1,176 Python docstrings + 2,244 TypeScript docs + 5,504 remaining docs
- Phase 4f: 7,385 test behavior descriptions + 8 Polly personality/refusal pairs
- Phase 4g: 177 CI workflows + README + skills
- Phase 5a: 12,989 pairs from Avalon Codex lore (406 Spiralverse files in Notion export + codebase)
- Phase 5b: 447 pairs from pasted comprehensive lore (7 codices, novel chapters, master timeline)
- Phase 5c: 8 lorem ipsum entries cleaned from book_drafts_sft.jsonl
- Phase 5d: 90 pairs from Shore to King novel (65KB Notion export)
- GRAND TOTAL: 123,929 SFT pairs (verified, was 96,996 -> 27.8% increase this session)
- Raw lore saved: training-data/raw/ (28 files, ~3.2MB total)
- Sacred Tongues dedicated SFT: scripts/sacred_tongues_to_sft.py
- All pushed to GitLab overnight/2026-03-30

## In Progress
- User pasting novel content across multiple sessions (6+ versions so far)
- Several pastes still in active conversation buffer awaiting transcript flush
- Content includes: 6 novel versions, Kor'aelin language system, Lexicon Training Codex,
  character profiles, worldbuilding docs, ChatGPT creative session logs, ChatGPT memory dumps

## Completed This Session
- Phase 5a: 12,989 pairs from Avalon Codex lore (previous session)
- Phase 5b: 447 pairs from initial lore paste (previous session)
- Phase 5c: 8 lorem ipsum entries cleaned
- Phase 5d: 90 pairs from Shore to King novel
- Phase 5e: 1,371 pairs from segmented novel versions (V3, V5, timeline, writing guide)
- Phase 5f: 273 pairs from Dark Setting V4 novel (192KB)
- Phase 5g: Multiple novel versions and ChatGPT session logs pasted (in buffer)
- Raw file cleanup: removed 11 duplicates, segmented into 25 unique files (2.8MB total)
- Phase 5h: 211 Sacred Tongues SFT pairs (all 6 tongues, tokenizer mechanics, crypto protocol, origin story)
- GRAND TOTAL: 123,929 SFT pairs (verified count from sft/ directory)

## Raw Files in training-data/raw/
- 25 unique files, 2.8MB total
- pasted_lore_01-03: Original Avalon Codex + novel chapters (previous session)
- pasted_lore_04-14: Earlier extractions (language, manuscripts, blueprints)
- pasted_lore_23: Dark Setting V4 novel (192KB)
- pasted_lore_30-36: Segmented novel versions (V3 chronicle, V5 variants, continuations)
- Additional content in active buffer: V5 "Architect of Realms", ChatGPT session, Kor'aelin guide

## Blocked
- Dropbox sync in progress -- dozens more book drafts waiting
- GitHub branch protection -- pushing to GitLab instead
- Some pastes still in conversation buffer (will be captured on next extraction run)

## New This Session: Polly Pump + Binary-First Stack
- Built `src/polly_pump/` (packet.py, retriever.py, stabilizer.py) -- inference-time orientation layer
- Pump separates ORIENTATION from EXPRESSION: sense → locate → lift → compose → respond
- PumpPacket carries: tongue profile, null pattern, governance posture, canon neighborhood, emotional register
- BundleRetriever scores aquifer bundles by cosine similarity on tongue profiles
- ResponseStabilizer composes structured pre-state block for model context
- Tests: 3 passing in `tests/test_polly_pump.py`
- Binary-First Training Stack spec: `docs/specs/BINARY_FIRST_TRAINING_STACK.md`
  - L0 bytes → L1 SS1 tokens → L2 pump packet → L3 words
  - Multi-objective loss: L_byte + L_tongue + L_null + L_word + L_policy
  - Measured anchor: semantic projector F1 0.481 → 0.813 (existing)
  - Target ranges: SEG >= 1.5x, OER >= 15%, DDR >= 20%, F1 gain >= 0.05
- Sacred Tongues SFT: 211 pairs from all 6 tongue lexicons (scripts/sacred_tongues_to_sft.py)
- GRAND TOTAL: 123,929 SFT pairs

## Next Actions (for next session)
- **Priority 1: Stack-lite dataset row generator** -- stamp 124K pairs with pump packets
- **Priority 2: Three-way benchmark** -- baseline vs stack-lite vs stack-binary on route/governance/QA tasks
- **Priority 3: Populate real aquifer** -- compute tongue profiles for representative SFT bundles
- Run extract script after conversation ends to capture buffered content
- Train Polly chatbot on pump-annotated pairs (Kaggle free GPU)
- Build multi-turn conversation pairs from Claude export
- Create DPO preference pairs (good vs bad answers)
- Push overnight branch to GitHub via PR
- Merge training data and upload to Kaggle/HuggingFace dataset
