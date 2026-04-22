# Session Notes — 2026-04-20

## Polly Assistant Repair

### Problems Found
1. **Backend URL mismatch**: All pages used `http://localhost:8001` instead of production `https://api.aethermoore.com`
2. **Missing API endpoints**: `polly-sidebar.js` called `/v1/polly/*` routes that didn't exist in `api_server.py`
3. **Broken HF fallback**: HuggingFace Inference API free tier discontinued — all models return 404
4. **Response format mismatch**: JS expected flat responses, new API returns nested `{ok, data: {...}}`

### Fixes Applied

#### Backend (SCBE-AETHERMOORE)
- **New**: `scripts/system/polly_service.py` — deterministic intent classifier
  - 13 intents: pricing, cx_guardrail, iso_42001, red_team, datasets, contact, support, tools, research, members, open_source, book, greeting
  - Keyword-based matching (no LLM required)
  - Optional Gemini enhancement via `GEMINI_API_KEY`
  - Uses `httpx` (already in venv)
- **Added endpoints** to `api_server.py`:
  - `POST /v1/polly/chat`
  - `POST /v1/polly/respond`
  - `GET /v1/polly/context`
  - `POST /v1/polly/search`
  - `POST /v1/polly/delegate`
- **PR**: [#1130](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/1130) — merged

#### Website (issdandavis.github.io)
- **Bulk update**: 31 HTML files — `localhost:8001` → `https://api.aethermoore.com`
- **`polly-sidebar.js`**:
  - Removed all HF Inference code (`HF_MODEL`, `getHFToken()`, `roundTableConsensus()`, etc.)
  - Added `LOCAL_INTENTS` client-side fallback (mirrors backend logic)
  - Fixed response parsing for nested API format
  - Keeps: web search, memory recall, training data export, thinking mode
- **Pushed**: `main` branch

### Verification
- `curl https://api.aethermoore.com/v1/polly/chat` → returns correct routing responses
- Cloudflare tunnel active and serving traffic
- Deployed `polly-sidebar.js` has 0 HF references, 2 `LOCAL_INTENTS`, 3 `localIntentResponse`

### Remaining Issues (from earlier context)
- Orphan pages: `thank-you.html`, `hello.html`, `benchmark-kit.html`, `receipt.html`, `challenges.html` have no nav links
- Performance: `hero.png` is 1.8MB (180KB `hero.webp` exists but unused)
- No alt text on images, no favicon
