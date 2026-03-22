# Browser Surface Map

Use this reference when a task needs the right browser surface, not just any browser surface.

## Core surfaces

### 1. Dispatcher

Route first:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\browser_chain_dispatcher.py --domain <domain> --task <task> --engine playwriter
```

Use for:

- picking a tentacle / domain lane
- documenting intended browser engine
- staying inside SCBE browser conventions

### 2. Lane runner

Inspect page state fast:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\playwriter_lane_runner.py --session 1 --task title --url "<url>"
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\playwriter_lane_runner.py --session 1 --task snapshot --url "<url>"
```

Use for:

- quick title checks
- deterministic snapshot evidence
- low-friction proof collection

### 3. AetherBrowse CLI

Run governed actions:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\agents\aetherbrowse_cli.py --backend cdp navigate "<url>"
python C:\Users\issda\SCBE-AETHERMOORE\agents\aetherbrowse_cli.py --backend cdp snapshot
python C:\Users\issda\SCBE-AETHERMOORE\agents\aetherbrowse_cli.py --list-backends
```

Use for:

- real browser actions
- governed action logging
- CDP / Playwright / Selenium-backed session control

### 4. Built-in search / fetch

Use for:

- discovery
- metadata lookup
- reading when login state is not needed

Do not use it as a substitute for:

- signed-in session state
- multi-tab workflow
- UI verification

## GitHub surface model

Treat GitHub work as four surfaces:

1. repo page
2. `github.dev`
3. Codespaces IDE
4. Codespaces terminal / preview ports

Pair browser movement with `$scbe-gh-powershell-workflow` when you need:

- `gh` auth
- PR/run inspection
- workflow run triage
- repo-aware branch operations

## Domain pairings

- arXiv: pair with `$aetherbrowser-arxiv-nav`
- GitHub: pair with `$aetherbrowser-github-nav`
- Notion: pair with `$aetherbrowser-notion-nav`
- Hugging Face: pair with `$aetherbrowser-huggingface-nav`
- Shopify: pair with `$aetherbrowser-shopify-nav`
