---
name: scbe-self-improvement-skill-management
description: Run the SCBE self-improvement loop by documenting completed work, creating new skills, updating existing skills, and propagating SCBE knowledge to other AI systems via context documents and structured knowledge files. Use when users ask to create/update skills, formalize repeated SCBE workflows, enforce skill approval gates, generate transfer prompts for Claude/Gemini/custom agents, or publish SCBE knowledge artifacts to Hugging Face datasets.
---

# SCBE Self-Improvement & Skill Management

Use this skill to keep SCBE capabilities compounding through a disciplined loop:
build something -> document it -> extract patterns -> create/update skill -> reuse it in the next build.

## Core Rules

1. Enforce explicit approval before installing any new skill.
2. Keep `SKILL.md` concise (target under 500 lines); move depth into `references/`.
3. Prefer overtriggering to undertriggering in skill descriptions.
4. Run dimensional analysis before changing canonical math constants or formulas.
5. Keep stable naming: `scbe-{domain}-{function}`.

## Workflow Decision

Choose one path:

- New skill creation
- Existing skill update
- Knowledge propagation to another AI system

If the user intent is mixed, split output by path and make each path explicit.

## New Skill Creation

Create a new skill when one of these holds:

- Workflow repeated 3+ times across conversations
- New SCBE component stabilized (tests passing, spec written)
- User explicitly asks for a new skill
- Cross-service integration pattern validated

Procedure:

1. Name skill as `scbe-{domain}-{function}`.
2. Initialize with `init_skill.py`.
3. Write trigger-rich description (what it does + when to invoke).
4. Keep core workflow in `SKILL.md`; move deep material to `references/`.
5. Add templates/assets needed for reuse.
6. Validate with `quick_validate.py`.
7. Test with 2-3 realistic prompts.
8. Present approval gate summary and wait for explicit approval before install.

## Existing Skill Update

Update when:

- Canonical constant changes (rare; dimensional analysis required first)
- New layer/component added
- Workflow step changed
- Glossary expanded
- Instruction bug discovered

Procedure:

1. Read current skill fully.
2. Identify exact sections to change.
3. Draft minimal diff.
4. Run dimensional analysis if math/constants are touched.
5. Present diff for user approval.
6. Apply and validate.

## Approval Gate (Mandatory)

Never install a new or updated skill without explicit user approval.

Before installation, present:

1. What the skill does (one sentence)
2. Trigger phrases/contexts
3. Files included
4. New dependencies (if any)

Wait for: `yes`, `approved`, or equivalent.

## Knowledge Propagation

When user asks to teach/update another AI:

1. Identify target AI and role.
2. Scope relevant layers/components/constants.
3. Generate transfer docs using templates in `assets/`.
4. Keep constants exact unless user explicitly asks for revision.
5. Optionally prepare Hugging Face dataset packaging.

Use:

- `assets/context-template.md`
- `assets/scbe-knowledge-v4.yaml`
- `assets/action-summary.template.yaml`
- `references/knowledge-propagation.md`
- `references/external-identity-research.md` (for handle/name/repo disambiguation; treat as verification-first input)

## Skill Composition

Prefer reuse/composition over creating redundant skills.

Contract:
`Skill A output -> action_summary.yaml -> Skill B input`

Use `assets/action-summary.template.yaml` for the handoff schema.

## Memory Guidance

Persist only stable, validated information and only with user approval.

Persist:
- Canonical terms
- Workflow preferences
- Naming conventions
- Milestones

Do not persist:
- Temporary debugging state
- One-off experiments
- Unapproved drafts
