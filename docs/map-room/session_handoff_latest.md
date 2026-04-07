---
objective: Train Polly chatbot with binary-first orientation stack
status: in_progress
phase: 6 — training pipeline + architecture validation
started: 2026-03-30T06:30:00-07:00
updated: 2026-03-31T02:00:00-07:00
---

## Source Re-anchor
- Root source map: `docs/map-room/scbe_source_roots.md`
- Binary-first stack spec: `docs/specs/BINARY_FIRST_TRAINING_STACK.md`
- Pump code: `src/polly_pump/` (packet.py, retriever.py, stabilizer.py)
- Sacred Tongues SFT: `scripts/sacred_tongues_to_sft.py`
- Tongue binary analysis: `scripts/tongue_binary_analysis.py`

## Key Discoveries This Session

### 1. The Pump Architecture
- **Separation of orientation from expression** is the real shift
- Pump = inference-time state retrieval + routing + pre-stabilization
- PumpPacket: tongue profile, null pattern, governance posture, canon, emotion
- BundleRetriever: cosine similarity on tongue profiles in aquifer
- Tests: 3 passing (`tests/test_polly_pump.py`)
- Demonstrated: different inputs produce measurably different orientations
  - Lore question: `[##__#_]` dominant UM, canon=lore, ALLOW
  - Adversarial: `[______]` all null, canon=security, DENY
  - Architecture: `[__#_##]` dominant RU, canon=architecture, ALLOW

### 2. Null Space as Vacuum / Pressure Differential
- Absence patterns are more diagnostic than presence patterns
- The null tongues are vacuums adjacent to active tongues
- Pressure differential IS the signal (physics: P = F/A maps to info density / parameters)
- Train the model to PREDICT null dimensions from active ones = structural generalization
- "You don't fill a vacuum. You create conditions where surrounding pressure fills it."

### 3. Training Data Layer Distribution (MEASURED)
```
L0 substrate:      ~0   (0.0%)  — effectively absent
L1 coordination:  ~220  (0.1%)  — only sacred_tongues_sft.jsonl
L2 orientation:     ~0  (0.0%)  — pump exists but no training data
L3 expression:  ~150K+ (99.9%)  — everything else
```
- Current data is 99.9% cortex. Brainstem barely exists.
- Mega files (42K each) have L1/L2 METADATA but L3 CONTENT = camouflage
- "Writing the novel in Morse code doesn't teach telegraph engineering"

### 4. Binary-First Stack (L0→L1→L2→L3)
- Follows brain developmental order: substrate → sensation → orientation → expression
- Principle: **shared substrate, separate supervision**
- Same data, multiple training objectives (L0/L1/L2/L3 jobs)
- Multi-objective loss: L_byte + L_tongue + L_null + L_word + L_policy
- Sacred Eggs = genesis/birth condition for the AI's identity and lineage

### 5. Brain Development Pressure Mapping
- REAL: developmental order (substrate → sensorimotor → association → prefrontal)
- REAL: current AI overweights expression, SCBE tries to restore substrate/routing/salience
- PARTIAL: PHDM radial zones as control architecture metaphor
- FORCED: exact brain-region and physical-pressure equivalence (corrected)

## Completed This Session (Continuation)
- Phase 5h: 211 Sacred Tongues SFT pairs (all 6 tongues)
- Polly Pump module: `src/polly_pump/` (3 files, 3 tests passing)
- Binary-First Training Stack spec: `docs/specs/BINARY_FIRST_TRAINING_STACK.md`
- Layer distribution audit of all training data
- Tongue binary analysis script: `scripts/tongue_binary_analysis.py`
- GRAND TOTAL SFT: 123,929 pairs (sft/ directory) + 42K mega files (overlap)

## Overnight Build Complete (14 commits)
- 233,179 multi-view SFT pairs built and uploaded to HuggingFace
  - L0 substrate: ~21K (9%), L1 coordination: ~25K (11%), L2 orientation: ~73K (31%), L3 expression: ~114K (49%)
- 10,000 dedicated L0/L1 substrate tasks (byte arithmetic, tongue encode/decode)
- 1,000-bundle pump aquifer built and uploaded (the dantian)
- 6 Sacred Egg genesis identity rows (first in every training run)
- 47 eval benchmark tasks generated
- Kaggle comparison notebook ready (`scripts/train_polly_kaggle_comparison.py`)
- Interactive pump chat interface (`scripts/polly_chat.py`)
- Canonical event compiler (`src/polly_pump/compiler.py`)
- 21 CodeQL fixes (16 high-severity + 5 warnings/notes)
- 233 tests passing (pump + Sacred Tongues + crypto + Sacred Eggs + null space)
- All artifacts verified (0 parse errors)
- HuggingFace dataset README updated
- Baseline benchmarks captured:
  - Unified triangulation: 75.8% detection, 13.3% FP
  - E4 semantic: 85.7% detection, 0% FP
  - E4 + null space: 100% detection (holdout FP needs tuning)

## Publishing (via PR #897)
- Website article: https://aethermoore.com/articles/2026-03-31-nightly-roundup.html
- GitHub Discussion #896: https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/896
- Bluesky: https://bsky.app/profile/issdandavis.bsky.social/post/3midtijmubb22
- Blocked: X (auth), Dev.to (key), HF discussion (shell restriction)
- Publish log: `notes/sessions/2026-03-31-nightly-roundup-publish.md`

## Next Actions
1. **Train on Kaggle** — paste `scripts/train_polly_kaggle_comparison.py`, enable GPU, set HF_TOKEN
2. **Compare** baseline (116K L3) vs stack-lite (233K L0-L3) on route/governance/tongue/drift
3. **Tune null-space threshold** — holdout FP at 100% needs calibration
4. **Fix X auth** — app config issue, not missing script
5. **Fix Dev.to key** — local key unusable
6. **Process remaining novel pastes** from conversation buffer
7. **DPO preference pairs** (good vs bad answers)
