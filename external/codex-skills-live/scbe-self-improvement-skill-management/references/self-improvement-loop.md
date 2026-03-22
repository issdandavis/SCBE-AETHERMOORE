# Self-Improvement Loop

## Trigger Examples

Use this loop when users ask for:

- "Create a skill for this workflow"
- "Update the SCBE skill"
- "Document this so we can reuse it"
- "Teach this to another AI system"
- "Turn this repeated process into a skill"

## Loop

1. Build capability in real work.
2. Capture implementation notes and outcomes.
3. Extract repeatable patterns.
4. Create or update skill.
5. Validate and test with realistic prompts.
6. Reuse skill in next task and iterate.

## New Skill Checklist

1. Confirm at least one create condition is satisfied.
2. Select `scbe-{domain}-{function}` name.
3. Initialize with `init_skill.py`.
4. Add concise `SKILL.md` instructions.
5. Move deep detail to `references/`.
6. Add output templates to `assets/` as needed.
7. Validate with `quick_validate.py`.
8. Run 2-3 test prompts.
9. Request explicit install approval.

## Update Checklist

1. Read current skill end-to-end.
2. Identify exact section(s) to modify.
3. Draft minimal diff.
4. Run dimensional analysis for formula/constant changes.
5. Present diff and ask approval.
6. Apply update and validate.
