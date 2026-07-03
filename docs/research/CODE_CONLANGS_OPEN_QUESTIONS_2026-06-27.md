# Code Conlangs Open Questions

Date: 2026-06-27

## Source/licensing questions

- Which language docs are license-compatible for direct training ingestion?
- Which sources should be summarized into training pairs rather than quoted or copied?
- Which interpreter repos have permissive licenses versus GPL or unknown terms?

## SCBE design questions

- Should SCBE's conlang target browser actions, code generation, GeoSeal packets, or all three through separate profiles?
- Should the first runtime be an interpreter, a TypeScript transpiler, or a JSON action-packet compiler?
- What minimum VM is enough: stack machine, register machine, event/action graph, or AST-to-host-code?

## Eval questions

- Can `scbe-coder` learn a new tiny conlang from documentation and interpreter feedback?
- Does conlang training improve structured action JSON without regressing bare-code output?
- Should the holdout include Brainfuck/Whitespace-style low-level tasks, or browser-action packet tasks that are closer to AetherDesk?

## Practical next checks

1. Build a tiny SCBE browser-action conlang spec.
2. Write an interpreter that only emits safe JSON action plans.
3. Add 10 human-authored open-source guide-derived examples after license review.
4. Test base vs tuned model on held-out conlang tasks.
5. Only then consider a local training run.

## Added SCBE-specific research lanes

- Tokenizers: compare BPE-style tokenization, grammar tokenization, and reversible fixed-token maps for six-tongue SCBE inputs.
- Compilers: prototype source -> AST -> typed IR -> verified JSON action packet before any host execution.
- Binary mapping: preserve byte/hex receipts as transport evidence, not semantic explanation.
- Music/piano mapping: map bytes, token classes, and control flow to pitch/rhythm/chord annotations as an inspection layer.
- Training: keep human-authored open-source guide data separate from synthetic SCBE route examples so each effect can be measured.
