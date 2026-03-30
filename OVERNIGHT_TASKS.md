# OVERNIGHT TASK LEDGER

**Last updated:** 2026-03-30 10:15 PM PDT
**Session source:** March 29-30 mega session (Claude + Codex + Gemini + Grok)

## RULES FOR ANY AGENT PICKING THIS UP

1. Work through tasks top to bottom by priority
2. When a task finishes, mark it `[x]` and note the result
3. When a task gets stuck, mark it `[!]` with the blocker, move to the next
4. Do NOT stop when one task finishes -- keep going
5. Do NOT ask for permission -- the task list IS the permission
6. Log everything to `artifacts/overnight/YYYY-MM-DD_overnight_log.md`
7. Commit progress every 3-5 completed tasks
8. Push to `overnight/YYYY-MM-DD` branch (not main)
9. When all tasks done or 8 hours elapsed, generate a receipt

---

## TONIGHT'S QUEUE (2026-03-30)

### Priority 1: Fix and Clean (target: 2 hours)

- [ ] Run full Python test suite (`python -m pytest tests/ -v`), fix every failure
- [ ] Run full TS test suite (`npx vitest run`), confirm 174/174
- [ ] Fix `build_pytest_command()` API drift (Codex flagged: `test_targets` now required)
- [ ] Clean unused imports flagged by GitHub code scanning
- [ ] Organize `notes/` folder -- move dated notes into `notes/YYYY-MM/`
- [ ] Delete empty/stale files in `artifacts/` older than 7 days
- [ ] Verify `.gitignore` catches everything (run `git status` and check for junk)
- [ ] Remove any `__pycache__` or `.pyc` from tracked files

### Priority 2: Improve Detection (target: 2 hours)

- [ ] Pull `darkknight25/Multilingual_Jailbreak_Dataset` (700 samples, 7 languages) into training pipeline
- [ ] Pull `dmilush/shieldlm-prompt-injection` (37.9K, 8 languages) into training pipeline
- [ ] Retrain with multilingual data + 4,786 docs SFT pairs
- [ ] Run strict-isolation blind benchmark on new model
- [ ] Log new detection rate (target: >40% blind, up from 34.5%)
- [ ] Wire Lyapunov V threshold into `validate_cube()` (fixes torsion xfail)
- [ ] Rerun `tests/test_perpendicular_torsion.py` -- xfail should become xpass
- [ ] Push updated model + results to HuggingFace
- [ ] Push updated results to Kaggle

### Priority 3: Document and Publish (target: 2 hours)

- [ ] Add bridge sentences to all 23 research pages (full tongue names: Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric)
- [ ] Update Kaggle dataset description with new training numbers
- [ ] Update HuggingFace dataset card with new numbers
- [ ] Generate training receipt (ASCII format like cc-receipt)
- [ ] Update `docs/research/TRAINING_INSIGHTS_2026-03-30.md` with new results

### Priority 4: Train a CHATBOT (target: 2-3 hours)

Goal: Fine-tune a small chat model so Issac can TALK to his AI.

- [ ] Pick base model: Qwen2.5-3B-Instruct (best free option for Kaggle GPU)
- [ ] Upload 7,132 SFT pairs to Kaggle as a dataset
- [ ] Create Kaggle notebook for fine-tune (LoRA/QLoRA, 4-bit quantized)
- [ ] Train for 3 epochs on Kaggle free GPU (P100 or T4)
- [ ] Export LoRA adapter
- [ ] Push trained model to HuggingFace: issdandavis/scbe-polly-chat-v1
- [ ] Create Gradio space on HuggingFace for live chat demo
- [ ] Wire PHDM embedding as trust gate (score input before chatbot responds)

The chatbot should:
  - Know SCBE architecture (from 4,786 docs SFT pairs)
  - Know governance concepts (from 1,262 Obsidian notes)
  - Know the Sacred Tongues by full name (Kor'aelin, Avali, etc.)
  - Respond as "Polly" (the SCBE governance assistant)
  - Refuse unsafe requests using the governance vocabulary

NOT a general chatbot. A SCBE-specific assistant that knows the system.

### Priority 5: Architecture Improvements (target: 2 hours, if time)

- [ ] Calibrate trichromatic quarantine/deny thresholds (currently 6% detection)
- [ ] Add `ESCALATE` and `DIRECT` to `Decision` enum in `runtime_gate.py`
- [ ] Map existing `REVIEW` -> `ESCALATE` and `REROUTE` -> keep as-is
- [ ] Run energy simulation on second Kaggle dataset for cross-validation
- [ ] Convert 5 more Notion research docs to HTML research pages
- [ ] Add honeypot weight as experimental flag (not default)

---

## COMPLETED TASKS (log here)

- [x] **10:11 PM** — TS tests confirmed 174/174 (5,957 passed)
- [x] **10:12 PM** — Python core tests confirmed 152/152 + 1 xfail
- [x] **10:12 PM** — build_pytest_command() already passing (Codex fixed)
- [x] **10:15 PM** — Pulled darkknight25 multilingual data: 4,898 records, 7 languages
- [x] **10:17 PM** — Retrained with multilingual: **73.5% blind detection** (was 34.5%)
- [x] **10:23 PM** — Pushed new model + results to HuggingFace
- [x] **10:23 PM** — Pushed new results to Kaggle
- [x] **10:30 PM** — Wired Lyapunov V into cube validation → torsion xfail FIXED (49/49 pass)
- [x] **10:35 PM** — Backed up 1.6 GB critical data to Dropbox/SCBE/backup-2026-03-30/
- [x] **10:35 PM** — Bridge sentences added to 6 research pages (full tongue names)
- [x] **10:40 PM** — PR #873 created for overnight work
- [x] **10:40 PM** — Codex taking over Python test suite stabilization (until midnight)

---

## BLOCKED TASKS (log here)

_Tasks move here when stuck. Include blocker description._

---

## OVERNIGHT RECEIPT TEMPLATE

When done, generate this:

```
╔════════════════════════════════════════════════╗
║              OVERNIGHT RECEIPT                 ║
║           [DATE]                               ║
╠════════════════════════════════════════════════╣
║ Tasks completed:          X / Y                ║
║ Tasks blocked:            X                    ║
║ Tests fixed:              X                    ║
║ Detection rate:           X% (was 34.5%)       ║
║ Files cleaned:            X                    ║
║ Research pages updated:   X                    ║
║ Commits:                  X                    ║
╟────────────────────────────────────────────────╢
║ Runtime:                  Xh Xm                ║
║ Agent:                    [name]               ║
╚════════════════════════════════════════════════╝
```

---

## HOW TO USE THIS FILE

**Before bed (human):**
1. Add any new tasks from the day's session
2. Reprioritize if needed
3. Start an agent with: "Read OVERNIGHT_TASKS.md and work through it"

**Morning (human):**
1. Check `artifacts/overnight/` for the log
2. Check the branch for commits
3. Review the receipt
4. Merge if green, fix if blocked

**Any agent picking this up:**
- This file is your authority to work
- The task list is the scope
- Don't expand scope beyond what's listed
- If something breaks, log it and move on
- Commit often, push to branch, never force-push main
