# CLI Operator Upgrade Plan

Last updated: 2026-03-21

## Purpose

Turn the current SCBE CLI from a strong internal research surface into a product-grade operator CLI that can:

- drive governed multi-agent swarms
- expose machine-readable outputs
- manage project context across Firebase, Hugging Face, GitHub, Notion, and browser lanes
- support real deployment, debugging, and replay loops

This document is based on live local smoke tests plus official CLI references from GitHub CLI, Vercel CLI, Wrangler, Supabase CLI, Stripe CLI, uv, and Firebase CLI.

## Local Smoke Test

These commands were run successfully on the current repo:

```powershell
python scbe.py --help
python scripts/scbe-system-cli.py --help
python scbe.py tongues list
python scbe.py tongues encode --tongue ko --text hello
python scbe.py pipeline run --text "test input"
python scbe.py ai explain L12
python scbe.py status
python scbe.py selftest
python scbe.py flow plan --task "cli smoke" --no-action-map
python scripts/scbe-system-cli.py --repo-root . flow --help
```

What is working well:

- The top-level `scbe` entrypoint is coherent enough to demo the stack.
- `scbe-system-cli.py` is already the right control-plane center.
- The new `flow plan` and `flow packetize` commands turn doctrine into replayable swarm packets.
- `selftest` gives immediate confidence for core math/tooling surfaces.
- Sacred Tongues tooling is already CLI-native and comprehensible.

## What Strong CLIs Do Better

### 1. Machine-readable output by default where it matters

Pattern examples:

- GitHub CLI supports `--json`, `--jq`, and templating for scripting.
- Stripe CLI turns event simulation into explicit commands (`stripe trigger ...`).

SCBE gap:

- Only a few commands expose JSON cleanly.
- Most commands print human-readable text but do not give a stable stdout contract for automation.

### 2. Clear project linking and active-context control

Pattern examples:

- Vercel uses `vercel link`, `vercel env pull`, `vercel deploy`, `vercel deploy --prod`.
- Firebase uses `firebase init`, `firebase use`, `firebase deploy`, project aliases, and `--project`.
- Supabase uses `supabase init`, `supabase start`, `supabase db push`, `supabase gen types`.

SCBE gap:

- No first-class `scbe init`, `scbe use`, or `scbe config` surface.
- Context is distributed across repo files, scripts, env vars, and connector setup.

### 3. Logs, follow, and runtime inspection

Pattern examples:

- Vercel emphasizes real-time logs and filtering.
- Firebase exposes `functions:log`.
- GitHub CLI has checks, runs, and watch-style workflow commands.

SCBE gap:

- Action maps exist, but there is no simple `scbe logs`, `scbe runs`, or `scbe flow watch`.
- Runtime/audit visibility is present in artifacts, but not packaged as an operator loop.

### 4. Autocomplete and command discovery

Pattern examples:

- Wrangler now ships dynamic shell completion.
- Supabase exposes `supabase completion`.
- GitHub CLI includes `completion`, `config`, and structured command groups.

SCBE gap:

- No built-in shell completion surface.
- Discovery depends on help text and docs instead of terminal-native completion.

### 5. Extensibility

Pattern examples:

- GitHub CLI supports extensions.
- Firebase supports hooks through `firebase.json`.
- Vercel and Supabase keep command groups modular and product-scoped.

SCBE gap:

- The repo already has many scripts and skills, but the CLI does not present them as a governed extension model.
- Skills, browser lanes, Firebase, HF, and MCP tooling feel adjacent instead of integrated.

### 6. Safe local testing and deployment simulation

Pattern examples:

- Stripe CLI supports explicit event triggers.
- Firebase supports local serving and function emulation.
- Supabase supports local startup and schema diff/push loops.
- uv keeps environments synchronized automatically.

SCBE gap:

- SCBE has tests and action maps, but no unified `scbe simulate`, `scbe trigger`, `scbe emulator`, or `scbe deploy` family.

## Highest-Value Gaps In Our CLI

### Packaging gap

- `package.json` does not expose a `bin` command for the unified CLI.
- `pyproject.toml` exposes scripts, but not the main `scbe` entrypoint.
- Result: the repo has a CLI, but not yet a clean installed product CLI.

### Control-plane gap

- `scbe` and `scbe-system-cli.py` are split correctly, but the command tree still looks like a collection of surfaces rather than one operator console.

### Execution gap

- We now have `flow plan` and `flow packetize`.
- We still need `flow dispatch`, `flow status`, and `flow watch`.

### Observability gap

- Action-map telemetry exists.
- It is not yet surfaced as real-time operator inspection.

### Connector gap

- Firebase, HF, Notion, GitHub, AetherBrowser, and PollyPad all exist in the system.
- They are not yet presented as first-class CLI families with common output rules.

## Concrete Upgrade Path

### Phase 1: Productize the install surface

Build next:

1. Add `scbe` as a Python console script in `pyproject.toml`.
2. Add `bin` support in `package.json` for the same command surface.
3. Make `scbe --version` and `scbe doctor` first-class commands.

Target outcome:

- `pip install scbe-aethermoore` gives a working `scbe` command.
- `npm install -g scbe-aethermoore` gives the same operator command.

### Phase 2: Normalize stdout contracts

Build next:

1. Add global `--json`.
2. Add `--format table|json|jsonl|path`.
3. Add stable result envelopes for:
   - `status`
   - `flow plan`
   - `flow packetize`
   - `agent call`
   - `runtime run`

Target outcome:

- Humans can read it.
- Scripts can depend on it.

### Phase 3: Add active-context commands

Build next:

1. `scbe init`
2. `scbe use`
3. `scbe config get/set/list`
4. `scbe auth status`

Backends to route:

- Firebase project / alias
- Hugging Face profile or repo target
- GitHub repo or org target
- Notion workspace token presence
- AetherBrowser service state

Target outcome:

- One active project/workspace state instead of scattered config guessing.

### Phase 4: Add execution and replay lanes

Build next:

1. `scbe flow dispatch`
2. `scbe flow status`
3. `scbe flow watch`
4. `scbe logs`
5. `scbe runs list/view`

Target outcome:

- Action maps become live operator state, not just post-run artifacts.

### Phase 5: Add connector-native command families

Build next:

1. `scbe firebase`
2. `scbe hf`
3. `scbe notion`
4. `scbe browser`
5. `scbe secrets`

Recommended first commands:

- `scbe firebase use`
- `scbe firebase deploy`
- `scbe firebase emulators`
- `scbe firebase logs`
- `scbe hf whoami`
- `scbe hf publish`
- `scbe notion sync`
- `scbe browser status`

Target outcome:

- The repo’s real deployment and training lanes become visible from one operator shell.

### Phase 6: Add completion and extension surfaces

Build next:

1. `scbe completion powershell|bash|zsh|fish`
2. `scbe extension list/install/remove`
3. `scbe skill list/run`

Target outcome:

- Skills and command families become governable plugin surfaces instead of hidden repo knowledge.

## Recommended Command Tree

```text
scbe
  doctor
  version
  init
  use
  config
  auth
  status
  logs
  runs
  flow
    plan
    packetize
    dispatch
    status
    watch
  agent
    bootstrap
    list
    register
    call
  runtime
    run
  firebase
    use
    deploy
    emulators
    logs
  hf
    whoami
    publish
    jobs
  notion
    sync
    gap
  browser
    start
    verify
    stop
  tongues
  pipeline
  ai
  docs
```

## Firebase Fit

Firebase should not be the long-term training source of truth.

Firebase should be used for:

- agent presence
- packet assignment state
- swarm dashboard state
- live logs and handoff status
- user/project auth context

Canonical durable outputs should remain:

- action maps in repo/cloud archive
- HF records in training lanes
- docs and notes in repo/Notion/Obsidian

## Immediate Build Order

This is the action-first order:

1. Expose installed `scbe` command from Python and npm packaging.
2. Add global `--json` and stable result envelopes.
3. Add `doctor`, `config`, and `use`.
4. Add `flow dispatch/status/watch`.
5. Add Firebase command family first, because it unlocks live swarm state.

## Official References

- GitHub CLI formatting and command surface: https://cli.github.com/manual/gh_help_formatting
- Vercel deploy-from-CLI workflow: https://vercel.com/docs/projects/deploy-from-cli
- Vercel runtime logs: https://vercel.com/docs/logs/runtime
- Wrangler shell completion: https://developers.cloudflare.com/changelog/post/2026-01-09-wrangler-tab-completion/
- Supabase CLI reference: https://supabase.com/docs/reference/cli/supabase-db-dump
- Stripe CLI trigger workflow: https://docs.stripe.com/stripe-cli/triggers
- uv lock/sync behavior: https://docs.astral.sh/uv/concepts/projects/sync/
- Firebase CLI reference: https://firebase.google.com/docs/cli
