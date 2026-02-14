# QUICKSTART: Monetization Demo Flow

This quickstart gives you a fast, repeatable governance demo you can use in pilot calls and sales conversations.

## 1) Run local gateway

From the repository root:

```bash
export SCBE_API_KEY="dev-key-local"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

In a second terminal, verify health:

```bash
curl -s http://localhost:8000/v1/health
```

## 2) Send 3 sample agent actions

Run the guided demo script:

```bash
chmod +x scripts/quickstart_demo.sh
SCBE_API_KEY="dev-key-local" ./scripts/quickstart_demo.sh
```

What the script does:

1. Registers three sample agents with different trust baselines.
2. Sends 3 governance requests to `POST /v1/authorize`.
3. Runs one fleet scenario via `POST /v1/fleet/run-scenario`.

## 3) View governance decision + audit output

The script prints:

- Decision, score, and decision ID for each action.
- Audit details from `GET /v1/audit/{decision_id}`.
- Fleet summary (allowed/denied/quarantined).

## Value proof metric

At the end of the run, the script prints one clear monetization metric:

- **Risky actions blocked/quarantined** = risky actions that did **not** get `ALLOW`.

Example output:

```text
VALUE PROOF: risky actions blocked/quarantined = 2/3 (66.7%)
```

Use this number in pilot updates to show measurable risk reduction tied directly to policy enforcement.
