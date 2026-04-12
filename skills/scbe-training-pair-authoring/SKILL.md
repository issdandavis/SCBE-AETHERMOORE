---
name: scbe-training-pair-authoring
description: Create prompt and response and metadata training pairs from SCBE documents, repair traces, terminal sessions, and operational workflows using the repository's canonical dataset contract and provenance rules.
---

# SCBE Training Pair Authoring

Use this skill when real SCBE work needs to become reusable supervised fine-tuning data instead of staying trapped in prose, logs, or one-off operator notes.

## When to Use

- User asks to create training pairs from a document, trace, transcript, or workflow
- A repair sequence produced a stable method worth teaching to future agents
- A system tutorial needs to become question and answer supervision
- A repeated operator workflow needs a dedicated dataset slice
- A new recurring data-authoring workflow justifies a new skill or skill update

## Workflow

1. Read `AGENTS.md`.
2. Read `training-data/README.md`.
3. Inspect one or more existing dataset files in the target config, especially `training-data/architecture_sessions/*.jsonl` when the material is system or operations knowledge.
4. Read the source material that will be converted.
5. Extract stable operator questions from real behavior, not imagined examples.
6. Write answers from what was actually fixed, verified, or learned.
7. Store each example in canonical JSON Lines format with `prompt`, `response`, and `metadata`.
8. Add extra top-level fields only when the target dataset already uses them consistently, such as `event_type`.
9. Keep provenance in `metadata` so later curation can trace every pair back to a source file, session, or repair trace.
10. If the workflow itself is now repeatable and missing from the skill library, create or update a skill before closing the task.

## Canonical Dataset Rules

- The stable contract is `prompt`, `response`, and `metadata`.
- Use `training-data/architecture_sessions/` for system architecture, operational guidance, repair traces, governance workflows, and tooling procedures.
- Prefer one concrete lesson per pair.
- Keep prompts phrased as real user or operator questions.
- Keep responses instructional, specific, and traceable to the source material.
- Prefer fully spelled names in prompt and response text when a readable expansion exists. Keep canonical identifiers such as skill names, file paths, and system keys unchanged.

## Metadata Rules

Include enough metadata to make filtering and later evaluation possible. Prefer fields like:

- `topic`
- `domain`
- `source_type`
- `source_trace`
- `skills`
- `quality`
- `validated`

If the source file uses an additional convention, follow that local pattern rather than inventing a competing schema.

## Quality Bar

- Do not fabricate runtime evidence.
- Do not convert temporary confusion into canonical guidance unless the final repair is clear.
- Do not collapse multiple distinct fixes into one vague answer.
- Prefer verified operational sequences over abstract summaries.
- If a trace includes an error, include the repair path and the final verified state.

## Good Targets

- Obsidian vault sync repairs
- documentation authority cleanup
- model training run interpretation
- connector health diagnosis
- shell workflow corrections
- data pipeline repair notes
- browser or automation operating procedures

## Avoid These Mistakes

- Do not write generic teaching content disconnected from the actual trace.
- Do not omit the final successful behavior.
- Do not bury the relevant skill names or file paths when they matter operationally.
- Do not move system operations knowledge into a lore or game dataset config.

## References

- `training-data/README.md`
- `training-data/architecture_sessions/scbe_architecture.jsonl`
- `skills/scbe-spin-conversation-engine/SKILL.md`
