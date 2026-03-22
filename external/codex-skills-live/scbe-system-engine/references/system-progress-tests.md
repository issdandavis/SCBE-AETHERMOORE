# Real System Progress Tests

Use these when you want the skill to prove actual progress instead of returning a generic plan.

## Test 1 — PQCM Audit + HF Route

Run:
- `python scripts/pqcm_audit.py --max-n 12`
- produce/update dataset card metadata for `scbe-pqcm-audit-log`
- create/update `references/scbe-pqcm-audit-log.md` as the dataset card artifact.
- write verdict to Notion page `PQCM κ_eff Audit — Feb 2026`
- patch `references/dimensional-analysis.md` with the observed O(N^N) scaling issue.

Success condition:
- output explicitly states the scaling risk.
- a concrete patch file exists for the dimensional-analysis reference.
- `action_summary` includes `tests_added_or_run`, `specs_or_cards_updated`.

## Test 2 — KO Reviewer + Chain Wiring

Run:
- `python scripts/ko_tongue_code_reviewer.py` to validate mock diff output.
- generate `scripts/route_github_linear_chain.yaml` and verify typed steps (`tool`, `llm`, `gate`).
- check available Zapier/Linear actions before promising run automation.

Success condition:
- mock reviewer returns a valid `AgentOutput` object.
- chain contains explicit branch to PR comment and Linear issue for failures.
- `action_summary.route.services_to_update` includes GitHub, Linear, Zapier, Notion.

## Test 3 — End-to-End Health Gap + Child Skill Draft

Run:
- search (or mock search if unavailable) for `@scbe/aethermoore`, `issdav...`, and SCBE entries.
- identify one concrete missing integration point and draft one sub-skill `SKILL.md` under 200 lines.
- include two executable prompts in the draft to prove the new skill is testable.

Success condition:
- prompt 2 and generated output both reference the parent skill (`scbe-system-engine`) glossary/constants.
- route leg identifies exact follow-up service updates.
