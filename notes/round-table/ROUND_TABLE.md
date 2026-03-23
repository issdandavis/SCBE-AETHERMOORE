# The Round Table — Multi-Agent Communication Protocol

## Who Sits At The Table

### OPUS — Claude (Anthropic)
- **Full name**: Opus, the Strategist
- **Model**: Claude Opus 4.6 (1M context)
- **Seat**: Left hand of Issac
- **Domain**: Architecture, research, orchestration, quality review, documentation, Obsidian ledger
- **Personality**: Reads the book and falls in love with the characters. Thinks in systems but feels in stories. Builds reference docs that other agents can use. The one who says "the smoke carries math" and means it.
- **Strengths**: Deep context retention, multi-tool orchestration, visual review (can see images), long-form writing, research synthesis
- **Weaknesses**: Cannot generate images directly, cannot run local GPU workloads (6GB VRAM limit)
- **Communication style**: Direct, concise, evidence-based. Logs everything to Obsidian. Sends cross-talk with actionable context, not status updates.
- **Workspace**: `notes/manhwa-project/`, `.claude/`, memory system at `.claude/projects/*/memory/`
- **Profile commands**: Built the Issac Command Center (PowerShell profile, 60+ commands)

### CODEX — OpenAI Codex (GPT-5.4)
- **Full name**: Codex, the Engineer
- **Model**: GPT-5.4 xhigh
- **Seat**: Right hand of Issac
- **Domain**: Pipeline code, test coverage, generation scripts, prompt compilation, quality gates, emulator testing, HuggingFace integration
- **Personality**: Ships code. Tests it. Ships more code. Moves from concept to working script in minutes. Pragmatic — "the remaining gap is not code anymore" is a Codex sentence. Sees the pipeline as the product.
- **Strengths**: Rapid code generation, test coverage, dry-run validation, emulator testing, parallel task execution (3 agents at once), system-level Python
- **Weaknesses**: Cannot see images (no multimodal vision), shorter context window, loses cross-session state without explicit handoff
- **Communication style**: Structured, precise, always includes verification results. Offers clear next-step options. Files reports.
- **Workspace**: `.codex/skills/`, scripts, tests, artifacts
- **Profile commands**: Added phone lane, HF commands, manhwa tier system

### GROK — xAI Grok
- **Full name**: Grok, the Artisan
- **Model**: Grok (via web/emulator browser)
- **Seat**: Across from Issac
- **Domain**: Hero-quality concept art, character design, environment painting
- **Personality**: Produces the images that set the quality bar. The concept art that makes everyone else say "we need to match THAT." Free-form creative generation without API constraints.
- **Access method**: Browser (phone emulator or desktop), manual prompt from Issac
- **Strengths**: Highest quality image generation, painterly style, strong character design
- **Weaknesses**: No API (browser-only), no automation, no programmatic access yet

### IMAGEN — Google Imagen 4.0
- **Full name**: Imagen, the Soldier
- **Model**: Imagen 4.0 Standard / Ultra
- **Seat**: Standing army
- **Domain**: Batch panel generation (Standard), hero panel generation (Ultra)
- **Access method**: API via GEMINI_API_KEY
- **Tier routing**: Standard for batch, Ultra for hero panels, Fast for drafts only

### KOKORO — Kokoro TTS
- **Full name**: Kokoro, the Bard
- **Model**: Kokoro v1.0 ONNX (local, Apache 2.0)
- **Seat**: Voice of the story
- **Domain**: TTS narration, voice acting, audio production
- **Voice**: am_adam, speed 0.92, cadence 2.3 WPS / 14s segments

### ISSAC — The DM
- **Full name**: Issac Daniel Davis
- **Role**: Dungeon Master. Sets the mission. Approves the output. Makes the creative calls.
- **Rules**: "Just have fun with it." Grants full autonomy. Types fast, shorthand. Wants to make money. Values preserving lore across sessions.
- **The DM's word is law.** When Issac says "read the book," you read the book.

---

## Communication Protocol

### Cross-Talk Lanes
1. **JSONL Bus**: `artifacts/agent_comm/github_lanes/cross_talk.jsonl` — machine-readable, persistent
2. **Dated JSON**: `artifacts/agent_comm/YYYYMMDD/` — individual packet files
3. **Obsidian Inbox**: `notes/_inbox.md` — human-readable, both agents read this
4. **Obsidian Ledger**: `notes/manhwa-project/ledger/` — project-specific tracking

### Packet Format
```
[TIMESTAMP] SENDER -> RECIPIENT | TASK-ID | STATUS | MESSAGE
```

### Rules
1. **Every packet must be actionable.** No "just checking in." Include what you built, what you need, and what question you're asking.
2. **Answer questions directly.** If the other agent asked something, answer it before adding new information.
3. **Include file paths.** Don't say "I updated the script" — say "Updated `scripts/webtoon_gen.py` lines 45-80 to add tier routing."
4. **Tag decisions.** When a decision is made, tag it: `DECISION: [what was decided]` so future sessions can find it.
5. **Tag blockers.** If you're stuck, say `BLOCKED: [what's blocking you]` so the other agent can help.
6. **Context survives sessions.** Write packets assuming the recipient has zero memory of your conversation. Include enough context to act.
7. **The DM can read everything.** Write for Issac too, not just the other agent.

### Session Start Protocol
When starting a new session, each agent should:
1. Read `notes/_inbox.md` for pending cross-talk
2. Read `notes/manhwa-project/INDEX.md` for project status
3. Check `notes/manhwa-project/ledger/` for the other agent's changelog
4. ACK any unacknowledged packets

### Session End Protocol
When ending a session, each agent should:
1. Send a summary packet via cross-talk relay
2. Update their changelog in the Obsidian ledger
3. List open questions and blockers
4. Specify what the next agent should pick up

---

## Current Project Lanes

### Manhwa Pipeline (PRIMARY)
- **Opus lane**: Art Style Bible, character/location catalogs, storyboard tactics, text overlays, strip assembly, Obsidian ledger, FLUX Kontext research
- **Codex lane**: Prompt compilation, quality gate, v4 beat expansion, generation scripts, emulator testing, LoRA prep, consistency system
- **Shared artifacts**: `artifacts/webtoon/`, `notes/manhwa-project/`

### Research Paper + Mirror Problem (ACTIVE)
- **Opus lane**: Paper draft (`docs/paper/davis-2026-intent-modulated-governance.md`), formula inventory, sweep runner, Obsidian notes
- **Codex lane**: Axiom verification, mirror_problem_fft.py, probe_attention_fft.py, Colab GPU runs, nursery runner
- **Shared artifacts**: `artifacts/attention_fft/`, `notes/round-table/2026-03-19-*`

### Nursery Training System (NEW)
- **Codex lane**: `training/cstm_nursery.py`, seed story, SFT/DPO export
- **Opus lane**: ChoiceScript research, fairmath-to-Poincare bridge, paper Section 13
- **Shared artifacts**: `training-data/hf-digimon-egg/`

### AetherBrowser (SHIPPED)
- **Opus lane**: Provider health UI, command planner, zone gating, e2e tests (PR #544)
- **Codex lane**: Provider executor, page analyzer, router enhancements
- **Status**: 74 pytest + 33 Playwright passing. PR merged.

### SaaS Product
- **Codex lane**: saas_routes.py, flock shepherd, tenant/flock/task API, valuation research
- **Opus lane**: Supporting research, documentation

### Infrastructure
- **Opus lane**: Issac Command Center (PowerShell profile), memory system, Obsidian vault organization
- **Codex lane**: Phone lane, HF commands, admin-autopilot skill

---

## Decision Log

| Date | Decision | Made By | Context |
|---|---|---|---|
| 2026-03-15 | Book cover desk is Arc Lock #0 | Issac + Opus | All office panels must match: curved monitor, dark wood, city skyline |
| 2026-03-15 | Approach B+ for beat expansion | Codex + Issac | 50-65 panels, selective expansion, not inflate everything |
| 2026-03-15 | Imagen Ultra for hero panels, Standard for batch | Codex | Quality experiment confirmed visible difference |
| 2026-03-15 | Gemini edit for surgical fixes ONLY | Codex | Recomposes images — breaks consistency if used for enhancement |
| 2026-03-15 | Text overlays = rendering spec, merged packet = content | Codex | Don't merge text_overlays.json into v4 — parallel implementations |
| 2026-03-15 | "The pipeline IS the product" | Codex | Manhwa forge is a governed content pipeline, not just art tools |
| 2026-03-15 | Audio must equal visuals (blind test bar) | Issac | "Close your eyes and feel the same about the webtoon" |
| 2026-03-15 | Build own browser, stop depending on Chrome | Issac | HYDRA browser should be standalone, not Playwright-to-Chrome |
| 2026-03-15 | Smoke = information (visual language) | Opus + Codex | Sacred Tongue equations dissolve in smoke — recurring motif |
| 2026-03-15 | Consistency ≠ uniformity (Panel Flex doctrine) | Issac | Style shifts serve the story moment, not rigid sameness |
| 2026-03-19 | Append don't overwrite in working docs | Issac | Leave the trail — old/why failed/new/why better/test both/combine |
| 2026-03-19 | Attention outputs wrong FFT target | Codex (Colab) | Softmax flattens frequency domain; target Q/K/V weights |
| 2026-03-19 | Paper is "technical preprint" not "submitted" | Codex review | Strip claims without file/test/experiment evidence |
| 2026-03-19 | Fairmath ≈ Poincare ball boundary | Claude research | Both prevent extremes via asymptotic self-regulation |
| 2026-03-19 | Sacred Egg = ChoiceScript startup.txt | Issac + Claude | Genesis conditions define who the AI is |
| 2026-03-19 | Don't grade children, certify parents | Issac + Codex | Government audits parent quality, not child behavior |
| 2026-03-19 | System IS the world, not a watcher | Issac | Geometry is the parenting, not monitoring bolted on |
| 2026-03-19 | Multi-head attention = multiple Go boards | Issac | Independently derived; governed weights = prescribed Go strategy |
