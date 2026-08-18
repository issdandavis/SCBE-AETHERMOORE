# scbe-polly-pad-cli

> A terminal workspace that remembers. Task state, model routing, and a tamper-evident record of everything an AI operator did in your project.

[![npm](https://img.shields.io/npm/v/scbe-polly-pad-cli.svg)](https://www.npmjs.com/package/scbe-polly-pad-cli)
[![node](https://img.shields.io/node/v/scbe-polly-pad-cli.svg)](https://nodejs.org)
[![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

## What it does

Shell sessions forget. Polly does not.

- **Keeps task state across sessions** — close the terminal, come back, the work is still there.
- **Routes prompts to whichever model you want** — local, free, or your own key.
- **Writes a hash-chained audit trail** — every run leaves a receipt, and tampering breaks the chain.

Use it when you want a record of what an AI actually did in a repo, not just what it said.

## Requirements

- **Node.js >= 20**

## Install

```bash
npm install -g scbe-polly-pad-cli
```

Installs one command: `polly`.

## Quick start — 60 seconds

```bash
polly init my-project          # create the workspace
polly task add "first task"    # add work
polly ask "what should I start with?"
polly audit verify             # prove nothing was tampered with
```

Expected output from `polly audit verify`:

```
audit chain OK — 4 entries, head 9f2c1a...
```

If that says anything other than OK, the record was altered. That is the whole point of the command.

## Where state lives

Everything is under `.polly/` in the current project — plain files, no database, safe to commit or gitignore as you prefer:

| path | holds |
|---|---|
| `.polly/pad.json` | pad metadata, tasks, attached repo |
| `.polly/runs/` | saved model and recipe runs |
| `.polly/snapshots/` | exported pad snapshots |
| `.polly/audit.jsonl` | append-only, hash-chained receipts |

## Command reference

| command | does | example |
|---|---|---|
| `polly init` | create a workspace | `polly init my-project` |
| `polly task add` | add a task | `polly task add "write tests"` |
| `polly task submit` | submit a governed run | `polly task submit "verify claim" --wait --json` |
| `polly ask` | one-shot model question | `polly ask "what next?"` |
| `polly run` | run a recipe | `polly run plan --dry-run "ship a website"` |
| `polly audit verify` | verify the hash chain | `polly audit verify` |
| `polly cross pack` | cross-language packet | `polly cross pack --text "def add(x,y): return x+y" --lang python` |
| `polly shell` | interactive session | `polly shell` |

## Security

- **Local by default.** State is files in your project; nothing is uploaded unless you route a prompt to a remote model.
- **`--dry-run` shows the plan without executing it.** Use it before anything destructive.
- **The audit chain is append-only.** `polly audit verify` fails loudly if history was edited — it cannot be silently rewritten.
- **Model keys** come from your environment, never from `.polly/`. Do not commit keys into the workspace.

## For AI agents

1. **`polly task submit --json`** is the machine surface. Parse that, not the human output.
2. **`--dry-run` first** on anything with side effects, then run for real.
3. **Cite the receipt id** from the run when you report completion — it is checkable.
4. **`polly audit verify` before you trust prior state.** If the chain is broken, previous session claims are not reliable.
5. **Runs are marked non-promotable until reviewed.** Do not restate their output as fact.

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `Unsupported engine` | Node < 20 | upgrade Node |
| `no pad found` | not initialised here | `polly init <name>` |
| `audit chain BROKEN` | `.polly/audit.jsonl` was edited | restore from a snapshot; do not hand-repair |
| model call fails | key not in environment | export the provider key, then retry |

## License

MIT OR Apache-2.0
