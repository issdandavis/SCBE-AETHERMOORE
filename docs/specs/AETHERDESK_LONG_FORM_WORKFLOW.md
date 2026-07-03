# AetherDesk Long-Form Workflow

Date: 2026-06-27
Status: draft v1
Scope: overnight work, multi-hour engineering, research, release prep, and agent handoff

## Purpose

Long-form AetherDesk work needs to continue from user intent without becoming uncontrolled automation. The workflow below gives agents a durable run manifest, a task queue, stop rules, receipts, and product handoff.

This is the local product version of the "keep working, make lists, and continue when I am asleep" instruction.

## Run manifest

Each long-form run should have:

```yaml
goal: "Make AetherDesk browser feel like a real product."
scope:
  - "Local docs/specs"
  - "AetherDesk UI files"
  - "SCBE training data prep"
in_scope_files:
  - "C:/Users/issda/AetherDesk/react-desktop/src/main.jsx"
  - "C:/Users/issda/AetherDesk/react-desktop/src/styles.css"
  - "C:/Users/issda/SCBE-AETHERMOORE/docs/product"
  - "C:/Users/issda/SCBE-AETHERMOORE/docs/specs"
out_of_scope_files:
  - "paid HF jobs"
  - "package publishing"
  - "destructive cleanup"
success_criteria:
  - "A future agent can resume from a task list."
  - "Product surfaces have specs before deeper implementation."
  - "No hidden paid jobs or repeated polling."
stop_criteria:
  - "Need token, password, payment, or human approval."
  - "Need build/test validation not explicitly approved."
  - "Risk of deleting, publishing, or overwriting user work."
```

## Phase model

| Phase | Purpose | Output |
|---|---|---|
| `capture` | Convert chat fragments into tasks. | Backlog, queue, assumptions. |
| `stabilize` | Fix obvious local blockers and dangerous ambiguity. | Small local patches or specs. |
| `improve` | Add product value without heavy machine use. | UI polish, docs, schemas, training prep. |
| `evaluate` | Only when approved, run builds/tests/evals. | Metrics and receipts. |
| `handoff` | Save current state for next agent/human. | Summary, changed files, next actions. |

## Sleeping-user mode

When the user says they are going to bed:

- Continue only on local, low-risk, reversible work.
- Prefer docs, specs, task lists, training data prep, and small UI patches.
- Do not run paid cloud jobs.
- Do not publish packages.
- Do not delete or move user files.
- Do not repeatedly poll long-running jobs.
- Do not claim validation unless it was explicitly run.
- Keep a visible queue of what was done, what is next, and what is approval-blocked.

## Work item shape

```yaml
id: AD-003
title: "Define local skill manifest schema"
lane: "product"
risk: "low"
machine_cost: "light"
status: "done"
files:
  - "docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md"
approval_required: false
receipt:
  - "docs/product-manual/AUTOLOG.jsonl"
next:
  - "Turn schema into app-side catalog JSON."
```

## Browser product workflow

The browser should support a repeatable product loop:

1. Human selects a skill or writes a question.
2. AetherDesk creates a browser action packet.
3. Browser shows the planned lane: answer, browse, audit, or agent.
4. Human approves risky actions if needed.
5. AI executes the smallest safe action.
6. Browser displays answer, sources, skipped checks, and receipt.
7. Long-form workflow either stops or appends a next task.

## Release workflow

Before npm/PyPI/GitHub release:

1. Build a local release manifest.
2. Confirm package versions and target repos.
3. Confirm no secrets in browser/client bundles.
4. Run builds/tests only after explicit approval.
5. Publish only after explicit approval.
6. Write a release receipt with commands and artifact paths.

## Training workflow

For trained-agent integration:

1. Collect local product examples from browser, terminal, and task queue use.
2. Add human-authored open-source guides when license-compatible.
3. Convert examples into SFT JSONL.
4. Maintain holdout tasks for browser boundary behavior.
5. Evaluate local model first where practical.
6. Use paid remote GPU only after explicit approval.

## Checkpoint format

Append checkpoint entries to the active queue:

```markdown
## Checkpoint - 2026-06-27

Done:
- AD-003 Skill manifest schema created.

Blocked:
- AD-B01 Build validation, needs explicit approval.

Next:
- AD-004 Convert manifest schema into app-side catalog JSON.
```

## Reliability report contract

When a run ends, the final report should include:

```yaml
action_summary:
  build:
    changed_runtime: true
    validation_run: false
    validation_note: "Not run by instruction."
  document:
    specs_created:
      - "AETHERDESK_SKILL_MANIFEST_SCHEMA.md"
      - "AETHERDESK_BROWSER_ACTION_PACKET.md"
      - "AETHERDESK_LONG_FORM_WORKFLOW.md"
  route:
    next_unattended: "AD-004 Convert manifests into local catalog JSON."
    approval_blocked:
      - "Build validation"
      - "Training run"
      - "Package publishing"
```

## Near-term backlog

Local and light:

- Convert the hardcoded skill cards into `skills/catalog.json`.
- Add browser preset handoff from skill cards.
- Add local receipts for browser actions.
- Draft Browser Audit, Deep Research, Secure Code Review, and Long-Form Workflow manifests.
- Extend browser-use training data with negative examples.

Approval-blocked:

- Run AetherDesk build.
- Run Playwright smoke.
- Launch training.
- Run HF jobs.
- Publish npm/PyPI packages.

