---
title: Source Roots Are Anti-Drift Infrastructure
tags: [ai, docs, architecture, governance]
series: SCBE Research Notes
---
# Source Roots Are Anti-Drift Infrastructure

**By Issac Davis** | April 1, 2026

---

## Abstract

One of the quietest failure modes in AI-assisted development is context drift. A system is real, the code exists, the docs exist, and yet the assistant starts talking as if major parts of the stack are speculative. The fix is not only better prompting. The fix is a grounded re-anchor document that tells the operator exactly where the source-of-truth lives. In SCBE, `docs/map-room/scbe_source_roots.md` is starting to play that role.

## Drift is an orientation problem

When an assistant drifts, the failure usually looks like reasoning. It sounds like uncertainty about tokenizer design, geometry, training architecture, or which documents count as canon. But the deeper problem is retrieval posture. The system does not begin from a stable root map, so every explanation becomes vulnerable to whatever partial context happened to survive the last few turns.

The Source Roots note states the problem in plain language. It says the file should be used as the first re-anchor point when a session starts drifting or when partial context makes established SCBE components sound speculative. That is the right framing because it treats drift as something operational, not mystical.

## What a real root map does

The value of the file is not just that it is a list of links. It groups the system by job:

- canon roots
- Sacred Tongues and tokenizer roots
- seed and identity roots
- geometry and projection roots
- embedding and training flow roots
- matching code roots

That structure changes how an agent or operator asks questions. Instead of asking “does this system have geometry docs,” the operator can route immediately into the geometry root set. Instead of vaguely remembering that Sacred Eggs exist somewhere, the operator gets the exact identity root path. The result is less theatrical confidence and more direct retrieval.

## Why the missing-file notes matter

One of the best parts of `scbe_source_roots.md` is that it does not pretend the orientation layer is complete. It explicitly says `references/repo-map.md` is missing and `references/runtime-entrypoints.md` is missing. Then it says the Source Roots file is the temporary replacement orientation anchor until a proper repo map is authored.

That is a healthy move.

A lot of system docs fail because they try to sound complete. This file does the opposite. It names the missing artifacts, narrows its own role, and still gives the operator a usable re-entry point. That is better documentation because it lowers false confidence.

## Why this matters for agentic systems

The more agentic the workflow becomes, the more important explicit root maps get.

If one lane is drafting an article, another lane is checking training flow, and a third lane is validating geometry, all three need a shared answer to a simple question: where do we look first before we explain anything?

Without that, each lane invents its own canon. One assistant uses a mirrored note, another uses an archive file, and a third cites an implementation path without checking whether the design doc disagrees. The result is not only slower. It becomes impossible to tell whether disagreement is intellectual or just navigational.

The Source Roots document gives the system a better baseline. It says:

- this is where canon starts
- this is where tokenizer roots live
- this is where geometry lives
- this is where matching code lives
- this is what is still missing

That is operationally valuable because it lets the system recover from context loss without having to rebuild the repo map from scratch every time.

## Why this is training-relevant

There is also a training implication here. A root map is not just a human convenience. It is a candidate substrate for grounded retrieval and future action maps. If the operator path is stable enough, it becomes easier to generate better training rows because the system can pair:

- question type
- root category
- canonical document
- matching code path
- next action

That is the difference between “assistant remembers a repo” and “assistant follows a repeatable orientation protocol.”

## Implemented versus next

Implemented now:

- a grounded root map for canon, tokenizer, geometry, training, and implementation paths
- explicit job grouping instead of a flat file dump
- explicit acknowledgment of missing repo-orientation artifacts

Next:

- a stricter component-to-job-to-state table
- a runtime entrypoint map
- tighter coupling between root maps, MCP discovery, and operator command selection

The point is not that a single markdown file solves agent drift. The point is that real anti-drift infrastructure starts small, explicit, and grounded.

## Sources

- `docs/map-room/scbe_source_roots.md`
- `docs/specs/BINARY_FIRST_TRAINING_STACK.md`
- `docs/01-architecture/sacred-eggs-systems-model.md`
- `mcp/scbe-server/README.md`
