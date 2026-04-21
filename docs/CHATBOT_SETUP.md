# Polly Chatbot Setup

Polly is the sidebar assistant on aethermoore.com. It runs free in three modes
and degrades gracefully between them.

## How it runs

| Mode | When active | Where the answer comes from |
|------|-------------|-----------------------------|
| Offline corpus | Default on GitHub Pages | `docs/chatbot-corpus.json` bag-of-words match |
| DuckDuckGo web | On `/search` or freeform "search ..." | DuckDuckGo Instant Answer JSON API |
| HF Space | When `POLLY_API_BASE` points at a live Space | Qwen2.5-7B-Instruct via server-side HF token |

No tokens are shipped to the browser. The offline corpus and DuckDuckGo path
need zero secrets. The HF Space path keeps `HF_TOKEN` inside the Space's
private secrets.

## Slash commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/help` | Show this list inside the widget | `/help` |
| `/nav <section>` | Jump to a page section by name or alias | `/nav milestones` |
| `/search <query>` | DuckDuckGo Instant Answer lookup | `/search hyperbolic geometry` |
| `/sections` | Dump every jumpable section and its anchor | `/sections` |

Freeform intent also works. These are equivalent to the commands above:

- `take me to the demos section`
- `jump to milestones`
- `search for MATHBAC proposers day`
- `look up port-Hamiltonian control`

## Keyboard shortcuts

- `Ctrl+/` (or `Cmd+/` on Mac) opens or closes the widget from anywhere on the page.
- `Enter` sends. `Shift+Enter` inserts a newline.
- `Escape` closes the widget when the input is empty.

## Pointing Polly at a backend

Two options:

1. Open the widget, click the gear, paste the backend base URL into the
   "Polly API base" field. The value is persisted in `localStorage` under
   `pollyApiBase`.
2. Set `window.POLLY_API_BASE = "https://<user>-scbe-polly-chat.hf.space"` in
   an inline script before `docs/static/polly-companion.js` loads.

The widget calls `${base}/v1/chat` (POST) and `${base}/v1/spaceport/status` (GET).

## Deploying the HF Space

Source lives in `space/scbe-chat/`:

- `app.py` - FastAPI proxy that never leaks the token
- `requirements.txt` - FastAPI, Uvicorn, httpx, Pydantic
- `Dockerfile` - python:3.11-slim + uvicorn on 7860
- `README.md` - HF Space frontmatter and deploy steps

One-time deploy:

1. Create a Space named `issdandavis/scbe-polly-chat`, SDK docker.
2. Copy the four files from `space/scbe-chat/` into the Space repo.
3. In Space settings, add the secret `HF_TOKEN` (read scope).
4. Optional variable `HF_MODEL` (default `Qwen/Qwen2.5-7B-Instruct`).
5. Wait for build. Live URL: `https://<user>-scbe-polly-chat.hf.space`.
6. Point the site at it with either option above.

If the Space is down or has no token, the widget falls back to the offline
corpus automatically. No configuration change is needed.

## Updating the offline corpus

`docs/chatbot-corpus.json` is a flat list of passages:

```json
{
  "id": "unique-slug",
  "title": "Human title",
  "path": "docs/path/to/source.md",
  "tags": ["tag1", "tag2"],
  "excerpt": "2-4 sentences. This is what Polly surfaces inline."
}
```

Bump `version` when you add a batch. Keep excerpts short; the match is
bag-of-words, so dense keyword coverage ranks better than verbose prose.

## OPSEC

- Never commit an `HF_TOKEN` or any secret to the repo.
- The Space proxy is the only place the token lives.
- CORS on the Space is restricted to the production site origins.
- The widget never sees the token and never logs any response verbatim to
  analytics.

## Files

| Path | Purpose |
|------|---------|
| `docs/static/polly-companion.js` | Widget source (runs on every page) |
| `docs/static/polly-sidebar.css` | Widget styles |
| `docs/chatbot-corpus.json` | Offline passage index |
| `space/scbe-chat/app.py` | HF Space backend |
| `space/scbe-chat/Dockerfile` | Space container |
| `space/scbe-chat/requirements.txt` | Space Python deps |
| `space/scbe-chat/README.md` | Space deploy instructions |
