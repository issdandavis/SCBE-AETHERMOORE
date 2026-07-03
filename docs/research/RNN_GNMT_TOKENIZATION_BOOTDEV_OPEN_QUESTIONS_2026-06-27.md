# RNN/GNMT/Tokenization/Boot.dev Open Questions

Date: 2026-06-27

## Research gaps

1. What did the user mean by "Claude Pal" or "clade pal"? I found no reliable primary source for that exact name. Closest documented patterns are Claude Artifacts, Claude Code, Claude tool use, and Claude for Chrome.
2. Should SCBE train a custom tokenizer first, or start with a deterministic token table for conlang/opcode words and use BPE only for natural-language fields?
3. Should `surface_text` always remain byte-exact, including typos and spacing, while `canonical_text` carries likely correction?
4. How much mentor help should be allowed before a row stops counting as a clean human-solved training example?
5. Should the first app run code locally through existing SCBE/AetherDesk bounded shell lanes, or use an in-browser sandbox for the first prototype?
6. Should game mechanics be XP/streaks/quests, or SCBE-native receipts/ranks/gates to avoid making the product feel like a copy of Boot.dev?
7. Which language comes first for the runnable trainer: Python only, Python plus Rust, or Python plus JavaScript for browser immediacy?
8. What is the minimum useful semi-token experiment: draft two future conlang/opcode tokens, speculative compile candidate IR, or train a tiny multi-token prediction head?
9. What local schema should admit a completed lesson into training: one JSONL row per attempt, one row per verified final solution, or both with different provenance tags?
10. How do we prevent the AI mentor from turning into answer-copying instead of learning support?

## Build questions

First vertical slice:

```text
CA add lesson
  -> user writes conlang/operator input
  -> tokenizer binds to opcode
  -> compiler emits Python
  -> test runner verifies
  -> mentor asks one hint
  -> receipt captures binds_to / emits_to / executed_on
```

Decisions needed:

1. App location: new `apps/scbe-forge` or inside existing `aetherdesk`.
2. Runtime: local Python subprocess through an allowlisted profile, or browser-only Pyodide-style execution.
3. Data store: JSONL files first, SQLite later.
4. UI: compact three-pane trainer, not a landing page.
5. Training capture: default off until the user marks a lesson row as admitted.

## Honest claim boundary

Allowed claim:

```text
SCBE Forge is inspired by coding-practice platforms and Claude-style coding assistants. It runs local verified lessons and captures provenance-rich training receipts.
```

Blocked claim:

```text
SCBE is an exact Boot.dev clone, a replacement for Boot.dev's content, or proof that semi-token retro thought is a new model architecture.
```

Better claim:

```text
SCBE implements a verified coding-trainer loop with conlang token receipts, mentor chat, tests, and optional training capture.
```
