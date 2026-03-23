# LatticeGate GitHub App

The GitHub App is the identity and permission layer. The service that actually processes webhook events is the FastAPI route in this repo:

- `POST /v1/github-app/webhook`
- `GET /v1/github-app/health`

## Required env vars

Set these before running `uvicorn api.main:app --host 0.0.0.0 --port 8080`:

```powershell
$env:GITHUB_APP_ID = "3147791"
$env:GITHUB_PRIVATE_KEY_PATH = "C:\path\to\latticegate.private-key.pem"
$env:GITHUB_WEBHOOK_SECRET = "your-webhook-secret"
$env:GITHUB_APP_CHECK_NAME = "LatticeGate"
$env:GITHUB_APP_COMMENT_MODE = "always"
```

You can also set `GITHUB_APP_PRIVATE_KEY` directly instead of `GITHUB_PRIVATE_KEY_PATH`.

## Local testing with Smee

1. In GitHub App settings, set the webhook URL to your Smee channel URL.
2. Run the FastAPI app locally:

```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

3. Forward the Smee channel to the local webhook route:

```powershell
smee -u https://smee.io/your-channel -t http://127.0.0.1:8080/v1/github-app/webhook
```

4. Verify local config:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/github-app/health
```

## What the route does

For `pull_request` events on `opened`, `edited`, `reopened`, `ready_for_review`, and `synchronize`:

1. Verifies `X-Hub-Signature-256`.
2. Mints a GitHub App installation token.
3. Lists changed PR files.
4. Scores the PR using:
   - `api.validation.run_nextgen_action_validation`
   - `python/scbe/phdm_embedding.py`
   - `src/minimal/davis_formula.py`
5. Creates a check run on the PR head SHA.
6. Optionally posts an issue comment, based on `GITHUB_APP_COMMENT_MODE`.
