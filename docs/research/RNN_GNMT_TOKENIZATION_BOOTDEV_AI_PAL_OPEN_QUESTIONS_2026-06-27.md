# Open Questions - AetherDesk Academy / AI Pal

Date: 2026-06-27

## Product checks

1. Decide whether this lives inside existing AetherDesk or as a separate `apps/aetherdesk-academy` package.
2. Choose first three lessons: Python basics, SCBE conlang macro, and browser-use task are the strongest trio.
3. Decide if the AI Pal starts rule-based only or uses the local model from day one.
4. Decide storage budget for traces: recommended default is compact JSONL plus file hashes, not full file snapshots forever.

## Research checks

1. Verify whether the user meant Claude Artifacts, Claude Code, Claude Cowork, Claude Tag, or an unofficial "Claude Pal" feature.
2. Compare Boot.dev lesson structure by using the actual demo interactively later; current notes are based on public pages and CLI README.
3. Decide tokenizer baseline: byte-level BPE vs SentencePiece unigram vs SCBE hybrid sidecar tokenizer.
4. Decide if conlang/opcode tokens become primary vocabulary tokens or sidecar labels first. Recommendation: sidecar labels first.

## Engineering checks

1. Locate the current AetherDesk app entrypoint before implementation.
2. Reuse existing bounded shell profiles for lesson execution.
3. Add schemas before UI so traces stay stable.
4. Add a one-command receipt runner for lessons before any model training.

## Safety checks

1. AI Pal must not run arbitrary commands; only lesson-defined allowlisted commands.
2. Patches must be user-accepted unless the lesson explicitly permits autonomous repair.
3. Browser/computer-use style actions must stay in sandboxed lesson worlds first.
4. Failed AI outputs must be labeled as failures, never blended into positive SFT data without verifier labels.
