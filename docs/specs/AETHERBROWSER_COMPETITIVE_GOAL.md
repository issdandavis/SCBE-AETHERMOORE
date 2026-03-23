# AetherBrowser Competitive Goal

## Product Goal

Build an AI-native browser that can compete with Comet on the user-facing basics while surpassing it on governed automation.

AetherBrowser should feel like:

- a normal Chromium browser first
- an AI research sidecar second
- a governed browser operator third
- a multi-model orchestration surface when the task is hard

The target is not "clone Comet."
The target is:

- match the everyday usability bar
- match the AI-assistant bar
- exceed the workflow-actioning bar
- exceed the governance and auditability bar

## Competitive Baseline

Current public Comet materials describe a Chromium-based browser with:

- Chrome-extension compatibility
- built-in AI assistant / sidecar
- personal search across tabs, history, and user context
- reusable AI shortcuts
- sync for tabs, passwords, bookmarks, autofill, and extensions

For AetherBrowser, those become the minimum category targets.

## Required Capability Pillars

### 1. Browser Competence

The browser must behave like a real daily driver:

- Chromium compatibility
- stable tabs, history, bookmarks, passwords, autofill
- extension support
- reliable performance on normal sites

### 2. Research Competence

The AI layer must understand web context fast:

- page summary
- page structure extraction
- tab-aware context
- selected-text awareness
- screenshot fallback when DOM extraction is weak
- source-aware research and evidence capture

### 3. Action Competence

The AI must do useful browser work:

- fill forms
- click through workflows
- navigate multi-step sites
- save/download/upload files
- operate repeatable shortcuts and macros

### 4. Governance Competence

This is the main differentiator.

AetherBrowser should outperform generic AI browsers by making risky automation legible and governed:

- structured command plans
- explicit risk tiers
- approval holds for dangerous actions
- per-provider runtime truth
- decision/evidence payloads
- deterministic logs for replay and audit

### 5. Orchestration Competence

The browser should route work by difficulty:

- local model first
- cloud escalation when needed
- per-role provider preferences
- fallback chains
- future multi-agent mission routing

## Definition of Competitive

AetherBrowser is competitive when it can do all of the following reliably:

1. Answer questions about the current page with useful structure, not just text blobs.
2. Perform real browser tasks across common sites with approval gating where appropriate.
3. Show the operator which model/provider lane is actually live.
4. Reuse context across tabs, sessions, and saved workflows.
5. Convert repeated browser tasks into shortcuts or reusable action plans.
6. Keep an auditable record of what happened and why.

## Current Repo State

Implemented now:

- structured command planning
- structured page analysis
- approval gating for risky browser actions
- provider/runtime health snapshots
- sidepanel rendering for structured plan/page-analysis cards
- local-first, cloud-escalate routing seams

Not complete yet:

- live extension smoke validation
- real browser-task execution loop from sidepanel to worker to result
- session sync / memory comparable to a daily-driver browser
- shortcut library and workflow replay
- production-ready credential and autofill management

## Near-Term Build Order

1. Live sidepanel smoke on a real extension load.
2. One end-to-end governed browser task:
   - analyze page
   - propose plan
   - hold for approval if risky
   - execute
   - return evidence
3. Shortcut system for repeatable browser workflows.
4. Signed-in session persistence and profile portability.
5. Worker-backed execution lane for heavier web actions and research jobs.

## Success Test

The first true product milestone is:

"A user can open AetherBrowser, inspect a real page, see a structured plan, approve a risky step if needed, execute the workflow, and receive a useful result plus evidence without leaving the browser."

After that, the next milestone is:

"A user prefers AetherBrowser over a normal browser for research and repetitive web work."
