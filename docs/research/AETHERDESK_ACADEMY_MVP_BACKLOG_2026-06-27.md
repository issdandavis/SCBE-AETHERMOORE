# AetherDesk Academy MVP Backlog

Date: 2026-06-27

## Build objective

Create a Boot.dev-like learning loop inside AetherDesk: map -> lesson -> code editor -> tests -> AI Pal -> receipt -> training trace.

## MVP components

1. `academy_lesson.schema.json`
   - Stable lesson format.
   - Includes starter files, tests, hints, expected receipts, and AI Pal policy.

2. `academy_trace.schema.json`
   - Stable training trace format.
   - Captures actor, action, hashes, tool result, reflection, verdict, provenance.

3. `academy-runtime`
   - Runs lesson-defined commands only.
   - Emits receipts with exit code, stdout/stderr tails, duration, hashes.

4. `academy-pal`
   - Starts as rule-based modes: Socratic, Explain, Inspect, Patch, Run, Reflect.
   - Later swaps in local/remote model behind the same policy gate.

5. `academy-web`
   - Home map, lesson view, editor, terminal/test output, AI Pal sidecar.
   - No copied Boot.dev assets.

6. `academy-cli`
   - `aether lesson run`
   - `aether lesson submit`
   - `aether lesson receipt`
   - `aether lesson trace export`

## First three lessons

1. Python foundation: function return value.
2. SCBE conlang macro: conlang sentence -> opcode -> Python/Rust receipt.
3. Browser task: inspect page title or fill a local form in a sandboxed browser tab.

## Training loop

1. Human attempts code.
2. Runtime executes tests.
3. AI Pal reads only lesson files and receipt.
4. AI Pal gives hint or patch depending on mode.
5. Runtime verifies again.
6. Trace writer emits JSONL.
7. Failed attempts remain negative/repair examples.
8. Passing final answer becomes positive only with receipt.

## Tokenization loop

1. Store exact human text.
2. Store normalized/corrected text as sidecar.
3. Tokenize with byte fallback.
4. Attach source/provenance tags per span.
5. Attach conlang/opcode/code-face labels when known.
6. Unknown recurring chunks go to Rosetta review queue.
7. Approved chunks become lexicon entries.

## Release gate

A feature is not "done" until it emits:

- Lesson schema instance.
- Runtime receipt.
- Trace JSONL row.
- UI route or CLI command.
- Failure example proving it blocks a bad action.
