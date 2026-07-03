# AetherDesk Academy MVP Spec

Date: 2026-06-27
Status: Draft MVP spec from RNN/GNMT/tokenization/Boot.dev/AI-pal research

## Product intent

AetherDesk Academy is a local-first coding dojo inside AetherDesk. It combines a Boot.dev-like lesson map, a bounded code runner, an AI Pal sidecar, SCBE compiler/conlang lanes, and receipt-based training traces.

This is not a Boot.dev copy. The reusable pattern is: structured path -> interactive lesson -> code attempt -> tests -> mentor hint/patch -> receipt -> progress/training trace.

## Core loop

1. Learner opens a lesson from the map.
2. Lesson loads starter files and objectives.
3. Learner edits code in the workspace.
4. Runtime runs only the lesson-defined allowlisted command.
5. Runtime emits a receipt with hashes, exit code, stdout/stderr tails, duration, and verdict.
6. AI Pal can inspect the receipt and respond in a selected mode.
7. Trace writer records compact training data.
8. Passing receipts unlock progress; failed receipts become labeled repair data.

## Surfaces

- `academy-web`: map, lesson view, editor, terminal/test output, AI Pal panel.
- `academy-runtime`: bounded runner for lesson commands.
- `academy-pal`: mentor sidecar with policy modes.
- `academy-cli`: submitter/receipt/trace commands.
- `academy-traces`: JSONL training trace writer.
- `academy-rosetta`: queue for unknown tokens/conlang chunks.

## AI Pal modes

- `socratic`: asks one targeted question; no code patch.
- `explain`: explains compiler/test output in plain language.
- `inspect`: reads lesson files and receipts; no edits.
- `patch`: proposes minimal diff; requires user acceptance unless lesson allows autonomous repair.
- `run`: invokes only lesson-defined allowlisted command.
- `reflect`: writes a compact success/failure reflection into the trace.

## Tokenization and provenance

Every training row stores exact surface text plus sidecars:

- normalized/corrected text, preserving human typos.
- byte spans and token IDs.
- provenance tags: human, AI, source, research, tool, compiler, test, verified, unverified.
- code face: python, js, rust, go, scbe, conlang, binary, etc.
- compile/test receipt pointer.
- source URL or local file path when applicable.

Unknown chunks use byte fallback first. Repeated useful chunks enter Rosetta review and can become approved lexicon entries.

## First three lessons

1. `py.return.001`: make a function return a string.
2. `scbe.conlang.add.001`: conlang sentence -> opcode -> Python/Rust receipt.
3. `browser.form.001`: use a sandboxed browser tab to fill a local form and assert DOM output.

## Runtime rule

No arbitrary shell. Every lesson declares exact allowed commands. The runner refuses commands outside the lesson policy.

## Training rule

A passing answer is only positive training data if it has a receipt. Failed attempts are useful, but they stay labeled as failed/repair examples.

## Release gate

A lesson feature is not complete until it has:

- a valid lesson JSON object.
- a runtime receipt.
- a trace JSONL row.
- one passing example.
- one blocked/failing example.
- an AI Pal response generated from the receipt, not from hidden assumptions.

## Research basis

- RNN/GNMT: sequence-to-sequence translation, attention alignment, production constraints.
- Tokenization: subword and byte fallback, with SCBE provenance sidecars.
- Semi-token prediction: speculative/multi-candidate drafting accepted only by verifier.
- Retro-thought: external attempt -> feedback -> reflection -> repair trace.
- Product pattern: Boot.dev-style lesson map and CLI, with original content/branding.
- AI sidecar pattern: Artifacts/Claude Code/computer-use style surfaces, bounded for safety.
