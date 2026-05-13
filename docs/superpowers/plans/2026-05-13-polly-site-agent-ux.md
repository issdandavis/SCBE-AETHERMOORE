# Polly Site Agent UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public site and Polly sidebar behave like a useful SCBE web agent that can route buyers, researchers, and AI assistants to real actions.

**Architecture:** Extend the existing static sidebar and Vercel Polly chat endpoint. Do not add a parallel chatbot. Use AI-readable docs (`robot.md`, `llms.txt`, `app-config.json`) as the public skill map, and keep deterministic commerce/research routing ahead of LLM fallback.

**Tech Stack:** Static HTML/CSS/JS in `docs/`, Vercel Node handlers in `api/polly/`, Vitest and pytest regression tests.

---

### Task 1: Polly Role Packet

**Files:**
- Modify: `docs/static/polly-sidebar.js`
- Modify: `api/polly/chat.js`
- Test: `tests/api/polly_commerce_js.test.ts`

- [ ] Add a compact `scbe-web-agent` role packet to sidebar chat requests.
- [ ] Server should convert a valid role packet into bounded system context for LLM fallback only.
- [ ] Deterministic routes must keep working without LLM or cloud keys.

### Task 2: Useful Sidebar UX

**Files:**
- Modify: `docs/static/polly-sidebar.js`
- Modify: `docs/static/polly-sidebar.css`
- Test: `tests/api/test_polly_widget_contract.py`

- [ ] Replace generic starter prompts with buyer, agent-task, and research prompts.
- [ ] Add a short mission strip that tells visitors what Polly can actually do.
- [ ] Keep actions accessible and keyboard-friendly.

### Task 3: Site Banner/Ticker Health

**Files:**
- Modify: `docs/index.html`
- Test: `tests/test_vercel_launch_bridge.py`

- [ ] Make ticker speed scale with feed size instead of being a fixed crawl.
- [ ] Add reduced-motion handling.
- [ ] Refresh homepage copy for live Workflow Snapshot + Polly agent routing.

### Task 4: AI-Readable Agent Map

**Files:**
- Modify: `docs/robot.md`
- Modify: `docs/robot.html`
- Modify: `docs/llms.txt`
- Modify: `docs/app-config.json`
- Test: `tests/test_vercel_launch_bridge.py`

- [ ] Add Polly role guidance, skill map, and exact public pages for AI assistants.
- [ ] Keep free path first, low-cost path second, and avoid certification overclaims.

### Task 5: Verification

**Files:**
- No code changes unless tests fail.

- [ ] Run `npx vitest run tests/api/polly_commerce_js.test.ts`.
- [ ] Run `python -m pytest tests/api/test_polly_widget_contract.py tests/test_vercel_launch_bridge.py -q`.
- [ ] Run a local chat handler smoke for `/help`, workflow snapshot price, and agent-task routing.
