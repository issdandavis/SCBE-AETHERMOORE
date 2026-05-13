---
title: SCBE Shim
emoji: 🛡️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
short_description: OpenAI-compatible governance proxy with SCBE axiom checks.
license: apache-2.0
---

# scbe-shim — HuggingFace Space

Python mirror of `services/scbe-shim` (the Cloudflare Worker). Same API,
same governed-response shape, deploys as a free HF Space (CPU tier).

## Deploy as your own Space

1. Create a new HF Space, SDK = Docker.
2. Copy this directory's contents into the Space repo:
   ```
   Dockerfile
   requirements.txt
   app.py
   shim/__init__.py
   shim/patterns.py
   shim/axioms.py
   shim/decision.py
   README.md
   ```
3. Set the `HF_TOKEN` secret in Space settings (your HF inference token).
4. Push. Space builds, exposes `/v1/chat/completions`.

## Endpoints

| Path | Method | Purpose |
|---|---|---|
| `/v1/chat/completions` | POST | Governed OpenAI-compatible chat |
| `/v1/health` | GET | Liveness + version |
| `/v1/scorecard` | GET | Internal benchmark numbers |

## Use with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<your-space>.hf.space/v1",
    api_key="not-used-but-required",
)

resp = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "Write a haiku about safe AI."}],
)

print(resp.choices[0].message.content)
print("decision:", resp.scbe_governance.decision)
```

## Local docker run

```bash
docker build -t scbe-shim .
docker run --rm -p 7860:7860 -e HF_TOKEN=hf_xxx scbe-shim
curl http://localhost:7860/v1/health
```

## Why two deploys (Worker AND Space)?

- **Cloudflare Worker**: 100K req/day free, edge latency, scales to
  millions when paid, but 50ms CPU budget per request.
- **HF Space**: clone-and-fork friendly for community/auditors, runs
  any Python pre/post-processing your shim grows into, sleeps after
  inactivity on free tier.

Same governed-response contract on both. Pick the one that fits the
caller.
