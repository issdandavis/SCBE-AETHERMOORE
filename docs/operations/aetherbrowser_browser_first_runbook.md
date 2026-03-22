# AetherBrowser Browser-First Runbook

This runbook makes AetherBrowser plus `playwriter` the default search and operator surface for SCBE work. The goal is to stop falling back into unmanaged Chrome, Safari, and Google habits when the repo already has site-native routing, evidence capture, and browser governance paths.

## Default Stance

- Start in AetherBrowser or the repo's browser lane, not in a personal browser tab.
- Route first with `browser_chain_dispatcher.py`.
- Prefer `playwriter` for signed-in, existing-session, operator work.
- Use `playwright` when you need isolated, deterministic automation or when the `playwriter` session is unavailable.
- Use site-native search pages and repo-local nav scripts instead of Google as the entry point.
- Preserve proof in `artifacts/page_evidence/`, session audit output, or Obsidian export notes.

## Tool Roles

### AetherBrowser

Use `agents/aetherbrowse_cli.py` when you need governed browser actions such as `navigate`, `click`, `type`, `scroll`, `snapshot`, `extract`, and `screenshot`. It is CDP-first by default and returns structured audit output.

### Playwriter

Use `playwriter` as the default operator engine for:

- signed-in sessions
- existing tabs
- quick title and snapshot checks
- human-guided page movement that should still land evidence

Repo-local evidence helper:

```powershell
python scripts/system/playwriter_lane_runner.py --session 1 --url https://github.com --task navigate
python scripts/system/playwriter_lane_runner.py --session 1 --task title
python scripts/system/playwriter_lane_runner.py --session 1 --task snapshot
```

### Playwright

Use Playwright when:

- `playwriter` is disconnected
- you need isolated headless automation
- you need deterministic browser fallback
- the task is better served by dedicated repo-local nav scripts

This is a fallback engine, not the primary habit.

## Browser-First Operating Loop

1. Route the task with the dispatcher.
2. Decide `playwriter` or `playwright` for the run.
3. Open the site-native surface directly.
4. Capture title or snapshot evidence before moving deeper.
5. Do the smallest useful browse or operator action.
6. Save proof to repo artifacts or vault export.
7. Hand off to API or CLI only when state changes need determinism.

Base dispatcher pattern:

```powershell
python scripts/system/browser_chain_dispatcher.py --domain <domain> --task <task> --engine playwriter
```

## Dispatcher and Evidence Path

The dispatcher is the first routing decision:

```powershell
python scripts/system/browser_chain_dispatcher.py --domain github.com --task navigate --engine playwriter
```

Current default fleet covers:

- `github.com`
- `arxiv.org`
- `notion.so`

Domains without an explicit tentacle, such as `huggingface.co`, still route through the generic tentacle and preserve the same contract.

Primary evidence paths:

- `artifacts/page_evidence/playwriter-session-<session>.json`
- `artifacts/page_evidence/playwriter-<host>-navigate-session<session>.json`
- `artifacts/page_evidence/playwriter-<host>-title-session<session>.json`
- `artifacts/page_evidence/playwriter-<host>-snapshot-session<session>.json`
- Obsidian export notes written by the dedicated nav scripts when `--vault` is used

If you need service-level proof instead of page-level proof, use the stack smoke outputs under `artifacts/system_smoke/`.

## Service Playbooks

### GitHub

Use GitHub's own search and route surfaces through AetherBrowser. Do not search GitHub repositories through Google first.

Route:

```powershell
python scripts/system/browser_chain_dispatcher.py --domain github.com --task navigate --engine playwriter
```

Search and browse:

```powershell
python scripts/system/aetherbrowser_github_nav.py "SCBE governance" --type repositories --json
python scripts/system/aetherbrowser_github_nav.py "SCBE governance" --type repositories --vault "<vault-path>"
```

Operator follow-up:

```powershell
python scripts/system/playwriter_lane_runner.py --session 1 --url https://github.com/<owner>/<repo> --task navigate
python scripts/system/playwriter_lane_runner.py --session 1 --task title
python scripts/system/playwriter_lane_runner.py --session 1 --task snapshot
```

Use AetherBrowser CLI when the task moves from discovery to governed interaction:

```powershell
python agents/aetherbrowse_cli.py --backend cdp navigate https://github.com/<owner>/<repo>
python agents/aetherbrowse_cli.py --backend cdp snapshot
python agents/aetherbrowse_cli.py --backend cdp screenshot
```

Default rule:

- `playwriter` for signed-in repo, PR, issues, and settings work
- Playwright or GitHub API fallback only when the signed-in lane is unavailable

### Hugging Face

There is no repo-local `aetherbrowser_huggingface_nav.py` yet, so use the generic browser-first path instead of reverting to ad hoc browser tabs.

Route:

```powershell
python scripts/system/browser_chain_dispatcher.py --domain huggingface.co --task navigate --engine playwriter
```

Open the exact target directly:

- user page: `https://huggingface.co/<user>`
- model: `https://huggingface.co/<user>/<model>`
- dataset: `https://huggingface.co/datasets/<user>/<dataset>`
- space: `https://huggingface.co/spaces/<user>/<space>`

Evidence loop:

```powershell
python scripts/system/playwriter_lane_runner.py --session 1 --url https://huggingface.co/<user>/<repo> --task navigate
python scripts/system/playwriter_lane_runner.py --session 1 --task title
python scripts/system/playwriter_lane_runner.py --session 1 --task snapshot
```

Governed browser follow-up:

```powershell
python agents/aetherbrowse_cli.py --backend cdp navigate https://huggingface.co/<user>/<repo>
python agents/aetherbrowse_cli.py --backend cdp extract
```

Default rule:

- browser-first for discovery, validation, and repo-card inspection
- `hf` CLI or API only after the browser lane has established the correct target and preserved evidence

### arXiv

Use arXiv's abstract pages and AetherBrowser scripts, not generic web search.

Route:

```powershell
python scripts/system/browser_chain_dispatcher.py --domain arxiv.org --task research --engine playwriter
```

Search and extract:

```powershell
python scripts/system/aetherbrowser_arxiv_nav.py "AI swarm governance" --json
python scripts/system/aetherbrowser_arxiv_nav.py "AI swarm governance" --vault "<vault-path>"
```

Direct paper work:

```powershell
python scripts/system/playwriter_lane_runner.py --session 1 --url https://arxiv.org/abs/<id> --task navigate
python scripts/system/playwriter_lane_runner.py --session 1 --task title
python scripts/system/playwriter_lane_runner.py --session 1 --task snapshot
```

Default rule:

- prefer abstract pages over PDF for fast metadata reads
- use the API fallback only when Playwright is missing or the browser path is blocked

### Notion

Notion is browser-first for discovery and path confirmation, but API-first for deterministic search and writes.

Route:

```powershell
python scripts/system/browser_chain_dispatcher.py --domain notion.so --task navigate --engine playwriter
```

Search and export:

```powershell
python scripts/system/aetherbrowser_notion_nav.py search "SCBE governance" --json
python scripts/system/aetherbrowser_notion_nav.py search "SCBE governance" --vault "<vault-path>"
python scripts/system/aetherbrowser_notion_nav.py search "SCBE governance" --browser --vault "<vault-path>"
```

Evidence loop:

```powershell
python scripts/system/playwriter_lane_runner.py --session 1 --url https://www.notion.so --task navigate
python scripts/system/playwriter_lane_runner.py --session 1 --task title
python scripts/system/playwriter_lane_runner.py --session 1 --task snapshot
```

Default rule:

- use browser navigation to find the right workspace surface
- use Notion API or MCP for deterministic updates after the right page or database is confirmed

## AetherBrowser CLI Patterns

CDP-first attach to the active browser surface:

```powershell
python agents/aetherbrowse_cli.py --backend cdp navigate https://github.com
python agents/aetherbrowse_cli.py --backend cdp snapshot
python agents/aetherbrowse_cli.py --backend cdp extract
python agents/aetherbrowse_cli.py --backend cdp screenshot
```

Playwright fallback path:

```powershell
python agents/aetherbrowse_cli.py --backend playwright navigate https://huggingface.co
python agents/aetherbrowse_cli.py --backend playwright snapshot
```

Use `--audit-only` when you want the governance decision and audit trail without executing the action.

## Fallback Rules

- If `playwriter` is connected, keep the run in `playwriter`.
- If `playwriter` is disconnected, move to Playwright or AetherBrowse CLI instead of dropping into unmanaged browser tabs.
- If site-native browser discovery succeeds but state change should be scripted or repeatable, hand off to API or CLI after evidence is captured.
- If the dispatcher has no dedicated tentacle for a domain, use the generic tentacle and keep the same evidence discipline.

## Anti-Pattern List

Do not do the following as the default habit:

- open Chrome or Safari manually and start with Google
- browse GitHub repos through web search instead of GitHub search
- inspect Hugging Face repo cards without preserving title or snapshot evidence
- search Notion manually and then perform writes without a deterministic API path
- skip dispatcher routing because the URL looks obvious

## Done Criteria

A browser-first run is complete when:

- the task was routed through the dispatcher or an equivalent explicit browser path
- the site-native surface was used directly
- evidence landed in `artifacts/page_evidence/`, session audit output, or Obsidian export
- any state-changing follow-up moved to the appropriate API or CLI after browser discovery
