# Product Quickstart

This is the supported first-run path for the active SCBE-AETHERMOORE product
lane: **AetherBrowser + AetherDesk**.

## One-command release proof

Prerequisites: Node.js 18+, Python, Chrome or Chromium, and `npm install`.

```bash
npm run product:release-gate
```

The gate:

1. starts the AetherBrowser backend and isolated Chrome/CDP session;
2. verifies backend health, CDP, the extension worker, and backend smoke;
3. starts AetherDesk on `127.0.0.1:5717`;
4. runs the allowlisted, read-only `token_lookup` action;
5. confirms AetherDesk emitted an audit receipt;
6. writes a consolidated PASS/FAIL receipt under
   `artifacts/product_surface/`; and
7. shuts down processes it started.

Use `npm run product:release-gate -- --keep-running` to leave a successful
stack running.

## What each app does

| Surface | Role | Default endpoint | Evidence |
|---|---|---|---|
| AetherBrowser | Governed browser viewport, extension automation, agent/model execution | backend `127.0.0.1:8002`, CDP `127.0.0.1:9222` | `artifacts/smokes/aetherbrowser-service-verify-*/service_verify_report.json` |
| AetherDesk | Local operator shell for visible tasks, files, browser tools, bounded commands, provider status, and receipts | `http://127.0.0.1:5717` | `artifacts/aetherdesk_receipts/` |
| Product gate | Proves both surfaces work together | command line | `artifacts/product_surface/product_surface_release_gate_*.json` |

## Manual operation

```bash
npm run aetherbrowser:service:start
npm run aetherbrowser:service:verify
npm run aetherdesk
# open http://127.0.0.1:5717
npm run aetherbrowser:service:stop
```

AetherDesk remains in the foreground. Stop it with Ctrl+C.

## Connect a model

The product uses a provider adapter instead of binding the UI to one model.

### Local/free model with Ollama

```bash
npm run ollama:start
npm run ollama:health
npm run ollama:list
npm run aetherbrowser:model:cli -- --provider ollama --model <installed-model> --prompt "hello"
```

Install/pull the Ollama model separately before selecting it. Local execution
keeps prompts on the machine unless the selected tool itself uses a network
service.

### Remote API

Set only the credential required by the selected provider, then select that
provider through the AetherBrowser model CLI or AetherDesk provider status
surface. Supported provider names and environment variables are reported by
the runtime; do not place keys in source files, command receipts, or screenshots.

```bash
npm run aetherbrowser:model:cli -- --help
npm run aetherbrowser:model:cli -- --provider <provider> --model <model> --prompt "hello"
```

A missing credential or unavailable local endpoint must remain visibly
unavailable; the router must not silently substitute a paid remote model.

## Control and governance boundary

The AI may browse through the managed browser lane and invoke commands exposed
by AetherDesk's allowlists. It does not receive arbitrary host command authority
from the UI. Read-only actions can run directly; write, external-send,
credential, destructive, or otherwise elevated actions require an explicit
approval surface before execution. Every completed bounded command writes a
receipt with command identity, risk tier, timestamps, exit status, and bounded
output. See [Aether Workspace Architecture](product/AETHER_WORKSPACE_ARCHITECTURE.md).

## Product inventory

| Classification | Surfaces | First-run status |
|---|---|---|
| Active product | `src/aetherbrowser/`, `src/extension/`, `aetherdesk/`, product gate | Supported path |
| Shared platform | `src/governance/`, `src/crypto/`, `src/tokenizer/`, `python/scbe/`, APIs | Used by product; not separate apps |
| Experimental/research | `research/`, `notes/`, `notebooks/`, exploratory scripts | Optional; claims require their own evidence |
| Training/generated/archive | `training/`, `training-data/`, `models/`, `artifacts/`, `dist/`, `build/`, `archive/` | Excluded from first run |

## Failure interpretation

- No Chrome/Chromium: provide `--ChromePath` to the underlying start script.
- Backend health failure: inspect the gate receipt and AetherBrowser service output.
- Extension not loaded: inspect `src/extension/` and the isolated Chrome profile.
- Provider unavailable: start the local provider or set the selected remote
  provider credential.
- A gate failure is not releasable merely because one HTTP endpoint responds;
  the consolidated receipt must say `PASS`.

The monorepo is not claimed to be one polished frontend. This quickstart names
the supported workspace lane and deliberately excludes corpora, notebooks,
generated artifacts, and unrelated experiments.
