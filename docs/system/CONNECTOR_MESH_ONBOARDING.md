# Connector Mesh Onboarding (Claude/Grok/HF/Ollama + Customer Templates)

## 1) Check what is wired now

```powershell
python scripts/system/browser_chain_dispatcher.py --provider-status
```

## 2) Check a platform before running tasks

```powershell
python scripts/system/browser_chain_dispatcher.py --domain github.com --task "api sync" --domain-plan
```

This returns:
- recommended channel (`api` / `cli` / `browser`)
- missing env vars
- setup steps

## 3) Run task with connector enforcement

```powershell
python scripts/system/browser_chain_dispatcher.py --domain github.com --task "api sync" --strict-connectivity
```

If connector auth is not ready, task is blocked with explicit missing setup.

## 4) Generate customer onboarding pack with admin PIN

```powershell
python scripts/system/customer_connector_template.py `
  --customer-id acme-core `
  --connectors "github.com,huggingface.co,shopify.com,notion.so,dev.to,linkedin.com,x.com" `
  --out-root external/intake
```

Outputs:
- `external/intake/<customer-id>/connector_profile.json`
- `external/intake/<customer-id>/admin_pin.json` (salted hash only)
- `external/intake/<customer-id>/.env.template`

## 5) Load keys without hardcoding in repo

Use the existing secret store:

```powershell
python scripts/system/secret_store.py set HF_TOKEN --stdin
python scripts/system/secret_store.py set ANTHROPIC_API_KEY --stdin
python scripts/system/secret_store.py set XAI_API_KEY --stdin
python scripts/system/secret_store.py set OPENROUTER_API_KEY --stdin
python scripts/system/secret_store.py export-env --shell powershell
```

Then re-check:

```powershell
python scripts/system/browser_chain_dispatcher.py --provider-status
```

