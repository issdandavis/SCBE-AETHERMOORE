# SCBE Governance Gate Run Modes

This repo supports two different ways to run the governance gate demo. They are both valid, but they are not interchangeable.

## 1. Colab Public Demo

Primary file:
- `notebooks/governance_gate_live_demo.ipynb`

Purpose:
- Start the FastAPI governance gate inside Google Colab.
- Expose it on a public URL so the external demo page can connect to it.

Requirements:
- `sentence-transformers`
- `fastapi`
- `uvicorn`
- `pyngrok`
- A valid `NGROK_AUTH_TOKEN`

What ngrok is doing:
- Colab is not directly reachable from the public web.
- Step 6 uses `pyngrok` to create a public tunnel.
- The printed `public_url` is what the demo page uses for:
  - `/api/health`
  - `/api/evaluate`
  - `/api/dye-inject`
  - `/api/batch`

Important constraint:
- This mode will not work without a valid `NGROK_AUTH_TOKEN`.
- Preferred setup is a Colab secret named `NGROK_AUTH_TOKEN`.
- Inline token fallback is supported, but secrets are the intended path.

## 2. Local Replay

Primary file:
- `.scbe/runners/run_governance_demo_local.py`

Purpose:
- Replay the notebook payload locally against the checked-out repo.
- Prove the runtime loads, serves, and evaluates correctly without depending on Colab.

Behavior:
- Skips the Colab-only clone step.
- Replaces the ngrok tunnel step with a local bind on `127.0.0.1:8765`.
- Runs the same governance pipeline locally and checks the served endpoints.

Important constraint:
- This mode does not produce a public URL.
- It is for local validation, replay, and debugging.
- It does not replace the notebook's public tunnel path.

## Which one to use

Use the notebook when:
- you need the public demo page to connect to a live backend
- you want a shareable external URL
- you are running from Colab

Use the local runner when:
- you want to validate the gate locally
- you are debugging imports, runtime behavior, or trust evolution
- you do not need a public tunnel

## Decision table

| Goal | Mode |
|------|------|
| Public live demo from Colab | `governance_gate_live_demo.ipynb` + ngrok |
| Local runtime verification | `.scbe/runners/run_governance_demo_local.py` |
| Shareable external URL | Colab notebook only |
| Fast local debug loop | Local runner only |

## Why this document exists

Loop record `.scbe/loop_records/005_run_local_demo.json` proves the local replay path works.
That does not remove the ngrok dependency from the notebook. The notebook and the local runner solve different problems and should be described separately.
