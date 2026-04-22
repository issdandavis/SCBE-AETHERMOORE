# Phase Plan — Website Refresh + Offline-Capable Polly Chatbot

Owner: claude-opus-4-7 (autonomous, longform skill)
Started: 2026-04-21
Parent objective: "update website to reflect recent things + add sidebar chatbot with curated docs + navigation + web search + free HF inference; then push/verify/improve x4."

## Discovered context (pre-work)

- Sidebar chatbot **already exists**: `docs/static/polly-companion.js` (325 lines) + `docs/static/polly-sidebar.css` (380 lines). Expects `POLLY_API_BASE` backend returning `/v1/chat` + `/v1/spaceport/status`.
- On GitHub Pages the backend is unreachable → widget renders "Backend unreachable / Set API URL" and is functionally dead.
- Task therefore shifts from **build** to **enhance**: add offline fallback (corpus RAG + nav-intents + DDG search), ship HF Space source so the backend is deployable, and refresh site content.

## Phases

### Phase 0 — Longform scaffolding (this file + handoff + decision log)
Done when: three files committed to `docs/map-room/`.

### Phase 1 — Iter 1: milestones section + offline corpus chatbot
- Add `recent-milestones` block to `docs/index.html` covering MATHBAC proposal, Brick3 drill, Drill v5, 47D manifold, Toroidal Polyhedral Confinement, KDP book, AetherBrowser, SAM registration.
- Build `docs/chatbot-corpus.json` (hand-curated ~20-40 passages from docs/ and notes/theory/).
- Patch `polly-companion.js` with `offlineMode()` fallback: if `/v1/chat` fetch fails, do fuzzy corpus search and return top-3 excerpts as the "response".
- Push to `feature/cli-code-tongues`. Verify via `git log origin/feature/cli-code-tongues`. Log via `scripts/agents/log.sh`.

### Phase 2 — Iter 2: navigation intents + DuckDuckGo web search
- Client-side slash-commands: `/nav demos`, `/nav pricing`, `/search <q>`.
- Parse intents from freeform text too ("take me to demos" → nav intent).
- DDG free Instant Answer JSON: `https://api.duckduckgo.com/?q=<q>&format=json&no_html=1&skip_disambig=1` (no token, CORS-friendly).
- Navigation dispatches `window.location.href` change (with confirm prompt).
- Push + verify + log.

### Phase 3 — Iter 3: HF Space backend source
- `space/scbe-chat/app.py` — FastAPI. `/v1/chat` proxies to HF Inference API using Qwen2.5-7B-Instruct or similar free model. `/v1/spaceport/status` returns backends shape the client expects. `HF_TOKEN` read from env (Space secret).
- `space/scbe-chat/requirements.txt` — fastapi, uvicorn, httpx.
- `space/scbe-chat/README.md` — deploy steps: create Space → add HF_TOKEN secret → push → point `POLLY_API_BASE`.
- Note: no autonomous deploy from this session; owner ships to HF manually.
- Push + verify + log.

### Phase 4 — Iter 4: polish
- ARIA labels on launcher/close/send.
- Keyboard shortcut: `Ctrl+/` toggles widget.
- Starters refreshed to reference new milestones.
- `docs/CHATBOT_SETUP.md` — one-page "how to connect a real backend" guide.
- Corpus v2: expand to 60+ passages including MATHBAC/Brick3/47D/Gyroscopic Interlattice/Gravity Battery.
- Push + verify + log.

## Done criteria for the whole run

1. All four iterations pushed to `origin/feature/cli-code-tongues` and visible in `git log`.
2. Each iteration logged in `scbe-backofhouse/CHANGELOG.md`.
3. On GitHub Pages, widget works even with no backend URL set: user can ask a doc question → gets corpus excerpts; `/nav demos` → navigates; `/search <q>` → DDG result.
4. HF Space source is ready to deploy (but deployment itself is deferred to owner).

## Invariants

- Do NOT touch `docs/members/` — still contained, PIN-gate decision pending.
- No secrets in any committed file. HF_TOKEN lives only as a Space secret, never in repo.
- No new dependencies beyond what's already in the site (vanilla JS only on client).
- Keep existing `polly-companion.js` API surface; only add fallbacks.
