# Polly Pad CLI

Polly is a governed terminal workpad for AI operators. It gives a shell session persistent task state, LLM routing, recipe prompts, run receipts, handoff packets, snapshots, and a hash-chained audit trail.

## Install

```bash
npm install -g scbe-polly-pad-cli
```

## Quick Start

```bash
polly init my-project
polly task add "first task"
polly ask "what should I start with?"
polly run plan --dry-run "ship a website"
polly audit verify
polly cross pack --text "def add(x, y): return x + y" --lang python
polly cross op add --json
polly shell
```

## Workspace

Polly stores state under `.polly/` in the current project:

- `.polly/pad.json` — pad metadata, tasks, and attached repo
- `.polly/runs/` — saved model or recipe runs
- `.polly/snapshots/` — exported pad snapshots
- `.polly/audit.jsonl` — append-only audit receipts

## Audit Trail

Every state-changing command appends a receipt to `.polly/audit.jsonl`. Receipts are canonical JSON records with a SHA-256 event hash and previous event hash.

```bash
polly audit list
polly audit verify
polly audit export --json
```

If a receipt is edited after it is written, `polly audit verify` exits non-zero and reports the first broken receipt.

## Cross-Language Packets

Polly can decompose text or source files into lossless UTF-8 hex/binary packets with SHA-256 receipts and lightweight semantic route evidence.

```bash
polly cross pack --file src/index.ts
polly cross pack --text "const result = x + y;" --lang javascript
polly cross unpack --hex 636f6e737420726573756c74203d2078202b20793b
polly cross op add --json
```

`cross pack` is lossless at the byte layer. `cross op` is intentionally bounded to known operation templates; it is not advertised as arbitrary AST translation.

## Model Routing

Polly tries model providers in this order:

1. Ollama at `localhost:11434`
2. `ANTHROPIC_API_KEY`
3. `OPENAI_API_KEY`
4. Template fallback with no model required

The fallback keeps Polly usable even when no external model is configured.
