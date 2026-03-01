# Local Secret Store (Offline, Tokenized)

Purpose:

- Keep API keys and connector secrets on local disk only.
- Store values tokenized through Sacred Tongue instead of plain text.
- Make secrets retrievable by `get_secret(...)` and CLI for AI/discoverability.

Default file:

`$HOME/.scbe/secret-store.json`  
override with `SCBE_SECRET_STORE_PATH`.

Implementation:

- Module: `src/security/secret_store.py`
- CLI: `scripts/system/secret_store.py`
- Runtime consumers:
  - `src/api/main.py` (API key map + connector signing key)
  - `src/api/hydra_routes.py` (API keys)
  - `scripts/connector_health_check.py`
  - `scripts/system/register_connector_profiles.py`

Quick setup:

```bash
# Save signing key for local connector signatures
python scripts/system/secret_store.py set SCBE_CONNECTOR_SIGNING_KEY "replace-with-key"

# Save API key map as JSON
python scripts/system/secret_store.py set SCBE_VALID_API_KEYS "{\"demo_key_12345\":\"demo_user\"}"

# Verify what exists
python scripts/system/secret_store.py list --names-only

# Read back the decoded value when needed
python scripts/system/secret_store.py get SCBE_CONNECTOR_SIGNING_KEY
```

Path check:

```bash
python scripts/system/secret_store.py path
```

Notes:

- Values are restored by detokenizing stored token arrays with the configured tongue (default `KO`).
- This is local/offline by default. If syncing across machines, copy the store file and
  keep it under your local secret management process.
