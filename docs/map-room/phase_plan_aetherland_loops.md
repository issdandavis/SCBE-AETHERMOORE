# Phase Plan — Long Form + Short Form Loops in Cycles (AetherLand Builds)

Owner: Grok (following user directive)
Date: 2026-06-20
Objective: Use long-form (checkpointed, manifest-driven) and short-form (rapid prototype/iter) loops in explicit cycles to build things in the AetherLand project. Demonstrate the pattern while delivering a new "ShortForm Desktop" embeddable widget + enhancements to the existing full desktop.

## Run Manifest (Long Form)
- Goal: Establish cyclic long/short form development as standard mode. Deliver:
  - ShortForm AetherLand: compact, single or dual window, embeddable desktop widget (for marketing pages, docs, quick demos).
  - Enhancements to full long-form aetherland-desktop.html (new app or polish).
- Scope in:
  - SCBE-AETHERMOORE/public/aetherland-desktop.html (long form base)
  - SCBE-AETHERMOORE/public/aetherland.html (marketing)
  - New: aetherland-shortform.html or integrated widget
  - docs/map-room/ artifacts for checkpoints
- Out of scope: Full backend, new servers, non-web.
- Success criteria:
  - Widget loads in <1s, works standalone and embeddable.
  - At least 2 full long/short cycles completed with artifacts.
  - Checkpoints written (phase_plan, handoff, decision log).
  - Measurable: 1 new app/feature in full desktop, ShortForm has 2+ working apps.
- Stop criteria: 2 cycles complete + working deliverables, or user redirects.

## Cycle Structure
**Long Form Phase** (detailed, using orchestrator style):
- Update manifest, phase plan, handoff.
- Architecture decisions, scope, risk analysis.
- Full evaluation plan.

**Short Form Loop** (rapid):
- Quick code bursts (1-3 edits or new small file).
- Immediate test (open in browser, manual + simple checks).
- Minimal docs.

Repeat cycles.

## Phases / Cycles
### Cycle 0 (Long) — Setup & Manifest (this file)
- Write phase plan + session handoff.
- Decide first build target: ShortForm widget (compact version of desktop with Terminal + Tongues for embed).
- Status: done

### Cycle 1 (Short Form) — Rapid ShortForm prototype
**Completed in short burst:**
- Created `public/aetherland-shortform.html` (self-contained, ~200 lines).
- Features: Tabbed apps (Terminal with live governance simulation + receipts, Tongues encoder with bars, Info).
- Fully embeddable, fast, no external deps.
- Integrated quick link into the AetherLand landing page (one-line edit).
- Manual tested: commands produce ALLOW/ESCALATE/DENY + receipt ids; tongues visual works.
- Time: one focused short-form pass.

**Artifacts:** new file + landing update.

### Cycle 1 (Short Form) — Rapid prototype ShortForm core
- Create minimal self-contained aetherland-shortform.html
- Core: desktop canvas + 1-2 apps (governed terminal + tongues).
- Make it embeddable (small size, iframe friendly).
- Quick test.

### Cycle 1 (Long Form) — Evaluate + detailed design
- Test the short prototype.
- Decide improvements.
- Plan enhancements for full desktop.
- Write checkpoint.

### Cycle 2 (Short) — Integrate + new feature
- Add the shortform as embed in aetherland.html
- Add one new app to full desktop using short bursts.
- Polish.

### Cycle 2 (Long) — Full evaluate + handoff
- End-to-end test.
- Metrics.
- Produce final handoff + action summary.

## Checkpoints
Every phase end: append to this file + update session_handoff_latest.md + decision_log.jsonl

## Notes
Follow long-form-work-orchestrator + scbe-longform-work patterns.
Use todo_write for active tracking.
Prefer deterministic: working HTML files, no hidden state.

### Cycle 3 (Short Form) — Optical + Thermal Fusion (just completed)

**Delivered:**
- `scripts/research/fuse_thermal_optical.py` — ready-to-use fusion function that takes your existing thermal score + the optical laser model and produces a combined anchor prediction score.
- Shows exactly how to call `apply_optical_laser` from the previous module and blend it.

**Next recommended short form:** Wire this into your main probe's scoring loop and re-run a small validation set.

**Cycle status:** Short form done. Ready for Long Form evaluation once you have sweep results.

### Cycle 2 (Short Form) — Enhance ShortForm (just completed)

**What was built in this short burst:**
- localStorage persistence for Terminal output/receipts + "Clear Log" button.
- New "Showcase" tab (4th app) with CSS product display: desk + monitor rendering a running AetherLand desktop (taskbar, icons, terminal window visible on screen). Fulfills original request for "user using computer and the computer displaying a desktop of the program running".
- Tab switching updated for 4 apps.
- All changes in one focused short-form iteration + immediate test.

**Deliverable:** `aetherland-shortform.html` now has persistence + visual product showcase.

**Cycle status:** Short form complete. Ready for Long Form evaluation.

Current cycle: Cycle 3 Short Form (optical model integration) — completed.

### Cycle 1 (Long Form) — Evaluation + Planning

**Evaluation of deliverables (as of 2026-06-20):**

**ShortForm Widget (`aetherland-shortform.html`):**
- Strengths: Extremely lightweight (~210 lines, instant load), fully self-contained, tabbed UX, convincing governance simulation in Terminal (realistic scoring + receipt generation), nice visual feedback on Tongues. Easy to embed (iframe or direct).
- Weaknesses: No state persistence, limited to 3 apps, no visual "product display" of user + running desktop yet. Info tab is basic.
- Metrics: 3 working apps, simulated SCBE decisions, receipt strings generated.

**Full Desktop (`aetherland-desktop.html`):**
- Strong long-form reference implementation with 5 rich apps, draggable windows, taskbar, start menu, lore integration. Very complete demo.
- Can serve as the "deep" experience.

**Landing (`aetherland.html`):**
- Good structure matching original request (banner, welcome, CTAs, promos, product display section).
- Now links both full and short versions.

**Cycle Method Adherence:**
- Successfully used Long setup → Short rapid build → Long checkpoint.
- Artifacts produced: phase plan, handoff, decision log entry.

**Overall Assessment:**
Good start. ShortForm fulfills "short form" need for quick embeds/marketing. Full version is the "long form" rich experience. Need to close the loop on the original "product display of user using computer showing the desktop".

**Decisions:**
- Prioritize ShortForm enhancements in next short burst (persistence + showcase visual).
- Keep pure static HTML/JS for easy deployment to GitHub Pages.
- Next measurable: Add localStorage + a CSS/JS "user at desk + monitor showing desktop" in ShortForm.

### Cycle 2 (Short Form) — Enhance ShortForm
Plan:
- Add localStorage persistence for the receipt log (so "past" actions survive reload).
- Add a 4th tab "Showcase" with stylized product display: desk + monitor showing a running AetherLand desktop (CSS mock + perhaps iframe the shortform itself or a canvas representation).
- Quick polish: better mobile styles, copy-receipt button.
- Test immediately in browser.
- One or two focused edits + new sections.

Then return to Long Form for evaluation.