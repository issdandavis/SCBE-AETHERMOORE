# SCBE-AETHERMOORE System State Consolidation

**Date**: 2026-04-05
**Branch**: site-publish-v4
**Commits**: 2,088
**Modified (uncommitted)**: 227 files

---

## 1. Codebase Scale

| Area | Python | TypeScript | Rust | Total Lines |
|------|--------|-----------|------|-------------|
| `src/` | 515 files (220K lines) | 699 files (164K lines) | — | 384K |
| `tests/` | — | — | — | 632 files, 78K lines |
| `training/` | 29 files | — | — | 13K lines |
| `scripts/` | 415 files | — | — | 149K lines |
| `agents/` | 53 files | — | — | 16K lines |
| `packages/` | — | 46+1 files | — | (kernel + sixtongues) |
| **Total** | ~1,012 .py | ~699 .ts | 2 .rs | **~640K lines** |

## 2. Module Map (`src/`)

### Core Pipeline (14-Layer)
| Module | Py | TS | Purpose |
|--------|----|----|---------|
| `harmonic/` | 8 | 52 | L1-L12 pipeline, hyperbolic, breathing, Mobius |
| `spectral/` | — | 1 | L9-10 FFT coherence |
| `crypto/` | 43 | 16 | PQC, gallery chromatics, tri-bundle, dark fill |
| `governance/` | 8 | 10 | L13 risk decisions |
| `fleet/` | 5 | 46 | Multi-agent consensus, Byzantine voting |
| `security-engine/` | — | 7 | Advanced security engine |
| `security/` | 4 | — | Security enforcement |

### Audio Stack (L14 — fully wired as of today)
| File | Lines | Role |
|------|-------|------|
| `src/audio/tongue_prosody.py` | 176 | 6D tongue weights → 5D voice params |
| `src/crypto/speech_render_plan.py` | 154 | Plan + earcon + dead tone pretones |
| `src/crypto/choral_render.py` | 273 | 1/2/4-voice layers, prosody curves |
| `src/crypto/gallery_chromatics.py` | 432 | Dual-iris color field (24 CIELAB points) |
| `src/audio/gallery_sonifier.py` | 220 | Color → audio params (hue→freq, chroma→amp) |
| `src/audio/spectrogram_bridge.py` | 639 | WAV → STFT → tongue bands → gallery projection |
| `src/crypto/world_bundle.py` | 313 | Chi circulation, alignment scoring |
| `src/crypto/harmonic_dark_fill.py` | 512 | 3-band fill (infra/audible/ultra), complement pairs |
| `src/symphonic_cipher/audio/stellar_octave_mapping.py` | 336 | f_human = f_stellar × 2^n |
| `src/crypto/quantum_frequency_bundle.py` | 2,316 | Dead tones, biological models, QHO states |
| `src/crypto/tri_bundle.py` | 524 | Light/sound/math tri-braid encoding |
| **Total Audio Stack** | **5,895** | |

### Supporting Modules
| Module | Files | Purpose |
|--------|-------|---------|
| `symphonic_cipher/` | 210 py | Python reference impl (CAUTION: dual package) |
| `ai_brain/` | 2py + 24ts | 21D brain mapping |
| `browser/` | 6py + 14ts | Hyperbolic trust browser |
| `aetherbrowser/` | 13 py | AI-native browser |
| `game/` | 13 ts | Combat, micro-ledger |
| `spiralverse/` | 11py + 6ts | Spiralverse protocol |
| `m4mesh/` | 13 py | M4 mesh networking |
| `knowledge/` | 20 py | Knowledge engine |
| `training_pad/` | 7 py | Training sandbox |
| `word-addin/` | 424 ts | Word add-in (bulk) |

## 3. Test Coverage

### Test Directories (632 files total)
| Directory | Files | Focus |
|-----------|-------|-------|
| `L2-unit/` | 30 | Isolated function tests |
| `harmonic/` | 35 | Pipeline-specific (L1-L12) |
| `crypto/` | 26 | PQC, bundles, chromatics |
| `ai_brain/` | 21 | 21D mapping |
| `hydra/` | 18 | HYDRA orchestration |
| `adversarial/` | 17 | Attack simulations |
| `fleet/` | 16 | Consensus, Byzantine |
| `aetherbrowser/` | 14 | Browser agent |
| `enterprise/` | 12 | Compliance |
| `interop/` | 11 | TS/Python parity |
| `cross-industry/` | 7 | Industry standards |
| `api/` | 6 | REST endpoints |
| `audio/` | 2 | **132 tests, 1.1s** (spectrogram + golden-path + stellar + dark fill) |
| `video/` | 4 | Video processing |
| Others | ~413 | Various domains |

### Audio Tests (verified green, 2026-04-05)
| File | Tests | Coverage |
|------|-------|----------|
| `test_spectrogram_bridge.py` | 69 | All module functions, full pipeline, constants, dead tone detection |
| `test_golden_path_integration.py` | 63 | 5 golden-path fixtures + drift detection + stellar octave (6) + dark fill (11) + bridge (5) |
| **Total** | **132** | **All passing, 1.13s** |

## 4. Training Infrastructure

### Snake Pipeline (18 stages)
| Stage | File | Status |
|-------|------|--------|
| 1. Intake & Marking | `training/auto_marker.py` | EXISTS |
| 2. HYDRA Deliberation | `training/snake/hydra_deliberation.py` | NEW |
| 3. Lattice Routing | `training/snake/lattice_router.py` | NEW |
| 3.5 Mirror Refractor | `training/snake/mirror_refractor.py` | NEW |
| 4. Hyperbolic Embedding | `training/snake/hyperbolic_embed.py` | NEW |
| 5. Friction Scoring | `training/snake/friction_scorer.py` | NEW |
| 6. Multi-Lang Forge | `training/snake/multilang_forge.py` | NEW |
| 6b. Sphere Grid | `training/snake/sphere_grid.py` | NEW |
| 7. Adversarial Traps | `training/snake/adversarial_traps.py` | NEW |
| 8. Big Brother Coach | `training/snake/big_brother_coach.py` | NEW |
| 9. EDE Defense | `training/snake/ede_defense.py` | NEW |
| 10. DTN Router | `training/snake/dtn_router.py` | NEW |
| 11. DTN Curriculum | `training/snake/dtn_curriculum.py` | NEW |
| 12. Primitives Curriculum | `training/snake/primitives_curriculum.py` | NEW |
| 13. Synesthesia | `training/snake/synesthesia.py` | NEW |
| 14. Polly Pad | `training/snake/polly_pad.py` | NEW |
| 15. Config | `training/snake/config.py` | NEW |
| 16. Pipeline Orchestrator | `training/snake/pipeline.py` | NEW |

### Training Data Inventory
| Category | Files | Size | Notes |
|----------|-------|------|-------|
| `multiview_sft.jsonl` | 1 | 239 MB | Largest single file |
| `polly_training_merged.jsonl` | 1 | 171 MB | Polly character data |
| `mega_tetris_enriched_sft.jsonl` | 1 | 102 MB | Tetris-enriched |
| `mega_ingest_sft.jsonl` | 1 | 91 MB | Mega ingestion |
| `code_master_sft.jsonl` | 1 | 39 MB | Code SFT |
| `code_triangulated_sft.jsonl` | 1 | 29 MB | Triangulated code |
| `code_multiview_sft.jsonl` | 1 | 11 MB | Code multiview |
| `sft/` subdirectory | 148 | various | Per-topic SFT files |
| `game_sessions/` | 19 | various | Game session data |
| **Total JSONL** | **267 files** | **~700+ MB** | |

### Training Run History
| Run | Dataset | Result | Platform |
|-----|---------|--------|----------|
| Round 1 (chat) | Vault-tagged SFT | 14% multiview improvement | Kaggle T4 |
| Round 2 (code) | Code SFT | 31% multiview improvement | Kaggle T4 |
| Round 3 (mixed L0) | Mixed L0+vault | 7.9% multiview improvement | Colab T4 |
| Model: Qwen2.5-0.5B, 4-bit QLoRA, 150 steps | | | |

### Training Pair Types (taxonomy documented)
- 5 industry standard (flat text)
- 8 SCBE structural (multi-view, friction, polyhedral, bit/float/trit, adversarial, multi-lang, null)
- 8 SCBE audio cross-modal (prosody, choir, color↔sound, dead tone, dark fill, stellar, coherence, spectral governance)
- **~21 base types, ~40-60 with compositions**
- Full taxonomy: `notes/theory/2026-04-05-training-pair-taxonomy.md`

## 5. Documentation

### Specifications (`docs/specs/`) — 82 files
Key frozen contracts:
- `AUDIO_SYSTEM_STACK.md` — v1.1, 10 modules, 12 cross-module rules, coherence metric
- `BINARY_FIRST_TRAINING_STACK.md` — L0-L3 training architecture
- `CANONICAL_FORMULA_REGISTRY.md` — All canonical formulas
- `HARMONIC_DARK_FILL_INTEGRATION.md` — Tri-braid dark fill
- `PHI_ACOUSTIC_ROUTER_SPEC.md` — 7 tuning systems, personality waves
- `SCBE_SYSTEM_GLOSSARY.md` — Strict scientific naming

### Research (`docs/research/`, `docs/paper/`, `docs/patent/`)
- Patent: `CIP_TECHNICAL_SPECIFICATION.md`, `PRIOR_ART_ANALYSIS.md`
- Paper: `davis-2026-intent-modulated-governance.md`
- Research: Various null-space, embedding-space, topology docs

### Architecture (`docs/00-overview/`, `docs/01-architecture/`)
- `LAYER_INDEX.md` — Complete 14-layer reference
- `SPEC.md` — Kernel specification
- `SYSTEM_ARCHITECTURE.md` — Detailed architecture
- `sacred-eggs-systems-model.md` — Sacred Eggs lifecycle

### Total docs: **1,181 .md files** in `docs/`

## 6. Obsidian Vault (`notes/`)

| Folder | Count | Content |
|--------|-------|---------|
| `sphere-grid/` | 122 | KO/AV/RU/CA/UM/DR tongue-specific notes |
| `round-table/` | 35 | Multi-agent research sessions |
| `manhwa-project/` | 12 | Webtoon/manhwa assets |
| `theory/` | 9 | Training taxonomy, formula inventory, harmonic training, personality matrix |
| `sessions/` | 5 | Session logs |
| `user-guides/` | 2 | Guides |
| `branch-archive/` | 1 | Branch notes |
| **Total** | **193** | All tagged with YAML frontmatter |

## 7. Claude Memory (62 entries)

Categories:
- **project**: Training infrastructure, polyhedral enrichment, dense cubes, self-healing, dark fill, revenue model, etc.
- **discovery**: 47D manifold, humor as intelligence, pazaak, toroidal confinement, friction training, gravity battery, phi cavity
- **feedback**: Just run it, don't suggest user run things, test like Issac, never delete data, OPSEC, strict rigor, training persistence
- **user**: Independent math derivation, creative process, location, SAM registration
- **reference**: Data locations, Notion chapters, DARPA contacts, Grok lore, HF deployment, APEX accelerator

## 8. Infrastructure

### Compute
| Resource | Spec | Status |
|----------|------|--------|
| Local CPU | i7-10750H, 12 threads | Active |
| Local RAM | 12 GB | Tight for >1B models |
| Local GPU | GTX 1660 Ti Max-Q, 6.4 GB VRAM, Compute 7.5 | **PyTorch 2.11.0+cu126 — CUDA ACTIVE** |
| Colab Pro | A100/V100 (paid) | Available |
| Kaggle | 2× T4 (16GB each), 30 hrs/week | Available |
| HuggingFace | `issdandavis` account | Active |

### Services
| Service | Status |
|---------|--------|
| Obsidian REST API | `127.0.0.1:27124` |
| Ollama | Running (PID 19132, GPU allocated) |
| n8n bridge | Port 8001 (when started) |
| GitHub Actions | 83 workflows |
| MCP servers | 10+ configured |

### Config Files
All present: `package.json`, `tsconfig.json`, `pytest.ini`, `vitest.config.ts`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`

## 9. Active Work Items

### Completed This Session (2026-04-05)
- [x] Audio system stack contract doc v1.1 (added stellar/dark-fill/phi-router)
- [x] 22 new integration tests (stellar octave + dark fill + bridge)
- [x] 132/132 audio tests green
- [x] Training pair taxonomy documented in vault
- [x] System state consolidation (this document)

### In Progress (other session)
- [ ] Superposition bridge (combined baseline + agent wave → FFT)
- [ ] Consonance scorer (ratio simplification → spectral flux)
- [ ] L14 gate wire (spectral flux → ALLOW/QUARANTINE/ESCALATE/DENY)
- [ ] 10 code review fixes applied across 8 files

### Next
- [x] CUDA PyTorch installation — PyTorch 2.11.0+cu126, GTX 1660 Ti, 6.4GB VRAM confirmed
- [ ] Local training run validation on 0.5B model
- [ ] Ablation: which of 21 pair types contributes most
- [ ] Colab Pro full run with enriched audio-stack pairs
- [ ] DARPA MATHBAC profile by 2026-04-14, Proposers Day 2026-04-21
- [ ] DARPA CLARA deadline 2026-04-17

## 10. Compression Log

### What this document replaces/consolidates
- Scattered mental model across 62 memory entries
- Informal knowledge of "what exists where"
- Test results from multiple sessions
- Training data inventory (previously unwritten)
- Audio stack wiring status (previously only in AUDIO_SYSTEM_STACK.md contract)

### What to verify before next training run
1. ~~CUDA PyTorch is installed and `torch.cuda.is_available() == True`~~ **DONE** (2.11.0+cu126)
2. Snake pipeline produces valid JSONL with all 16 stage annotations
3. Audio-enriched pairs are included in training data
4. Multiview batching generates all 4 views per record
5. Cross-consistency loss is wired into training loop
6. Friction vectors are computed alongside governance scores
