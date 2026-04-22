---
title: SCBE Polly Space
emoji: 🦜
colorFrom: indigo
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# SCBE Polly Space

Free-tier Hugging Face Space that backs the site-side Polly chat widget at
[docs/static/polly-companion.js](../../docs/static/polly-companion.js).

## Endpoints

| Method | Path                       | Purpose                                             |
|--------|----------------------------|-----------------------------------------------------|
| GET    | `/`                        | health ping                                         |
| GET    | `/v1/spaceport/status`     | status chip data for the widget header              |
| POST   | `/v1/chat`                 | `{message, tentacle, mode, context}` -> `{response, model, domain, sources}` |

## Deploy (one-time)

1. Create a Space: `issdandavis/scbe-polly-chat`, SDK = `docker` (or `gradio` + `fastapi`).
2. Copy `app.py`, `requirements.txt`, `README.md`, and this `Dockerfile` (below).
3. **In Space settings -> Variables and secrets**:
   - `HF_TOKEN` (secret, scope read): your Inference API token.
   - `HF_MODEL` (variable, optional): default `Qwen/Qwen2.5-7B-Instruct`.
4. Wait for build; the Space goes live at `https://<user>-scbe-polly-chat.hf.space`.
5. Point the site widget: on the live site open Polly settings, paste the Space URL,
   or set `window.POLLY_API_BASE` in a small inline script.

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

## OPSEC

- `HF_TOKEN` is a **Space secret**, never committed to this repo.
- The Space runs server-side; the client never sees the token.
- CORS is restricted to the live site origins.
- If the token is absent at request time, the Space returns a graceful
  message and the on-site widget falls back to its offline corpus.

## Model choice rationale

`Qwen/Qwen2.5-7B-Instruct` is free-tier friendly, handles multi-turn chat
template tokens (`<|im_start|>`...`<|im_end|>`), and is strong enough for the
three Polly lanes (lore / science / coding) without fine-tuning. Swap by
setting `HF_MODEL` in Space variables; the widget contract does not change.

## Local smoke test

```bash
pip install -r requirements.txt
HF_TOKEN=hf_xxx uvicorn app:app --port 7860
curl http://127.0.0.1:7860/v1/spaceport/status
curl -X POST http://127.0.0.1:7860/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the harmonic wall?"}'
```

## Cost

Free. Inference API uses the HF community tier. If you exceed rate limits,
upgrade the Space to a paid CPU (cheapest tier) or swap to a smaller model
via `HF_MODEL`.
