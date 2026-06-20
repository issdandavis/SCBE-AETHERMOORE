# scbe-shim — Free Deployment Playbook

Three free deploy shapes, ranked by your existing assets. Pick one or
combine. Same governed-response contract on all three.

---

## Shape A · Cloudflare Worker (recommended for production demo)

**What it gets you:** 100K req/day free, edge latency, OpenAI-compatible
public URL like `https://scbe-shim.<account>.workers.dev/v1`.

```bash
# 0. Prereqs: Node 18+, a free Cloudflare account, an HF token
cd services/scbe-shim
npm install

# 1. Authenticate wrangler (browser pops to login once)
npx wrangler login

# 2. Add your HuggingFace inference token as a secret
npx wrangler secret put HF_TOKEN
# paste your hf_xxx token when prompted

# 3. (optional) Enable response cache
npx wrangler kv:namespace create SHIM_CACHE
# paste the returned id into wrangler.toml under [[kv_namespaces]]

# 4. Deploy
npx wrangler deploy
```

Smoke test:

```bash
curl https://scbe-shim.<account>.workers.dev/v1/health
curl https://scbe-shim.<account>.workers.dev/v1/scorecard

curl -X POST https://scbe-shim.<account>.workers.dev/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Write a haiku about safe AI."}]}'
```

Point any OpenAI SDK at it:

```python
from openai import OpenAI
client = OpenAI(
    base_url="https://scbe-shim.<account>.workers.dev/v1",
    api_key="not-used",
)
```

---

## Shape B · HuggingFace Space (free CPU, slow but always reproducible)

**What it gets you:** an `https://<your>.hf.space/v1` endpoint that
anyone can fork and verify.

1. Go to <https://huggingface.co/new-space>, pick **Docker** SDK.
2. Copy `services/scbe-shim-space/` contents into the new Space repo.
3. In Space settings → Variables and secrets, add `HF_TOKEN`.
4. Push. First build takes ~3 min.

Detailed instructions in `services/scbe-shim-space/README.md`.

---

## Shape C · Local Ollama + Cloudflare Tunnel (max quality, your PC)

**What it gets you:** zero rate limits, ~80–200ms latency, a public
`https://<random>.trycloudflare.com` URL. PC must be on.

```powershell
# 1. Install Ollama (https://ollama.com/download/windows)
ollama pull qwen2.5:7b-instruct
ollama serve  # binds 11434

# 2. Run the shim against local Ollama instead of HF Inference
cd services/scbe-shim-space
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:HF_TOKEN = "ollama"           # bearer is ignored locally
$env:HF_INFERENCE_BASE = "http://localhost:11434/v1"
$env:HF_MODEL = "qwen2.5:7b-instruct"
uvicorn app:app --port 7860

# 3. Expose via Cloudflare Tunnel (free, no signup needed)
#    Download cloudflared: https://github.com/cloudflare/cloudflared/releases
cloudflared tunnel --url http://localhost:7860
# prints: https://<random>.trycloudflare.com
```

You now have a public OpenAI-compatible governed endpoint backed by
your own machine.

---

## Choosing the shape

| Need | Shape |
|---|---|
| Always-on for demo / sales | A (Worker) |
| Hammer-test without rate limits | C (Local + Tunnel) |
| Forkable for auditors / DARPA reviewers | B (HF Space) |
| All three at once with smart routing | A in front, B/C as failover (write later) |

## Sanity checks

After any deploy:

1. `GET /v1/health` returns `{"ok": true, ...}` — service alive
2. `GET /v1/scorecard` returns the benchmark numbers — config loaded
3. `POST /v1/chat/completions` with a clean prompt returns
   `"decision": "ALLOW"`
4. `POST /v1/chat/completions` with a prompt containing
   `"rollback_conversation"` returns `"decision": "DENY"` and the
   safe-fallback text

## Cost ramp

- Free: A worker + HF Pro inference quota you already have
- ~$5/month: A worker paid tier kicks in past 100K req/day
- ~$15/month: KV reads/writes pile up at heavy traffic
- Time to charge customers before any of this matters

## Failure modes & fallbacks

| Failure | Behavior |
|---|---|
| HF Inference returns 5xx | Worker returns 502 with upstream message |
| HF rate-limit hit | Worker returns 429 (passed through) |
| HF_TOKEN missing | Worker returns 500 `config_error` (caught at startup) |
| Worker quota exhausted | Cloudflare returns 1015 — bump to paid tier |
| Ollama not running (Shape C) | Worker returns 502 — start Ollama |

## Observability

Worker:

```bash
npx wrangler tail   # live request log
```

Open Cloudflare dashboard → Workers → scbe-shim → Logs / Analytics for
historical numbers and decision-band distribution.

## Next public artifact

After deploy, file these in the repo:

1. The deployed URL in `docs/shim/README.md` under "Try it"
2. A short cURL screenshot or asciinema in the repo README
3. The `/v1/scorecard` JSON pinned in a Gist for citation
