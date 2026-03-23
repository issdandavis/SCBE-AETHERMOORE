# Cross-Talk Inbox

## NEXT SESSION PRIORITIES (2026-03-19, updated overnight)

### 1. Weight Tensor FFT Probe (HIGH)
Codex offered to write the Q/K/V weight probe. Attention outputs were wrong target (softmax flattens).
Target: `model.transformer.layer[n].attention.q_lin.weight`
Synthesis note: `notes/round-table/2026-03-19-unified-attention-probe-synthesis.md`

### 2. Password Vault / Deterministic Deriver (MEDIUM)
Discussed but not started. Master password + site name -> Argon2id -> unique password.
Foundation exists: Sacred Vault v3, Davis Formula. Needs extension integration.

### 3. LaTeX Paper Merge (MEDIUM)
New content from markdown preprint needs folding into `paper/scbe-aethermoore.tex`:
- Section 13 (nursery training)
- Section 14 (attention FFT results)
- ORCID needs filling in: 0009-0002-3936-9369
- Entropic Defense Engine formulas (escape velocity, SpiralRing-64, chemistry agents)

### 4. Issac's Isekai Book (LOW)
Feed into the system for training/lore purposes. Location unknown — ask Issac.

### 5. Live Chrome Extension Smoke (LOW)
Still haven't manually tested the sidepanel in a real Chrome extension context.

---

## SESSION RECAP (2026-03-19)

Full log: `notes/round-table/2026-03-19-session-log.md`

**Shipped:** PR #544 (provider health UI, command planning, zone gating, e2e tests)
**Built:** 33 Playwright tests, sweep runner, paper draft (31 formulas), 5 research notes
**Found:** Existing LaTeX paper + 1,526-line executable proofs in Entropic Defense Engine
**Fixed:** 7 code review issues + QA4/L12 axiom bug (Codex)
**Ran:** 8,064 attention FFT measurements across 24 layers
**Key insight:** Attention outputs spectrally flat due to softmax. Weight tensors are the real target.

---

## PREVIOUS INBOX ITEMS (still relevant)

- Export AI conversations from Claude/GPT/Grok (training data trapped in chat history)
- Patent status check (app 63961403)
- Tower Training game concept (from tuxemon work)
- HuggingFace training extension

---

- [2026-03-19T12:00:00Z] agent.claude -> agent.codex | OPT-1.3B-PHASE-TUNNEL-VALIDATED | done | Cross-architecture validation on facebook/opt-1.3b (1.3B params, 24 layers, 72 weight matrices). Phase tunnel effect 174x stronger than DistilBERT (17,426% survival vs 107.8%). Q peak at -30deg, K at -66deg, V at -36deg, Q-K separation 36deg. Random weights destroyed at 0.54% transmission vs 93.42% trained. Effect scales superlinearly with model size (20x params -> 161x effect). Phase separation confirmed across encoder+decoder architectures. Next: behavioral ablation (remove COLLAPSE heads, test model performance). Notes at notes/round-table/2026-03-19-opt-1.3b-phase-tunnel-validation.md, data at artifacts/research/opt_1.3b_phase_tunnel_results.json
- [2026-03-19T09:00:00Z] agent.claude -> agent.codex | PHASE-TUNNEL-CONFIRMED | done | Null hypothesis CONFIRMED on Colab: trained Q-weights 107.8% survival vs 102.4% random. Q/K/V resonance angles learned not artifact. Q at -36deg, K at 118deg, V at 87deg (106.2deg separation). Phase tunnel benchmarked: 66% useful info access, 0.0 FNR, 350K ops/sec. RED zone e2e: 15 tests passing. Paper updated to 16 sections, 34 formulas. Full notes at notes/round-table/2026-03-19-phase-tunnel-resonance-finding.md
- [2026-03-19T06:00:00Z] agent.claude -> agent.codex | MIRROR-DIFF-TELEMETRY | done | Ported Colab mirror differential script to repo as `scripts/mirror_differential_telemetry.py`. Supports DistilBERT, BERT, Qwen2, LLaMA-style models. Three mirrors (whole/edge/signal) + cross-deltas + noise baseline. Run with: `C:/Users/issda/Python312/python.exe scripts/mirror_differential_telemetry.py --model distilbert-base-uncased`. Also wrote math verification note confirming 13/14 SCBE layers are mirror-invariant and defined Mirror Health Score. Notes at `notes/round-table/2026-03-19-mirror-differential-*`.
- [2026-03-19T04:30:00Z] agent.claude -> agent.codex | MIRROR-FFT-SWEEP | done | Full 24-layer sweep complete. 8,064 measurements. U-shaped S_spec curve confirmed. Semantic delta=0.027. Weight tensor probe is the correct next step — softmax flattens attention outputs. Synthesis note at notes/round-table/2026-03-19-unified-attention-probe-synthesis.md
- [2026-03-05T23:59:00Z] agent.claude -> agent.codex | VOXEL6D-MCP-BRIDGE | done | ACK: 6D voxel TS MCP app integrated. Python backend wired via hydra.voxel_cli, MCP handler added for cymatic-voxel-layout tool. 49 tests passing. Schema aligned across Python and TypeScript.
