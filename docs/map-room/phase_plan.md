# Training Data Conversion — Phase Plan

## Objective
Convert all available local training data into SFT pairs for the Polly chatbot.
Target: 50K+ richly structured pairs from 3 sources.
Do NOT touch Dropbox (syncing).

## Phases

### Phase 1: Consolidate existing unused JSONL (116K lines)
- Scan training-data/*.jsonl (root level, not in sft/)
- Identify format, extract user/assistant pairs
- Deduplicate against existing sft/ content
- Output: training-data/sft/consolidated_root_sft.jsonl
- Done criteria: all usable root JSONL converted and deduped

### Phase 2: Convert Notion export (1,190 files)
- Scan artifacts/notion_export_unpacked/Export-*/*.md
- Split by headings, generate Q&A pairs with Polly system prompt
- Quality filter: 80+ char minimum, technical term required
- Output: training-data/sft/notion_export_sft.jsonl
- Done criteria: all 1,190 files processed

### Phase 3: Convert Everweave logs (34K lines)
- Parse artifacts/notion_export_unpacked/Export-*/everweave-*.md
- Extract dialogue, narration, and world-building segments
- Convert to conversational SFT (Polly narrating/explaining lore)
- Output: training-data/sft/everweave_lore_sft.jsonl
- Done criteria: 34K lines processed into conversational pairs

### Phase 4: Build enriched triplets
- Take top 5K pairs from Phase 1-3
- Add context (source file, chapter, character)
- Add tongue assignment (which Sacred Tongue domain)
- Add governance tag (ALLOW/QUARANTINE/ESCALATE/DENY)
- Output: training-data/sft/enriched_triplets_sft.jsonl
- Done criteria: 5K triplets with full metadata

### Phase 5: Checkpoint and stats
- Count total pairs across all sft/ files
- Update overnight task ledger
- Push to git
- Output: session_handoff_latest.md updated
