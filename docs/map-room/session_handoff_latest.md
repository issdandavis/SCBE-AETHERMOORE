---
objective: Train Polly chatbot with binary-first orientation stack
status: in_progress
phase: 6 — training pipeline + architecture validation
started: 2026-03-30T06:30:00-07:00
updated: 2026-03-31T01:00:00-07:00
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

## Active: Training Pipeline
- Merge training data for Kaggle/HuggingFace upload
- Train Polly on Kaggle free GPU (Qwen2.5-3B + QLoRA)
- Test pump packet at inference time
- Verify Sacred Tongues encoding/decoding in trained model
- Run adversarial detection with null-space signatures

## Next Actions
1. **Merge + upload** training data to HuggingFace/Kaggle
2. **Train baseline** Polly (L3 only, no pump) on Kaggle
3. **Train stack-lite** Polly (L3 + pump packet in system prompt)
4. **Compare** baseline vs stack-lite on:
   - route classification
   - governance posture accuracy
   - domain drift
   - in-domain QA
   - adversarial prompt handling
5. **Build L0/L1/L2 curriculum** — separate training tasks for each layer
6. **Canonical event compiler** — normalize every row into multi-view format
7. **Sacred Egg genesis wrapper** — seed identity before training begins
